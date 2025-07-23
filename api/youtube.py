from flask import Flask, jsonify, request
from yt_dlp import YoutubeDL
import re
import traceback

app = Flask(__name__)

def extract_video_id(url):
    """Extract YouTube video ID from various URL formats"""
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

def format_size(bytes_size):
    """Convert bytes to human readable format"""
    if bytes_size is None:
        return None
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"

@app.route('/api/youtube', methods=['GET'])
def get_youtube_info():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({
            "success": False,
            "error": "URL parameter is required",
            "example": "/api/youtube?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        }), 400

    video_id = extract_video_id(video_url)
    if not video_id:
        return jsonify({
            "success": False,
            "error": "Invalid YouTube URL",
            "supported_formats": [
                "https://www.youtube.com/watch?v=VIDEO_ID",
                "https://youtu.be/VIDEO_ID",
                "https://www.youtube.com/embed/VIDEO_ID"
            ]
        }), 400

    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'force_generic_extractor': True,
            'format': 'best',
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            # Find the best preview URL (direct streaming link)
            preview_url = None
            best_format = None
            for fmt in info.get('formats', []):
                if fmt.get('ext') == 'mp4' and fmt.get('height'):
                    if not preview_url or (fmt.get('height', 0) > (best_format.get('height', 0) if best_format else 0):
                        preview_url = fmt['url']
                        best_format = fmt

            # Prepare response format
            response = {
                "success": True,
                "video_id": info.get('id'),
                "data": {
                    "channel": info.get('channel'),
                    "channel_id": info.get('channel_id'),
                    "description": info.get('description'),
                    "duration": info.get('duration'),
                    "formats": {
                        "audio": [],
                        "video": []
                    },
                    "like_count": info.get('like_count'),
                    "thumbnail": info.get('thumbnail'),
                    "title": info.get('title'),
                    "upload_date": info.get('upload_date'),
                    "view_count": info.get('view_count'),
                    "webpage_url": info.get('webpage_url'),
                    "preview_url": preview_url,  # Direct streaming link
                    "preview_quality": f"{best_format.get('height', 'N/A')}p" if best_format else None
                }
            }

            # Process all formats
            for fmt in info.get('formats', []):
                format_info = {
                    "ext": fmt.get('ext'),
                    "filesize": fmt.get('filesize'),
                    "filesize_readable": format_size(fmt.get('filesize')),
                    "format_id": fmt.get('format_id'),
                    "quality": fmt.get('height'),
                    "quality_label": f"{fmt.get('height', '')}p" if fmt.get('height') else fmt.get('format_note', ''),
                    "type": "video_with_audio" if fmt.get('acodec') != 'none' and fmt.get('vcodec') != 'none' 
                           else "video_only" if fmt.get('vcodec') != 'none' 
                           else "audio_only",
                    "url": fmt.get('url')
                }
                
                if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                    response["data"]["formats"]["audio"].append(format_info)
                else:
                    response["data"]["formats"]["video"].append(format_info)

            return jsonify(response)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "message": "Failed to fetch video info. Please try again later."
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
