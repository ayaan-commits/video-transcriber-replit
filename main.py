import os
import uuid
import tempfile
import shutil
from flask import Flask, request, jsonify, render_template_string

import whisper
import yt_dlp

app = Flask(__name__)

# Load Whisper model at startup
print("Loading Whisper model...")
model = whisper.load_model("base")
print("Whisper model loaded!")

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Transcriber</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900">
    <div class="container mx-auto px-4 py-12">
        <div class="text-center mb-12">
            <h1 class="text-4xl md:text-5xl font-bold text-white mb-4">Video Transcriber</h1>
            <p class="text-gray-300 text-lg max-w-2xl mx-auto">
                Transcribe videos from YouTube, Instagram Reels, TikTok, Twitter/X, and more.
            </p>
        </div>

        <div class="flex justify-center gap-4 mb-8 flex-wrap">
            <span class="px-4 py-2 bg-white/10 rounded-full text-gray-300 text-sm">YouTube</span>
            <span class="px-4 py-2 bg-white/10 rounded-full text-gray-300 text-sm">Instagram</span>
            <span class="px-4 py-2 bg-white/10 rounded-full text-gray-300 text-sm">TikTok</span>
            <span class="px-4 py-2 bg-white/10 rounded-full text-gray-300 text-sm">Twitter/X</span>
        </div>

        <div class="max-w-3xl mx-auto">
            <form id="transcribeForm" class="mb-8">
                <div class="flex flex-col md:flex-row gap-4">
                    <input type="url" id="urlInput" placeholder="Paste video URL here..."
                        class="flex-1 px-6 py-4 rounded-xl bg-white/10 border border-white/20 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500">
                    <button type="submit" id="submitBtn"
                        class="px-8 py-4 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-800 rounded-xl text-white font-semibold transition-all min-w-[160px]">
                        Transcribe
                    </button>
                </div>
            </form>

            <div id="loading" class="hidden bg-white/5 border border-white/10 rounded-xl p-8 text-center mb-6">
                <div class="animate-pulse">
                    <svg class="w-16 h-16 text-purple-400 mx-auto mb-4 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                </div>
                <h3 class="text-xl font-semibold text-white mb-2">Processing your video...</h3>
                <p class="text-gray-400">Downloading audio and transcribing. This may take a minute.</p>
            </div>

            <div id="error" class="hidden bg-red-500/10 border border-red-500/30 rounded-xl p-6 mb-6">
                <h4 class="text-red-400 font-semibold mb-1">Error</h4>
                <p id="errorText" class="text-red-300"></p>
            </div>

            <div id="result" class="hidden bg-white/5 border border-white/10 rounded-xl overflow-hidden">
                <div class="bg-white/5 px-6 py-4 border-b border-white/10 flex items-center justify-between flex-wrap gap-4">
                    <div class="flex items-center gap-4">
                        <span class="px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-sm font-medium">Success</span>
                        <span id="langInfo" class="text-gray-400 text-sm"></span>
                        <span id="durationInfo" class="text-gray-400 text-sm"></span>
                    </div>
                    <button onclick="copyTranscript()" class="flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-white transition-all">
                        <span id="copyText">Copy to Clipboard</span>
                    </button>
                </div>
                <div class="p-6">
                    <h3 class="text-lg font-semibold text-white mb-4">Transcript</h3>
                    <div class="bg-black/30 rounded-lg p-4 max-h-96 overflow-y-auto">
                        <p id="transcript" class="text-gray-200 whitespace-pre-wrap leading-relaxed"></p>
                    </div>
                </div>
            </div>
        </div>

        <footer class="text-center mt-16 text-gray-500 text-sm">
            <p>Powered by OpenAI Whisper & yt-dlp</p>
        </footer>
    </div>

    <script>
        const form = document.getElementById('transcribeForm');
        const urlInput = document.getElementById('urlInput');
        const submitBtn = document.getElementById('submitBtn');
        const loading = document.getElementById('loading');
        const error = document.getElementById('error');
        const errorText = document.getElementById('errorText');
        const result = document.getElementById('result');
        const transcript = document.getElementById('transcript');
        const langInfo = document.getElementById('langInfo');
        const durationInfo = document.getElementById('durationInfo');

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const url = urlInput.value.trim();
            if (!url) return;

            loading.classList.remove('hidden');
            error.classList.add('hidden');
            result.classList.add('hidden');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Processing...';

            try {
                const response = await fetch('/transcribe', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({url})
                });
                const data = await response.json();

                if (data.success) {
                    transcript.textContent = data.transcript;
                    langInfo.textContent = data.language ? `Language: ${data.language.toUpperCase()}` : '';
                    durationInfo.textContent = data.duration ? `Duration: ${Math.floor(data.duration/60)}:${String(Math.floor(data.duration%60)).padStart(2,'0')}` : '';
                    result.classList.remove('hidden');
                } else {
                    errorText.textContent = data.error || 'Transcription failed';
                    error.classList.remove('hidden');
                }
            } catch (err) {
                errorText.textContent = err.message || 'An error occurred';
                error.classList.remove('hidden');
            } finally {
                loading.classList.add('hidden');
                submitBtn.disabled = false;
                submitBtn.textContent = 'Transcribe';
            }
        });

        function copyTranscript() {
            navigator.clipboard.writeText(transcript.textContent);
            document.getElementById('copyText').textContent = 'Copied!';
            setTimeout(() => document.getElementById('copyText').textContent = 'Copy to Clipboard', 2000);
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/transcribe', methods=['POST'])
def transcribe():
    data = request.get_json()
    url = data.get('url', '').strip()

    if not url:
        return jsonify({'success': False, 'error': 'Please provide a URL'})

    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp()
        output_template = os.path.join(temp_dir, f"{uuid.uuid4()}.%(ext)s")

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            return jsonify({'success': False, 'error': f'Download failed: {str(e)}'})

        audio_file = None
        for file in os.listdir(temp_dir):
            if file.endswith(('.mp3', '.m4a', '.wav', '.webm', '.opus', '.ogg')):
                audio_file = os.path.join(temp_dir, file)
                break

        if not audio_file:
            return jsonify({'success': False, 'error': 'Audio file not found'})

        result = model.transcribe(audio_file)

        transcript = result.get("text", "").strip()
        language = result.get("language", "unknown")
        segments = result.get("segments", [])
        duration = segments[-1]["end"] if segments else 0

        return jsonify({
            'success': True,
            'transcript': transcript,
            'language': language,
            'duration': round(duration, 2)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
