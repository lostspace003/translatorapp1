# Azure OpenAI Translator (FastAPI + Tailwind)

Translate **French → English** using **Azure OpenAI (GPT‑4o)**. Upload PDFs, DOCX, TXT, or images (OCR via Azure OpenAI (GPT‑4 vision, e.g., gpt‑4o)). See results inline and download as **TXT**, **DOCX**, or **PDF**. Ships with **GitHub Actions** CI/CD to **Azure App Service (B1)**.

---

## Features
- FastAPI backend with simple, clean Tailwind UI
- Accepts: `.pdf`, `.docx`, `.txt`, `.csv`, `.xlsx`, `.png`, `.jpg`, `.jpeg`
- OCR for images via **Azure Computer Vision Read API**
- Translation & OCR via **Azure OpenAI GPT‑4o** (Chat Completions)
- Chunking for long documents; preserves paragraphs & list structure
- Download translated output as **TXT**, **DOCX**, **PDF**
- One-click deploy via GitHub Actions to **Azure App Service**

---

## Prerequisites
1. **Azure OpenAI** resource
   - Create a **GPT‑4o** (vision-capable chat) deployment (e.g., `gpt4o-all`).
2. A **vision-capable GPT‑4 deployment** in Azure OpenAI (e.g., `gpt-4o`) for OCR.
3. **Azure App Service** (Linux, Python 3.10) on **B1** App Service Plan.
4. A **GitHub** repository (for CI/CD).

---

## Local Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env and set:
# AZURE_OPENAI_API_KEY=...
# AZURE_OPENAI_ENDPOINT=...
# AZURE_OPENAI_GPT4O_DEPLOYMENT=gpt-4o

uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000

---

## Deploy to Azure App Service (B1) with GitHub Actions

### 1) Create resources
- Create a **Resource Group**.
- Create an **App Service Plan** (B1) and a **Web App** (Linux, runtime: Python 3.10).
- Create **Azure OpenAI** + **GPT‑4o** deployment (single deployment for both translation & OCR) and note `endpoint`, `api key`, `deployment name`.
- (Optional) Create **Computer Vision** for OCR and note `endpoint` and `key`.

### 2) Configure Web App Settings
In **Azure Portal → Your Web App → Configuration → Application settings**, add:
- `AZURE_OPENAI_API_KEY` = `...`
- `AZURE_OPENAI_ENDPOINT` = `https://<your-openai-name>.openai.azure.com/`
- `AZURE_OPENAI_GPT4O_DEPLOYMENT` = your **GPT‑4o** deployment name

Also set **Startup Command** (General Settings → Startup Command):
```
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

> App Service will build with Oryx and install dependencies from `requirements.txt`.

### 3) Add GitHub Action Secret
In **Azure Portal → Your Web App → Deployment Center → Manage publish profile**, download the **Publish Profile** XML.
In your GitHub repo, go to **Settings → Secrets and variables → Actions**:
- Add new **Repository secret** named `AZURE_WEBAPP_PUBLISH_PROFILE` with the contents of the publish profile XML.

### 4) Update workflow and push
- Edit `.github/workflows/azure-webapp.yml` → set `AZURE_WEBAPP_NAME` to your Web App name.
- Commit & push to `main`. The workflow will build and deploy automatically.

---

## Usage
1. Open your site (e.g., `https://<your-app>.azurewebsites.net`).
2. Upload a file or paste French text.
3. Click **Translate**.
4. Read the translated output inline and download as **TXT**, **DOCX**, or **PDF**.

---

## Notes & Limits
- Supported files: `.pdf`, `.docx`, `.txt`, `.png`, `.jpg`, `.jpeg`.
- Legacy `.doc` is **not** supported—please convert to `.docx`.
- For image uploads, ensure **GPT‑4o** is configured via `AZURE_OPENAI_GPT4O_DEPLOYMENT`; otherwise image uploads will be rejected.
- The app performs naive chunking for long inputs to respect token limits.

---

## Security & Cost
- Keep API keys in **App Service Application settings** (not in code).
- Consider enabling **Managed Identity** and private networking in production.
- Azure OpenAI usage is billable; set usage quotas/alerts.

---

## Troubleshooting
- **500 Translation failed** → Verify `AZURE_OPENAI_*` settings and that your GPT‑4 **deployment name** is correct.
- **Image OCR not configured** → Add `AZURE_VISION_*` settings.
- **Oryx build issues** → Ensure Python version is 3.10 in App Service. Check `Log stream` for errors.
- **Slow downloads or timeouts** → Large PDFs may be slow to extract; consider increasing App Service size/tier.

---

## License
MIT

---

## Local .env
This repo includes `.env.example`. Copy to `.env` and set your three variables. Do **not** commit `.env`.


**CSV/XLSX notes:** Excel workbooks with multiple worksheets are supported. The app flattens each sheet into pipe-delimited rows and adds a `===== Sheet: <Name> =====` header so GPT‑4o can translate content while preserving table structure in the output.


**Formatting:** The translator emits Markdown (e.g., `**bold**`). The UI renders this as real bold via Marked + DOMPurify, DOCX/PDF exports apply bold formatting, and TXT exports strip the markers.

**PDF rendering:** Uses ReportLab **Platypus** (Paragraph, ListFlowable, headings) for rich layout, proper wrapping, bold/italic, lists, and optional page breaks when a block equals `---`.


### Dynamic download formats
The available downloads adapt to the uploaded file type:

- **Excel (.xlsx)** → CSV or XLSX
- **CSV (.csv)** → CSV or XLSX
- **PDF (.pdf)** → PDF, Word (.docx), or TXT
- **Word (.docx)** → Word (.docx), PDF, or TXT
- **TXT (.txt)** → TXT
- **Images (.png/.jpg/.jpeg)** → TXT, DOCX, or PDF
