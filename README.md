# AI Agent for Window Manufacturing Company

AI-powered assistant for analyzing customer emails and PDF files before working with MBcad / Klaes.

The system helps employees:
- analyze customer requests
- extract technical information
- detect missing data
- generate response drafts
- prepare structured summaries for MBcad/Klaes

The goal is to reduce repetitive manual work in quotation workflows.

---

# Features

- Email analysis
- PDF analysis
- Technical parameter extraction
- Missing information detection
- AI-generated response drafts
- Structured employee summaries
- Classical NLP + LLM hybrid approach

---

# Tech Stack

## Backend
- Python
- FastAPI
- Uvicorn
- Pydantic

## AI / NLP
- OpenAI API
- Transformers
- Torch
- Regex
- Classical NLP methods

## PDF / OCR
- PyMuPDF
- pytesseract
- OpenCV

## UI
- Streamlit

## Integrations
- Microsoft Graph API
- MSAL

---

# Project Structure

```txt
app/
    services/   -> business logic
    routers/    -> API endpoints
    models/     -> database models
    schemas/    -> validation
    main.py     -> application entry point

prompts/
docs/
streamlit.py
requirements.txt
```

---

# Installation

## 1. Clone project

```bash
git clone YOUR_REPOSITORY_URL
cd YOUR_PROJECT_NAME
```

---

## 2. Create virtual environment

### Windows

```powershell
python -m venv .venv
```

Activate:

```powershell
.\.venv\Scripts\Activate.ps1
```

---

## 3. Install requirements

```bash
pip install -r requirements.txt
```

---

# Environment Variables

Create `.env.local`

Example:

```env
OPENAI_API_KEY=your_key

AZURE_CLIENT_ID=your_client_id
AZURE_CLIENT_SECRET=your_secret
AZURE_TENANT_ID=your_tenant_id
```

---

# Running the Project

The project uses TWO terminals.

---

# Terminal 1 — FastAPI Backend

Activate venv:

```powershell
.\.venv\Scripts\Activate.ps1
```

Run backend:

```bash
python -m uvicorn app.main:app --reload
```

Backend runs on:

```txt
http://127.0.0.1:8000
```

Swagger documentation:

```txt
http://127.0.0.1:8000/docs
```

---

# Terminal 2 — Streamlit UI

Open SECOND terminal.

Activate venv again:

```powershell
.\.venv\Scripts\Activate.ps1
```

Run Streamlit:

```bash
streamlit run streamlit.py
```

UI opens on:

```txt
http://localhost:8501
```

---

# Microsoft Graph / Outlook Integration

OAuth callback URL:

```txt
http://localhost:8000/auth/callback
```

Used for:
- Outlook email access
- Microsoft Graph integration
- future email automation

---

# Current Workflow

1. User uploads:
   - email text
   - PDF file

2. Backend:
   - extracts PDF text
   - preprocesses text
   - extracts technical parameters

3. AI Agent:
   - analyzes request
   - detects missing data
   - generates summaries

4. UI displays:
   - extracted data
   - missing information
   - response draft
   - MBcad summary

---

# Future Plans

- Better PDF parsing
- JSON structured outputs
- CRM integration
- Outlook/Gmail integration
- MBcad workflow analysis
- Azure AI action recording
- MBcad automation assistant

---

# Important Notes

The system DOES NOT:
- calculate final pricing
- replace MBcad/Klaes
- automatically send emails

The AI assistant is designed to support employees, not replace decision-making.