import os
import re
import yt_dlp
import logging

class YouTubeDownloader:
    def __init__(self, ffmpeg_path=None, logger=None):
        self.ffmpeg_path = ffmpeg_path
        self.logger = logger or logging.getLogger(__name__)
        self.quality_options = {
            'best': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            '1080p': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            '720p': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            '480p': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            '360p': 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            '240p': 'bestvideo[height<=240][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            '144p': 'bestvideo[height<=144][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        }

    def validate_url(self, url):
        """Validate if URL is a proper YouTube URL"""
        patterns = [
            r'(https?://)?(www\.)?youtube\.com/watch\?v=',
            r'(https?://)?(www\.)?youtu\.be/',
            r'(https?://)?(www\.)?youtube\.com/shorts/'
        ]
        return any(re.search(pattern, url) for pattern in patterns)

    def get_video_info(self, url):
        """Get video information without downloading"""
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'view_count': info.get('view_count', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'formats': info.get('formats', [])
                }
            except Exception as e:
                self.logger.error(f"Error getting video info: {str(e)}")
                return None

    def download(self, url, output_dir, quality='best', progress_callback=None):
        """
        Download YouTube video
        
        Args:
            url (str): YouTube URL
            output_dir (str): Directory to save the video
            quality (str): Quality setting (best, 1080p, 720p, etc.)
            progress_callback (function): Callback for progress updates
            
        Returns:
            str: Path to downloaded video file
        """
        if not self.validate_url(url):
            raise ValueError("Invalid YouTube URL")

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        ydl_opts = {
            'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
            'ffmpeg_location': self.ffmpeg_path,
            'progress_hooks': [lambda d: self._progress_hook(d, progress_callback)],
            'quiet': True,
            'no_warnings': True,
            'format': self.quality_options.get(quality, 'best')
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                self.logger.info(f"Downloaded: {filename}")
                return filename
        except Exception as e:
            self.logger.error(f"Download failed: {str(e)}")
            raise RuntimeError(f"Failed to download video: {e}")

    def _progress_hook(self, data, progress_callback):
        """Internal progress hook for yt-dlp"""
        if data['status'] == 'downloading':
            downloaded = data.get('downloaded_bytes', 0)
            total = data.get('total_bytes', 0)
            
            if total > 0:
                percent = min(100, (downloaded / total) * 100)
                if progress_callback:
                    progress_callback(percent)
                
                if int(percent) % 10 == 0:
                    self.logger.info(
                        f"Download progress: {int(percent)}% "
                        f"({downloaded/(1024*1024):.2f}MB of {total/(1024*1024):.2f}MB)"
                    )