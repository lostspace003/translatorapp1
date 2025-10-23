import os
import base64
from openai import AzureOpenAI
from dotenv import load_dotenv

# Environment variables required:
#   AZURE_OPENAI_API_KEY
#   AZURE_OPENAI_ENDPOINT
#   AZURE_OPENAI_GPT4O_DEPLOYMENT  (single deployment for both translation and OCR)
# Optional:
#   AZURE_OPENAI_API_VERSION  (default: 2024-02-15-preview)

load_dotenv()
API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
DEPLOYMENT = os.environ.get("AZURE_OPENAI_GPT4O_DEPLOYMENT")

if not os.environ.get("AZURE_OPENAI_API_KEY") or not os.environ.get("AZURE_OPENAI_ENDPOINT") or not DEPLOYMENT:
    raise RuntimeError(
        "Missing Azure OpenAI OCR configuration. Set AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_GPT4O_DEPLOYMENT."
    )

client = AzureOpenAI(
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version=API_VERSION,
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
)

def _guess_mime(image_bytes: bytes) -> str:
    if image_bytes.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_bytes[:4] == b"GIF8":
        return "image/gif"
    return "application/octet-stream"

def extract_text_from_image(image_bytes: bytes) -> str:
    """
    OCR using Azure OpenAI GPT-4o (vision) via Chat Completions.
    Returns plain text in reading order.
    """
    mime = _guess_mime(image_bytes)
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:{mime};base64,{b64}"

    messages = [
        {
            "role": "system",
            "content": (
                "You are an OCR engine. Extract all readable text from the user-provided image. "
                "Return only the plain text in logical reading order. Do not add commentary."
            ),
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Extract the text as plain UTF-8. Preserve line breaks where appropriate."},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        },
    ]

    resp = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=messages,
        temperature=0.0,
    )
    return resp.choices[0].message.content.strip() if resp.choices else ""
