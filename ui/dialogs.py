"""Dialogs for Dedutto: settings, manual entry, OCR preview, password."""
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable, Dict, Optional

from core.llm_adapter import PROVIDERS, LLMAdapter
from ui import theme
from utils.validators import validate_amount, validate_date


def _get_strings(lang: str = "it") -> Dict[str, str]:
    if lang == "en":
        from ui.lang.en import STRINGS
    else:
        from ui.lang.it import STRINGS
    return STRINGS


class PasswordDialog(tk.Toplevel):
    """Prompt the user for a master password."""

    def __init__(self, parent, is_new: bool = False, lang: str = "it"):
        super().__init__(parent)
        self.strings = _get_strings(lang)
        self.result: Optional[str] = None
        self.is_new = is_new

        self.title(self.strings["password_title"])
        self.resizable(False, False)
        self.configure(bg=theme.BG_PRIMARY)
        self.grab_set()
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.after(100, self._center)

    def _center(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"+{x}+{y}")

    def _build(self):
        s = self.strings
        pad = {"padx": theme.PAD_LG, "pady": theme.PAD_SM}

        ttk.Label(self, text="Dedutto", style="Title.TLabel").pack(**pad)
        ttk.Label(
            self,
            text=s["password_new"] if self.is_new else s["password_prompt"],
            style="Subtitle.TLabel",
            wraplength=320,
        ).pack(**pad)

        self._pw_var = tk.StringVar()
        pw_entry = ttk.Entry(self, textvariable=self._pw_var, show="•", width=30)
        pw_entry.pack(**pad)
        pw_entry.focus_set()
        pw_entry.bind("<Return>", lambda e: self._confirm())

        if self.is_new:
            ttk.Label(self, text=s["password_confirm"]).pack(**pad)
            self._pw2_var = tk.StringVar()
            pw2_entry = ttk.Entry(self, textvariable=self._pw2_var, show="•", width=30)
            pw2_entry.pack(**pad)
            pw2_entry.bind("<Return>", lambda e: self._confirm())

        btn_frame = ttk.Frame(self)
        btn_frame.pack(**pad)
        ttk.Button(btn_frame, text=s["btn_ok"], style="Accent.TButton",
                   command=self._confirm).pack(side="left", padx=4)
        ttk.Button(btn_frame, text=s["btn_cancel"],
                   command=self._cancel).pack(side="left", padx=4)

    def _confirm(self):
        pw = self._pw_var.get()
        if len(pw) < 8:
            messagebox.showerror(
                self.strings["error_title"],
                self.strings["password_weak"],
                parent=self,
            )
            return
        if self.is_new:
            pw2 = self._pw2_var.get()
            if pw != pw2:
                messagebox.showerror(
                    self.strings["error_title"],
                    self.strings["password_mismatch"],
                    parent=self,
                )
                return
        self.result = pw
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()

    @classmethod
    def ask(cls, parent, is_new: bool = False, lang: str = "it") -> Optional[str]:
        dlg = cls(parent, is_new=is_new, lang=lang)
        parent.wait_window(dlg)
        return dlg.result


class ManualEntryDialog(tk.Toplevel):
    """Dialog for manual expense entry or editing."""

    def __init__(self, parent, lang: str = "it", existing: Optional[Dict] = None):
        super().__init__(parent)
        self.strings = _get_strings(lang)
        self.result: Optional[Dict] = None
        self.existing = existing or {}

        self.title(self.strings["manual_title"])
        self.resizable(False, False)
        self.configure(bg=theme.BG_PRIMARY)
        self.grab_set()
        self._build()
        self._load_existing()
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.after(100, self._center)

    def _center(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"+{x}+{y}")

    def _build(self):
        s = self.strings
        pad = {"padx": theme.PAD_MD, "pady": 4, "sticky": "ew"}

        frame = ttk.Frame(self, padding=theme.PAD_MD)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        fields = [
            ("manual_vendor", "vendor"),
            ("manual_date", "date"),
            ("manual_amount", "amount"),
            ("manual_vat", "vat_amount"),
            ("manual_description", "description"),
            ("manual_notes", "notes"),
        ]

        self._vars: Dict[str, tk.StringVar] = {}
        for row, (label_key, field) in enumerate(fields):
            ttk.Label(frame, text=s[label_key]).grid(row=row, column=0, **pad)
            var = tk.StringVar()
            self._vars[field] = var
            ttk.Entry(frame, textvariable=var, width=30).grid(row=row, column=1, **pad)

        # Category dropdown
        cat_row = len(fields)
        ttk.Label(frame, text=s["manual_category"]).grid(row=cat_row, column=0, **pad)
        cat_keys = [
            "cat_software", "cat_hosting", "cat_hardware", "cat_office",
            "cat_training", "cat_insurance", "cat_accounting", "cat_bank",
            "cat_advertising", "cat_internet", "cat_transport", "cat_utilities",
            "cat_food", "cat_travel", "cat_other", "cat_personal", "cat_fines",
        ]
        self._cat_var = tk.StringVar()
        cat_values = [s[k] for k in cat_keys]
        self._cat_map = {s[k]: k.replace("cat_", "") for k in cat_keys}
        cat_combo = ttk.Combobox(frame, textvariable=self._cat_var,
                                 values=cat_values, state="readonly", width=28)
        cat_combo.grid(row=cat_row, column=1, **pad)

        # Deductibility
        ded_row = cat_row + 1
        ttk.Label(frame, text=s["col_deductibility"]).grid(row=ded_row, column=0, **pad)
        self._ded_var = tk.StringVar()
        ded_values = [s["deduct_full"], s["deduct_partial"],
                      s["deduct_amortizable"], s["deduct_none"]]
        self._ded_map = {
            s["deduct_full"]: "full", s["deduct_partial"]: "partial",
            s["deduct_amortizable"]: "amortizable", s["deduct_none"]: "none",
        }
        ttk.Combobox(frame, textvariable=self._ded_var,
                     values=ded_values, state="readonly", width=28).grid(
            row=ded_row, column=1, **pad)

        # Buttons
        btn_row = ded_row + 1
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=btn_row, column=0, columnspan=2, pady=theme.PAD_MD)
        ttk.Button(btn_frame, text=s["btn_save"], style="Accent.TButton",
                   command=self._save).pack(side="left", padx=6)
        ttk.Button(btn_frame, text=s["btn_cancel"],
                   command=self._cancel).pack(side="left", padx=6)

    def _load_existing(self):
        if not self.existing:
            # Default date to today
            self._vars["date"].set(datetime.now().strftime("%d/%m/%Y"))
            return
        for field, var in self._vars.items():
            val = self.existing.get(field, "")
            if val is not None:
                var.set(str(val))

    def _save(self):
        s = self.strings
        vendor = self._vars["vendor"].get().strip()
        date_str = self._vars["date"].get().strip()
        amount_str = self._vars["amount"].get().strip()

        if not vendor:
            messagebox.showerror(s["error_title"], "Fornitore obbligatorio", parent=self)
            return
        if not date_str:
            messagebox.showerror(s["error_title"], "Data obbligatoria", parent=self)
            return

        parsed_date = validate_date(date_str)
        if not parsed_date:
            messagebox.showerror(s["error_title"], "Formato data non valido (gg/mm/aaaa)", parent=self)
            return

        amount = validate_amount(amount_str)
        if amount is None:
            messagebox.showerror(s["error_title"], "Importo non valido", parent=self)
            return

        vat = validate_amount(self._vars["vat_amount"].get()) or 0.0
        cat_label = self._cat_var.get()
        cat = self._cat_map.get(cat_label, "other")
        ded_label = self._ded_var.get()
        ded = self._ded_map.get(ded_label, "")

        self.result = {
            "vendor": vendor,
            "date": parsed_date.strftime("%Y-%m-%d"),
            "amount": amount,
            "vat_amount": vat,
            "description": self._vars["description"].get().strip(),
            "notes": self._vars["notes"].get().strip(),
            "category": cat,
            "deductibility_type": ded,
        }
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


class OCRPreviewDialog(tk.Toplevel):
    """Preview and confirm OCR-extracted expense data."""

    def __init__(self, parent, ocr_result, lang: str = "it"):
        super().__init__(parent)
        self.strings = _get_strings(lang)
        self.result: Optional[Dict] = None
        self.ocr_result = ocr_result

        self.title(self.strings["ocr_preview_title"])
        self.configure(bg=theme.BG_PRIMARY)
        self.grab_set()
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.after(100, self._center)

    def _center(self):
        self.update_idletasks()
        w = max(self.winfo_width(), 600)
        h = self.winfo_height()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        s = self.strings
        ocr = self.ocr_result

        main = ttk.Frame(self, padding=theme.PAD_MD)
        main.pack(fill="both", expand=True)
        main.columnconfigure(1, weight=1)

        conf = getattr(ocr, "confidence", 0)
        conf_color = theme.ACCENT if conf >= 70 else theme.WARNING
        conf_label = ttk.Label(
            main,
            text=s["ocr_low_confidence"].format(conf) if conf < 70 else s["ocr_complete"],
            foreground=conf_color,
            font=theme.FONT_MEDIUM,
        )
        conf_label.grid(row=0, column=0, columnspan=2, pady=(0, theme.PAD_SM), sticky="w")

        # Editable fields pre-filled from OCR
        pad = {"padx": theme.PAD_SM, "pady": 3, "sticky": "ew"}
        self._vars: Dict[str, tk.StringVar] = {}

        date_val = ocr.date or datetime.now().strftime("%Y-%m-%d")
        fields = [
            (s["manual_vendor"], "vendor", ocr.vendor or ""),
            (s["manual_date"], "date", date_val),
            (s["manual_amount"], "amount", f"{ocr.amount:.2f}" if ocr.amount else ""),
            (s["manual_vat"], "vat_amount", f"{ocr.vat_amount:.2f}" if ocr.vat_amount else ""),
            (s["manual_description"], "description", ocr.description or ""),
        ]

        for row, (label, field, default) in enumerate(fields, start=1):
            ttk.Label(main, text=label).grid(row=row, column=0, **pad)
            var = tk.StringVar(value=default)
            self._vars[field] = var
            ttk.Entry(main, textvariable=var, width=35).grid(row=row, column=1, **pad)

        # Raw OCR text
        raw_row = len(fields) + 1
        ttk.Label(main, text="Testo OCR grezzo:").grid(row=raw_row, column=0, sticky="nw", **pad)
        raw_frame = ttk.Frame(main)
        raw_frame.grid(row=raw_row, column=1, **pad, sticky="nsew")
        raw_text = tk.Text(raw_frame, height=8, width=40, bg=theme.BG_TERTIARY,
                           fg=theme.TEXT_SECONDARY, font=theme.FONT_MONO,
                           wrap="word", state="normal")
        scrollbar = ttk.Scrollbar(raw_frame, command=raw_text.yview)
        raw_text.configure(yscrollcommand=scrollbar.set)
        raw_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        raw_text.insert("1.0", ocr.raw_text or "")
        raw_text.configure(state="disabled")

        # Buttons
        btn_frame = ttk.Frame(main)
        btn_frame.grid(row=raw_row + 1, column=0, columnspan=2, pady=theme.PAD_MD)
        ttk.Button(btn_frame, text=s["ocr_confirm"], style="Accent.TButton",
                   command=self._confirm).pack(side="left", padx=6)
        ttk.Button(btn_frame, text=s["btn_cancel"],
                   command=self._cancel).pack(side="left", padx=6)

    def _confirm(self):
        date_str = self._vars["date"].get().strip()
        parsed = validate_date(date_str)
        amount = validate_amount(self._vars["amount"].get()) or 0.0
        vat = validate_amount(self._vars["vat_amount"].get()) or 0.0

        self.result = {
            "vendor": self._vars["vendor"].get().strip(),
            "date": parsed.strftime("%Y-%m-%d") if parsed else date_str,
            "amount": amount,
            "vat_amount": vat,
            "description": self._vars["description"].get().strip(),
        }
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


class SettingsDialog(tk.Toplevel):
    """Application settings: LLM provider, API key, model, language."""

    def __init__(self, parent, db, lang: str = "it", on_save: Optional[Callable] = None):
        super().__init__(parent)
        self.strings = _get_strings(lang)
        self.db = db
        self.on_save = on_save
        self._lang = lang

        self.title(self.strings["settings_title"])
        self.configure(bg=theme.BG_PRIMARY)
        self.grab_set()
        self._build()
        self._load_settings()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.after(100, self._center)

    def _center(self):
        self.update_idletasks()
        w = max(self.winfo_width(), 520)
        h = self.winfo_height()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        s = self.strings
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=theme.PAD_MD, pady=theme.PAD_MD)

        # LLM Tab
        llm_frame = ttk.Frame(nb, padding=theme.PAD_MD)
        nb.add(llm_frame, text=s["settings_llm"])
        llm_frame.columnconfigure(1, weight=1)
        self._build_llm_tab(llm_frame)

        # General Tab
        gen_frame = ttk.Frame(nb, padding=theme.PAD_MD)
        nb.add(gen_frame, text="Generale")
        self._build_general_tab(gen_frame)

        # Save button
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=theme.PAD_MD)
        ttk.Button(btn_frame, text=s["settings_save"], style="Accent.TButton",
                   command=self._save).pack(side="left", padx=6)
        ttk.Button(btn_frame, text=s["btn_cancel"],
                   command=self.destroy).pack(side="left", padx=6)

    def _build_llm_tab(self, frame):
        s = self.strings
        pad = {"padx": theme.PAD_SM, "pady": 5, "sticky": "ew"}

        ttk.Label(frame, text=s["settings_provider"]).grid(row=0, column=0, **pad)
        self._provider_var = tk.StringVar()
        provider_combo = ttk.Combobox(
            frame, textvariable=self._provider_var,
            values=list(PROVIDERS.keys()), state="readonly", width=20
        )
        provider_combo.grid(row=0, column=1, **pad)
        provider_combo.bind("<<ComboboxSelected>>", self._on_provider_change)

        ttk.Label(frame, text=s["settings_api_key"]).grid(row=1, column=0, **pad)
        self._api_key_var = tk.StringVar()
        api_entry = ttk.Entry(frame, textvariable=self._api_key_var, show="•", width=35)
        api_entry.grid(row=1, column=1, **pad)

        # Show/hide toggle
        self._show_key = tk.BooleanVar()
        def toggle_key():
            api_entry.configure(show="" if self._show_key.get() else "•")
        ttk.Checkbutton(frame, text="Mostra", variable=self._show_key,
                        command=toggle_key).grid(row=1, column=2, padx=4)

        ttk.Label(frame, text=s["settings_model"]).grid(row=2, column=0, **pad)
        self._model_var = tk.StringVar()
        self._model_combo = ttk.Combobox(frame, textvariable=self._model_var, width=30)
        self._model_combo.grid(row=2, column=1, **pad)

        ttk.Label(frame, text=s["settings_custom_endpoint"]).grid(row=3, column=0, **pad)
        self._endpoint_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self._endpoint_var, width=35).grid(row=3, column=1, **pad)

        ttk.Label(frame, text=s["settings_timeout"]).grid(row=4, column=0, **pad)
        self._timeout_var = tk.StringVar(value="60")
        ttk.Entry(frame, textvariable=self._timeout_var, width=10).grid(row=4, column=1, **pad)

        ttk.Label(frame, text="⚠ La chiave API non viene mai inviata a server terzi.",
                  foreground=theme.WARNING).grid(
            row=5, column=0, columnspan=3, pady=(theme.PAD_MD, 0), sticky="w"
        )

    def _build_general_tab(self, frame):
        s = self.strings
        pad = {"padx": theme.PAD_SM, "pady": 5, "sticky": "ew"}
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text=s["settings_language"]).grid(row=0, column=0, **pad)
        self._lang_var = tk.StringVar()
        ttk.Combobox(frame, textvariable=self._lang_var,
                     values=["it", "en"], state="readonly", width=10).grid(row=0, column=1, **pad)

        ttk.Label(frame, text="Anno fiscale corrente").grid(row=1, column=0, **pad)
        self._year_var = tk.StringVar(value=str(datetime.now().year))
        ttk.Entry(frame, textvariable=self._year_var, width=10).grid(row=1, column=1, **pad)

    def _on_provider_change(self, _event=None):
        provider = self._provider_var.get()
        models = LLMAdapter.models_for_provider(provider)
        self._model_combo["values"] = models
        if models:
            default = LLMAdapter.default_model_for_provider(provider)
            self._model_var.set(default)

    def _load_settings(self):
        if not self.db:
            return
        all_settings = self.db.get_all_settings()
        provider = all_settings.get("llm_provider", "openai")
        self._provider_var.set(provider)
        self._on_provider_change()
        self._api_key_var.set(all_settings.get("llm_api_key", ""))
        model = all_settings.get("llm_model", LLMAdapter.default_model_for_provider(provider))
        self._model_var.set(model)
        self._endpoint_var.set(all_settings.get("llm_endpoint", ""))
        self._timeout_var.set(str(all_settings.get("llm_timeout", 60)))
        self._lang_var.set(all_settings.get("language", "it"))
        self._year_var.set(str(all_settings.get("fiscal_year", datetime.now().year)))

    def _save(self):
        if not self.db:
            return
        self.db.set_setting("llm_provider", self._provider_var.get())
        self.db.set_setting("llm_api_key", self._api_key_var.get())
        self.db.set_setting("llm_model", self._model_var.get())
        self.db.set_setting("llm_endpoint", self._endpoint_var.get())
        try:
            self.db.set_setting("llm_timeout", int(self._timeout_var.get()))
        except ValueError:
            self.db.set_setting("llm_timeout", 60)
        self.db.set_setting("language", self._lang_var.get())
        try:
            self.db.set_setting("fiscal_year", int(self._year_var.get()))
        except ValueError:
            pass

        if self.on_save:
            self.on_save()
        self.destroy()
        messagebox.showinfo(self.strings["success_saved"], self.strings["success_saved"])
