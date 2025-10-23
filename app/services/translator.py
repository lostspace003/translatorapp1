import os
from typing import List
from dotenv import load_dotenv
from openai import AzureOpenAI

# Load .env for local dev
load_dotenv()

# Environment variables required:
#   AZURE_OPENAI_API_KEY
#   AZURE_OPENAI_ENDPOINT
#   AZURE_OPENAI_GPT4O_DEPLOYMENT  (single GPT-4o deployment for both translation & OCR)
# Optional:
#   AZURE_OPENAI_API_VERSION  (default: 2024-08-01-preview)
API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
DEPLOYMENT = os.environ.get("AZURE_OPENAI_GPT4O_DEPLOYMENT")

if not os.environ.get("AZURE_OPENAI_API_KEY") or not os.environ.get("AZURE_OPENAI_ENDPOINT") or not DEPLOYMENT:
    raise RuntimeError(
        "Missing Azure OpenAI configuration. Set AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_GPT4O_DEPLOYMENT."
    )

client = AzureOpenAI(
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version=API_VERSION,
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
)


def _chunk_text(text: str, max_chars: int = 6000) -> List[str]:
    """
    Naive chunker by characters, splitting on double newlines to avoid
    breaking paragraphs or table blocks. For CSV/XLSX 'table mode' the
    extractor inserts blank lines between sections/sheets, so this still works.
    """
    text = text or ""
    if len(text) <= max_chars:
        return [text]
    parts: List[str] = []
    current: List[str] = []
    current_len = 0
    for block in text.split("\n\n"):
        # +2 accounts for the two newlines we stripped by splitting
        block_len = len(block) + 2
        if current_len + block_len <= max_chars:
            current.append(block)
            current_len += block_len
        else:
            if current:
                parts.append("\n\n".join(current))
            current = [block]
            current_len = len(block)
    if current:
        parts.append("\n\n".join(current))
    return parts


def translate_text(french_text: str, mode: str = "document") -> str:
    """
    Translate French -> English using Azure OpenAI GPT-4o.
    mode:
      - "document": regular documents (PDF/DOCX/TXT)
      - "table": tabular data (CSV/XLSX) -> keep rows/cells strictly
      - "ocr": OCR’d text from images (noisy line breaks)
    """
    # Choose a system prompt tuned for the content type
    if mode == "table":
        sys_prompt = (
            "You are a professional translator for tabular data. Translate French into clear, natural English. "
            "Keep the table structure STRICTLY. Represent each row as pipe-delimited cells: col1 | col2 | col3. "
            "For Excel with multiple sheets, begin each sheet with an exact header line: '===== Sheet: <Name> ====='. "
            "Do not add commentary or notes. Do not say the data is encoded. Only output the translated cells."
        )
    elif mode == "ocr":
        sys_prompt = (
            "You are a professional translator. The input was extracted via OCR and may have noisy line breaks. "
            "Translate the French text into clear, natural English, preserving layout where reasonable "
            "(headings, lists, paragraphs). Do NOT add commentary."
        )
    else:
        sys_prompt = (
            "You are a professional translator. Translate the user's French text into clear, natural English. "
            "Preserve document structure, paragraph breaks, numbered lists, and headings. Do NOT add commentary."
        )

    chunks = _chunk_text(french_text)
    outputs: List[str] = []

    for ch in chunks:
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": ch},
        ]
        resp = client.chat.completions.create(
            model=DEPLOYMENT,
            messages=messages,
            temperature=0.2 if mode != "table" else 0.0,  # be stricter for tables
        )
        content = (resp.choices[0].message.content or "").strip()
        outputs.append(content)

    return "\n\n".join(outputs)
