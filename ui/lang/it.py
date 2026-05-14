"""Italian UI strings."""

STRINGS = {
    # App
    "app_title": "Dedutto — Gestione Spese Partita IVA",
    "app_subtitle": "Privacy-first per liberi professionisti italiani",

    # Menu
    "menu_file": "File",
    "menu_import": "Importa Documento",
    "menu_export_pdf": "Esporta Report PDF",
    "menu_backup": "Backup Cifrato",
    "menu_restore": "Ripristina Backup",
    "menu_quit": "Esci",
    "menu_edit": "Modifica",
    "menu_settings": "Impostazioni",
    "menu_help": "Aiuto",
    "menu_about": "Informazioni",

    # Tabs
    "tab_dashboard": "Dashboard",
    "tab_expenses": "Spese",
    "tab_amortization": "Ammortamenti",
    "tab_reports": "Report",
    "tab_deadlines": "Scadenze Fiscali",

    # Dashboard
    "dashboard_total_expenses": "Spese Totali",
    "dashboard_deductible": "Deducibili",
    "dashboard_vat_credit": "Credito IVA",
    "dashboard_pending": "Da Classificare",
    "dashboard_monthly_chart": "Andamento Mensile",
    "dashboard_category_chart": "Ripartizione per Categoria",

    # Expense table
    "col_date": "Data",
    "col_vendor": "Fornitore",
    "col_description": "Descrizione",
    "col_amount": "Importo",
    "col_vat": "IVA",
    "col_category": "Categoria",
    "col_deductibility": "Deducibilità",
    "col_confidence": "Affidabilità",
    "col_vat_regime": "Regime IVA",

    # Deductibility types
    "deduct_full": "100% Deducibile",
    "deduct_partial": "50% Uso Misto",
    "deduct_amortizable": "Ammortizzabile",
    "deduct_none": "Non Deducibile",

    # Buttons
    "btn_add": "Aggiungi",
    "btn_edit": "Modifica",
    "btn_delete": "Elimina",
    "btn_classify": "Classifica",
    "btn_save": "Salva",
    "btn_cancel": "Annulla",
    "btn_ok": "OK",
    "btn_generate_report": "Genera Report PDF",
    "btn_export_backup": "Esporta Backup",
    "btn_import_backup": "Importa Backup",
    "btn_classify_all": "Classifica Tutte",
    "btn_refresh": "Aggiorna",

    # Drop zone
    "drop_zone_text": "Trascina qui PDF, PNG o JPG\noppure clicca per selezionare",
    "drop_zone_hint": "Supportati: ricevute, fatture, estratti conto",

    # OCR
    "ocr_processing": "Elaborazione OCR in corso...",
    "ocr_complete": "OCR completato",
    "ocr_failed": "OCR fallito — inserimento manuale",
    "ocr_low_confidence": "Confidenza bassa ({:.0f}%) — verifica i dati",
    "ocr_preview_title": "Anteprima OCR",
    "ocr_confirm": "Conferma Dati",

    # LLM
    "llm_classifying": "Classificazione in corso...",
    "llm_classified": "Classificato con {:.0f}% di confidenza",
    "llm_error": "Errore LLM: {}",
    "llm_cached": "Risultato dalla cache",

    # Settings
    "settings_title": "Impostazioni",
    "settings_llm": "Provider LLM",
    "settings_provider": "Provider",
    "settings_api_key": "Chiave API",
    "settings_model": "Modello",
    "settings_language": "Lingua",
    "settings_language_it": "Italiano",
    "settings_language_en": "English",
    "settings_db": "Database",
    "settings_change_password": "Cambia Password",
    "settings_save": "Salva Impostazioni",
    "settings_custom_endpoint": "Endpoint Personalizzato",
    "settings_timeout": "Timeout (secondi)",

    # Password
    "password_title": "Password Master",
    "password_prompt": "Inserisci la password master per sbloccare il database:",
    "password_new": "Crea una nuova password master:",
    "password_confirm": "Conferma password:",
    "password_mismatch": "Le password non corrispondono",
    "password_weak": "Password troppo corta (min. 8 caratteri)",
    "password_wrong": "Password errata",

    # Reports
    "report_title": "Report Spese — Partita IVA",
    "report_period": "Periodo",
    "report_total": "Totale Spese",
    "report_deductible_total": "Totale Deducibile",
    "report_vat_total": "Totale IVA Recuperabile",
    "report_by_category": "Spese per Categoria",
    "report_amortization": "Piano di Ammortamento",
    "report_alerts": "Avvisi Deduzioni",
    "report_deadlines": "Scadenze Fiscali",
    "report_yoy": "Confronto Anno su Anno",
    "report_savings": "Risparmio Fiscale Stimato",

    # Tax deadlines
    "deadline_f24": "Versamento F24",
    "deadline_iva_q": "Liquidazione IVA Trimestrale",
    "deadline_iva_m": "Liquidazione IVA Mensile",
    "deadline_cu": "Certificazione Unica",
    "deadline_redditi": "Dichiarazione Redditi (Modello Redditi PF)",
    "deadline_imu": "IMU",
    "deadline_730": "Modello 730",
    "deadline_inps": "Contributi INPS Gestione Separata",

    # Amortization
    "amort_laptop": "Laptop / PC",
    "amort_furniture": "Mobili e Arredi",
    "amort_machinery": "Macchinari",
    "amort_vehicle": "Veicoli",
    "amort_renovation": "Ristrutturazione",
    "amort_years": "anni di ammortamento",
    "amort_annual": "Quota annua",
    "amort_remaining": "Valore residuo",
    "amort_alert": "Hai acquistato {} per €{:.2f} il {} ma non hai avviato l'ammortamento — risparmia ~€{:.2f} ripartendo in {} anni",

    # Status bar
    "status_expenses": "{} spese",
    "status_pending": "{} da classificare",
    "status_last_sync": "Ultimo aggiornamento: {}",
    "status_ready": "Pronto",

    # Errors
    "error_title": "Errore",
    "error_tesseract": "Tesseract non trovato. Installa tesseract-ocr.",
    "error_db": "Errore database: {}",
    "error_db_corrupt": "Database corrotto. Ripristinare da backup?",
    "error_llm": "Errore LLM: {}",
    "error_pdf": "Errore generazione PDF: {}",
    "error_api_key": "Chiave API mancante o non valida",
    "error_file_type": "Tipo file non supportato. Usa PDF, PNG o JPG.",

    # Success
    "success_saved": "Salvato con successo",
    "success_classified": "Classificazione completata",
    "success_report": "Report generato: {}",
    "success_backup": "Backup salvato: {}",
    "success_restore": "Ripristino completato",

    # Confirmations
    "confirm_delete": "Eliminare questa spesa?",
    "confirm_delete_title": "Conferma eliminazione",
    "confirm_backup_overwrite": "Il file esiste già. Sovrascrivere?",

    # Manual entry dialog
    "manual_title": "Inserimento Manuale",
    "manual_vendor": "Fornitore",
    "manual_date": "Data (gg/mm/aaaa)",
    "manual_amount": "Importo (€)",
    "manual_vat": "IVA (€)",
    "manual_description": "Descrizione",
    "manual_category": "Categoria",
    "manual_notes": "Note",

    # VAT regimes
    "vat_normale": "IVA Normale",
    "vat_sospensione": "Acquisti in Sospensione d'Imposta",
    "vat_split_payment": "Split Payment",
    "vat_reverse_charge": "Reverse Charge",
    "vat_esente": "Esente IVA",
    "vat_forfettario": "Regime Forfettario",

    # Categories
    "cat_software": "Software e Licenze",
    "cat_hosting": "Hosting e Cloud",
    "cat_hardware": "Hardware",
    "cat_office": "Cancelleria e Ufficio",
    "cat_training": "Formazione Professionale",
    "cat_insurance": "Assicurazioni",
    "cat_accounting": "Commercialista e Consulenze",
    "cat_bank": "Spese Bancarie",
    "cat_advertising": "Pubblicità e Marketing",
    "cat_internet": "Internet e Telefonia",
    "cat_transport": "Trasporti e Auto",
    "cat_utilities": "Utenze",
    "cat_food": "Pasti di Lavoro",
    "cat_travel": "Trasferte",
    "cat_other": "Altro",
    "cat_personal": "Personale (Non Deducibile)",
    "cat_fines": "Sanzioni (Non Deducibile)",

    # About
    "about_title": "Informazioni su Dedutto",
    "about_text": (
        "Dedutto v1.0.0\n\n"
        "Gestore spese privacy-first per Partita IVA italiane.\n"
        "Tutti i dati rimangono sul tuo dispositivo.\n\n"
        "Nessun cloud. Nessun tracciamento. Solo il tuo commercialista."
    ),
}
