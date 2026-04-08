# ProfServ – Mac-First Local Expense Tracker

A local web app for tracking professional expenses, uploading receipts, entering per-diems, and exporting to Excel `.xlsx`. Built with Python + FastAPI. No database — the Excel workbook **is** the system of record.

---

## Features

- **Trip management** – create trips with date ranges; expenses are auto-matched by date
- **Receipt upload** – drag-and-drop PDF or image upload with AI extraction (Anthropic Claude or OpenAI, falls back to regex mock)
- **Review & correct** – every extracted field is editable before saving
- **Canonical file naming** – receipts are renamed to `YYYY-MM-DD - Vendor Name.ext` and stored by trip
- **Per-diem entry** – fixed rates (Breakfast $20 / Lunch $25 / Dinner $45 CAD), USD→CAD conversion using the historical exchange rate for the entered date
- **Excel workbook** – `data/expenses.xlsx` with Trips, Expenses, and Settings sheets
- **Expense list** – filter by trip, date range, type, vendor, currency, submitted status; full-text search
- **Reports** – total by trip, by type, by month, total GST captured
- **CSV export** – export any filtered view to CSV

---

## Requirements

- **macOS** (also runs on Linux/Windows)
- **Python 3.11+**
- **Tesseract OCR** (for image receipts)
  ```
  brew install tesseract
  ```
- *(Optional)* **Poppler** (for OCR fallback on scanned PDFs)
  ```
  brew install poppler
  ```

---

## Quick Start

### 1. Clone and set up

```bash
cd ProfServ
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env` as needed. The defaults work out of the box with the **mock AI provider** (no API key required).

### 3. Run

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

The workbook and folder structure are created automatically on first run.

---

## Configuration (`.env`)

| Variable | Default | Description |
|---|---|---|
| `EXTRACTION_PROVIDER` | `mock` | `mock` \| `anthropic` \| `openai` |
| `ANTHROPIC_API_KEY` | *(blank)* | Required when provider = `anthropic` |
| `OPENAI_API_KEY` | *(blank)* | Required when provider = `openai` |
| `FX_PROVIDER` | `frankfurter` | `frankfurter` (free, no key) |
| `DATA_DIR` | `data` | Where the workbook and cache are stored |
| `RECEIPTS_DIR` | `receipts` | Where uploaded receipt files are stored |
| `WORKBOOK_NAME` | `expenses.xlsx` | Workbook filename inside `DATA_DIR` |
| `BREAKFAST_AMOUNT` | `20` | Per-diem breakfast rate (CAD) |
| `LUNCH_AMOUNT` | `25` | Per-diem lunch rate (CAD) |
| `DINNER_AMOUNT` | `45` | Per-diem dinner rate (CAD) |

---

## Using Real AI Extraction

### Anthropic Claude (recommended)

1. Get an API key at [console.anthropic.com](https://console.anthropic.com)
2. In `.env`:
   ```
   EXTRACTION_PROVIDER=anthropic
   ANTHROPIC_API_KEY=sk-ant-...
   ```

### OpenAI GPT-4o

1. Get an API key at [platform.openai.com](https://platform.openai.com)
2. In `.env`:
   ```
   EXTRACTION_PROVIDER=openai
   OPENAI_API_KEY=sk-...
   ```

The provider interface is in `app/services/extraction/base.py`. Adding a new provider requires implementing `extract(raw_text, file_name) → ExtractionResult`.

---

## Folder Structure

```
ProfServ/
├── main.py                        # FastAPI app entry point
├── bootstrap.py                   # First-run setup (called by main.py)
├── config.py                      # Settings via pydantic-settings + .env
├── requirements.txt
├── .env.example
│
├── app/
│   ├── models/
│   │   ├── trip.py                # Trip, TripCreate pydantic models
│   │   └── expense.py             # Expense, ExtractionResult, filters, forms
│   │
│   ├── services/
│   │   ├── workbook_service.py    # All Excel read/write logic
│   │   ├── file_storage_service.py # Receipt file naming and storage
│   │   ├── fx_service.py          # Historical FX rates + local cache
│   │   ├── ocr_service.py         # PDF text extraction + OCR
│   │   ├── receipt_pipeline.py    # Orchestrates the ingestion stages
│   │   └── extraction/
│   │       ├── base.py            # BaseExtractor ABC
│   │       ├── factory.py         # Provider factory
│   │       ├── mock_provider.py   # Regex-based fallback (no API key)
│   │       ├── anthropic_provider.py
│   │       └── openai_provider.py
│   │
│   ├── routes/
│   │   ├── dashboard.py
│   │   ├── trips.py
│   │   ├── expenses.py
│   │   ├── receipts.py
│   │   ├── perdiem.py
│   │   └── reports.py
│   │
│   ├── templates/                 # Jinja2 HTML templates
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── error.html
│   │   ├── trips/
│   │   ├── expenses/
│   │   ├── receipts/
│   │   ├── perdiem/
│   │   └── reports/
│   │
│   └── static/css/style.css
│
├── data/
│   ├── expenses.xlsx              # The system of record (auto-created)
│   └── fx_cache.json              # Cached FX rates (auto-created)
│
└── receipts/
    ├── unassigned/                # Receipts with no trip
    └── <Trip Name>/               # One folder per trip (auto-created)
```

---

## Workbook Schema

### Trips sheet
`Trip ID | Trip Name | Start Date | End Date | Notes | Created At | Updated At`

### Expenses sheet
`Expense ID | Trip ID | Trip Name | Expense Date | Vendor Name | Expense Type | Amount Original | Currency Original | Exchange Rate to CAD | Amount CAD | GST Original | GST CAD | Source Type | Per Diem Type | Receipt File Name | Receipt File Path | Notes | Submitted Status | Created At | Updated At`

### Settings sheet
`Key | Value` – stores per-diem rates and base currency.

---

## Receipt File Naming

After user confirmation, receipt files are renamed to:
```
YYYY-MM-DD - Vendor Name.ext
```
Examples:
```
2026-03-15 - Delta Hotels Toronto.pdf
2026-03-16 - Tim Hortons.jpg
2026-03-16 - Tim Hortons (2).jpg     ← duplicate handled
```

Files are stored in `receipts/<trip-name>/` or `receipts/unassigned/`.

---

## Per-Diem Rules

| Meal | CAD Rate |
|---|---|
| Breakfast | $20 |
| Lunch | $25 |
| Dinner | $45 |

- If entered in **CAD**: Amount CAD = rate directly.
- If entered in **USD**: historical exchange rate for that date is fetched from [Frankfurter API](https://www.frankfurter.app) and cached locally. If the lookup fails, a manual override field is shown.
- The exact exchange rate used is stored in the expense record.

---

## FX Rate Caching

Rates are cached in `data/fx_cache.json` keyed by `YYYY-MM-DD:FROM:TO`. This means the same date is only fetched from the API once per currency pair.

---

## Troubleshooting

**Workbook is open in Excel and the app can't save**
Close Excel, then retry.

**OCR not working**
Install Tesseract: `brew install tesseract`

**Scanned PDF gives no text**
Install Poppler: `brew install poppler` (enables `pdf2image`)

**FX rate unavailable**
Enter the rate manually in the form. It will be cached for future use.

**AI extraction returns empty fields**
The mock provider uses regex heuristics. For better results, configure an AI provider in `.env`.
