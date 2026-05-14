"""PDF report generator for Dedutto using ReportLab and matplotlib."""
import io
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from utils.logging import get_logger

log = get_logger(__name__)

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        HRFlowable, Image, PageBreak, Paragraph, SimpleDocTemplate,
        Spacer, Table, TableStyle,
    )
    _REPORTLAB_AVAILABLE = True
except ImportError:
    _REPORTLAB_AVAILABLE = False
    log.warning("reportlab not installed — PDF generation disabled")

try:
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    _MATPLOTLIB_AVAILABLE = True
except ImportError:
    _MATPLOTLIB_AVAILABLE = False
    log.warning("matplotlib not installed — charts disabled")

# Theme colors
COLOR_BG = "#1E1E1E"
COLOR_GREEN = "#2E8B57"
COLOR_WHITE = "#F0F0F0"
COLOR_GRAY = "#A0A0A0"
COLOR_DARK = "#252526"

CATEGORY_LABELS_IT = {
    "software": "Software e Licenze",
    "hosting": "Hosting e Cloud",
    "hardware": "Hardware",
    "office": "Cancelleria",
    "training": "Formazione",
    "insurance": "Assicurazioni",
    "accounting": "Commercialista",
    "bank": "Spese Bancarie",
    "advertising": "Pubblicità",
    "internet": "Internet/Telefono",
    "transport": "Trasporti",
    "utilities": "Utenze",
    "food": "Pasti",
    "travel": "Trasferte",
    "other": "Altro",
    "personal": "Personale",
    "fines": "Sanzioni",
    "": "Non Classificato",
}


class ReportGenerator:
    """Generates PDF expense reports for Italian Partita IVA."""

    def __init__(self, db=None):
        self.db = db
        if not _REPORTLAB_AVAILABLE:
            log.warning("ReportLab not available — PDF generation disabled")

    def is_available(self) -> bool:
        return _REPORTLAB_AVAILABLE

    def generate(
        self,
        output_path: str,
        year: Optional[int] = None,
        title: str = "Report Spese — Partita IVA",
    ) -> str:
        if not _REPORTLAB_AVAILABLE:
            raise RuntimeError("ReportLab non installato. Eseguire: pip install reportlab")
        if not self.db:
            raise RuntimeError("Database non disponibile")

        year = year or datetime.now().year
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        styles = self._build_styles()
        story = []

        # Header
        story += self._build_header(styles, title, year)
        story.append(Spacer(1, 0.5 * cm))

        # Summary cards
        story += self._build_summary(styles, year)
        story.append(Spacer(1, 0.5 * cm))

        # Expense table by category
        story += self._build_category_table(styles, year)
        story.append(Spacer(1, 0.5 * cm))

        # Charts
        story += self._build_charts(styles, year)
        story.append(Spacer(1, 0.5 * cm))

        # Amortization alerts
        story += self._build_amortization_section(styles, year)
        story.append(Spacer(1, 0.5 * cm))

        # Tax deadlines
        story += self._build_deadlines_section(styles, year)

        # Expense detail table on new page
        story.append(PageBreak())
        story += self._build_expense_detail(styles, year)

        doc.build(story)
        log.info("PDF report generated: %s", output_path)
        return output_path

    def _build_styles(self):
        styles = getSampleStyleSheet()

        green = colors.HexColor(COLOR_GREEN)
        dark = colors.HexColor(COLOR_DARK)
        light = colors.HexColor(COLOR_WHITE)
        gray = colors.HexColor(COLOR_GRAY)

        styles.add(ParagraphStyle(
            "DTitle", parent=styles["Title"],
            fontSize=22, textColor=green, spaceAfter=6,
        ))
        styles.add(ParagraphStyle(
            "DSubtitle", parent=styles["Normal"],
            fontSize=11, textColor=gray, spaceAfter=12,
        ))
        styles.add(ParagraphStyle(
            "DHeading", parent=styles["Heading2"],
            fontSize=13, textColor=green, spaceBefore=12, spaceAfter=6,
        ))
        styles.add(ParagraphStyle(
            "DBody", parent=styles["Normal"],
            fontSize=10, textColor=colors.black, spaceAfter=4,
        ))
        styles.add(ParagraphStyle(
            "DAlert", parent=styles["Normal"],
            fontSize=10, textColor=colors.HexColor("#C0392B"),
            spaceAfter=4, leading=14,
        ))
        styles.add(ParagraphStyle(
            "DSmall", parent=styles["Normal"],
            fontSize=8, textColor=gray,
        ))
        styles.add(ParagraphStyle(
            "DRight", parent=styles["Normal"],
            fontSize=10, alignment=TA_RIGHT,
        ))
        return styles

    def _build_header(self, styles, title: str, year: int):
        green = colors.HexColor(COLOR_GREEN)
        return [
            Paragraph(title, styles["DTitle"]),
            Paragraph(f"Anno fiscale {year} — Generato il {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles["DSubtitle"]),
            HRFlowable(width="100%", thickness=2, color=green, spaceAfter=8),
        ]

    def _build_summary(self, styles, year: int):
        totals = self.db.expense_totals(year)
        items = [
            ("Spese Totali", f"€ {totals['total']:,.2f}"),
            ("Totale Deducibile", f"€ {totals['deductible']:,.2f}"),
            ("IVA Recuperabile", f"€ {totals['vat_total']:,.2f}"),
            ("Risparmio Fiscale Stimato (23%)", f"€ {totals['deductible'] * 0.23:,.2f}"),
        ]
        data = [["Voce", "Importo"]]
        data += [[k, v] for k, v in items]

        table = Table(data, colWidths=[12 * cm, 5 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(COLOR_GREEN)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, 0), 11),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
            ("FONTSIZE", (0, 1), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        return [Paragraph("Riepilogo Finanziario", styles["DHeading"]), table]

    def _build_category_table(self, styles, year: int):
        categories = self.db.category_totals(year)
        if not categories:
            return [Paragraph("Nessuna spesa registrata.", styles["DBody"])]

        data = [["Categoria", "N° Spese", "Importo Totale", "Deducibile"]]
        deductibility_map = self._get_deductibility_map(year)

        for cat in categories:
            label = CATEGORY_LABELS_IT.get(cat["category"], cat["category"])
            deduct = deductibility_map.get(cat["category"], 0)
            data.append([
                label,
                str(cat["count"]),
                f"€ {cat['total']:,.2f}",
                f"€ {deduct:,.2f}",
            ])

        table = Table(data, colWidths=[7 * cm, 2.5 * cm, 4 * cm, 4 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(COLOR_GREEN)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        return [Paragraph("Spese per Categoria", styles["DHeading"]), table]

    def _get_deductibility_map(self, year: int) -> Dict[str, float]:
        expenses = self.db.list_expenses(year=year)
        result: Dict[str, float] = {}
        for exp in expenses:
            cat = exp.get("category", "")
            d_type = exp.get("deductibility_type", "none")
            amount = exp.get("amount", 0)
            if d_type == "full":
                deductible = amount
            elif d_type == "partial":
                deductible = amount * 0.5
            else:
                deductible = 0
            result[cat] = result.get(cat, 0) + deductible
        return result

    def _build_charts(self, styles, year: int):
        if not _MATPLOTLIB_AVAILABLE:
            return [Paragraph("Charts non disponibili (matplotlib non installato).", styles["DBody"])]

        flowables = [Paragraph("Grafici", styles["DHeading"])]

        # Monthly bar chart
        monthly_chart = self._create_monthly_chart(year)
        if monthly_chart:
            flowables.append(Image(monthly_chart, width=16 * cm, height=8 * cm))
            flowables.append(Spacer(1, 0.3 * cm))

        # Category pie chart
        category_chart = self._create_category_chart(year)
        if category_chart:
            flowables.append(Image(category_chart, width=12 * cm, height=8 * cm))

        return flowables

    def _create_monthly_chart(self, year: int) -> Optional[str]:
        try:
            monthly = self.db.monthly_totals(year)
            months_it = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
                         "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
            totals = [0.0] * 12
            for row in monthly:
                idx = int(row["month"]) - 1
                totals[idx] = row["total"]

            fig, ax = plt.subplots(figsize=(10, 5))
            fig.patch.set_facecolor("#F8F8F8")
            ax.set_facecolor("#F8F8F8")
            bars = ax.bar(months_it, totals, color=COLOR_GREEN, edgecolor="white", linewidth=0.5)
            ax.set_title(f"Spese Mensili {year}", fontsize=13, color="#1E1E1E", pad=12)
            ax.set_ylabel("€", fontsize=10)
            ax.tick_params(colors="#333333")
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            for bar, val in zip(bars, totals):
                if val > 0:
                    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 5,
                            f"€{val:.0f}", ha="center", va="bottom", fontsize=8, color="#333333")
            plt.tight_layout()

            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            plt.savefig(tmp.name, dpi=150, bbox_inches="tight")
            plt.close(fig)
            return tmp.name
        except Exception as exc:
            log.error("Monthly chart error: %s", exc)
            return None

    def _create_category_chart(self, year: int) -> Optional[str]:
        try:
            categories = self.db.category_totals(year)
            if not categories:
                return None
            labels = [CATEGORY_LABELS_IT.get(c["category"], c["category"]) for c in categories]
            values = [c["total"] for c in categories]
            palette = [
                COLOR_GREEN, "#3498DB", "#9B59B6", "#E67E22", "#E74C3C",
                "#1ABC9C", "#F39C12", "#2ECC71", "#D35400", "#8E44AD",
            ]
            colors_list = [palette[i % len(palette)] for i in range(len(labels))]

            fig, ax = plt.subplots(figsize=(8, 6))
            fig.patch.set_facecolor("#F8F8F8")
            wedges, texts, autotexts = ax.pie(
                values, labels=None, colors=colors_list,
                autopct=lambda p: f"{p:.1f}%\n€{p * sum(values) / 100:.0f}" if p > 3 else "",
                startangle=140, pctdistance=0.8,
            )
            for at in autotexts:
                at.set_fontsize(8)
            ax.legend(wedges, labels, loc="lower center", bbox_to_anchor=(0.5, -0.15),
                      ncol=3, fontsize=8, frameon=False)
            ax.set_title(f"Ripartizione per Categoria {year}", fontsize=13, color="#1E1E1E", pad=12)
            plt.tight_layout()

            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            plt.savefig(tmp.name, dpi=150, bbox_inches="tight")
            plt.close(fig)
            return tmp.name
        except Exception as exc:
            log.error("Category chart error: %s", exc)
            return None

    def _build_amortization_section(self, styles, year: int):
        from core.amortization import AmortizationTracker
        tracker = AmortizationTracker(self.db)
        alerts = tracker.missing_amortization_alerts()
        summary = tracker.summary_by_year(year)

        flowables = [Paragraph("Ammortamenti", styles["DHeading"])]

        if summary["assets"]:
            data = [["Bene", "Quota Annua", "Valore Residuo"]]
            for asset in summary["assets"]:
                data.append([
                    f"{asset['vendor']} — {asset['description']}"[:50],
                    f"€ {asset['annual_amount']:,.2f}",
                    f"€ {asset['remaining_value']:,.2f}",
                ])
            data.append(["TOTALE", f"€ {summary['total_deductible']:,.2f}", ""])
            table = Table(data, colWidths=[9 * cm, 4 * cm, 4 * cm])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(COLOR_GREEN)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F5F5F5")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            flowables.append(table)
            flowables.append(Spacer(1, 0.3 * cm))

        if alerts:
            flowables.append(Paragraph("⚠ Avvisi Ammortamento", styles["DAlert"]))
            for alert in alerts:
                flowables.append(Paragraph(f"• {alert['message']}", styles["DAlert"]))

        if not summary["assets"] and not alerts:
            flowables.append(Paragraph("Nessun bene ammortizzabile registrato.", styles["DBody"]))

        return flowables

    def _build_deadlines_section(self, styles, year: int):
        deadlines = self.db.get_deadlines(year)
        flowables = [Paragraph("Scadenze Fiscali", styles["DHeading"])]
        if not deadlines:
            flowables.append(Paragraph("Nessuna scadenza per questo anno.", styles["DBody"]))
            return flowables

        today = datetime.now().date().isoformat()
        data = [["Scadenza", "Data", "Note"]]
        for dl in deadlines:
            is_past = dl["deadline_date"] < today
            name = dl["name"]
            if is_past:
                name = f"✓ {name}"
            data.append([name, dl["deadline_date"], dl.get("description", "")[:60]])

        table = Table(data, colWidths=[7 * cm, 3 * cm, 7 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(COLOR_GREEN)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        flowables.append(table)
        return flowables

    def _build_expense_detail(self, styles, year: int):
        expenses = self.db.list_expenses(year=year)
        flowables = [Paragraph("Dettaglio Spese", styles["DHeading"])]
        if not expenses:
            flowables.append(Paragraph("Nessuna spesa.", styles["DBody"]))
            return flowables

        data = [["Data", "Fornitore", "Descrizione", "Importo", "Deducibilità"]]
        deduct_labels = {
            "full": "100%", "partial": "50%",
            "amortizable": "Amm.", "none": "-", "": "?",
        }
        for exp in expenses:
            data.append([
                exp.get("date", "")[:10],
                (exp.get("vendor") or "")[:20],
                (exp.get("description") or "")[:30],
                f"€{exp.get('amount', 0):,.2f}",
                deduct_labels.get(exp.get("deductibility_type", ""), "?"),
            ])

        col_widths = [2.5 * cm, 4.5 * cm, 6 * cm, 2.5 * cm, 2 * cm]
        table = Table(data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(COLOR_GREEN)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (3, 0), (3, -1), "RIGHT"),
            ("ALIGN", (4, 0), (4, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#DDDDDD")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        flowables.append(table)
        return flowables
