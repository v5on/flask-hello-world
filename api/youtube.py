from flask import Flask, jsonify, request
from urllib.parse import urlparse, parse_qs
import re
import requests

app = Flask(__name__)

# Cookie-free YouTube data extractor
class YouTubeExtractor:
    @staticmethod
    def get_video_id(url):
        """Extract video ID from various YouTube URL formats"""
        patterns = [
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([^&]+)',
            r'(?:https?:\/\/)?(?:www\.)?youtu\.be\/([^?]+)',
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([^\/]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def get_video_info(video_id):
        """Get video info without cookies using YouTube oEmbed"""
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        response = requests.get(oembed_url)
        return response.json() if response.status_code == 200 else None

    @staticmethod
    def get_streaming_links(video_id):
        """Get streaming links using youtube-dl alternative approach"""
        # This is a simplified version - in production you might want to use a proxy service
        return {
            "previews": {
                "audio": f"https://yt.llscdn.com/{video_id}",
                "video_144p": f"https://yt.llscdn.com/{video_id}/144",
                "video_360p": f"https://yt.llscdn.com/{video_id}/360",
                "video_720p": f"https://yt.llscdn.com/{video_id}/720"
            },
            "downloads": {
                "audio_mp3": f"https://yt.llscdn.com/{video_id}/mp3",
                "video_mp4": f"https://yt.llscdn.com/{video_id}/mp4"
            }
        }

@app.route('/api/youtube', methods=['GET'])
def get_youtube_info():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({
            "success": False,
            "error": "URL parameter is required",
            "example": "/api/youtube?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        }), 400

    video_id = YouTubeExtractor.get_video_id(video_url)
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
        # Get basic video info
        video_info = YouTubeExtractor.get_video_info(video_id)
        if not video_info:
            return jsonify({
                "success": False,
                "error": "Could not fetch video information"
            }), 500

        # Get streaming/preview links
        streaming_links = YouTubeExtractor.get_streaming_links(video_id)

        response = {
            "success": True,
            "video_id": video_id,
            "info": {
                "title": video_info.get('title'),
                "author_name": video_info.get('author_name'),
                "thumbnail_url": video_info.get('thumbnail_url'),
                "duration": "N/A"  # oEmbed doesn't provide duration
            },
            "previews": streaming_links['previews'],
            "downloads": streaming_links['downloads']
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "An error occurred while processing your request"
        }), 500

# Vercel requires this
application = app

if __name__ == '__main__':
    app.run(debug=True)
