# PDF2Audio - Convert PDF to Audio (MP3)

**PDF2Audio** is a free, easy-to-use web app that converts text or PDF documents into high-quality MP3 audio files using Text-to-Speech (TTS). Perfect for listening to books, articles, notes, or any document on the go!

### Live Demo
[https://your-app.onrender.com](https://your-app.onrender.com)

### Features
- **Two input modes**: Paste text directly or upload a PDF file (up to 10MB)
- **Accurate PDF text extraction** using PyPDF2
- **Natural-sounding audio** powered by Google TTS (gTTS)
- **Voice selection**: Male (US English) or Female (Australian English) voice
- **Instant browser preview** – listen before downloading
- **Direct MP3 download** with timestamped filenames
- **Responsive & modern UI** built with Bootstrap 5
- **No data stored** – everything processed in memory for privacy

### Tech Stack
- **Backend**: Python + Flask
- **TTS Engine**: gTTS (Google Text-to-Speech)
- **PDF Processing**: PyPDF2
- **Audio Handling**: pydub (for seamless long-text concatenation)
- **Frontend**: HTML5, Bootstrap 5, Font Awesome, Custom CSS/JS
- **Deployment**: Render.com

### Local Setup & Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/olatideenoch/pdf2audio.git
   cd pdf2audio
