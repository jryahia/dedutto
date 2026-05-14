"""Dark theme configuration for Dedutto."""
import tkinter as tk
from tkinter import ttk

# Color palette
BG_PRIMARY = "#1E1E1E"      # Charcoal background
BG_SECONDARY = "#252526"    # Slightly lighter panels
BG_TERTIARY = "#2D2D30"     # Cards / table rows
ACCENT = "#2E8B57"          # Sea green accent
ACCENT_HOVER = "#3AAD6E"    # Lighter green on hover
ACCENT_DIM = "#1A5C3A"      # Darker green
TEXT_PRIMARY = "#F0F0F0"    # Main text
TEXT_SECONDARY = "#A0A0A0"  # Muted text
TEXT_DISABLED = "#555555"   # Disabled
BORDER = "#3C3C3C"          # Borders / separators
ERROR = "#E05252"           # Error red
WARNING = "#D4A017"         # Warning yellow
SUCCESS = "#2E8B57"         # Same as accent
ROW_EVEN = "#252526"
ROW_ODD = "#2D2D30"
ROW_SELECTED = "#1A5C3A"

# Fonts
FONT_FAMILY = "Helvetica"
FONT_SMALL = (FONT_FAMILY, 9)
FONT_NORMAL = (FONT_FAMILY, 11)
FONT_MEDIUM = (FONT_FAMILY, 12)
FONT_LARGE = (FONT_FAMILY, 14, "bold")
FONT_TITLE = (FONT_FAMILY, 18, "bold")
FONT_MONO = ("Courier New", 10)

# Padding
PAD_XS = 4
PAD_SM = 8
PAD_MD = 12
PAD_LG = 16
PAD_XL = 24

TREEVIEW_ROW_HEIGHT = 28


def apply_theme(root: tk.Tk) -> None:
    """Apply the dark theme to the Tk root and ttk styles."""
    root.configure(bg=BG_PRIMARY)

    style = ttk.Style(root)
    # Use clam as base — most customizable
    style.theme_use("clam")

    # General
    style.configure(".", background=BG_PRIMARY, foreground=TEXT_PRIMARY,
                    font=FONT_NORMAL, bordercolor=BORDER, relief="flat")
    style.configure("TFrame", background=BG_PRIMARY)
    style.configure("TLabel", background=BG_PRIMARY, foreground=TEXT_PRIMARY,
                    font=FONT_NORMAL)
    style.configure("TLabelframe", background=BG_PRIMARY, foreground=TEXT_PRIMARY,
                    bordercolor=BORDER)
    style.configure("TLabelframe.Label", background=BG_PRIMARY,
                    foreground=ACCENT, font=FONT_MEDIUM)
    style.configure("TEntry", fieldbackground=BG_TERTIARY, foreground=TEXT_PRIMARY,
                    insertcolor=TEXT_PRIMARY, bordercolor=BORDER,
                    selectbackground=ACCENT, selectforeground=TEXT_PRIMARY)
    style.configure("TCombobox", fieldbackground=BG_TERTIARY, foreground=TEXT_PRIMARY,
                    background=BG_TERTIARY, selectbackground=ACCENT,
                    selectforeground=TEXT_PRIMARY, arrowcolor=TEXT_PRIMARY)
    style.map("TCombobox", fieldbackground=[("readonly", BG_TERTIARY)])

    # Buttons
    style.configure("TButton", background=BG_TERTIARY, foreground=TEXT_PRIMARY,
                    bordercolor=BORDER, padding=(PAD_SM, PAD_XS), font=FONT_NORMAL)
    style.map("TButton",
              background=[("active", ACCENT), ("pressed", ACCENT_DIM)],
              foreground=[("active", TEXT_PRIMARY)])

    style.configure("Accent.TButton", background=ACCENT, foreground=TEXT_PRIMARY,
                    bordercolor=ACCENT_DIM, padding=(PAD_MD, PAD_SM), font=FONT_MEDIUM)
    style.map("Accent.TButton",
              background=[("active", ACCENT_HOVER), ("pressed", ACCENT_DIM)])

    style.configure("Danger.TButton", background="#7B2020", foreground=TEXT_PRIMARY,
                    bordercolor="#5C1818", padding=(PAD_SM, PAD_XS))
    style.map("Danger.TButton",
              background=[("active", ERROR), ("pressed", "#5C1818")])

    # Notebook (tabs)
    style.configure("TNotebook", background=BG_PRIMARY, bordercolor=BORDER, tabmargins=0)
    style.configure("TNotebook.Tab", background=BG_SECONDARY, foreground=TEXT_SECONDARY,
                    padding=(PAD_MD, PAD_SM), font=FONT_NORMAL)
    style.map("TNotebook.Tab",
              background=[("selected", BG_PRIMARY), ("active", BG_TERTIARY)],
              foreground=[("selected", ACCENT), ("active", TEXT_PRIMARY)])

    # Treeview
    style.configure("Treeview", background=BG_SECONDARY, foreground=TEXT_PRIMARY,
                    fieldbackground=BG_SECONDARY, bordercolor=BORDER,
                    rowheight=TREEVIEW_ROW_HEIGHT, font=FONT_NORMAL)
    style.configure("Treeview.Heading", background=BG_TERTIARY, foreground=ACCENT,
                    bordercolor=BORDER, font=FONT_NORMAL)
    style.map("Treeview",
              background=[("selected", ROW_SELECTED)],
              foreground=[("selected", TEXT_PRIMARY)])
    style.map("Treeview.Heading",
              background=[("active", ACCENT_DIM)])

    # Scrollbar
    style.configure("Vertical.TScrollbar", background=BG_TERTIARY, troughcolor=BG_SECONDARY,
                    arrowcolor=TEXT_SECONDARY, bordercolor=BORDER)
    style.configure("Horizontal.TScrollbar", background=BG_TERTIARY, troughcolor=BG_SECONDARY,
                    arrowcolor=TEXT_SECONDARY, bordercolor=BORDER)

    # Progressbar
    style.configure("TProgressbar", background=ACCENT, troughcolor=BG_TERTIARY,
                    bordercolor=BORDER)

    # Separator
    style.configure("TSeparator", background=BORDER)

    # Scale
    style.configure("TScale", background=BG_PRIMARY, troughcolor=BG_TERTIARY,
                    sliderthickness=16)

    # Checkbutton / Radiobutton
    style.configure("TCheckbutton", background=BG_PRIMARY, foreground=TEXT_PRIMARY,
                    font=FONT_NORMAL)
    style.map("TCheckbutton",
              background=[("active", BG_PRIMARY)],
              foreground=[("active", ACCENT)])
    style.configure("TRadiobutton", background=BG_PRIMARY, foreground=TEXT_PRIMARY,
                    font=FONT_NORMAL)
    style.map("TRadiobutton",
              background=[("active", BG_PRIMARY)],
              foreground=[("active", ACCENT)])

    # Status bar
    style.configure("Status.TLabel", background=BG_SECONDARY, foreground=TEXT_SECONDARY,
                    font=FONT_SMALL, padding=(PAD_SM, PAD_XS))
    style.configure("StatusOk.TLabel", background=BG_SECONDARY, foreground=SUCCESS,
                    font=FONT_SMALL, padding=(PAD_SM, PAD_XS))

    # Title labels
    style.configure("Title.TLabel", background=BG_PRIMARY, foreground=TEXT_PRIMARY,
                    font=FONT_TITLE)
    style.configure("Subtitle.TLabel", background=BG_PRIMARY, foreground=TEXT_SECONDARY,
                    font=FONT_SMALL)
    style.configure("Accent.TLabel", background=BG_PRIMARY, foreground=ACCENT,
                    font=FONT_MEDIUM)

    # Stat card
    style.configure("Card.TFrame", background=BG_SECONDARY, relief="flat")
    style.configure("CardValue.TLabel", background=BG_SECONDARY, foreground=TEXT_PRIMARY,
                    font=FONT_TITLE)
    style.configure("CardLabel.TLabel", background=BG_SECONDARY, foreground=TEXT_SECONDARY,
                    font=FONT_SMALL)
    style.configure("CardAccent.TLabel", background=BG_SECONDARY, foreground=ACCENT,
                    font=FONT_LARGE)

    # Spinbox
    style.configure("TSpinbox", fieldbackground=BG_TERTIARY, foreground=TEXT_PRIMARY,
                    insertcolor=TEXT_PRIMARY, bordercolor=BORDER,
                    arrowcolor=TEXT_PRIMARY, background=BG_TERTIARY)
