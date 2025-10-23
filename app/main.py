import uuid
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse

from app.services.translator import translate_text
from app.services.file_utils import (
    detect_type,
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_text_from_txt,
    extract_text_from_csv,
    extract_text_from_xlsx,
    save_txt,
    save_docx,
    save_pdf,
    save_csv_from_flat,
    save_xlsx_from_flat,
)
from app.services.ocr import extract_text_from_image

# Paths
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
OUTPUT_DIR = STATIC_DIR / "outputs"
TEMPLATES_DIR = BASE_DIR / "templates"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Azure OpenAI Translator", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/translate")
async def api_translate(
    file: UploadFile | None = File(default=None),
    text: str | None = Form(default=None),
):
    if not file and not (text and text.strip()):
        raise HTTPException(status_code=400, detail="Provide either a file or text to translate.")

    source_text = None
    file_kind: str | None = None

    if file:
        filename = file.filename or "upload"
        file_ext = Path(filename).suffix.lower()
        file_kind = detect_type(file_ext)
        content = await file.read()

        if file_kind == "pdf":
            source_text = extract_text_from_pdf(content)
        elif file_kind == "docx":
            source_text = extract_text_from_docx(content)
        elif file_kind == "txt":
            source_text = extract_text_from_txt(content)
        elif file_kind == "csv":
            source_text = extract_text_from_csv(content)
        elif file_kind == "xlsx":
            source_text = extract_text_from_xlsx(content)
        elif file_kind == "image":
            # GPT-4o OCR (no Computer Vision)
            source_text = extract_text_from_image(content)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_ext}. Use .pdf, .docx, .txt, .csv, .xlsx, .png, .jpg, .jpeg",
            )

        if not source_text or not source_text.strip():
            raise HTTPException(status_code=422, detail="Could not extract text from uploaded file.")
    else:
        source_text = text.strip()

    # Translate via Azure OpenAI GPT-4o
    try:
        translated = translate_text(source_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation failed: {e}")

    # Persist outputs with a unique job id — dynamic per input type
    job_id = str(uuid.uuid4())
    downloads: dict[str, str] = {}

    try:
        if file_kind == "xlsx":
            xlsx_path = OUTPUT_DIR / f"{job_id}.xlsx"
            csv_path = OUTPUT_DIR / f"{job_id}.csv"
            save_xlsx_from_flat(translated, xlsx_path)
            save_csv_from_flat(translated, csv_path)
            downloads = {"xlsx": f"/download/{job_id}/xlsx", "csv": f"/download/{job_id}/csv"}

        elif file_kind == "csv":
            csv_path = OUTPUT_DIR / f"{job_id}.csv"
            xlsx_path = OUTPUT_DIR / f"{job_id}.xlsx"
            save_csv_from_flat(translated, csv_path)
            save_xlsx_from_flat(translated, xlsx_path)
            downloads = {"csv": f"/download/{job_id}/csv", "xlsx": f"/download/{job_id}/xlsx"}

        elif file_kind == "pdf":
            pdf_path = OUTPUT_DIR / f"{job_id}.pdf"
            docx_path = OUTPUT_DIR / f"{job_id}.docx"
            txt_path = OUTPUT_DIR / f"{job_id}.txt"
            save_pdf(translated, pdf_path)
            save_docx(translated, docx_path)
            save_txt(translated, txt_path)
            downloads = {
                "pdf": f"/download/{job_id}/pdf",
                "docx": f"/download/{job_id}/docx",
                "txt": f"/download/{job_id}/txt",
            }

        elif file_kind == "docx":
            docx_path = OUTPUT_DIR / f"{job_id}.docx"
            pdf_path = OUTPUT_DIR / f"{job_id}.pdf"
            txt_path = OUTPUT_DIR / f"{job_id}.txt"
            save_docx(translated, docx_path)
            save_pdf(translated, pdf_path)
            save_txt(translated, txt_path)
            downloads = {
                "docx": f"/download/{job_id}/docx",
                "pdf": f"/download/{job_id}/pdf",
                "txt": f"/download/{job_id}/txt",
            }

        elif file_kind == "txt" or file_kind is None:
            # Spec: TXT -> TXT only
            txt_path = OUTPUT_DIR / f"{job_id}.txt"
            save_txt(translated, txt_path)
            downloads = {"txt": f"/download/{job_id}/txt"}

        else:
            # Images/unknown — provide useful text outputs
            txt_path = OUTPUT_DIR / f"{job_id}.txt"
            docx_path = OUTPUT_DIR / f"{job_id}.docx"
            pdf_path = OUTPUT_DIR / f"{job_id}.pdf"
            save_txt(translated, txt_path)
            save_docx(translated, docx_path)
            save_pdf(translated, pdf_path)
            downloads = {
                "txt": f"/download/{job_id}/txt",
                "docx": f"/download/{job_id}/docx",
                "pdf": f"/download/{job_id}/pdf",
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate output files: {e}")

    return JSONResponse(
        content={
            "job_id": job_id,
            "translated_text": translated,
            "downloads": downloads,
        }
    )


@app.get("/download/{job_id}/{fmt}")
async def download(job_id: str, fmt: str):
    fmt = fmt.lower()
    path_map = {
        "txt": OUTPUT_DIR / f"{job_id}.txt",
        "docx": OUTPUT_DIR / f"{job_id}.docx",
        "pdf": OUTPUT_DIR / f"{job_id}.pdf",
        "csv": OUTPUT_DIR / f"{job_id}.csv",
        "xlsx": OUTPUT_DIR / f"{job_id}.xlsx",
    }
    if fmt not in path_map:
        raise HTTPException(status_code=400, detail="Unsupported format. Use txt, docx, pdf, csv, or xlsx.")
    path = path_map[fmt]
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found or expired.")
    media = {
        "txt": "text/plain",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pdf": "application/pdf",
        "csv": "text/csv",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }[fmt]
    return FileResponse(path, media_type=media, filename=path.name)
