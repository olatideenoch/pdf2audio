from flask import Flask, render_template, request, send_file, jsonify
from PyPDF2 import PdfReader
import io
import os
import re
import traceback
import requests
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key-goes-here'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB

VOICE_RSS_API_KEY = os.environ.get("VOICE_RSS_API_KEY")

# Voice RSS language + voice codes per language and gender
VOICE_RSS_VOICES = {
    "en": {"male": ("en-us", "John"),   "female": ("en-us", "Mary")},
    "es": {"male": ("es-es", "Miguel"), "female": ("es-es", "Lucia")},
    "fr": {"male": ("fr-fr", "Brice"),  "female": ("fr-fr", "Amelie")},
    "de": {"male": ("de-de", "Yannick"),"female": ("de-de", "Lena")},
    "it": {"male": ("it-it", "Luca"),   "female": ("it-it", "Federica")},
    "pt": {"male": ("pt-pt", "Heitor"), "female": ("pt-pt", "Marcia")},
    "zh": {"male": ("zh-cn", "Liang"),  "female": ("zh-cn", "Lingling")},
    "ja": {"male": ("ja-jp", "Ichiro"), "female": ("ja-jp", "Sakura")},
    "ko": {"male": ("ko-kr", "Joon"),   "female": ("ko-kr", "Sora")},
    "hi": {"male": ("hi-in", "Prabhat"),"female": ("hi-in", "Aditi")},
    "ru": {"male": ("ru-ru", "Mikhail"),"female": ("ru-ru", "Irina")},
}


# ─── TEXT CLEANING ───────────────────────────────────────────────────────────

def clean_extracted_text(text):
    """Clean and format text extracted from PDF."""
    if not text:
        return ""
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    text = re.sub(r'([.!?])([A-Za-z])', r'\1 \2', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.replace('\n', ' ').replace('\r', ' ').replace('  ', ' ')
    return text.strip()


# ─── PDF EXTRACTION ──────────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_bytes):
    """Extract and concatenate all text from every page of the PDF."""
    text = ""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        print(f"PDF has {len(reader.pages)} page(s)")
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += clean_extracted_text(page_text) + " "
        return clean_extracted_text(text)
    except Exception as e:
        print(f"PDF extraction error: {e}")
        print(traceback.format_exc())
        return ""


# ─── VOICE RSS DOWNLOAD ──────────────────────────────────────────────────────

def generate_audio_with_voice_rss(text, language="en", gender="male"):
    """
    Call Voice RSS API to generate an MP3.
    Returns raw MP3 bytes on success, None on failure.
    Docs: https://www.voicerss.org/api/
    """
    voices = VOICE_RSS_VOICES.get(language, VOICE_RSS_VOICES["en"])
    lang_code, voice_name = voices.get(gender, voices["male"])

    # Voice RSS supports up to 100 KB of text per request (~100 000 chars).
    # For very long texts we chunk and concatenate the raw MP3 bytes.
    chunks = _chunk_text(text, max_chars=3000)
    print(f"Voice RSS: {len(chunks)} chunk(s), lang={lang_code}, voice={voice_name}")

    all_audio = b""
    for i, chunk in enumerate(chunks):
        params = {
            "key":    VOICE_RSS_API_KEY,
            "src":    chunk,
            "hl":     lang_code,
            "v":      voice_name,
            "r":      "0",          # speed: -10 (slow) to 10 (fast), 0 = normal
            "c":      "MP3",
            "f":      "44khz_16bit_stereo",
            "ssml":   "false",
            "b64":    "false",
        }
        try:
            resp = requests.post(
                "https://api.voicerss.org/",
                data=params,
                timeout=60
            )
            if resp.status_code == 200 and not resp.content.startswith(b"ERROR"):
                all_audio += resp.content
                print(f"  chunk {i+1}/{len(chunks)}: {len(resp.content)} bytes OK")
            else:
                error_msg = resp.content.decode("utf-8", errors="replace")[:200]
                print(f"  chunk {i+1} Voice RSS error: {error_msg}")
                return None
        except requests.RequestException as e:
            print(f"  chunk {i+1} network error: {e}")
            return None

    print(f"Total audio: {len(all_audio)} bytes")
    return all_audio if all_audio else None


def _chunk_text(text, max_chars=3000):
    """Split text into sentence-aware chunks under max_chars."""
    if len(text) <= max_chars:
        return [text]
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks, current = [], ""
    for s in sentences:
        if len(current) + len(s) + 1 <= max_chars:
            current += s + " "
        else:
            if current:
                chunks.append(current.strip())
            current = s + " "
    if current:
        chunks.append(current.strip())
    return chunks


# ─── ROUTES ──────────

@app.route("/")
def index():
    return render_template(
        "index.html",
        current_year=datetime.now().year,
        text=request.args.get("text", ""),
        language=request.args.get("language", "en"),
    )


@app.route("/api/extract-text", methods=["POST"])
def api_extract_text():
    """Extract all text from uploaded PDF and return it as JSON."""
    if "pdf_file" not in request.files:
        return jsonify({"success": False, "error": "No PDF file uploaded"})

    pdf_file = request.files["pdf_file"]
    if not pdf_file.filename:
        return jsonify({"success": False, "error": "No file selected"})
    if not pdf_file.filename.lower().endswith(".pdf"):
        return jsonify({"success": False, "error": "File must be a PDF"})

    try:
        pdf_bytes = pdf_file.read()
        if len(pdf_bytes) > app.config["MAX_CONTENT_LENGTH"]:
            return jsonify({"success": False, "error": "File too large (max 10 MB)"})

        print(f"Extracting: {pdf_file.filename} ({len(pdf_bytes)} bytes)")
        text = extract_text_from_pdf(pdf_bytes)

        if not text or len(text.strip()) < 10:
            return jsonify({"success": False, "error": "Could not extract meaningful text from PDF"})

        return jsonify({
            "success": True,
            "text": text,            
            "text_length": len(text),
            "preview": text[:500] + ("…" if len(text) > 500 else ""),
        })
    except Exception as e:
        print(f"extract-text error: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/download-audio", methods=["POST"])
def api_download_audio():
    try:
        data = request.get_json()
        text     = data.get("text", "")
        language = data.get("language", "en")
        gender   = data.get("gender", "male")

        print(f"\n{'='*55}")
        print(f"DOWNLOAD REQUEST  lang={language}  gender={gender}  chars={len(text)}")
        print(f"{'='*55}\n")

        if not text or len(text.strip()) < 10:
            return jsonify({"success": False, "error": "Text too short or empty"})

        audio_bytes = generate_audio_with_voice_rss(text, language, gender)

        if audio_bytes and len(audio_bytes) > 1024:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename  = f"pdf2audio_{language}_{gender}_{timestamp}.mp3"
            return send_file(
                io.BytesIO(audio_bytes),
                as_attachment=True,
                download_name=filename,
                mimetype="audio/mpeg",
            )
        else:
            return jsonify({"success": False, "error": "Failed to generate audio — check your Voice RSS API key"})

    except Exception as e:
        print(f"download-audio error: {e}")
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)})

@app.route("/health")
def health():
    return jsonify(status="ok"), 200


# ─── ENTRY POINT ────────

if __name__ == "__main__":
    app.run(debug=True, port=5000)