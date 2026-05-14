"""English UI strings."""

STRINGS = {
    # App
    "app_title": "Dedutto — Expense Manager for Italian Freelancers",
    "app_subtitle": "Privacy-first for Italian Partita IVA holders",

    # Menu
    "menu_file": "File",
    "menu_import": "Import Document",
    "menu_export_pdf": "Export PDF Report",
    "menu_backup": "Encrypted Backup",
    "menu_restore": "Restore Backup",
    "menu_quit": "Quit",
    "menu_edit": "Edit",
    "menu_settings": "Settings",
    "menu_help": "Help",
    "menu_about": "About",

    # Tabs
    "tab_dashboard": "Dashboard",
    "tab_expenses": "Expenses",
    "tab_amortization": "Amortization",
    "tab_reports": "Reports",
    "tab_deadlines": "Tax Deadlines",

    # Dashboard
    "dashboard_total_expenses": "Total Expenses",
    "dashboard_deductible": "Deductible",
    "dashboard_vat_credit": "VAT Credit",
    "dashboard_pending": "Pending Classification",
    "dashboard_monthly_chart": "Monthly Trend",
    "dashboard_category_chart": "Category Breakdown",

    # Expense table
    "col_date": "Date",
    "col_vendor": "Vendor",
    "col_description": "Description",
    "col_amount": "Amount",
    "col_vat": "VAT",
    "col_category": "Category",
    "col_deductibility": "Deductibility",
    "col_confidence": "Confidence",
    "col_vat_regime": "VAT Regime",

    # Deductibility types
    "deduct_full": "100% Deductible",
    "deduct_partial": "50% Mixed Use",
    "deduct_amortizable": "Amortizable",
    "deduct_none": "Non-Deductible",

    # Buttons
    "btn_add": "Add",
    "btn_edit": "Edit",
    "btn_delete": "Delete",
    "btn_classify": "Classify",
    "btn_save": "Save",
    "btn_cancel": "Cancel",
    "btn_ok": "OK",
    "btn_generate_report": "Generate PDF Report",
    "btn_export_backup": "Export Backup",
    "btn_import_backup": "Import Backup",
    "btn_classify_all": "Classify All",
    "btn_refresh": "Refresh",

    # Drop zone
    "drop_zone_text": "Drag & drop PDF, PNG or JPG here\nor click to select",
    "drop_zone_hint": "Supported: receipts, invoices, bank statements",

    # OCR
    "ocr_processing": "Processing OCR...",
    "ocr_complete": "OCR complete",
    "ocr_failed": "OCR failed — manual entry",
    "ocr_low_confidence": "Low confidence ({:.0f}%) — please verify data",
    "ocr_preview_title": "OCR Preview",
    "ocr_confirm": "Confirm Data",

    # LLM
    "llm_classifying": "Classifying...",
    "llm_classified": "Classified with {:.0f}% confidence",
    "llm_error": "LLM error: {}",
    "llm_cached": "Result from cache",

    # Settings
    "settings_title": "Settings",
    "settings_llm": "LLM Provider",
    "settings_provider": "Provider",
    "settings_api_key": "API Key",
    "settings_model": "Model",
    "settings_language": "Language",
    "settings_language_it": "Italiano",
    "settings_language_en": "English",
    "settings_db": "Database",
    "settings_change_password": "Change Password",
    "settings_save": "Save Settings",
    "settings_custom_endpoint": "Custom Endpoint",
    "settings_timeout": "Timeout (seconds)",

    # Password
    "password_title": "Master Password",
    "password_prompt": "Enter master password to unlock the database:",
    "password_new": "Create a new master password:",
    "password_confirm": "Confirm password:",
    "password_mismatch": "Passwords do not match",
    "password_weak": "Password too short (min. 8 characters)",
    "password_wrong": "Wrong password",

    # Reports
    "report_title": "Expense Report — Partita IVA",
    "report_period": "Period",
    "report_total": "Total Expenses",
    "report_deductible_total": "Total Deductible",
    "report_vat_total": "Total Recoverable VAT",
    "report_by_category": "Expenses by Category",
    "report_amortization": "Amortization Schedule",
    "report_alerts": "Deduction Alerts",
    "report_deadlines": "Tax Deadlines",
    "report_yoy": "Year-over-Year Comparison",
    "report_savings": "Estimated Tax Savings",

    # Tax deadlines
    "deadline_f24": "F24 Payment",
    "deadline_iva_q": "Quarterly VAT Return",
    "deadline_iva_m": "Monthly VAT Return",
    "deadline_cu": "Certificazione Unica",
    "deadline_redditi": "Income Tax Return (Modello Redditi PF)",
    "deadline_imu": "IMU",
    "deadline_730": "Modello 730",
    "deadline_inps": "INPS Contributions",

    # Amortization
    "amort_laptop": "Laptop / PC",
    "amort_furniture": "Furniture",
    "amort_machinery": "Machinery",
    "amort_vehicle": "Vehicle",
    "amort_renovation": "Renovation",
    "amort_years": "years amortization",
    "amort_annual": "Annual quota",
    "amort_remaining": "Remaining value",
    "amort_alert": "You purchased {} for €{:.2f} on {} but haven't started amortization — save ~€{:.2f} spread over {} years",

    # Status bar
    "status_expenses": "{} expenses",
    "status_pending": "{} pending",
    "status_last_sync": "Last update: {}",
    "status_ready": "Ready",

    # Errors
    "error_title": "Error",
    "error_tesseract": "Tesseract not found. Please install tesseract-ocr.",
    "error_db": "Database error: {}",
    "error_db_corrupt": "Database corrupted. Restore from backup?",
    "error_llm": "LLM error: {}",
    "error_pdf": "PDF generation error: {}",
    "error_api_key": "API key missing or invalid",
    "error_file_type": "Unsupported file type. Use PDF, PNG or JPG.",

    # Success
    "success_saved": "Saved successfully",
    "success_classified": "Classification complete",
    "success_report": "Report generated: {}",
    "success_backup": "Backup saved: {}",
    "success_restore": "Restore complete",

    # Confirmations
    "confirm_delete": "Delete this expense?",
    "confirm_delete_title": "Confirm delete",
    "confirm_backup_overwrite": "File already exists. Overwrite?",

    # Manual entry dialog
    "manual_title": "Manual Entry",
    "manual_vendor": "Vendor",
    "manual_date": "Date (dd/mm/yyyy)",
    "manual_amount": "Amount (€)",
    "manual_vat": "VAT (€)",
    "manual_description": "Description",
    "manual_category": "Category",
    "manual_notes": "Notes",

    # VAT regimes
    "vat_normale": "Standard VAT",
    "vat_sospensione": "VAT Suspension",
    "vat_split_payment": "Split Payment",
    "vat_reverse_charge": "Reverse Charge",
    "vat_esente": "VAT Exempt",
    "vat_forfettario": "Forfettario Regime",

    # Categories
    "cat_software": "Software & Licenses",
    "cat_hosting": "Hosting & Cloud",
    "cat_hardware": "Hardware",
    "cat_office": "Office Supplies",
    "cat_training": "Professional Training",
    "cat_insurance": "Insurance",
    "cat_accounting": "Accounting & Consulting",
    "cat_bank": "Bank Fees",
    "cat_advertising": "Advertising & Marketing",
    "cat_internet": "Internet & Phone",
    "cat_transport": "Transport & Car",
    "cat_utilities": "Utilities",
    "cat_food": "Business Meals",
    "cat_travel": "Travel",
    "cat_other": "Other",
    "cat_personal": "Personal (Non-Deductible)",
    "cat_fines": "Fines (Non-Deductible)",

    # About
    "about_title": "About Dedutto",
    "about_text": (
        "Dedutto v1.0.0\n\n"
        "Privacy-first expense manager for Italian Partita IVA.\n"
        "All data stays on your device.\n\n"
        "No cloud. No tracking. Just your accountant."
    ),
}
