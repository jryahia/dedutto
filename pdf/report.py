import io
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from utils.helpers import log, format_currency

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        BaseDocTemplate,
        Frame,
        KeepTogether,
        PageBreak,
        PageTemplate,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
        Image as RLImage,
    )
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    log.error("ReportLab non installato")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

COLOR_BG = colors.HexColor("#1E1E1E")
COLOR_GREEN = colors.HexColor("#2E8B57")
COLOR_LIGHT = colors.HexColor("#F0F0F0")
COLOR_GRAY = colors.HexColor("#888888")
COLOR_RED = colors.HexColor("#CC3333")
COLOR_ORANGE = colors.HexColor("#E07000")

TAX_DEADLINES = [
    ("16 gen", "F24 - Versamento ritenute dicembre"),
    ("31 mar", "CU - Certificazione Unica"),
    ("16 apr", "F24 - Versamento ritenute marzo / IVA 1° trimestre"),
    ("16 giu", "IMU - Prima rata"),
    ("16 lug", "F24 - IVA 2° trimestre"),
    ("16 ago", "F24 - Versamento ritenute luglio"),
    ("30 nov", "Redditi - Dichiarazione dei redditi (Modello Redditi PF)"),
    ("30 nov", "F24 - Saldo IRPEF + 1° acconto"),
    ("16 dic", "IMU - Seconda rata"),
    ("16 dic", "F24 - IVA 4° trimestre / dicembre"),
]


def _make_chart(yearly_data: List[Tuple[int, float]]) -> Optional[bytes]:
    if not HAS_MATPLOTLIB or not yearly_data:
        return None
    fig, ax = plt.subplots(figsize=(10, 4), facecolor="#1E1E1E")
    ax.set_facecolor("#2A2A2A")
    years = [str(y) for y, _ in yearly_data]
    amounts = [a for _, a in yearly_data]
    bars = ax.bar(years, amounts, color="#2E8B57", edgecolor="#1E1E1E", width=0.6)
    for bar, amt in zip(bars, amounts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(amounts) * 0.01,
            format_currency(amt),
            ha="center",
            va="bottom",
            color="white",
            fontsize=9,
        )
    ax.set_ylabel("Importo (€)", color="white")
    ax.set_xlabel("Anno", color="white")
    ax.set_title("Spese Anno per Anno", color="white", fontsize=13)
    ax.tick_params(colors="white")
    ax.spines["bottom"].set_color("#555555")
    ax.spines["left"].set_color("#555555")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def generate_report(
    expenses,
    classifications,
    amortizations,
    yearly_data: List[Tuple[int, float]],
    output_path: str,
    irpef_rate: float = 23.0,
    regional_rate: float = 2.03,
) -> None:
    if not HAS_REPORTLAB:
        raise RuntimeError("ReportLab non installato. Eseguire: pip install reportlab")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DeduttoTitle",
        parent=styles["Title"],
        fontSize=28,
        textColor=COLOR_GREEN,
        spaceAfter=0.5 * cm,
        alignment=TA_CENTER,
    )
    h1_style = ParagraphStyle(
        "DeduttoH1",
        parent=styles["Heading1"],
        fontSize=16,
        textColor=COLOR_GREEN,
        spaceBefore=0.8 * cm,
        spaceAfter=0.3 * cm,
    )
    h2_style = ParagraphStyle(
        "DeduttoH2",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=COLOR_LIGHT,
        spaceBefore=0.5 * cm,
        spaceAfter=0.2 * cm,
    )
    body_style = ParagraphStyle(
        "DeduttoBody",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.black,
        spaceAfter=0.15 * cm,
    )
    alert_style = ParagraphStyle(
        "DeduttoAlert",
        parent=styles["Normal"],
        fontSize=9,
        textColor=COLOR_RED,
        spaceAfter=0.2 * cm,
        leftIndent=10,
    )
    small_style = ParagraphStyle(
        "DeduttoSmall",
        parent=styles["Normal"],
        fontSize=8,
        textColor=COLOR_GRAY,
    )

    story = []
    now = datetime.now()

    # ── Title Page ─────────────────────────────────────────────────────────────
    story.append(Spacer(1, 3 * cm))
    story.append(Paragraph("DEDUTTO", title_style))
    story.append(Paragraph("Gestione Spese Partita IVA", ParagraphStyle(
        "sub", parent=styles["Normal"], fontSize=14, textColor=COLOR_GRAY, alignment=TA_CENTER, spaceAfter=0.3 * cm
    )))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        f"Report generato il {now.strftime('%d/%m/%Y alle %H:%M')}",
        ParagraphStyle("date_st", parent=styles["Normal"], alignment=TA_CENTER, fontSize=10, textColor=COLOR_GRAY),
    ))
    story.append(PageBreak())

    # ── Expense Summary ────────────────────────────────────────────────────────
    story.append(Paragraph("Riepilogo Spese", h1_style))

    total_amount = sum(e.amount for e in expenses)
    classified_count = sum(1 for e in expenses if e.classification_id)
    pending_count = len(expenses) - classified_count

    summary_data = [
        ["Descrizione", "Valore"],
        ["Numero totale spese", str(len(expenses))],
        ["Importo totale", format_currency(total_amount)],
        ["Spese classificate", str(classified_count)],
        ["Spese in attesa", str(pending_count)],
    ]
    summary_table = Table(summary_data, colWidths=[10 * cm, 6 * cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.5 * cm))

    # ── Categorized Expense Table ─────────────────────────────────────────────
    story.append(Paragraph("Dettaglio Spese per Categoria", h1_style))

    exp_data = [["Data", "Fornitore", "Importo", "IVA", "Categoria", "Deducibilità"]]
    class_map = {c.id: c for c in classifications if c.id}

    for e in sorted(expenses, key=lambda x: x.date or datetime.min):
        cls = class_map.get(e.classification_id) if e.classification_id else None
        ded_label = cls.deductibility_label() if cls else "In attesa"
        cat_label = cls.category if cls else "—"
        exp_data.append([
            e.date_str(),
            (e.vendor or "N/D")[:25],
            format_currency(e.amount),
            format_currency(e.vat_amount) if e.vat_amount else "—",
            cat_label[:20],
            ded_label,
        ])

    if len(exp_data) > 1:
        exp_table = Table(exp_data, colWidths=[2.2*cm, 5*cm, 2.8*cm, 2.2*cm, 3.5*cm, 3.3*cm])
        exp_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_GREEN),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
            ("ALIGN", (2, 0), (3, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 4),
            ("WORDWRAP", (0, 0), (-1, -1), True),
        ]))
        story.append(exp_table)

    story.append(PageBreak())

    # ── Deduction Analysis ────────────────────────────────────────────────────
    story.append(Paragraph("Analisi Deduzioni", h1_style))

    tax_rate = (irpef_rate + regional_rate) / 100
    total_deductible = 0.0
    total_savings = 0.0

    ded_data = [["Categoria", "Deducibilità", "Importo", "Risparmio IRPEF"]]
    for e in expenses:
        cls = class_map.get(e.classification_id) if e.classification_id else None
        if not cls:
            continue
        pct = cls.deductibility_pct / 100
        ded_amount = e.amount * pct
        savings = ded_amount * tax_rate
        total_deductible += ded_amount
        total_savings += savings
        ded_data.append([
            (cls.category or "—")[:20],
            cls.deductibility_label(),
            format_currency(ded_amount),
            format_currency(savings),
        ])

    if len(ded_data) > 1:
        ded_data.append([
            "TOTALE",
            "",
            format_currency(total_deductible),
            format_currency(total_savings),
        ])
        ded_table = Table(ded_data, colWidths=[5*cm, 4*cm, 4*cm, 4*cm])
        ded_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_GREEN),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E8F5E9")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F5F5F5")]),
            ("ALIGN", (2, 0), (3, -1), "RIGHT"),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(ded_table)

    # Missing deduction alerts
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph("Alert Deduzioni Mancanti", h2_style))
    alerts_found = False
    for e in expenses:
        cls = class_map.get(e.classification_id) if e.classification_id else None
        if cls and cls.deductibility == "amortizable" and e.id:
            amort_list = [a for a in amortizations if a.expense_id == e.id]
            if not amort_list:
                msg = (
                    f"⚠ Hai acquistato <b>{e.vendor or 'un bene'}</b> per "
                    f"<b>{format_currency(e.amount)}</b> il "
                    f"<b>{e.date_str()}</b> ma non hai avviato l'ammortamento."
                )
                story.append(Paragraph(msg, alert_style))
                alerts_found = True
    if not alerts_found:
        story.append(Paragraph("Nessun alert: tutte le spese ammortizzabili sono configurate.", body_style))

    story.append(PageBreak())

    # ── Amortization Schedule ─────────────────────────────────────────────────
    story.append(Paragraph("Piano di Ammortamento", h1_style))
    exp_map = {e.id: e for e in expenses}

    if amortizations:
        amort_data = [["Fornitore", "Anno", "Quota Annua", "Valore Residuo", "% Ammort.", "Dedotto"]]
        for a in amortizations:
            e = exp_map.get(a.expense_id)
            vendor = (e.vendor or "N/D")[:20] if e else "N/D"
            amort_data.append([
                vendor,
                str(a.year),
                format_currency(a.annual_amount),
                format_currency(a.remaining_value),
                f"{a.pct_used:.1f}%",
                "Sì" if a.is_deducted else "No",
            ])
        amort_table = Table(amort_data, colWidths=[4*cm, 2*cm, 3.5*cm, 3.5*cm, 2.5*cm, 2*cm])
        amort_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_GREEN),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
            ("ALIGN", (2, 0), (4, -1), "RIGHT"),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(amort_table)
    else:
        story.append(Paragraph("Nessun piano di ammortamento presente.", body_style))

    story.append(PageBreak())

    # ── Year-over-Year Chart ───────────────────────────────────────────────────
    story.append(Paragraph("Andamento Anno per Anno", h1_style))
    chart_bytes = _make_chart(yearly_data)
    if chart_bytes:
        chart_img = RLImage(io.BytesIO(chart_bytes), width=16 * cm, height=7 * cm)
        story.append(chart_img)
    else:
        story.append(Paragraph("Grafico non disponibile (installare matplotlib).", small_style))

    story.append(PageBreak())

    # ── Tax Deadline Calendar ─────────────────────────────────────────────────
    story.append(Paragraph("Calendario Scadenze Fiscali", h1_style))
    story.append(Paragraph(
        f"Anno fiscale {now.year} — principali scadenze per Partita IVA",
        body_style,
    ))
    story.append(Spacer(1, 0.3 * cm))

    deadline_data = [["Scadenza", "Descrizione"]]
    for date_str, desc in TAX_DEADLINES:
        deadline_data.append([date_str, desc])

    deadline_table = Table(deadline_data, colWidths=[3 * cm, 14 * cm])
    deadline_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(deadline_table)

    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph(
        "Report generato da Dedutto — gestione spese Partita IVA italiana",
        small_style,
    ))

    doc.build(story)
    log.info(f"Report PDF generato: {output_path}")
