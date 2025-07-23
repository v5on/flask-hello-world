from flask import Flask, request, jsonify, send_file
import requests
import os
import re
from io import BytesIO
from urllib.parse import parse_qs, urlparse

app = Flask(__name__)

def extract_video_id(url):
    # Extract video ID from various YouTube URL formats
    patterns = [
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([^&]+)',
        r'(?:https?:\/\/)?(?:www\.)?youtu\.be\/([^?]+)',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([^\/]+)',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/v\/([^\/]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_video_info(video_id):
    # Fetch video info using YouTube's get_video_info endpoint
    url = f"https://www.youtube.com/get_video_info?video_id={video_id}&el=detailpage"
    response = requests.get(url)
    if response.status_code != 200:
        return None
    
    query = parse_qs(response.text)
    if 'player_response' not in query:
        return None
    
    import json
    player_response = json.loads(query['player_response'][0])
    return player_response

def get_direct_url(video_id):
    # Try to get direct download URL (simplified approach)
    url = f"https://www.youtube.com/watch?v={video_id}"
    response = requests.get(url)
    if response.status_code != 200:
        return None
    
    # This is a simplified approach - in production you'd want to use youtube-dl or similar
    # Here we just look for common patterns in the HTML
    patterns = [
        r'"url":"(https://[^"]+googlevideo.com[^"]+)"',
        r'"url_encoded_fmt_stream_map":"([^"]+)"'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response.text)
        if match:
            return match.group(1)
    return None

@app.route('/api/info', methods=['GET'])
def video_info():
    url = request.args.get('url')
    if not url:
        return jsonify({'success': False, 'error': 'URL parameter is required'}), 400
    
    video_id = extract_video_id(url)
    if not video_id:
        return jsonify({'success': False, 'error': 'Invalid YouTube URL'}), 400
    
    info = get_video_info(video_id)
    if not info:
        return jsonify({'success': False, 'error': 'Could not fetch video info'}), 500
    
    # Format the response similar to your example
    video_details = info.get('videoDetails', {})
    response_data = {
        'success': True,
        'data': {
            'video_id': video_id,
            'title': video_details.get('title', ''),
            'channel': video_details.get('author', ''),
            'channel_id': video_details.get('channelId', ''),
            'description': video_details.get('shortDescription', ''),
            'view_count': video_details.get('viewCount', ''),
            'thumbnail': f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",
            'webpage_url': f"https://www.youtube.com/watch?v={video_id}",
            'formats': {
                'audio': [],
                'video': []
            }
        }
    }
    
    # Note: In a real implementation, you'd parse the streamingData from player_response
    # and populate the formats list with actual available formats
    
    return jsonify(response_data)

@app.route('/api/download', methods=['GET'])
def download_video():
    url = request.args.get('url')
    format_type = request.args.get('type', 'video')  # 'video' or 'audio'
    quality = request.args.get('quality', 'medium')  # 'low', 'medium', 'high'
    
    if not url:
        return jsonify({'success': False, 'error': 'URL parameter is required'}), 400
    
    video_id = extract_video_id(url)
    if not video_id:
        return jsonify({'success': False, 'error': 'Invalid YouTube URL'}), 400
    
    # In a real implementation, you would:
    # 1. Use youtube-dl or similar library to get download URLs
    # 2. Choose the appropriate URL based on format_type and quality
    # 3. Stream the file to the client
    
    # This is a simplified placeholder that just redirects to YouTube
    return jsonify({
        'success': False,
        'error': 'Download functionality not implemented in this example',
        'note': 'In a real implementation, this would return the actual video/audio file'
    })

@app.route('/')
def home():
    return """
    <h1>YouTube Video Downloader API</h1>
    <p>Endpoints:</p>
    <ul>
        <li><strong>GET /api/info?url=YOUTUBE_URL</strong> - Get video info</li>
        <li><strong>GET /api/download?url=YOUTUBE_URL&type=[video|audio]&quality=[low|medium|high]</strong> - Download video/audio</li>
    </ul>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
