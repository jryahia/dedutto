# Dedutto — Gestione Spese Partita IVA

**Applicazione desktop privacy-first per liberi professionisti italiani con Partita IVA.**

Dedutto ti aiuta a classificare le spese secondo le norme fiscali italiane, generare report PDF per il commercialista e gestire gli ammortamenti — il tutto senza mai inviare i tuoi dati a server terzi (eccetto le chiamate LLM).

---

## Funzionalità Principali

- **OCR automatico**: trascina ricevute, fatture e estratti conto (PDF/PNG/JPG) per estrarre automaticamente i dati con Tesseract
- **Classificazione LLM**: classifica le spese con qualsiasi provider AI (OpenAI, Claude, Groq, DeepSeek, OpenRouter, Gemini, endpoint custom)
- **Deducibilità italiana**: classifica in 100% deducibile, 50% uso misto, ammortizzabile o non deducibile
- **Piano di ammortamento**: calcola automaticamente le quote annue per beni strumentali
- **Report PDF**: genera report completi per il commercialista con tabelle, grafici e calendario scadenze
- **Backup cifrato**: esporta/importa tutti i dati con cifratura AES-256 (Fernet)
- **Zero cloud**: tutti i dati rimangono sul tuo dispositivo
- **Scadenze fiscali**: calendario integrato con F24, IVA trimestrale, Certificazione Unica, Redditi, IMU

---

## Prerequisiti di Sistema

### Python
```bash
python3 --version  # Richiede Python 3.11+
```

### Tesseract OCR (per OCR automatico)
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-ita

# macOS
brew install tesseract
brew install tesseract-lang  # Include italiano

# Verifica installazione
tesseract --version
tesseract --list-langs  # Deve includere 'ita'
```

### SQLCipher (opzionale — per database cifrato)
```bash
# Ubuntu/Debian
sudo apt-get install libsqlcipher-dev
pip install pysqlcipher3

# senza SQLCipher il database usa sqlite3 standard (non cifrato)
```

---

## Installazione

```bash
# 1. Clona il repository
git clone https://github.com/tuousername/dedutto.git
cd dedutto

# 2. Crea un ambiente virtuale
python3 -m venv .venv
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate      # Windows

# 3. Installa le dipendenze
pip install -r requirements.txt

# 4. Avvia l'applicazione
python main.py
```

---

## Configurazione Iniziale

### 1. Password Master
Al primo avvio ti verrà chiesta una password master (minimo 8 caratteri). Questa password viene usata per:
- Cifrare il database locale (se SQLCipher è installato)
- Cifrare i file di backup

**Conserva questa password in un luogo sicuro — non è recuperabile.**

### 2. Configurazione Provider LLM
Vai in **Modifica → Impostazioni** e configura:

| Campo | Descrizione |
|-------|-------------|
| Provider | openai, claude, openrouter, gemini, groq, deepseek, custom |
| Chiave API | La tua chiave API del provider scelto |
| Modello | Es. `gpt-4o-mini`, `claude-haiku-4-5-20251001`, `llama-3.1-8b-instant` |
| Endpoint | Solo per provider custom (OpenAI-compatibili) |

**La chiave API viene salvata solo localmente — mai trasmessa a server Dedutto.**

---

## Utilizzo

### Importare una Spesa

**Via drag-and-drop:**
1. Trascina un PDF, PNG o JPG nella zona di caricamento della Dashboard
2. L'OCR elabora il documento e propone i dati estratti
3. Verifica/correggi i dati nella finestra di anteprima
4. Clicca "Conferma Dati" per salvare

**Inserimento manuale:**
1. Vai nella scheda **Spese**
2. Clicca **+ Aggiungi**
3. Compila il modulo e salva

### Classificare le Spese

1. Seleziona una spesa nella tabella
2. Clicca **Classifica** (usa il LLM configurato)
3. Oppure clicca **Classifica Tutte** per elaborare le spese non classificate

Le classificazioni vengono salvate in cache locale per evitare chiamate ripetute.

### Generare un Report PDF

1. Vai nella scheda **Report**
2. Seleziona l'anno fiscale
3. Clicca **Genera Report PDF**
4. Scegli dove salvare il file

Il report include:
- Riepilogo finanziario (totale, deducibile, IVA recuperabile)
- Tabella spese per categoria
- Grafici mensili e per categoria
- Piano di ammortamento
- Avvisi su ammortamenti non avviati
- Calendario scadenze fiscali

### Backup e Ripristino

**Esporta backup:**
1. **File → Backup Cifrato**
2. Inserisci la password (o scegline una nuova per il file)
3. Scegli dove salvare il file `.dedutto`

**Ripristina backup:**
1. **File → Ripristina Backup**
2. Seleziona il file `.dedutto`
3. Inserisci la password del backup

---

## Regole di Classificazione Fiscale

### Deducibilità 100%
- Software e licenze
- Hosting e cloud
- Formazione professionale
- Assicurazioni professionali
- Spese bancarie e commissioni
- Commercialista e consulenze
- Pubblicità e marketing
- Cancelleria e materiali d'ufficio
- Abbonamenti professionali

### Deducibilità 50% (uso misto)
- Internet e telefono
- Spese auto (se non uso esclusivo)
- Utenze domestiche per home office

### Ammortizzabili
| Bene | Anni |
|------|------|
| Laptop / PC / Tablet | 2 anni |
| Mobili e arredi | 5 anni |
| Macchinari e attrezzature | 10 anni |
| Veicoli | 4 anni |
| Ristrutturazioni | 20 anni |
| Fabbricati | 33 anni |

### Non Deducibili
- Sanzioni e multe
- Acquisti personali
- Svago senza giustificazione commerciale

---

## Regimi IVA Supportati

| Regime | Descrizione |
|--------|-------------|
| IVA Normale | Acquisti ordinari da fornitori italiani |
| Sospensione d'Imposta | Acquisti PA con IVA in sospensione |
| Split Payment | Acquisti da/per PA |
| Reverse Charge | Servizi intracomunitari / edilizia |
| Esente IVA | Operazioni esenti ex art.10 DPR 633/72 |
| Forfettario | Per chi è in regime forfettario |

---

## Scadenze Fiscali Precaricate

- Liquidazione IVA trimestrale (Q1-Q4)
- Certificazione Unica
- Modello Redditi PF
- Contributi INPS Gestione Separata
- IMU (1ª rata e saldo)

---

## Provider LLM Supportati

| Provider | Endpoint | Note |
|----------|----------|------|
| OpenAI | api.openai.com | GPT-4o, GPT-4o-mini |
| Anthropic Claude | api.anthropic.com | Claude Opus/Sonnet/Haiku |
| OpenRouter | openrouter.ai | Aggregatore multi-modello |
| Google Gemini | generativelanguage.googleapis.com | Gemini 1.5/2.0 |
| Groq | api.groq.com | Llama, Mixtral ultra-veloce |
| DeepSeek | api.deepseek.com | DeepSeek Chat/Reasoner |
| Custom | Qualsiasi endpoint OpenAI-compatibile | LM Studio, Ollama, etc. |

---

## Privacy e Sicurezza

- **Nessun cloud**: tutti i dati in SQLite locale (opzionalmente cifrato con SQLCipher)
- **Backup cifrati**: AES-256 via PBKDF2 + Fernet
- **Nessun telemetria**: Dedutto non raccoglie dati
- **API key locale**: salvata solo nel database locale
- **Unica eccezione**: le chiamate al provider LLM inviano il testo dell'expense (fornitore, descrizione, importo) all'API del provider configurato

---

## Log e Debug

Il log dell'applicazione si trova in:
```
~/.dedutto/dedutto.log
```

---

## Struttura del Progetto

```
dedutto/
├── main.py                  # Entry point
├── requirements.txt
├── core/
│   ├── database.py          # Layer database SQLite/SQLCipher
│   ├── ocr.py               # Pipeline OCR (pytesseract)
│   ├── llm_adapter.py       # Adapter unificato LLM
│   ├── classifier.py        # Classificatore spese italiane
│   ├── amortization.py      # Tracker ammortamenti
│   ├── report.py            # Generatore PDF (ReportLab)
│   ├── backup.py            # Backup/restore cifrato
│   └── status_tracker.py    # Stato applicazione
├── ui/
│   ├── main_window.py       # Finestra principale
│   ├── dialogs.py           # Dialog: impostazioni, OCR, password
│   ├── theme.py             # Tema dark (#1E1E1E / #2E8B57)
│   └── lang/
│       ├── it.py            # Stringhe italiane
│       └── en.py            # Stringhe inglesi
└── utils/
    ├── logging.py           # Logging su file
    └── validators.py        # Validazione input
```

---

## Dipendenze Principali

| Libreria | Utilizzo |
|----------|----------|
| pytesseract | OCR da immagini |
| Pillow | Manipolazione immagini |
| PyMuPDF (fitz) | Conversione PDF → immagine |
| openai | Client per OpenAI e provider compatibili |
| anthropic | Client per Claude |
| reportlab | Generazione PDF |
| matplotlib | Grafici |
| cryptography | Cifratura backup (Fernet/PBKDF2) |
| pysqlcipher3 | Database cifrato (opzionale) |

---

## Licenza

MIT License — vedi `LICENSE` per i dettagli.

---

*Dedutto non è uno strumento di consulenza fiscale. Verifica sempre le classificazioni con il tuo commercialista.*
