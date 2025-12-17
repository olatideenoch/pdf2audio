// DOM Elements
const textInputRadio = document.getElementById('textInput');
const pdfUploadRadio = document.getElementById('pdfUpload');
const textInputArea = document.getElementById('textInputArea');
const pdfUploadArea = document.getElementById('pdfUploadArea');
const textArea = document.getElementById('textArea');
const charCount = document.getElementById('charCount');
const pdfFileInput = document.getElementById('pdfFile');
const dropArea = document.getElementById('dropArea');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const extractBtn = document.getElementById('extractBtn');
const downloadBtn = document.getElementById('downloadBtn');
const extractedTextSection = document.getElementById('extractedTextSection');
const extractedText = document.getElementById('extractedText');
const extractedCharCount = document.getElementById('extractedCharCount');
const audioPlayerSection = document.getElementById('audioPlayerSection');
const audioPlayer = document.getElementById('audioPlayer');
const playBtn = document.getElementById('playBtn');
const pauseBtn = document.getElementById('pauseBtn');
const playPreviewBtn = document.getElementById('playPreviewBtn');
const steps = document.querySelectorAll('.step');

// State variables
let extractedTextContent = '';

// Sample text initialization
const sampleText = "Welcome to PDF2Audio! This is a demonstration of how our text-to-speech converter works. You can paste your own text here or upload a PDF document. After conversion, you'll be able to download a high-quality MP3 file that you can listen to on any device.";
textArea.value = sampleText;
updateCharCount();

// =============== EVENT LISTENERS ===============

// Toggle between text input and PDF upload
textInputRadio.addEventListener('change', function() {
    if (this.checked) {
        textInputArea.classList.remove('d-none');
        pdfUploadArea.classList.add('d-none');
        extractBtn.style.display = 'none';
        
        // Adjust button layout for text input mode
        document.getElementById('extractBtnCol').classList.add('d-none');
        document.getElementById('playPreviewBtnCol').classList.replace('col-md-4', 'col-md-6');
        document.getElementById('downloadBtnCol').classList.replace('col-md-4', 'col-md-6');
        
        updateStep(1);
        
        pdfFileInput.value = '';
        fileInfo.style.display = 'none';
        extractedTextSection.style.display = 'none';
        extractedTextContent = '';
        
        downloadBtn.disabled = false;
        playPreviewBtn.disabled = false;
    }
});


pdfUploadRadio.addEventListener('change', function() {
    if (this.checked) {
        textInputArea.classList.add('d-none');
        pdfUploadArea.classList.remove('d-none');
        extractBtn.style.display = 'block';
        
        // Restore original 3-column layout for PDF mode
        document.getElementById('extractBtnCol').classList.remove('d-none');
        document.getElementById('playPreviewBtnCol').classList.replace('col-md-6', 'col-md-4');
        document.getElementById('downloadBtnCol').classList.replace('col-md-6', 'col-md-4');
        
        updateStep(1);
        
        textArea.value = '';
        updateCharCount();
        
        downloadBtn.disabled = true;
        playPreviewBtn.disabled = true;
    }
});

// Character count for text area
textArea.addEventListener('input', updateCharCount);

function updateCharCount() {
    const count = textArea.value.length;
    charCount.textContent = `${count} characters`;
}

// Drag and drop functionality
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

['dragenter', 'dragover'].forEach(eventName => {
    dropArea.addEventListener(eventName, highlight, false);
});

['dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, unhighlight, false);
});

function highlight() {
    dropArea.style.borderColor = 'var(--primary-color)';
    dropArea.style.backgroundColor = 'rgba(67, 97, 238, 0.1)';
}

function unhighlight() {
    dropArea.style.borderColor = 'var(--primary-color)';
    dropArea.style.backgroundColor = 'rgba(67, 97, 238, 0.05)';
}

dropArea.addEventListener('drop', handleDrop, false);

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    handleFiles(files);
}

pdfFileInput.addEventListener('change', function() {
    handleFiles(this.files);
});

function handleFiles(files) {
    if (files.length > 0) {
        const file = files[0];
        if (file.type === 'application/pdf') {
            displayFileInfo(file);
        } else {
            alert('Please upload a PDF file.');
            pdfFileInput.value = '';
        }
    }
}

function displayFileInfo(file) {
    fileName.textContent = file.name;
    fileSize.textContent = `Size: ${(file.size / 1024 / 1024).toFixed(2)} MB`;
    fileInfo.style.display = 'block';
    updateStep(2);
}

function removeFile() {
    pdfFileInput.value = '';
    fileInfo.style.display = 'none';
    updateStep(1);
    extractedTextSection.style.display = 'none';
    extractedTextContent = '';
    downloadBtn.disabled = true;
    playPreviewBtn.disabled = true;
}

// =============== BUTTON FUNCTIONS ===============

// Get current text based on input method
function getCurrentText() {
    if (textInputRadio.checked) {
        return textArea.value;
    } else if (pdfUploadRadio.checked) {
        return extractedTextContent || '';
    }
    return '';
}

// Get current language
function getCurrentLanguage() {
    return document.getElementById('languageSelect').value;
}

// Get current gender
function getCurrentGender() {
    const genderRadios = document.querySelectorAll('input[name="voiceGender"]');
    for (const radio of genderRadios) {
        if (radio.checked) {
            return radio.value;
        }
    }
    return 'default';
}

// Extract Text Button (PDF only)
extractBtn.addEventListener('click', async function() {
    if (!pdfFileInput.files[0]) {
        alert('Please upload a PDF file first.');
        return;
    }

    showProcessing('Extracting text from PDF...');
    extractBtn.disabled = true;

    try {
        const formData = new FormData();
        formData.append('pdf_file', pdfFileInput.files[0]);

        const response = await fetch('/api/extract-text', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            extractedTextContent = result.text;
            
            extractedText.textContent = result.preview;
            extractedCharCount.textContent = `${result.text_length} characters extracted`;
            
            extractedTextSection.style.display = 'block';
            updateStep(2);
            
            // Enable buttons after successful extraction
            downloadBtn.disabled = false;
            playPreviewBtn.disabled = false;
            
            hideProcessing();
            showSuccess('Text extracted successfully!');
            
            extractedTextSection.scrollIntoView({ behavior: 'smooth' });
        } else {
            hideProcessing();
            showError('Failed to extract text: ' + result.error);
            extractBtn.disabled = false;
        }
    } catch (error) {
        console.error('Error:', error);
        hideProcessing();
        showError('Failed to extract text. Please try again.');
        extractBtn.disabled = false;
    }
});

// Play Preview Button (streams and plays in browser)
playPreviewBtn.addEventListener('click', async function() {
    const textToPlay = getCurrentText();
    
    if (!textToPlay.trim()) {
        alert('Please enter some text or extract from PDF first.');
        return;
    }

    showProcessing('Generating audio preview...');
    playPreviewBtn.disabled = true;

    try {
        const response = await fetch('/api/play-preview', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text: textToPlay,
                language: getCurrentLanguage(),
                gender: getCurrentGender()
            })
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            audioPlayer.src = url;
            audioPlayer.play();
            audioPlayerSection.style.display = 'block';
            hideProcessing();
            showSuccess('Playing audio preview... Check your speakers!');
        } else {
            const errorData = await response.json();
            hideProcessing();
            showError('Failed to play preview: ' + (errorData.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error:', error);
        hideProcessing();
        showError('Failed to play preview. Please try again.');
    } finally {
        playPreviewBtn.disabled = false;
    }
});

// Download Audio Button
downloadBtn.addEventListener('click', async function() {
    const textToDownload = getCurrentText();
    
    if (!textToDownload.trim()) {
        alert('Please enter some text or extract from PDF first.');
        return;
    }

    showProcessing('Creating audio file...');
    downloadBtn.disabled = true;

    try {
        const response = await fetch('/api/download-audio', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text: textToDownload,
                language: getCurrentLanguage(),
                gender: getCurrentGender()
            })
        });

        if (response.ok) {
            // Get blob and create download
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            // Get filename from Content-Disposition header or use default
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = 'converted_audio.mp3';
            
            if (contentDisposition) {
                const match = contentDisposition.match(/filename="(.+)"/);
                if (match) {
                    filename = match[1];
                }
            }
            
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            hideProcessing();
            showSuccess('Audio file downloaded successfully!');
        } else {
            const errorData = await response.json();
            hideProcessing();
            showError('Failed to download audio: ' + (errorData.error || 'Unknown error'));
            downloadBtn.disabled = false;
        }
    } catch (error) {
        console.error('Error:', error);
        hideProcessing();
        showError('Failed to download audio. Please try again.');
        downloadBtn.disabled = false;
    }
});

// Audio player controls
playBtn.addEventListener('click', function() {
    if (audioPlayer.src) {
        audioPlayer.play();
    }
});

pauseBtn.addEventListener('click', function() {
    audioPlayer.pause();
});

// =============== HELPER FUNCTIONS ===============

function showProcessing(message) {
    const indicator = document.getElementById('processingIndicator');
    const text = document.getElementById('processingText');
    if (indicator && text) {
        text.textContent = message;
        indicator.style.display = 'block';
    }
}

function hideProcessing() {
    const indicator = document.getElementById('processingIndicator');
    if (indicator) {
        indicator.style.display = 'none';
    }
}

function showSuccess(message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-success alert-dismissible fade show position-fixed top-0 end-0 m-3';
    alertDiv.style.zIndex = '9999';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

function showError(message) {
    alert(message);
}

// Update step indicator
function updateStep(stepNumber) {
    steps.forEach((step, index) => {
        if (index < stepNumber) {
            step.classList.add('active');
        } else {
            step.classList.remove('active');
        }
    });
}

// =============== INITIALIZATION ===============

document.addEventListener('DOMContentLoaded', function() {
    updateStep(1);
    extractBtn.style.display = 'none';
    
    textInputRadio.checked = true;
    textInputArea.classList.remove('d-none');
    pdfUploadArea.classList.add('d-none');
    
    downloadBtn.disabled = false;
    playPreviewBtn.disabled = false;
});