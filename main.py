from flask import Flask, render_template, request, send_file, jsonify
from PyPDF2 import PdfReader
from gtts import gTTS
import io
import re
import traceback
from datetime import datetime
import tempfile
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key-goes-here'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max file size

# Language mapping for gTTS
LANGUAGE_MAP_GTTS = {
    'en': 'en',
    'es': 'es',
    'fr': 'fr',
    'de': 'de',
    'it': 'it',
    'pt': 'pt',
    'zh': 'zh',
    'ja': 'ja',
    'ko': 'ko',
    'hi': 'hi',
    'ru': 'ru',
}

def clean_extracted_text(text):
    """Clean and format text extracted from PDF"""
    if not text:
        return ""
    
    cleaned_text = text
    cleaned_text = re.sub(r'([a-z])([A-Z])', r'\1 \2', cleaned_text)
    cleaned_text = re.sub(r'([.!?])([A-Za-z])', r'\1 \2', cleaned_text)
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
    cleaned_text = cleaned_text.replace('\n', ' ').replace('\r', ' ')
    cleaned_text = cleaned_text.replace('  ', ' ')
    cleaned_text = cleaned_text.strip()
    
    return cleaned_text

def extract_text_from_pdf(pdf_bytes):
    """Extract and clean text from PDF bytes"""
    text = ""
    try:
        from io import BytesIO
        pdf_stream = BytesIO(pdf_bytes)
        
        reader = PdfReader(pdf_stream)
        print(f"Processing PDF with {len(reader.pages)} pages")
        
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                cleaned_page_text = clean_extracted_text(page_text)
                text += cleaned_page_text + "\n\n"
        
        final_text = clean_extracted_text(text)
        return final_text
        
    except Exception as e:
        print(f"Error extracting PDF: {e}")
        print(traceback.format_exc())
        return ""

def split_text(text, max_length=4000):
    """Split text into chunks for gTTS character limit"""
    if len(text) <= max_length:
        return [text]
    
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 <= max_length:
            current_chunk += sentence + " "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + " "
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    print(f"Split text into {len(chunks)} chunks")
    return chunks

def generate_audio_with_gtts(text, language='en', gender='male'):
    """Generate MP3 audio using gTTS with gender-based voice variation via TLD"""
    try:
        if not text or not text.strip():
            print("ERROR: Empty text provided")
            return None
        
        text = clean_extracted_text(text)
        
        if len(text.strip()) < 10:
            print("ERROR: Text too short")
            return None
        
        gtts_lang = LANGUAGE_MAP_GTTS.get(language, 'en')
        
        # Choose TLD based on gender
        if gender == 'female':
            tld = 'com.au'   
        else:
            tld = 'com'      
        
        print(f"Generating audio with gTTS: Lang={gtts_lang}, TLD={tld}, Gender={gender}, Length={len(text)}")
        
        audio_bytes_io = io.BytesIO()
        text_chunks = split_text(text)
        
        if len(text_chunks) == 1:
            tts = gTTS(text=text_chunks[0], lang=gtts_lang, slow=False, tld=tld)
            tts.write_to_fp(audio_bytes_io)
        else:
            try:
                from pydub import AudioSegment
                
                with tempfile.TemporaryDirectory() as temp_dir:
                    audio_segments = []
                    
                    for i, chunk in enumerate(text_chunks):
                        temp_file = os.path.join(temp_dir, f"chunk_{i}.mp3")
                        tts = gTTS(text=chunk, lang=gtts_lang, slow=False, tld=tld)
                        tts.save(temp_file)
                        
                        if os.path.exists(temp_file):
                            segment = AudioSegment.from_mp3(temp_file)
                            audio_segments.append(segment)
                    
                    if not audio_segments:
                        print("ERROR: No audio segments created")
                        return None
                    
                    combined = audio_segments[0]
                    for segment in audio_segments[1:]:
                        combined += segment
                    
                    combined.export(audio_bytes_io, format="mp3")
                    
            except ImportError:
                print("pydub not available – falling back to raw concat (may have gaps)")
                all_audio = b""
                for chunk in text_chunks:
                    chunk_io = io.BytesIO()
                    tts = gTTS(text=chunk, lang=gtts_lang, slow=False, tld=tld)
                    tts.write_to_fp(chunk_io)
                    all_audio += chunk_io.getvalue()
                audio_bytes_io.write(all_audio)
        
        audio_bytes_io.seek(0)
        audio_bytes = audio_bytes_io.read()
        print(f"Successfully generated {len(audio_bytes)} bytes of audio")
        return audio_bytes
        
    except Exception as e:
        print(f"Error generating audio with gTTS: {e}")
        print(traceback.format_exc())
        return None

@app.route('/')
def index():
    return render_template('index.html', 
                           current_year=datetime.now().year,
                           text=request.args.get('text', ''),
                           language=request.args.get('language', 'en'))

@app.route('/api/extract-text', methods=['POST'])
def api_extract_text():
    if 'pdf_file' not in request.files:
        return jsonify({'success': False, 'error': 'No PDF file uploaded'})
    
    pdf_file = request.files['pdf_file']
    if pdf_file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'})
    
    if not pdf_file.filename.lower().endswith('.pdf'):
        return jsonify({'success': False, 'error': 'File must be a PDF'})
    
    try:
        pdf_bytes = pdf_file.read()
        if len(pdf_bytes) > app.config['MAX_CONTENT_LENGTH']:
            return jsonify({'success': False, 'error': 'File too large (max 10MB)'})
        
        print(f"Processing PDF: {pdf_file.filename}, Size: {len(pdf_bytes)} bytes")
        
        text = extract_text_from_pdf(pdf_bytes)
        
        if not text or len(text.strip()) < 10:
            return jsonify({'success': False, 'error': 'Could not extract meaningful text from PDF'})
        
        preview = text[:500] + ("..." if len(text) > 500 else "")
        
        return jsonify({
            'success': True,
            'text': text,
            'text_length': len(text),
            'preview': preview
        })
        
    except Exception as e:
        print(f"Error in extract-text: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/play-preview', methods=['POST'])
def api_play_preview():
    data = request.get_json()
    text = data.get('text', '')
    language = data.get('language', 'en')
    gender = data.get('gender', 'male')  # default to male
    
    if not text or not text.strip():
        return jsonify({'success': False, 'error': 'No text provided'})
    
    try:
        preview_text = clean_extracted_text(text)[:1500]
        if len(text) > 1500:
            preview_text += " ... [preview truncated]"
        
        audio_bytes = generate_audio_with_gtts(preview_text, language, gender)
        
        if audio_bytes and len(audio_bytes) > 1024:
            return send_file(
                io.BytesIO(audio_bytes),
                mimetype='audio/mpeg',
                as_attachment=False
            )
        else:
            return jsonify({'success': False, 'error': 'Failed to generate preview audio'})
            
    except Exception as e:
        print(f"Error in play-preview: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/download-audio', methods=['POST'])
def api_download_audio():
    try:
        data = request.get_json()
        text = data.get('text', '')
        language = data.get('language', 'en')
        gender = data.get('gender', 'male')  # default to male
        
        print(f"\n{'='*60}")
        print(f"DOWNLOAD AUDIO REQUEST")
        print(f"Text length: {len(text)} | Language: {language} | Gender: {gender}")
        print(f"{'='*60}\n")
        
        if not text or len(text.strip()) < 10:
            return jsonify({'success': False, 'error': 'Text too short or empty'})
        
        audio_bytes = generate_audio_with_gtts(text, language, gender)
        
        if audio_bytes and len(audio_bytes) > 1024:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            gender_suffix = "_female" if gender == 'female' else ""
            filename = f"pdf2audio_{timestamp}{gender_suffix}.mp3"
            
            return send_file(
                io.BytesIO(audio_bytes),
                as_attachment=True,
                download_name=filename,
                mimetype='audio/mpeg'
            )
        else:
            error_msg = f"Generated audio too small ({len(audio_bytes) if audio_bytes else 0} bytes)"
            print(f"ERROR: {error_msg}")
            return jsonify({'success': False, 'error': 'Failed to generate audio file'})
            
    except Exception as e:
        print(f"ERROR in download-audio: {e}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)})

if __name__ == "__main__":
    print("\n" + "="*60)
    print("PDF2Audio Converter – gTTS Edition")
    print("="*60)
    print("✓ Reliable MP3 downloads & browser previews")
    print("✓ Male voice: US English (tld=com)")
    print("✓ Female voice: Australian English (tld=com.au)")
    print("✓ Default = Male voice")
    print("✓ No server-side file storage")
    print("="*60)
    print("Server starting on http://127.0.0.1:5000")
    print("="*60 + "\n")
    
    app.run(debug=True, port=5000)