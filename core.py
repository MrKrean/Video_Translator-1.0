import os
import sys
import math
import re
import glob
import pysrt
import ffmpeg
import yt_dlp
import logging
import platform
import subprocess
import asyncio
import argostranslate.package
import argostranslate.translate
from pydub import AudioSegment
from datetime import datetime
import edge_tts

class VideoTranslator:
    def __init__(self):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.ffmpeg_path = self._get_ffmpeg_path("ffmpeg")
        self.ffprobe_path = self._get_ffmpeg_path("ffprobe")
        self.temp_folder = None
        self.clean_temp_files = True
        self.temp_files_to_keep = set()
        self.temp_folders = set()
        self.cancel_process = False
        
        AudioSegment.converter = self.ffmpeg_path
        AudioSegment.ffprobe = self.ffprobe_path
        
        self._register_temp_patterns()
        
        self.language_codes = {
            "English": "en",
            "Polish": "pl",
            "Spanish": "es",
            "French": "fr",
            "German": "de",
            "Italian": "it",
            "Japanese": "ja",
            "Russian": "ru",
            "Chinese": "zh",
            "Portuguese": "pt"
        }
        
        self.edge_tts_voices = {
            "en": "en-US-GuyNeural",
            "pl": "pl-PL-MarekNeural",
            "es": "es-ES-AlvaroNeural",
            "fr": "fr-FR-HenriNeural",
            "de": "de-DE-ConradNeural",
            "it": "it-IT-DiegoNeural",
            "ja": "ja-JP-NanjoNeural",
            "ru": "ru-RU-DmitryNeural",
            "zh": "zh-CN-YunxiNeural",
            "pt": "pt-BR-AntonioNeural"
        }

        self._initialize_translation()

    def _initialize_translation(self):
        try:
            argostranslate.package.update_package_index()
            self.installed_languages = argostranslate.translate.get_installed_languages()
        except Exception as e:
            logging.error(f"Translation init error: {str(e)}")
            self.installed_languages = []

    def _register_temp_patterns(self):
        self.temp_file_patterns = [
            r'.*_extracted_audio\.(wav|mp3)$',
            r'.*_subtitles\.srt$',
            r'.*_subtitles_(?:pl|en|ru|es|fr|de|it|ja|zh|pt)\.srt$',
            r'.*_translated_audio\.(wav|mp3)$',
            r'temp_\d+\.(mp3|wav)$',
            r'.*temp_.*',
            r'^tmp.*',
            r'.*\.temp$',
            r'ffmpeg_temp\.\w+'
        ]

    def _get_ffmpeg_path(self, executable):
        if platform.system() == "Windows":
            executable += ".exe"
        
        # Sprawdź w folderze ffmpeg/
        ffmpeg_dir = os.path.join(self.script_dir, "ffmpeg_vt")
        custom_path = os.path.join(ffmpeg_dir, executable)
        
        if os.path.exists(custom_path):
            return custom_path
        
        # Sprawdź w głównym folderze skryptu
        local_path = os.path.join(self.script_dir, executable)
        if os.path.exists(local_path):
            return local_path
        
        # Sprawdź w PATH systemowym
        path = subprocess.run(f"where {executable}", capture_output=True, shell=True).stdout.decode().strip()
        if path:
            return path
        
        raise FileNotFoundError(
            f"{executable} not found. Please install ffmpeg and add to PATH or place in the 'ffmpeg' folder."
        )

    def _register_temp_file(self, file_path):
        if file_path and os.path.exists(file_path):
            self.temp_files_to_keep.discard(file_path)
            base_name = os.path.basename(file_path)
            for pattern in self.temp_file_patterns:
                if re.match(pattern, base_name):
                    self.temp_files_to_keep.discard(file_path)
                    break

    def _keep_temp_file(self, file_path):
        if file_path and os.path.exists(file_path):
            self.temp_files_to_keep.add(file_path)

    def _clean_temp_files(self):
        if not self.clean_temp_files:
            return

        if not self.temp_folder or not os.path.exists(self.temp_folder):
            return

        try:
            specific_patterns = [
                "*_extracted_audio.*",
                "*_subtitles.srt",
                "*_subtitles_*.srt",
                "*_translated_audio.*"
            ]
            
            for pattern in specific_patterns:
                for file in glob.glob(os.path.join(self.temp_folder, pattern)):
                    if file not in self.temp_files_to_keep:
                        try:
                            os.remove(file)
                            logging.info(f"Deleted temp file: {file}")
                        except Exception as e:
                            logging.warning(f"Error deleting {file}: {str(e)}")
            
            for root, dirs, files in os.walk(self.temp_folder, topdown=False):
                for file in files:
                    file_path = os.path.join(root, file)
                    if file_path not in self.temp_files_to_keep:
                        try:
                            file_match = any(
                                re.fullmatch(pattern, file) 
                                for pattern in self.temp_file_patterns
                            )
                            if file_match or "temp" in file.lower() or "tmp" in file.lower():
                                os.remove(file_path)
                                logging.info(f"Deleted temp file: {file_path}")
                        except Exception as e:
                            logging.warning(f"Error deleting file {file_path}: {str(e)}")
                
                try:
                    if not os.listdir(root):
                        os.rmdir(root)
                except Exception:
                    pass

        except Exception as e:
            logging.error(f"Error cleaning files: {str(e)}")

    def _clean_empty_folders(self):
        for folder in list(self.temp_folders):
            try:
                if os.path.exists(folder) and not os.listdir(folder):
                    os.rmdir(folder)
                    self.temp_folders.remove(folder)
                    logging.info(f"Deleted empty temp folder: {folder}")
            except Exception as e:
                logging.warning(f"Error deleting folder {folder}: {str(e)}")

    def _create_output_folder(self, base_path):
        base_name = os.path.splitext(os.path.basename(base_path))[0]
        cleaned_name = self._clean_filename(base_name)
        output_dir = os.path.dirname(base_path)
        
        counter = 1
        folder_name = cleaned_name
        while True:
            self.temp_folder = os.path.join(output_dir, folder_name)
            if not os.path.exists(self.temp_folder):
                break
            folder_name = f"{cleaned_name}_{counter}"
            counter += 1
        
        os.makedirs(self.temp_folder, exist_ok=True)
        self.temp_folders.add(self.temp_folder)
        return self.temp_folder

    def _clean_filename(self, filename):
        return re.sub(r'[\\/*?:"<>|#]', "", filename)

    def _validate_youtube_url(self, url):
        patterns = [
            r'(https?://)?(www\.)?youtube\.com/watch\?v=',
            r'(https?://)?(www\.)?youtu\.be/',
            r'(https?://)?(www\.)?youtube\.com/shorts/'
        ]
        return any(re.search(pattern, url) for pattern in patterns)

    def _check_disk_space(self, path, required_gb=2):
        try:
            if platform.system() == "Windows":
                import ctypes
                free_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p(path), None, None, ctypes.pointer(free_bytes))
                free_gb = free_bytes.value / (1024 ** 3)
            else:
                stat = os.statvfs(path)
                free_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
            
            if free_gb < required_gb:
                raise RuntimeError(
                    f"Insufficient disk space. Required: {required_gb}GB, Available: {free_gb:.2f}GB"
                )
        except Exception as e:
            logging.warning(f"Could not check disk space: {str(e)}")

    def format_time(self, seconds):
        hours = math.floor(seconds / 3600)
        seconds %= 3600
        minutes = math.floor(seconds / 60)
        seconds %= 60
        milliseconds = round((seconds - math.floor(seconds)) * 1000)
        seconds = math.floor(seconds)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

    def download_youtube_video(self, youtube_url, output_path, quality='best', progress_callback=None):
        if not self._validate_youtube_url(youtube_url):
            raise ValueError("Invalid YouTube URL")
        
        self._check_disk_space(output_path)
        
        try:
            ydl_opts = {
                'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
                'ffmpeg_location': self.ffmpeg_path,
                'progress_hooks': [lambda d: self._download_progress(d, progress_callback)],
                'quiet': True,
            }
            
            format_options = {
                'best': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                '1080p': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                '720p': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                '480p': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                '360p': 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                '240p': 'bestvideo[height<=240][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                '144p': 'bestvideo[height<=144][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            }
            
            ydl_opts['format'] = format_options.get(quality, 'best')
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(youtube_url, download=True)
                video_filename = ydl.prepare_filename(info_dict)
                
                output_folder = self._create_output_folder(video_filename)
                new_path = os.path.join(output_folder, os.path.basename(video_filename))
                os.rename(video_filename, new_path)
                self._keep_temp_file(new_path)
                
            return new_path
        except Exception as e:
            logging.error(f"Video download error: {str(e)}")
            raise RuntimeError(f"Failed to download video: {e}")

    def _download_progress(self, d, progress_callback):
        if self.cancel_process:
            raise RuntimeError("Process cancelled by user")
        
        if progress_callback and d['status'] == 'downloading':
            percent = 10 + (d.get('downloaded_bytes', 0) / d.get('total_bytes', 1) * 30)
            progress_callback(percent)

    def extract_audio(self, video_path, progress_callback=None):
        try:
            base_name = os.path.splitext(os.path.basename(video_path))[0]
            extracted_audio = os.path.join(self.temp_folder, f"{base_name}_extracted_audio.wav")
            
            if os.path.exists(extracted_audio):
                os.remove(extracted_audio)
                
            (
                ffmpeg.input(video_path)
                .output(extracted_audio, ac=1, ar=16000)
                .overwrite_output()
                .run(cmd=self.ffmpeg_path, quiet=True)
            )
            
            self._register_temp_file(extracted_audio)
            
            if progress_callback:
                progress_callback(50)
                
            return extracted_audio
        except ffmpeg.Error as e:
            logging.error(f"FFmpeg error: {e.stderr.decode()}")
            raise RuntimeError(f"Failed to extract audio: {e}")
        except Exception as e:
            logging.error(f"Audio extraction error: {str(e)}")
            raise RuntimeError(f"Failed to extract audio: {e}")

    def transcribe(self, audio_path, progress_callback=None):
        try:
            from faster_whisper import WhisperModel
            
            model = WhisperModel(
                "small",
                device="cpu",
                compute_type="int8",
                download_root=os.path.join(self.script_dir, "whisper_models")
            )
            
            segments, info = model.transcribe(
                audio_path,
                beam_size=5
            )
            
            language = info.language
            segments_list = []
            
            for segment in segments:
                if self.cancel_process:
                    break
                    
                segments_list.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text
                })
                
            if progress_callback:
                progress_callback(60)
                
            return language, segments_list
        except ImportError:
            raise RuntimeError("faster-whisper not installed. Install with: pip install faster-whisper")
        except Exception as e:
            logging.error(f"Transcription error: {str(e)}")
            raise RuntimeError(f"Transcription error: {e}")

    def generate_subtitle_file(self, language, segments, output_path):
        try:
            base_name = os.path.splitext(os.path.basename(output_path))[0]
            subtitle_file = os.path.join(self.temp_folder, f"{base_name}_subtitles.srt")
            
            subs = pysrt.SubRipFile()
            
            for index, segment in enumerate(segments):
                sub = pysrt.SubRipItem()
                sub.index = index + 1
                
                def seconds_to_time(seconds):
                    hours = int(seconds // 3600)
                    seconds %= 3600
                    minutes = int(seconds // 60)
                    seconds %= 60
                    sec = int(seconds)
                    milliseconds = int((seconds - sec) * 1000)
                    return pysrt.SubRipTime(hours, minutes, sec, milliseconds)
                
                sub.start = seconds_to_time(segment["start"])
                sub.end = seconds_to_time(segment["end"])
                sub.text = segment["text"]
                subs.append(sub)
            
            subs.save(subtitle_file, encoding='utf-8')
            self._register_temp_file(subtitle_file)
            return subtitle_file
        except Exception as e:
            logging.error(f"Subtitle generation error: {str(e)}")
            raise RuntimeError(f"Failed to generate subtitles: {e}")

    def translate_subtitles(self, subtitle_path, from_lang, to_lang, progress_callback=None):
        try:
            subs = pysrt.open(subtitle_path)
            
            if not self.installed_languages:
                self._initialize_translation()
            
            from_lang_obj = next(
                (lang for lang in self.installed_languages if lang.code == from_lang),
                None
            )
            to_lang_obj = next(
                (lang for lang in self.installed_languages if lang.code == to_lang),
                None
            )
            
            if not from_lang_obj or not to_lang_obj:
                argostranslate.package.update_package_index()
                available_packages = argostranslate.package.get_available_packages()
                package_to_install = next(
                    (pkg for pkg in available_packages 
                     if pkg.from_code == from_lang and pkg.to_code == to_lang),
                    None
                )
                
                if package_to_install:
                    argostranslate.package.install_from_path(package_to_install.download())
                    self._initialize_translation()
                    
                    from_lang_obj = next(
                        (lang for lang in self.installed_languages if lang.code == from_lang),
                        None
                    )
                    to_lang_obj = next(
                        (lang for lang in self.installed_languages if lang.code == to_lang),
                        None
                    )
            
            if not from_lang_obj or not to_lang_obj:
                raise RuntimeError(f"No translation installed from {from_lang} to {to_lang}")
            
            translation = from_lang_obj.get_translation(to_lang_obj)
            if not translation:
                raise RuntimeError(f"Could not create translation from {from_lang} to {to_lang}")
            
            for i, sub in enumerate(subs):
                if self.cancel_process:
                    break
                    
                sub.text = translation.translate(sub.text)
                
                if progress_callback and i % 10 == 0:
                    progress = 70 + (i / len(subs)) * 10
                    progress_callback(progress)
            
            base_name = os.path.splitext(os.path.basename(subtitle_path))[0]
            translated_subtitle_path = os.path.join(self.temp_folder, f"{base_name}_subtitles_{to_lang}.srt")
            
            subs.save(translated_subtitle_path, encoding='utf-8')
            self._register_temp_file(translated_subtitle_path)
            
            if progress_callback:
                progress_callback(80)
                
            return translated_subtitle_path
        except Exception as e:
            logging.error(f"Translation error: {str(e)}")
            raise RuntimeError(f"Translation error: {e}")

    async def _generate_edge_tts_audio(self, text, output_file, voice):
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_file)

    def generate_translated_audio(self, subtitle_path, output_path, to_lang="en", progress_callback=None):
        try:
            subs = pysrt.open(subtitle_path)
            combined = AudioSegment.silent(duration=0)
            temp_files = []
            
            voice = self.edge_tts_voices.get(to_lang, "en-US-GuyNeural")
            
            for i, sub in enumerate(subs):
                if self.cancel_process:
                    break
                    
                start_time = sub.start.ordinal / 1000.0
                temp_file = os.path.join(self.temp_folder, f"temp_{i}.mp3")
                
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self._generate_edge_tts_audio(sub.text, temp_file, voice))
                    loop.close()
                    
                    temp_files.append(temp_file)
                    self._register_temp_file(temp_file)
                    
                    audio = AudioSegment.from_mp3(temp_file)
                    silent_duration = max(0, start_time * 1000 - len(combined))
                    combined += AudioSegment.silent(duration=silent_duration)
                    combined += audio
                    
                    if progress_callback and i % 5 == 0:
                        progress = 80 + (i / len(subs)) * 15
                        progress_callback(progress)
                except Exception as e:
                    logging.warning(f"Failed to generate TTS for segment {i}: {str(e)}")
                    continue
            
            base_name = os.path.splitext(os.path.basename(output_path))[0]
            translated_audio_path = os.path.join(self.temp_folder, f"{base_name}_translated_audio.wav")
            self._register_temp_file(translated_audio_path)
            
            combined.export(translated_audio_path, format='wav')
            
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                except:
                    pass
            
            if progress_callback:
                progress_callback(95)
                
            return translated_audio_path
        except Exception as e:
            logging.error(f"Audio generation error: {str(e)}")
            raise RuntimeError(f"Audio generation error: {e}")

    def replace_audio(self, video_path, audio_path, output_path, progress_callback=None):
        try:
            if progress_callback:
                progress_callback(96)
            
            command = [
                self.ffmpeg_path,
                "-i", video_path,
                "-i", audio_path,
                "-c:v", "copy",
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-shortest",
                "-y",
                output_path,
            ]
            
            subprocess.run(
                command, 
                check=True, 
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self._keep_temp_file(output_path)
            
            if progress_callback:
                progress_callback(100)
            
            return output_path
        except subprocess.CalledProcessError as e:
            logging.error(f"FFmpeg error: {e.stderr.decode()}")
            raise RuntimeError(f"Failed to replace audio track: {e}")
        except Exception as e:
            logging.error(f"Failed to replace audio: {str(e)}")
            raise RuntimeError(f"Failed to replace audio: {e}")

    def burn_subtitles_to_video(self, video_path, subtitle_path, output_path, style=None):
        if style is None:
            style = {
                'fontsize': 24,
                'fontcolor': 'white',
                'boxcolor': 'black@0.5',
                'box': 1,
                'borderw': 1,
                'bordercolor': 'black',
                'position': 'bottom',
                'alignment': 'center',
                'fontfamily': 'Arial'
            }

        try:
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

            input_video = ffmpeg.input(video_path)
            
            output = ffmpeg.output(
                input_video,
                output_path,
                vf=subtitle_filter,
                acodec='copy',
                vcodec='libx264',
                crf=18,
                preset='fast'
            )
            
            output.run(cmd=self.ffmpeg_path, overwrite_output=True)
            self._keep_temp_file(output_path)
            return output_path
            
        except ffmpeg.Error as e:
            logging.error(f"FFmpeg error: {e.stderr.decode()}")
            raise RuntimeError(f"Failed to burn subtitles: {e}")
        except Exception as e:
            logging.error(f"Error burning subtitles: {str(e)}")
            raise RuntimeError(f"Error burning subtitles: {e}")

    def process_local_video(self, video_path, from_lang="en", to_lang="pl", output_dir=None, progress_callback=None, add_subtitles=False, subtitle_style=None):
        try:
            self._create_output_folder(video_path)
            
            if progress_callback:
                progress_callback(40)
            logging.info("Extracting audio...")
            audio_path = self.extract_audio(video_path, progress_callback)
            
            if progress_callback:
                progress_callback(50)
            logging.info("Transcribing audio...")
            language, segments = self.transcribe(audio_path, progress_callback)
            
            if progress_callback:
                progress_callback(60)
            logging.info("Generating subtitles...")
            subtitle_path = self.generate_subtitle_file(language, segments, video_path)
            
            if progress_callback:
                progress_callback(70)
            logging.info("Translating subtitles...")
            translated_subtitle_path = self.translate_subtitles(subtitle_path, language, to_lang, progress_callback)
            
            if progress_callback:
                progress_callback(80)
            logging.info("Generating translated audio...")
            translated_audio_path = self.generate_translated_audio(translated_subtitle_path, video_path, to_lang, progress_callback)
            
            if progress_callback:
                progress_callback(95)
            logging.info("Replacing audio track...")
            
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            final_filename = f"{video_name}_translated.mp4"
            final_video_path = os.path.join(self.temp_folder, final_filename)
            
            final_video_path = self.replace_audio(
                video_path, 
                translated_audio_path, 
                final_video_path, 
                progress_callback
            )

            if add_subtitles:
                final_with_subs = os.path.join(self.temp_folder, f"{video_name}_with_subs.mp4")
                self.burn_subtitles_to_video(final_video_path, translated_subtitle_path, final_with_subs, subtitle_style)
                final_video_path = final_with_subs
            
            logging.info(f"Translated video saved as: {final_video_path}")
            return final_video_path
            
        except Exception as e:
            logging.error(f"Translation process error: {str(e)}")
            raise
        finally:
            self._clean_temp_files()

    def main(self, youtube_url, from_lang="en", to_lang="pl", output_dir=None, quality='best', progress_callback=None, add_subtitles=False, subtitle_style=None):
        if output_dir is None:
            output_dir = self.script_dir
        
        try:
            if progress_callback:
                progress_callback(10)
            logging.info(f"Downloading YouTube video in quality: {quality}...")
            video_path = self.download_youtube_video(youtube_url, output_dir, quality, progress_callback)
            
            if progress_callback:
                progress_callback(40)
            logging.info("Extracting audio...")
            audio_path = self.extract_audio(video_path, progress_callback)
            
            if progress_callback:
                progress_callback(50)
            logging.info("Transcribing audio...")
            language, segments = self.transcribe(audio_path, progress_callback)
            
            if progress_callback:
                progress_callback(60)
            logging.info("Generating subtitles...")
            subtitle_path = self.generate_subtitle_file(language, segments, video_path)
            
            if progress_callback:
                progress_callback(70)
            logging.info("Translating subtitles...")
            translated_subtitle_path = self.translate_subtitles(subtitle_path, from_lang, to_lang, progress_callback)
            
            if progress_callback:
                progress_callback(80)
            logging.info("Generating translated audio...")
            translated_audio_path = self.generate_translated_audio(translated_subtitle_path, video_path, to_lang, progress_callback)
            
            if progress_callback:
                progress_callback(95)
            logging.info("Replacing audio track...")
            
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            final_filename = f"{video_name}_translated.mp4"
            final_video_path = os.path.join(self.temp_folder, final_filename)
            
            final_video_path = self.replace_audio(
                video_path, 
                translated_audio_path, 
                final_video_path, 
                progress_callback
            )

            if add_subtitles:
                final_with_subs = os.path.join(self.temp_folder, f"{video_name}_with_subs.mp4")
                self.burn_subtitles_to_video(final_video_path, translated_subtitle_path, final_with_subs, subtitle_style)
                final_video_path = final_with_subs
            
            logging.info(f"Translated video saved as: {final_video_path}")
            return final_video_path
            
        except Exception as e:
            logging.error(f"Translation process error: {str(e)}")
            raise
        finally:
            self._clean_temp_files()

    def cancel(self):
        self.cancel_process = True
        if self.clean_temp_files:
            self._clean_temp_files()