# main.py - Ultimate anti-block YouTube API
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
import socket
import socks

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Temporary file management
temp_dir = tempfile.mkdtemp()

# Enhanced user agents and headers
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36'
]

def get_random_user_agent():
    return random.choice(USER_AGENTS)

def get_random_ip():
    return f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"

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
    """Get yt-dlp options with advanced anti-bot measures"""
    headers = {
        'User-Agent': get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'X-Forwarded-For': get_random_ip()
    }
    
    return {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'referer': 'https://www.youtube.com/',
        'http_headers': headers,
        'cookiefile': None,
        # Proxy settings (uncomment if you have proxies available)
        # 'proxy': 'socks5://your-proxy-ip:port',
        'socket_timeout': 30,
        'extractor_args': {
            'youtube': {
                'skip': ['hls', 'dash', 'translated_subs'],
                'player_client': ['android', 'web'],
                'player_skip': ['configs', 'webpage']
            }
        },
        'compat_opts': {
            'youtube-skip-dash-manifest': True,
            'youtube-skip-hls-manifest': True
        }
    }

@app.route('/api/video-info')
def get_video_info():
    """Get video information with advanced bot avoidance"""
    try:
        url = request.args.get('url')
        if not url or not is_valid_youtube_url(url.strip()):
            return jsonify({'error': 'Invalid YouTube URL', 'success': False}), 400
        
        # Clean URL by removing tracking parameters
        clean_url = url.split('?')[0]
        
        ydl_opts = get_ytdl_options()
        
        # Enhanced retry mechanism
        max_retries = 5
        backoff_factor = 1.5
        
        for attempt in range(max_retries):
            try:
                # Rotate user agent and IP for each attempt
                ydl_opts['http_headers']['User-Agent'] = get_random_user_agent()
                ydl_opts['http_headers']['X-Forwarded-For'] = get_random_ip()
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(clean_url, download=False)
                    
                    if not info:
                        raise Exception("No video info returned")
                    
                    # Simplified but comprehensive response
                    video_info = {
                        'title': info.get('title'),
                        'duration': info.get('duration'),
                        'thumbnail': info.get('thumbnail'),
                        'view_count': info.get('view_count'),
                        'uploader': info.get('uploader'),
                        'formats': []
                    }
                    
                    # Process formats with better filtering
                    for fmt in info.get('formats', []):
                        if not fmt.get('url') or any(x in fmt.get('url', '') for x in ['manifest.googlevideo.com', 'm3u8']):
                            continue
                        
                        format_info = {
                            'format_id': fmt.get('format_id'),
                            'ext': fmt.get('ext'),
                            'quality': fmt.get('height'),
                            'filesize': fmt.get('filesize'),
                            'type': 'audio' if fmt.get('vcodec') == 'none' else 'video',
                            'fps': fmt.get('fps'),
                            'tbr': fmt.get('tbr')
                        }
                        
                        # Only add if we have essential info
                        if format_info['quality'] or format_info['type'] == 'audio':
                            video_info['formats'].append(format_info)
                    
                    return jsonify({'success': True, 'data': video_info})
                    
            except yt_dlp.utils.DownloadError as e:
                if "Sign in to confirm you're not a bot" in str(e):
                    logger.warning(f"Bot detection triggered on attempt {attempt + 1}")
                    if attempt == max_retries - 1:
                        return jsonify({
                            'error': 'YouTube is blocking requests. Please try again later or use a different network.',
                            'success': False
                        }), 429
                else:
                    raise
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
            
            # Exponential backoff
            sleep_time = backoff_factor ** (attempt + 1)
            time.sleep(sleep_time)
                
    except Exception as e:
        logger.error(f"Final error getting video info: {e}")
        return jsonify({
            'error': 'YouTube is currently blocking requests. This is not a problem with your app but with YouTube\'s bot detection.',
            'success': False,
            'tip': 'Try again in a few hours or consider using proxies if this persists'
        }), 500

@app.route('/')
def home():
    return jsonify({
        'service': 'YouTube API',
        'status': 'running',
        'endpoints': {
            '/api/video-info': 'Get video information',
            '/api/download': 'Download video/audio'
        },
        'warning': 'YouTube may block requests if used excessively'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
