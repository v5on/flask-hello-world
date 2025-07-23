# main.py - Consolidated version for Vercel
import os
import logging
from flask import Flask, jsonify, request, send_file
from werkzeug.middleware.proxy_fix import ProxyFix
import yt_dlp
import tempfile
import re
import time
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Temporary file management
temp_dir = tempfile.mkdtemp()

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

@app.route('/api/video-info')
def get_video_info():
    """Get video information without cookies"""
    try:
        url = request.args.get('url')
        if not url or not is_valid_youtube_url(url.strip()):
            return jsonify({'error': 'Invalid YouTube URL', 'success': False}), 400
        
        ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': False}
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Simplified response structure
            video_info = {
                'title': info.get('title'),
                'duration': info.get('duration'),
                'thumbnail': info.get('thumbnail'),
                'formats': []
            }
            
            # Process formats
            for fmt in info.get('formats', []):
                if not fmt.get('url') or 'manifest.googlevideo.com' in fmt.get('url', ''):
                    continue
                
                video_info['formats'].append({
                    'format_id': fmt.get('format_id'),
                    'ext': fmt.get('ext'),
                    'quality': fmt.get('height'),
                    'filesize': fmt.get('filesize'),
                    'vcodec': fmt.get('vcodec'),
                    'acodec': fmt.get('acodec')
                })
            
            return jsonify({'success': True, 'data': video_info})
            
    except Exception as e:
        logger.error(f"Error getting video info: {e}")
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/download')
def download_video():
    """Download endpoint without cookie dependencies"""
    try:
        url = request.args.get('url')
        if not url or not is_valid_youtube_url(url.strip()):
            return jsonify({'error': 'Invalid YouTube URL', 'success': False}), 400
        
        format_id = request.args.get('format_id')
        audio_only = request.args.get('audio_only', 'false').lower() == 'true'
        
        # Configure download options
        ydl_opts = {
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }
        
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
        
        # Perform download
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
        logger.error(f"Error downloading video: {e}")
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/')
def home():
    """Simple home page"""
    return jsonify({
        'service': 'YouTube Video Info API',
        'version': '1.0',
        'endpoints': {
            '/api/video-info': 'Get video information',
            '/api/download': 'Download video/audio'
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
