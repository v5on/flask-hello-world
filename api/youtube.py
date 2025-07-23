from flask import Flask, jsonify, request
from yt_dlp import YoutubeDL
import re

app = Flask(__name__)

def extract_video_id(url):
    # ইউটিউব URL থেকে ভিডিও আইডি এক্সট্র্যাক্ট
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

@app.route('/api/youtube', methods=['GET'])
def get_youtube_info():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"success": False, "error": "URL parameter is required"}), 400

    video_id = extract_video_id(video_url)
    if not video_id:
        return jsonify({"success": False, "error": "Invalid YouTube URL"}), 400

    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'force_generic_extractor': True,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            # প্রিভিউ লিংক জেনারেট (ডাইরেক্ট স্ট্রিমিং লিংক)
            preview_url = None
            for fmt in info.get('formats', []):
                if fmt.get('ext') == 'mp4' and fmt.get('height'):
                    preview_url = fmt['url']
                    break

            # রেস্পন্স ফরম্যাট
            response = {
                "success": True,
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
                    "video_id": info.get('id'),
                    "view_count": info.get('view_count'),
                    "webpage_url": info.get('webpage_url'),
                    "preview_url": preview_url  # প্রিভিউ/স্ট্রিমিং লিংক
                }
            }

            # অডিও/ভিডিও ফরম্যাট প্রসেসিং
            for fmt in info.get('formats', []):
                format_info = {
                    "ext": fmt.get('ext'),
                    "filesize": fmt.get('filesize'),
                    "format_id": fmt.get('format_id'),
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
            "error": str(e)
        }), 500

if __name__ == '__main__':
    app.run()
