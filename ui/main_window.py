"""Main application window for Dedutto."""
import os
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional

from core.amortization import AmortizationTracker
from core.backup import BackupManager
from core.classifier import ExpenseClassifier
from core.database import Database
from core.llm_adapter import LLMAdapter
from core.ocr import OCRProcessor
from core.report import ReportGenerator
from core.status_tracker import StatusTracker
from ui import theme
from ui.dialogs import ManualEntryDialog, OCRPreviewDialog, SettingsDialog
from utils.logging import get_logger

log = get_logger(__name__)


def _strings(lang: str = "it") -> Dict:
    if lang == "en":
        from ui.lang.en import STRINGS
    else:
        from ui.lang.it import STRINGS
    return STRINGS


class MainWindow:
    """Main application window."""

    def __init__(self, root: tk.Tk, db: Database):
        self.root = root
        self.db = db
        self.lang = db.get_setting("language", "it")
        self.s = _strings(self.lang)
        self.ocr = OCRProcessor()
        self.report_gen = ReportGenerator(db)
        self.backup_mgr = BackupManager(db)
        self.amort = AmortizationTracker(db)
        self.status = StatusTracker(db)
        self.status.register_callback(self._refresh_status_bar)
        self._classifier: Optional[ExpenseClassifier] = None
        self._selected_expense_id: Optional[int] = None

        theme.apply_theme(root)
        self._build_ui()
        self._refresh_all()
        root.after(2000, self._check_upcoming_deadlines)

    # ------------------------------------------------------------------ #
    # UI Construction                                                      #
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        self.root.title(self.s["app_title"])
        self.root.geometry("1200x750")
        self.root.minsize(900, 600)

        self._build_menu()
        self._build_main_layout()
        self._build_status_bar()

    def _build_menu(self):
        s = self.s
        menubar = tk.Menu(self.root, bg=theme.BG_SECONDARY, fg=theme.TEXT_PRIMARY,
                          activebackground=theme.ACCENT, activeforeground=theme.TEXT_PRIMARY)

        file_menu = tk.Menu(menubar, tearoff=0, bg=theme.BG_SECONDARY, fg=theme.TEXT_PRIMARY,
                            activebackground=theme.ACCENT, activeforeground=theme.TEXT_PRIMARY)
        file_menu.add_command(label=s["menu_import"], command=self._import_document)
        file_menu.add_command(label=s["menu_export_pdf"], command=self._export_pdf)
        file_menu.add_separator()
        file_menu.add_command(label=s["menu_backup"], command=self._export_backup)
        file_menu.add_command(label=s["menu_restore"], command=self._import_backup)
        file_menu.add_separator()
        file_menu.add_command(label=s["menu_quit"], command=self.root.quit)

        edit_menu = tk.Menu(menubar, tearoff=0, bg=theme.BG_SECONDARY, fg=theme.TEXT_PRIMARY,
                            activebackground=theme.ACCENT, activeforeground=theme.TEXT_PRIMARY)
        edit_menu.add_command(label=s["menu_settings"], command=self._open_settings)

        menubar.add_cascade(label=s["menu_file"], menu=file_menu)
        menubar.add_cascade(label=s["menu_edit"], menu=edit_menu)
        menubar.add_command(label=s["menu_about"], command=self._show_about)
        self.root.config(menu=menubar)

    def _build_main_layout(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=0, pady=0)

        self._build_dashboard_tab()
        self._build_expenses_tab()
        self._build_amortization_tab()
        self._build_reports_tab()
        self._build_deadlines_tab()

    def _build_status_bar(self):
        bar = ttk.Frame(self.root, style="TFrame")
        bar.pack(fill="x", side="bottom")
        ttk.Separator(bar, orient="horizontal").pack(fill="x")

        inner = ttk.Frame(bar)
        inner.pack(fill="x", padx=theme.PAD_SM, pady=2)

        self._status_expenses = ttk.Label(inner, text="", style="Status.TLabel")
        self._status_expenses.pack(side="left")

        ttk.Label(inner, text=" | ", style="Status.TLabel").pack(side="left")

        self._status_pending = ttk.Label(inner, text="", style="Status.TLabel")
        self._status_pending.pack(side="left")

        ttk.Label(inner, text=" | ", style="Status.TLabel").pack(side="left")

        self._status_sync = ttk.Label(inner, text="", style="Status.TLabel")
        self._status_sync.pack(side="left")

        self._status_right = ttk.Label(inner, text="Dedutto v1.0", style="Status.TLabel")
        self._status_right.pack(side="right")

    # ------------------------------------------------------------------ #
    # Dashboard Tab                                                        #
    # ------------------------------------------------------------------ #

    def _build_dashboard_tab(self):
        s = self.s
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=s["tab_dashboard"])

        canvas = tk.Canvas(frame, bg=theme.BG_PRIMARY, highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self._dash_inner = ttk.Frame(canvas)
        canvas_win = canvas.create_window((0, 0), window=self._dash_inner, anchor="nw")

        def _on_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(canvas_win, width=canvas.winfo_width())

        self._dash_inner.bind("<Configure>", _on_configure)
        canvas.bind("<Configure>", _on_configure)

        self._build_drop_zone(self._dash_inner)

        self._stat_frame = ttk.Frame(self._dash_inner)
        self._stat_frame.pack(fill="x", padx=theme.PAD_LG, pady=theme.PAD_SM)
        self._stat_cards: Dict[str, ttk.Label] = {}
        card_defs = [
            ("total", s["dashboard_total_expenses"], "€0.00"),
            ("deductible", s["dashboard_deductible"], "€0.00"),
            ("vat", s["dashboard_vat_credit"], "€0.00"),
            ("pending", s["dashboard_pending"], "0"),
        ]
        for i, (key, label, default) in enumerate(card_defs):
            self._stat_frame.columnconfigure(i, weight=1)
            card = ttk.Frame(self._stat_frame, style="Card.TFrame", padding=theme.PAD_MD)
            card.grid(row=0, column=i, padx=6, sticky="nsew")
            ttk.Label(card, text=label, style="CardLabel.TLabel").pack()
            val_lbl = ttk.Label(card, text=default, style="CardValue.TLabel")
            val_lbl.pack()
            self._stat_cards[key] = val_lbl

        self._dash_chart_frame = ttk.LabelFrame(
            self._dash_inner, text=s["dashboard_monthly_chart"], padding=theme.PAD_SM
        )
        self._dash_chart_frame.pack(fill="both", expand=True, padx=theme.PAD_LG, pady=theme.PAD_SM)
        self._chart_canvas_label = ttk.Label(
            self._dash_chart_frame, text="Caricamento grafico...", style="Subtitle.TLabel"
        )
        self._chart_canvas_label.pack(pady=theme.PAD_XL)

    def _build_drop_zone(self, parent):
        s = self.s
        drop_frame = ttk.LabelFrame(parent, text="Importa Documento", padding=theme.PAD_SM)
        drop_frame.pack(fill="x", padx=theme.PAD_LG, pady=theme.PAD_SM)

        self._drop_canvas = tk.Canvas(
            drop_frame, height=100, bg=theme.BG_SECONDARY,
            highlightthickness=2, highlightbackground=theme.ACCENT,
            cursor="hand2",
        )
        self._drop_canvas.pack(fill="x", padx=4, pady=4)

        self._drop_text_id = self._drop_canvas.create_text(
            400, 38, text=s["drop_zone_text"],
            font=theme.FONT_MEDIUM, fill=theme.TEXT_PRIMARY,
        )
        self._drop_hint_id = self._drop_canvas.create_text(
            400, 72, text=s["drop_zone_hint"],
            font=theme.FONT_SMALL, fill=theme.TEXT_SECONDARY,
        )

        self._drop_canvas.bind("<Button-1>", lambda e: self._import_document())
        self._drop_canvas.bind("<Enter>", self._drop_enter)
        self._drop_canvas.bind("<Leave>", self._drop_leave)

        try:
            self._drop_canvas.drop_target_register("DND_Files")  # type: ignore
            self._drop_canvas.dnd_bind("<<Drop>>", self._on_file_drop)  # type: ignore
        except Exception:
            pass

    def _drop_enter(self, _event):
        self._drop_canvas.configure(highlightbackground=theme.ACCENT_HOVER)

    def _drop_leave(self, _event):
        self._drop_canvas.configure(highlightbackground=theme.ACCENT)

    def _on_file_drop(self, event):
        path = event.data.strip().strip("{}")
        if path:
            self._process_file(path)

    # ------------------------------------------------------------------ #
    # Expenses Tab                                                         #
    # ------------------------------------------------------------------ #

    def _build_expenses_tab(self):
        s = self.s
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=s["tab_expenses"])

        toolbar = ttk.Frame(frame)
        toolbar.pack(fill="x", padx=theme.PAD_SM, pady=theme.PAD_SM)

        ttk.Button(toolbar, text=f"+ {s['btn_add']}",
                   command=self._add_expense_manual).pack(side="left", padx=3)
        ttk.Button(toolbar, text=s["btn_edit"],
                   command=self._edit_expense).pack(side="left", padx=3)
        ttk.Button(toolbar, text=s["btn_delete"], style="Danger.TButton",
                   command=self._delete_expense).pack(side="left", padx=3)
        ttk.Button(toolbar, text=s["btn_classify"], style="Accent.TButton",
                   command=self._classify_selected).pack(side="left", padx=3)
        ttk.Button(toolbar, text=s["btn_classify_all"],
                   command=self._classify_all).pack(side="left", padx=3)

        ttk.Label(toolbar, text="🔍").pack(side="right", padx=(0, 3))
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *a: self._refresh_expense_list())
        ttk.Entry(toolbar, textvariable=self._search_var, width=20).pack(side="right", padx=3)

        ttk.Label(toolbar, text="Anno:").pack(side="right", padx=(0, 3))
        self._year_filter = tk.StringVar(value=str(datetime.now().year))
        years = [str(y) for y in range(datetime.now().year, datetime.now().year - 6, -1)]
        years.insert(0, "Tutti")
        year_combo = ttk.Combobox(toolbar, textvariable=self._year_filter,
                                  values=years, state="readonly", width=8)
        year_combo.pack(side="right", padx=3)
        year_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_expense_list())

        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill="both", expand=True, padx=theme.PAD_SM, pady=0)

        columns = ("date", "vendor", "description", "amount", "vat",
                   "category", "deductibility", "confidence")
        col_labels = [
            s["col_date"], s["col_vendor"], s["col_description"],
            s["col_amount"], s["col_vat"], s["col_category"],
            s["col_deductibility"], s["col_confidence"],
        ]
        col_widths = [90, 150, 200, 90, 70, 120, 120, 80]

        self._expense_tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings", selectmode="browse"
        )
        for col, label, width in zip(columns, col_labels, col_widths):
            self._expense_tree.heading(col, text=label,
                                       command=lambda c=col: self._sort_by(c))
            self._expense_tree.column(col, width=width, minwidth=60)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._expense_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self._expense_tree.xview)
        self._expense_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._expense_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        self._expense_tree.bind("<<TreeviewSelect>>", self._on_expense_select)
        self._expense_tree.bind("<Double-1>", lambda e: self._edit_expense())
        self._expense_tree.tag_configure("even", background=theme.ROW_EVEN)
        self._expense_tree.tag_configure("odd", background=theme.ROW_ODD)
        self._expense_tree.tag_configure("pending", foreground=theme.WARNING)

        self._sort_col = "date"
        self._sort_asc = False

    def _sort_by(self, col: str):
        if self._sort_col == col:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col = col
            self._sort_asc = True
        self._refresh_expense_list()

    # ------------------------------------------------------------------ #
    # Amortization Tab                                                     #
    # ------------------------------------------------------------------ #

    def _build_amortization_tab(self):
        s = self.s
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=s["tab_amortization"])

        ttk.Label(frame, text=s["tab_amortization"], style="Title.TLabel").pack(
            pady=theme.PAD_MD, padx=theme.PAD_LG, anchor="w"
        )

        self._amort_tree = ttk.Treeview(
            frame,
            columns=("vendor", "date", "amount", "years", "annual", "remaining"),
            show="headings",
        )
        headers = ["Fornitore", "Data Acquisto", "Importo", "Anni", "Quota Annua", "Valore Residuo"]
        widths = [150, 100, 100, 60, 100, 120]
        for col, hdr, w in zip(self._amort_tree["columns"], headers, widths):
            self._amort_tree.heading(col, text=hdr)
            self._amort_tree.column(col, width=w)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self._amort_tree.yview)
        self._amort_tree.configure(yscrollcommand=vsb.set)
        self._amort_tree.pack(side="left", fill="both", expand=True, padx=theme.PAD_SM)
        vsb.pack(side="right", fill="y")

        self._amort_alert_frame = ttk.LabelFrame(
            frame, text="Avvisi Ammortamento", padding=theme.PAD_SM
        )
        self._amort_alert_frame.pack(fill="x", padx=theme.PAD_SM, pady=theme.PAD_SM, side="bottom")

    # ------------------------------------------------------------------ #
    # Reports Tab                                                          #
    # ------------------------------------------------------------------ #

    def _build_reports_tab(self):
        s = self.s
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=s["tab_reports"])

        ttk.Label(frame, text=s["tab_reports"], style="Title.TLabel").pack(
            pady=theme.PAD_MD, padx=theme.PAD_LG, anchor="w"
        )

        opts = ttk.LabelFrame(frame, text="Opzioni Report", padding=theme.PAD_MD)
        opts.pack(fill="x", padx=theme.PAD_LG, pady=theme.PAD_SM)
        opts.columnconfigure(1, weight=1)

        ttk.Label(opts, text="Anno:").grid(row=0, column=0, padx=theme.PAD_SM, pady=4, sticky="w")
        self._report_year = tk.StringVar(value=str(datetime.now().year))
        years = [str(y) for y in range(datetime.now().year, datetime.now().year - 6, -1)]
        ttk.Combobox(opts, textvariable=self._report_year,
                     values=years, state="readonly", width=10).grid(row=0, column=1, sticky="w", padx=4)

        ttk.Button(
            frame, text=s["btn_generate_report"], style="Accent.TButton",
            command=self._generate_pdf_report,
        ).pack(pady=theme.PAD_MD)

        self._report_status = ttk.Label(frame, text="", style="Subtitle.TLabel")
        self._report_status.pack()

        self._report_preview = ttk.LabelFrame(frame, text="Anteprima Dati", padding=theme.PAD_SM)
        self._report_preview.pack(fill="both", expand=True, padx=theme.PAD_LG, pady=theme.PAD_SM)
        self._report_text = tk.Text(
            self._report_preview, bg=theme.BG_TERTIARY, fg=theme.TEXT_PRIMARY,
            font=theme.FONT_MONO, state="disabled", wrap="word",
        )
        self._report_text.pack(fill="both", expand=True)

    # ------------------------------------------------------------------ #
    # Deadlines Tab                                                        #
    # ------------------------------------------------------------------ #

    def _build_deadlines_tab(self):
        s = self.s
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=s["tab_deadlines"])

        ttk.Label(frame, text=s["tab_deadlines"], style="Title.TLabel").pack(
            pady=theme.PAD_MD, padx=theme.PAD_LG, anchor="w"
        )

        filter_frame = ttk.Frame(frame)
        filter_frame.pack(fill="x", padx=theme.PAD_LG, pady=(0, theme.PAD_SM))
        ttk.Label(filter_frame, text="Anno:").pack(side="left")
        self._deadline_year = tk.StringVar(value=str(datetime.now().year))
        years = [str(y) for y in range(datetime.now().year, datetime.now().year + 3)]
        year_cb = ttk.Combobox(filter_frame, textvariable=self._deadline_year,
                                values=years, state="readonly", width=8)
        year_cb.pack(side="left", padx=6)
        year_cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_deadlines())

        self._deadline_tree = ttk.Treeview(
            frame,
            columns=("name", "date", "description", "status"),
            show="headings",
        )
        for col, hdr, w in zip(
            ("name", "date", "description", "status"),
            ["Scadenza", "Data", "Descrizione", "Stato"],
            [200, 100, 300, 80],
        ):
            self._deadline_tree.heading(col, text=hdr)
            self._deadline_tree.column(col, width=w)

        self._deadline_tree.tag_configure("past", foreground=theme.TEXT_SECONDARY)
        self._deadline_tree.tag_configure("upcoming", foreground=theme.WARNING)
        self._deadline_tree.tag_configure("future", foreground=theme.TEXT_PRIMARY)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self._deadline_tree.yview)
        self._deadline_tree.configure(yscrollcommand=vsb.set)
        self._deadline_tree.pack(side="left", fill="both", expand=True, padx=theme.PAD_SM)
        vsb.pack(side="right", fill="y")

    # ------------------------------------------------------------------ #
    # Data Refresh                                                         #
    # ------------------------------------------------------------------ #

    def _refresh_all(self):
        self._refresh_dashboard()
        self._refresh_expense_list()
        self._refresh_amortization()
        self._refresh_deadlines()
        self._refresh_report_preview()
        self._refresh_status_bar()

    def _refresh_status_bar(self):
        status = self.status.get_status()
        self._status_expenses.configure(
            text=self.s["status_expenses"].format(status["total_expenses"])
        )
        pending = status["pending_classifications"]
        self._status_pending.configure(
            text=self.s["status_pending"].format(pending),
            foreground=theme.WARNING if pending > 0 else theme.TEXT_SECONDARY,
        )
        self._status_sync.configure(
            text=self.s["status_last_sync"].format(status["last_update"])
        )

    def _refresh_dashboard(self):
        try:
            year = datetime.now().year
            totals = self.db.expense_totals(year)
            pending = self.db.count_pending()

            self._stat_cards["total"].configure(text=f"€ {totals['total']:,.2f}")
            self._stat_cards["deductible"].configure(text=f"€ {totals['deductible']:,.2f}")
            self._stat_cards["vat"].configure(text=f"€ {totals['vat_total']:,.2f}")
            self._stat_cards["pending"].configure(
                text=str(pending),
                foreground=theme.WARNING if pending > 0 else theme.ACCENT,
            )
            self.root.after(100, self._refresh_dashboard_chart)
        except Exception as exc:
            log.error("Dashboard refresh error: %s", exc)

    def _refresh_dashboard_chart(self):
        try:
            import io
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from PIL import Image, ImageTk

            year = datetime.now().year
            monthly = self.db.monthly_totals(year)
            months_it = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
                         "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
            totals_m = [0.0] * 12
            for row in monthly:
                totals_m[int(row["month"]) - 1] = row["total"]

            fig, ax = plt.subplots(figsize=(9, 3.5))
            fig.patch.set_facecolor(theme.BG_SECONDARY)
            ax.set_facecolor(theme.BG_SECONDARY)
            ax.bar(months_it, totals_m, color=theme.ACCENT,
                   edgecolor=theme.BG_PRIMARY, linewidth=0.5)
            ax.set_title(f"Spese Mensili {year}", color=theme.TEXT_PRIMARY, fontsize=12)
            ax.tick_params(colors=theme.TEXT_SECONDARY, labelsize=9)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_color(theme.BORDER)
            ax.spines["bottom"].set_color(theme.BORDER)

            buf = io.BytesIO()
            plt.savefig(buf, format="png", dpi=110, bbox_inches="tight",
                        facecolor=theme.BG_SECONDARY)
            plt.close(fig)
            buf.seek(0)

            img = Image.open(buf)
            self._chart_img = ImageTk.PhotoImage(img)

            for widget in self._dash_chart_frame.winfo_children():
                widget.destroy()
            ttk.Label(self._dash_chart_frame, image=self._chart_img).pack()
        except Exception as exc:
            log.debug("Chart render error: %s", exc)

    def _refresh_expense_list(self):
        for row in self._expense_tree.get_children():
            self._expense_tree.delete(row)

        year_str = self._year_filter.get()
        year = int(year_str) if year_str.isdigit() else None
        search = self._search_var.get().strip() or None
        order = f"{self._sort_col} {'ASC' if self._sort_asc else 'DESC'}"

        try:
            expenses = self.db.list_expenses(year=year, search=search, order_by=order)
        except Exception as exc:
            log.error("List expenses error: %s", exc)
            return

        s = self.s
        deduct_labels = {
            "full": s["deduct_full"],
            "partial": s["deduct_partial"],
            "amortizable": s["deduct_amortizable"],
            "none": s["deduct_none"],
            "": "—",
        }
        for i, exp in enumerate(expenses):
            conf = exp.get("classification_confidence", 0) or 0
            ded = exp.get("deductibility_type", "") or ""
            tag = "even" if i % 2 == 0 else "odd"
            if not ded or conf == 0:
                tag = "pending"

            self._expense_tree.insert(
                "", "end",
                iid=str(exp["id"]),
                values=(
                    exp.get("date", "")[:10],
                    exp.get("vendor", ""),
                    (exp.get("description") or "")[:40],
                    f"€ {exp.get('amount', 0):,.2f}",
                    f"€ {exp.get('vat_amount', 0):,.2f}" if exp.get("vat_amount") else "—",
                    exp.get("category", "") or "—",
                    deduct_labels.get(ded, ded),
                    f"{conf:.0f}%" if conf else "—",
                ),
                tags=(tag,),
            )

    def _refresh_amortization(self):
        for row in self._amort_tree.get_children():
            self._amort_tree.delete(row)

        try:
            year = datetime.now().year
            data = self.amort.get_all_amortizable()
            for item in data:
                exp = item["expense"]
                schedule = item["schedule"]
                annual = 0.0
                for entry in schedule:
                    if entry["year"] == year:
                        annual = entry["amount"]
                        break
                self._amort_tree.insert(
                    "", "end",
                    values=(
                        exp.get("vendor", ""),
                        exp.get("date", "")[:10],
                        f"€ {exp.get('amount', 0):,.2f}",
                        exp.get("amortization_years", 0),
                        f"€ {annual:,.2f}",
                        f"€ {item['remaining']:,.2f}",
                    ),
                )

            for w in self._amort_alert_frame.winfo_children():
                w.destroy()
            alerts = self.amort.missing_amortization_alerts()
            for alert in alerts:
                ttk.Label(
                    self._amort_alert_frame,
                    text=f"⚠ {alert['message']}",
                    foreground=theme.WARNING,
                    wraplength=700,
                ).pack(anchor="w", pady=2)
            if not alerts:
                ttk.Label(self._amort_alert_frame, text="Nessun avviso.",
                          style="Subtitle.TLabel").pack()
        except Exception as exc:
            log.error("Amortization refresh error: %s", exc)

    def _refresh_deadlines(self):
        for row in self._deadline_tree.get_children():
            self._deadline_tree.delete(row)
        try:
            year_str = self._deadline_year.get()
            year = int(year_str) if year_str.isdigit() else None
            deadlines = self.db.get_deadlines(year)
            today = datetime.now().date().isoformat()
            thirty_days = datetime.now().date()
            import datetime as dt
            cutoff = (datetime.now().date() + dt.timedelta(days=30)).isoformat()
            for dl in deadlines:
                date = dl["deadline_date"]
                if date < today:
                    tag = "past"
                    status_str = "✓ Passata"
                elif date <= cutoff:
                    tag = "upcoming"
                    status_str = "⚠ Imminente"
                else:
                    tag = "future"
                    status_str = "📅 Futura"
                self._deadline_tree.insert(
                    "", "end",
                    values=(dl["name"], date, dl.get("description", ""), status_str),
                    tags=(tag,),
                )
        except Exception as exc:
            log.error("Deadlines refresh error: %s", exc)

    def _refresh_report_preview(self):
        try:
            year = datetime.now().year
            totals = self.db.expense_totals(year)
            cats = self.db.category_totals(year)
            lines = [
                f"=== Riepilogo Spese {year} ===",
                f"Totale: € {totals['total']:,.2f}",
                f"Deducibile: € {totals['deductible']:,.2f}",
                f"IVA recuperabile: € {totals['vat_total']:,.2f}",
                f"Risparmio stimato (23%): € {totals['deductible'] * 0.23:,.2f}",
                "",
                "--- Per categoria ---",
            ]
            for cat in cats:
                lines.append(f"  {cat['category'] or 'N/D'}: € {cat['total']:,.2f} ({cat['count']} spese)")

            self._report_text.configure(state="normal")
            self._report_text.delete("1.0", "end")
            self._report_text.insert("1.0", "\n".join(lines))
            self._report_text.configure(state="disabled")
        except Exception as exc:
            log.error("Report preview error: %s", exc)

    # ------------------------------------------------------------------ #
    # Expense Actions                                                      #
    # ------------------------------------------------------------------ #

    def _on_expense_select(self, _event=None):
        sel = self._expense_tree.selection()
        self._selected_expense_id = int(sel[0]) if sel else None

    def _add_expense_manual(self):
        dlg = ManualEntryDialog(self.root, lang=self.lang)
        self.root.wait_window(dlg)
        if dlg.result:
            try:
                self.db.add_expense(dlg.result)
                self.status.expense_added()
                self._refresh_all()
            except Exception as exc:
                messagebox.showerror(self.s["error_title"], str(exc))

    def _edit_expense(self):
        if not self._selected_expense_id:
            messagebox.showinfo("", "Seleziona una spesa da modificare.")
            return
        existing = self.db.get_expense(self._selected_expense_id)
        dlg = ManualEntryDialog(self.root, lang=self.lang, existing=existing)
        self.root.wait_window(dlg)
        if dlg.result:
            try:
                self.db.update_expense(self._selected_expense_id, dlg.result)
                self.status.mark_updated()
                self._refresh_all()
            except Exception as exc:
                messagebox.showerror(self.s["error_title"], str(exc))

    def _delete_expense(self):
        if not self._selected_expense_id:
            messagebox.showinfo("", "Seleziona una spesa da eliminare.")
            return
        if messagebox.askyesno(self.s["confirm_delete_title"], self.s["confirm_delete"]):
            try:
                self.db.delete_expense(self._selected_expense_id)
                self._selected_expense_id = None
                self.status.expense_deleted()
                self._refresh_all()
            except Exception as exc:
                messagebox.showerror(self.s["error_title"], str(exc))

    def _classify_selected(self):
        if not self._selected_expense_id:
            messagebox.showinfo("", "Seleziona una spesa da classificare.")
            return
        self._do_classify([self._selected_expense_id])

    def _classify_all(self):
        try:
            pending = self.db.list_expenses()
            ids = [e["id"] for e in pending if not e.get("deductibility_type")]
            if not ids:
                messagebox.showinfo("", "Nessuna spesa da classificare.")
                return
            self._do_classify(ids)
        except Exception as exc:
            messagebox.showerror(self.s["error_title"], str(exc))

    def _do_classify(self, expense_ids: List[int]):
        classifier = self._get_classifier()
        if not classifier:
            return

        def worker():
            for exp_id in expense_ids:
                exp = self.db.get_expense(exp_id)
                if not exp:
                    continue
                try:
                    result = classifier.classify(
                        exp.get("vendor", ""),
                        exp.get("description", ""),
                        exp.get("amount", 0),
                        exp.get("vat_amount", 0),
                    )
                    self.db.update_expense(exp_id, {
                        "category": result["category"],
                        "deductibility_type": result["deductibility_type"],
                        "amortization_years": result["amortization_years"],
                        "vat_regime": result["vat_regime"],
                        "classification_confidence": result["confidence"],
                        "llm_provider": classifier.llm.provider,
                    })
                    if result["deductibility_type"] == "amortizable":
                        self.amort.compute_schedule(
                            expense_id=exp_id,
                            amount=exp["amount"],
                            purchase_date=exp["date"],
                            asset_type=result["category"],
                            custom_years=result["amortization_years"],
                        )
                except Exception as exc:
                    log.error("Classification error for expense %d: %s", exp_id, exc)

            self.root.after(0, lambda: (self.status.classification_done(), self._refresh_all()))

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        messagebox.showinfo("", self.s["llm_classifying"])

    def _get_classifier(self) -> Optional[ExpenseClassifier]:
        settings = self.db.get_all_settings()
        api_key = settings.get("llm_api_key", "")
        if not api_key:
            messagebox.showerror(self.s["error_title"], self.s["error_api_key"])
            return None
        try:
            llm = LLMAdapter(
                provider=settings.get("llm_provider", "openai"),
                api_key=api_key,
                model=settings.get("llm_model") or None,
                base_url=settings.get("llm_endpoint") or None,
                timeout=int(settings.get("llm_timeout", 60)),
            )
            return ExpenseClassifier(llm, self.db)
        except Exception as exc:
            messagebox.showerror(self.s["error_title"], str(exc))
            return None

    # ------------------------------------------------------------------ #
    # File Import / OCR                                                    #
    # ------------------------------------------------------------------ #

    def _import_document(self):
        path = filedialog.askopenfilename(
            title="Importa Documento",
            filetypes=[
                ("Documenti supportati", "*.pdf *.png *.jpg *.jpeg"),
                ("PDF", "*.pdf"),
                ("Immagini", "*.png *.jpg *.jpeg"),
                ("Tutti", "*.*"),
            ],
        )
        if path:
            self._process_file(path)

    def _process_file(self, path: str):
        ext = Path(path).suffix.lower()
        if ext not in {".pdf", ".png", ".jpg", ".jpeg"}:
            messagebox.showerror(self.s["error_title"], self.s["error_file_type"])
            return

        if not self.ocr.is_available():
            messagebox.showwarning(
                "OCR non disponibile",
                self.s["error_tesseract"] + "\n\nInserimento manuale.",
            )
            self._add_expense_manual()
            return

        def worker():
            try:
                ocr_result = self.ocr.process_file(path)
                self.root.after(0, lambda: self._show_ocr_preview(ocr_result))
            except Exception as exc:
                log.error("OCR failed: %s", exc)
                self.root.after(0, lambda: (
                    messagebox.showerror(self.s["error_title"], f"OCR: {exc}"),
                    self._add_expense_manual(),
                ))

        threading.Thread(target=worker, daemon=True).start()

    def _show_ocr_preview(self, ocr_result):
        dlg = OCRPreviewDialog(self.root, ocr_result, lang=self.lang)
        self.root.wait_window(dlg)
        if dlg.result:
            try:
                self.db.add_expense(dlg.result)
                self.status.expense_added()
                self._refresh_all()
            except Exception as exc:
                messagebox.showerror(self.s["error_title"], str(exc))

    # ------------------------------------------------------------------ #
    # Reports / Backup                                                     #
    # ------------------------------------------------------------------ #

    def _export_pdf(self):
        self._generate_pdf_report()

    def _generate_pdf_report(self):
        if not self.report_gen.is_available():
            messagebox.showerror(
                self.s["error_title"],
                "ReportLab non installato. Eseguire: pip install reportlab",
            )
            return

        year_str = self._report_year.get()
        year = int(year_str) if year_str.isdigit() else datetime.now().year

        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile=f"dedutto_report_{year}.pdf",
            filetypes=[("PDF", "*.pdf")],
        )
        if not path:
            return

        def worker():
            try:
                self.report_gen.generate(path, year=year)
                self.root.after(0, lambda: (
                    self._report_status.configure(
                        text=self.s["success_report"].format(path),
                        foreground=theme.ACCENT,
                    ),
                    messagebox.showinfo("", self.s["success_report"].format(path)),
                ))
            except Exception as exc:
                log.error("PDF generation error: %s", exc)
                self.root.after(0, lambda: messagebox.showerror(
                    self.s["error_title"], self.s["error_pdf"].format(exc)
                ))

        threading.Thread(target=worker, daemon=True).start()
        self._report_status.configure(text="Generazione in corso...", foreground=theme.WARNING)

    def _export_backup(self):
        from ui.dialogs import PasswordDialog
        password = PasswordDialog.ask(self.root, is_new=False, lang=self.lang)
        if not password:
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".dedutto",
            initialfile=f"dedutto_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.dedutto",
            filetypes=[("Dedutto Backup", "*.dedutto"), ("Tutti", "*.*")],
        )
        if not path:
            return

        try:
            self.backup_mgr.export_backup(path, password)
            messagebox.showinfo("", self.s["success_backup"].format(path))
        except Exception as exc:
            messagebox.showerror(self.s["error_title"], str(exc))

    def _import_backup(self):
        path = filedialog.askopenfilename(
            filetypes=[("Dedutto Backup", "*.dedutto"), ("Tutti", "*.*")]
        )
        if not path:
            return

        from ui.dialogs import PasswordDialog
        password = PasswordDialog.ask(self.root, is_new=False, lang=self.lang)
        if not password:
            return

        try:
            count = self.backup_mgr.import_backup(path, password)
            messagebox.showinfo("", f"{self.s['success_restore']} ({count} spese ripristinate)")
            self.status.mark_updated()
            self._refresh_all()
        except Exception as exc:
            messagebox.showerror(self.s["error_title"], str(exc))

    # ------------------------------------------------------------------ #
    # Settings / About                                                     #
    # ------------------------------------------------------------------ #

    def _open_settings(self):
        SettingsDialog(self.root, self.db, lang=self.lang, on_save=self._on_settings_saved)

    def _on_settings_saved(self):
        self.lang = self.db.get_setting("language", "it")
        self.s = _strings(self.lang)
        self._refresh_all()

    def _show_about(self):
        messagebox.showinfo(self.s["about_title"], self.s["about_text"])

    def _check_upcoming_deadlines(self):
        try:
            upcoming = self.db.get_upcoming_deadlines(days=30)
            if upcoming:
                names = "\n".join(f"• {d['name']} ({d['deadline_date']})" for d in upcoming[:3])
                messagebox.showinfo(
                    "Scadenze Fiscali Imminenti",
                    f"Hai {len(upcoming)} scadenza/e entro 30 giorni:\n\n{names}",
                )
        except Exception:
            pass
