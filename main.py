# main.py - Bot-resistant YouTube API
import os
import logging
from flask import Flask, jsonify, request, send_file
from werkzeug.middleware.proxy_fix import ProxyFix
import yt_dlp
import tempfile
import re
import time
import threading
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Temporary file management
temp_dir = tempfile.mkdtemp()

# Rotating user agents to prevent bot detection
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
]

def get_random_user_agent():
    return random.choice(USER_AGENTS)

def cleanup_temp_file(file_path, delay=300):
    """Clean up temporary file after delay"""
    def cleanup():
        time.sleep(delay)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            logger.error(f"Error cleaning up temp file {file_path}: {e}")
    
    thread = threading.Thread(target=cleanup)
    thread.daemon = True
    thread.start()

def is_valid_youtube_url(url):
    """Validate YouTube URL"""
    youtube_regex = re.compile(
        r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
    return youtube_regex.match(url) is not None

def get_ytdl_options():
    """Get yt-dlp options with anti-bot measures"""
    return {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'referer': 'https://www.youtube.com/',
        'http_headers': {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        },
        'cookiefile': None,  # Explicitly disable cookies
        'extractor_args': {
            'youtube': {
                'skip': ['hls', 'dash', 'translated_subs']
            }
        }
    }

@app.route('/api/video-info')
def get_video_info():
    """Get video information with bot avoidance"""
    try:
        url = request.args.get('url')
        if not url or not is_valid_youtube_url(url.strip()):
            return jsonify({'error': 'Invalid YouTube URL', 'success': False}), 400
        
        ydl_opts = get_ytdl_options()
        
        # Retry mechanism
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    video_info = {
                        'title': info.get('title'),
                        'duration': info.get('duration'),
                        'thumbnail': info.get('thumbnail'),
                        'formats': []
                    }
                    
                    for fmt in info.get('formats', []):
                        if not fmt.get('url') or 'manifest.googlevideo.com' in fmt.get('url', ''):
                            continue
                        
                        video_info['formats'].append({
                            'format_id': fmt.get('format_id'),
                            'ext': fmt.get('ext'),
                            'quality': fmt.get('height'),
                            'filesize': fmt.get('filesize'),
                            'type': 'audio' if fmt.get('vcodec') == 'none' else 'video'
                        })
                    
                    return jsonify({'success': True, 'data': video_info})
                    
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"Attempt {attempt + 1} failed, retrying...")
                time.sleep(1)  # Add delay between retries
                ydl_opts['http_headers']['User-Agent'] = get_random_user_agent()
                
    except Exception as e:
        logger.error(f"Error getting video info: {e}")
        return jsonify({
            'error': 'Could not fetch video info. YouTube might be blocking requests. Try again later.',
            'success': False
        }), 500

@app.route('/api/download')
def download_video():
    """Download endpoint with bot avoidance"""
    try:
        url = request.args.get('url')
        if not url or not is_valid_youtube_url(url.strip()):
            return jsonify({'error': 'Invalid YouTube URL', 'success': False}), 400
        
        format_id = request.args.get('format_id')
        audio_only = request.args.get('audio_only', 'false').lower() == 'true'
        
        ydl_opts = get_ytdl_options()
        ydl_opts['outtmpl'] = os.path.join(temp_dir, '%(title)s.%(ext)s')
        
        if audio_only:
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }]
        elif format_id:
            ydl_opts['format'] = format_id
        else:
            ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]'
        
        # Retry mechanism
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)
                    
                    if audio_only:
                        filename = filename.rsplit('.', 1)[0] + '.mp3'
                    
                    if not os.path.exists(filename):
                        raise Exception("Downloaded file not found")
                    
                    cleanup_temp_file(filename)
                    return send_file(
                        filename,
                        as_attachment=True,
                        download_name=os.path.basename(filename),
                        mimetype='audio/mpeg' if audio_only else 'video/mp4'
                    )
                    
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"Attempt {attempt + 1} failed, retrying...")
                time.sleep(1)
                ydl_opts['http_headers']['User-Agent'] = get_random_user_agent()
                
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        return jsonify({
            'error': 'Could not download video. YouTube might be blocking requests. Try again later.',
            'success': False
        }), 500

@app.route('/')
def home():
    return jsonify({
        'service': 'YouTube API',
        'status': 'running',
        'tips': 'Use /api/video-info?url=YOUTUBE_URL or /api/download?url=YOUTUBE_URL'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
