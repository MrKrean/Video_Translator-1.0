import os
import platform
import subprocess
import logging
from pydub import AudioSegment

class SubtitleBurner:
    def __init__(self, ffmpeg_path, ffprobe_path, logger=None):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.logger = logger or logging.getLogger(__name__)
        
        # Ustaw ścieżki dla pydub
        AudioSegment.converter = self.ffmpeg_path
        AudioSegment.ffprobe = self.ffprobe_path

    def log_with_emoji(self, message, level=logging.INFO, emoji_type=None):
        """Funkcja pomocnicza do logowania z emoji"""
        if self.logger:
            extra = {'emoji_type': emoji_type} if emoji_type else {}
            self.logger.log(level, message, extra=extra)

    def burn_subtitles_to_video(self, video_path, subtitle_path, output_path, style=None):
        """Burn subtitles into video with customizable styling"""
        if style is None:
            style = {
                'fontfamily': 'Arial',
                'fontsize': 24,
                'fontcolor': 'white',
                'boxcolor': 'black@0.5',
                'borderw': 1,
                'bordercolor': 'black',
                'position': 'bottom',
                'alignment': 'center'
            }

        try:
            self.log_with_emoji("Burning subtitles into video...", emoji_type='SUBTITLES')
            self.log_with_emoji(f"Video: {os.path.basename(video_path)}", emoji_type='FILE')
            self.log_with_emoji(f"Subtitles: {os.path.basename(subtitle_path)}", emoji_type='FILE')
            self.log_with_emoji(f"Output: {os.path.basename(output_path)}", emoji_type='FILE')
            
            subtitle_path_escaped = subtitle_path.replace('\\', '/').replace(':', '\\:').replace("'", "\\'")
            
            color_mapping = {
                'white': '0xFFFFFF',
                'black': '0x000000',
                'red': '0xFF0000',
                'green': '0x00FF00',
                'blue': '0x0000FF',
                'yellow': '0xFFFF00',
                'cyan': '0x00FFFF',
                'magenta': '0xFF00FF'
            }
            
            fontcolor = style['fontcolor']
            if fontcolor.lower() in color_mapping:
                fontcolor = color_mapping[fontcolor.lower()]
            elif fontcolor.startswith('#'):
                fontcolor = f"0x{fontcolor[1:]}"
            else:
                fontcolor = '0xFFFFFF'
            
            boxcolor = style['boxcolor'].split('@')[0] if '@' in style['boxcolor'] else 'black'
            if boxcolor.lower() in color_mapping:
                boxcolor = color_mapping[boxcolor.lower()]
            elif boxcolor.startswith('#'):
                boxcolor = f"0x{boxcolor[1:]}"
            else:
                boxcolor = '0x000000'
            
            bg_opacity = style['boxcolor'].split('@')[1] if '@' in style['boxcolor'] else '0.5'
            boxcolor_alpha = f"{boxcolor}{int(float(bg_opacity)*255):02x}"
            
            bordercolor = style['bordercolor']
            if bordercolor.lower() in color_mapping:
                bordercolor = color_mapping[bordercolor.lower()]
            elif bordercolor.startswith('#'):
                bordercolor = f"0x{bordercolor[1:]}"
            else:
                bordercolor = '0x000000'
            
            position_mapping = {
                'top': '10',
                'middle': '(h-text_h)/2',
                'bottom': 'h-text_h-10'
            }
            position = position_mapping.get(style['position'], 'h-text_h-10')
            
            alignment_mapping = {
                'left': '1',
                'center': '2',
                'right': '3'
            }
            alignment = alignment_mapping.get(style.get('alignment', 'center'), '2')
            
            subtitle_filter = (
                f"subtitles='{subtitle_path_escaped}':"
                f"force_style='"
                f"Fontname={style.get('fontfamily', 'Arial')},"
                f"Fontsize={style['fontsize']},"
                f"PrimaryColour={fontcolor},"
                f"BackColour={boxcolor_alpha},"
                f"BorderStyle={style['borderw']},"
                f"OutlineColour={bordercolor},"
                f"Alignment={alignment},"
                f"MarginV=20'"
            )

            cmd = [
                self.ffmpeg_path,
                '-i', video_path,
                '-vf', subtitle_filter,
                '-c:a', 'copy',
                '-c:v', 'libx264',
                '-crf', '18',
                '-preset', 'fast',
                '-y',
                output_path
            ]
            
            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            )
            
            self.log_with_emoji(f"Subtitles burned successfully: {os.path.basename(output_path)}", emoji_type='COMPLETE')
            return output_path
            
        except subprocess.CalledProcessError as e:
            self.log_with_emoji(f"FFmpeg error: {str(e)}", logging.ERROR, 'ERROR')
            raise RuntimeError(f"Failed to burn subtitles: {e}")
        except Exception as e:
            self.log_with_emoji(f"Subtitle burning error: {str(e)}", logging.ERROR, 'ERROR')
            raise RuntimeError(f"Error burning subtitles: {e}")