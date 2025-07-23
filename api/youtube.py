from flask import Flask, jsonify, request
import youtube_dl
import re
import traceback
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)

class VideoInfoExtractor:
    def __init__(self):
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'force_generic_extractor': True,
        }

    def extract_info(self, url):
        with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

def extract_video_id(url):
    """Extract YouTube video ID from URL"""
    query = urlparse(url)
    if query.hostname == 'youtu.be':
        return query.path[1:]
    if query.hostname in ('www.youtube.com', 'youtube.com'):
        if query.path == '/watch':
            return parse_qs(query.query)['v'][0]
        if query.path.startswith(('/embed/', '/v/')):
            return query.path.split('/')[2]
    return None

@app.route('/api/youtube', methods=['GET'])
def get_youtube_info():
    try:
        video_url = request.args.get('url')
        if not video_url:
            return jsonify({"success": False, "error": "URL parameter is required"}), 400

        video_id = extract_video_id(video_url)
        if not video_id:
            return jsonify({"success": False, "error": "Invalid YouTube URL"}), 400

        extractor = VideoInfoExtractor()
        info = extractor.extract_info(video_url)

        # Prepare simplified response
        response = {
            "success": True,
            "video_id": video_id,
            "title": info.get('title'),
            "duration": info.get('duration'),
            "view_count": info.get('view_count'),
            "thumbnail": info.get('thumbnail'),
            "formats": self._process_formats(info.get('formats', []))
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to fetch video info"
        }), 500

def _process_formats(self, formats):
    """Process and simplify formats information"""
    simplified_formats = []
    for fmt in formats:
        simplified_formats.append({
            "url": fmt.get('url'),
            "ext": fmt.get('ext'),
            "quality": fmt.get('height'),
            "type": "video" if fmt.get('height') else "audio"
        })
    return simplified_formats

# Vercel requires this
application = app

if __name__ == '__main__':
    app.run(debug=True)
