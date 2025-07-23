# api.py
from flask import Flask, jsonify, request
# IMPORTANT: Using libraries like youtube-dl or yt-dlp to fetch download URLs
# often violates YouTube's Terms of Service.
# This example uses a placeholder approach to demonstrate structure.
# DO NOT use this for actual downloading without careful consideration.
import yt_dlp # You'll need to install this: pip install yt-dlp
import logging

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

# Configure yt-dlp options
# We request specific formats and metadata
ydl_opts_info = {
    'format': 'bestvideo*+bestaudio/best', # Get best available, preferring separate streams
    'noplaylist': True,
    'extract_flat': 'in_playlist', # Get metadata without downloading
    'dump_single_json': True, # Output JSON
    # Add more options as needed (e.g., proxy, user-agent if required)
}

def get_video_info(video_url):
    """Fetches video info using yt-dlp."""
    try:
        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)
            # yt-dlp's output is complex. We need to process it.
            return info_dict
    except Exception as e:
        app.logger.error(f"Error fetching video info for {video_url}: {e}")
        return None

def format_response(info_dict):
    """Formats the raw yt-dlp info into the desired JSON structure."""
    if not info_dict:
        return None

    try:
        # Basic video details
        video_data = {
            "title": info_dict.get('title'),
            "video_id": info_dict.get('id'),
            "description": info_dict.get('description'),
            "channel": info_dict.get('uploader'),
            "channel_id": info_dict.get('uploader_id'),
            "duration": info_dict.get('duration'), # In seconds
            "view_count": info_dict.get('view_count'),
            "like_count": info_dict.get('like_count'), # Might be None
            "upload_date": info_dict.get('upload_date'), # YYYYMMDD format
            "thumbnail": info_dict.get('thumbnail'),
            "webpage_url": info_dict.get('webpage_url'),
            "formats": {
                "audio": [],
                "video": []
            }
        }

        # Process available formats
        formats = info_dict.get('formats', [])
        for fmt in formats:
            format_entry = {
                "format_id": fmt.get('format_id'),
                "ext": fmt.get('ext'),
                "filesize": fmt.get('filesize'), # Can be None
                "quality_label": fmt.get('format_note') or fmt.get('height', 'N/A'),
                "type": "audio_only" if fmt.get('vcodec') == 'none' else ("video_only" if fmt.get('acodec') == 'none' else "video_with_audio"),
                "url": fmt.get('url') # Direct download URL
            }

            # Categorize formats
            if format_entry["type"] == "audio_only":
                video_data["formats"]["audio"].append(format_entry)
            else: # video_only or video_with_audio
                 video_data["formats"]["video"].append(format_entry)

        # Sort formats for better presentation (optional)
        video_data["formats"]["audio"].sort(key=lambda x: x.get("filesize", 0) or 0, reverse=True)
        video_data["formats"]["video"].sort(key=lambda x: (x.get("quality_label", "0p").rstrip('p'), x.get("filesize", 0) or 0), reverse=True)


        return {
            "success": True,
            "data": video_data
        }
    except Exception as e:
        app.logger.error(f"Error formatting response: {e}")
        return {
            "success": False,
            "error": "Failed to format video information."
        }

@app.route('/api/video_info', methods=['GET'])
def video_info():
    """API endpoint to get video information."""
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"success": False, "error": "Missing 'url' parameter."}), 400

    # Optional: Add basic URL validation here
    # if not video_url.startswith("https://www.youtube.com/watch?v=") and not video_url.startswith("https://youtu.be/"):
    #     return jsonify({"success": False, "error": "Invalid YouTube URL format."}), 400

    app.logger.info(f"Fetching info for URL: {video_url}")
    raw_info = get_video_info(video_url)

    if not raw_info:
         return jsonify({
            "success": False,
            "error": "Could not retrieve video information. The video might be unavailable, age-restricted, or the URL format is incorrect."
        }), 404 # Or 500 if it's a processing error on our side

    formatted_response = format_response(raw_info)

    if formatted_response and formatted_response.get("success"):
        return jsonify(formatted_response), 200
    else:
        error_msg = formatted_response.get("error") if formatted_response else "Unknown error during formatting."
        return jsonify({
            "success": False,
            "error": error_msg
        }), 500

# Health check endpoint (useful for Vercel)
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(debug=True) # Disable debug in production
