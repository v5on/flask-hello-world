from flask import Flask, request, jsonify
import requests
import re
from urllib.parse import parse_qs
import json

app = Flask(__name__)

def extract_video_id(url):
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
    try:
        # Use youtube-dl or similar library in production
        # This is a simplified version for demo purposes
        info_url = f"https://www.youtube.com/get_video_info?video_id={video_id}"
        response = requests.get(info_url)
        
        if response.status_code != 200:
            return None
            
        query = parse_qs(response.text)
        if 'player_response' not in query:
            return None
            
        player_response = json.loads(query['player_response'][0])
        return player_response
    except Exception as e:
        print(f"Error getting video info: {e}")
        return None

def format_response(video_data):
    video_details = video_data.get('videoDetails', {})
    streaming_data = video_data.get('streamingData', {})
    
    formats = {
        "audio": [],
        "video": []
    }
    
    # Parse formats (simplified - use youtube-dl in production)
    if 'formats' in streaming_data:
        for fmt in streaming_data['formats']:
            formats['video'].append({
                "ext": fmt.get('mimeType', '').split('/')[-1].split(';')[0],
                "filesize": fmt.get('contentLength'),
                "format_id": fmt.get('itag'),
                "quality_label": fmt.get('qualityLabel', ''),
                "type": "video_with_audio" if fmt.get('audioQuality') else "video_only",
                "url": fmt.get('url')
            })
    
    if 'adaptiveFormats' in streaming_data:
        for fmt in streaming_data['adaptiveFormats']:
            if fmt.get('audioQuality'):
                formats['audio'].append({
                    "ext": fmt.get('mimeType', '').split('/')[-1].split(';')[0],
                    "filesize": fmt.get('contentLength'),
                    "format_id": fmt.get('itag'),
                    "quality_label": fmt.get('qualityLabel', ''),
                    "type": "audio_only",
                    "url": fmt.get('url')
                })
            else:
                formats['video'].append({
                    "ext": fmt.get('mimeType', '').split('/')[-1].split(';')[0],
                    "filesize": fmt.get('contentLength'),
                    "format_id": fmt.get('itag'),
                    "quality_label": fmt.get('qualityLabel', ''),
                    "type": "video_only",
                    "url": fmt.get('url')
                })
    
    return {
        "success": True,
        "data": {
            "channel": video_details.get('author', ''),
            "channel_id": video_details.get('channelId', ''),
            "description": video_details.get('shortDescription', ''),
            "duration": int(video_details.get('lengthSeconds', 0)),
            "formats": formats,
            "like_count": video_details.get('likes', 0),
            "thumbnail": f"https://i.ytimg.com/vi/{video_details.get('videoId')}/maxresdefault.jpg",
            "title": video_details.get('title', ''),
            "upload_date": "",  # Would need additional API call to get this
            "video_id": video_details.get('videoId', ''),
            "view_count": video_details.get('viewCount', ''),
            "webpage_url": f"https://www.youtube.com/watch?v={video_details.get('videoId')}"
        }
    }

@app.route('/api/info', methods=['GET'])
def video_info():
    url = request.args.get('url')
    if not url:
        return jsonify({'success': False, 'error': 'URL parameter is required'}), 400
    
    video_id = extract_video_id(url)
    if not video_id:
        return jsonify({'success': False, 'error': 'Invalid YouTube URL'}), 400
    
    video_data = get_video_info(video_id)
    if not video_data:
        return jsonify({'success': False, 'error': 'Could not fetch video info'}), 500
    
    response = format_response(video_data)
    return jsonify(response)

@app.route('/')
def home():
    return """
    <h1>YouTube Video Info API</h1>
    <p>Example request: <code>/api/info?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ</code></p>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
