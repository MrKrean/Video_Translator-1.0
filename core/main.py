import os
import math
import re
import glob
import pysrt
import logging
import platform
import subprocess
import argostranslate.package
import argostranslate.translate
from pydub import AudioSegment
from core.youtube_downloader import YouTubeDownloader
from core.audio_extractor import AudioExtractor
from core.audio_transcriber import AudioTranscriber
from core.audio_generator import AudioGenerator
from core.audio_replacer import AudioReplacer
from core.subtitle_burner import SubtitleBurner
from core.logging_manager import LoggingManager

class VideoTranslator:
    def __init__(self):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))       

        # Initialize logging using LoggingManager
        self.logging_manager = LoggingManager(self.script_dir)
        self.logger = self.logging_manager.initialize()
        
        # Now get ffmpeg paths
        self.ffmpeg_path = self._get_ffmpeg_path("ffmpeg")
        self.ffprobe_path = self._get_ffmpeg_path("ffprobe")
        
        self.downloader = YouTubeDownloader(ffmpeg_path=self.ffmpeg_path, logger=self.logger)
        self.audio_extractor = AudioExtractor(ffmpeg_path=self.ffmpeg_path, ffprobe_path=self.ffprobe_path, logger=self.logger)
        self.transcriber = AudioTranscriber(model_size="small", device="cpu", compute_type="int8", logger=self.logger)
        self.audio_generator = AudioGenerator(ffmpeg_path=self.ffmpeg_path, ffprobe_path=self.ffprobe_path, logger=self.logger)
        self.audio_replacer = AudioReplacer(ffmpeg_path=self.ffmpeg_path, ffprobe_path=self.ffprobe_path, logger=self.logger)
        self.subtitle_burner = SubtitleBurner(ffmpeg_path=self.ffmpeg_path, ffprobe_path=self.ffprobe_path, logger=self.logger)
        
        # Rest of initialization
        self.temp_folder = None
        self.clean_temp_files = True
        self.temp_files_to_keep = set()
        self.temp_folders = set()
        self.cancel_process = False
        
        # Definicja etapów przetwarzania i ich wag
        self.progress_stages = {
            'download': 20,       # 0-20%
            'extract_audio': 10,  # 20-30%
            'transcribe': 30,     # 30-60%
            'translate': 20,      # 60-80%
            'generate_audio': 15, # 80-95%
            'finalize': 5         # 95-100%
        }
        
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
        self._log_system_info()

    def _clean_old_logs(self, keep_last=5):
        """Czyści stare logi, zachowując tylko określoną liczbę najnowszych"""
        try:
            # Znajdź wszystkie pliki logów posortowane według daty modyfikacji
            log_files = sorted(
                glob.glob(os.path.join(self.logs_dir, 'translation_*.log')),
                key=os.path.getmtime, 
                reverse=True
            )
            
            # Usuń wszystkie poza keep_last najnowszymi
            for old_log in log_files[keep_last:]:
                try:
                    os.remove(old_log)
                    self.log_with_emoji(f"Removed old log file: {os.path.basename(old_log)}", emoji_type='CLEANUP')
                except Exception as e:
                    self.log_with_emoji(f"Error removing old log {old_log}: {str(e)}", logging.WARNING)
        except Exception as e:
            self.log_with_emoji(f"Error cleaning old logs: {str(e)}", logging.WARNING)

    def _log_system_info(self):
        """Loguje informacje o systemie"""
        self.logging_manager.log_with_emoji(f"System: {platform.system()} {platform.release()}", emoji_type='SYSTEM')
        self.logging_manager.log_with_emoji(f"Python version: {platform.python_version()}", emoji_type='SYSTEM')
        self.logging_manager.log_with_emoji(f"FFmpeg path: {self.ffmpeg_path}", emoji_type='SYSTEM')
        self.logging_manager.log_with_emoji(f"FFprobe path: {self.ffprobe_path}", emoji_type='SYSTEM')
        self.logging_manager.log_with_emoji(f"Working directory: {self.script_dir}", emoji_type='SYSTEM')
        self.logging_manager.log_with_emoji(f"Log file: {self.logging_manager.log_file}", emoji_type='SYSTEM')

    def log_with_emoji(self, message, level=logging.INFO, emoji_type=None, stage=None):
        """Funkcja pomocnicza do logowania z emoji i kolorem etapu"""
        extra = {'emoji_type': emoji_type} if emoji_type else {}
        if stage:
            extra['stage'] = stage
        self.logger.log(level, message, extra=extra)
    
    def _initialize_translation(self):
        try:
            self.log_with_emoji("Initializing translation module...", emoji_type='TRANSLATE')
            argostranslate.package.update_package_index()
            self.installed_languages = argostranslate.translate.get_installed_languages()
            
            langs = ", ".join([f"{lang.code} ({lang.name})" for lang in self.installed_languages])
            self.log_with_emoji(f"Available languages: {langs}", emoji_type='TRANSLATE')
            
            self.log_with_emoji("Translation module initialized successfully", emoji_type='COMPLETE')
        except Exception as e:
            self.log_with_emoji(f"Translation initialization error: {str(e)}", logging.ERROR, 'ERROR')
            self.installed_languages = []

    def _register_temp_patterns(self):
        """Rejestruje wzorce nazw plików tymczasowych do czyszczenia"""
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
        
        path = os.path.join(self.script_dir, executable)
        
        if not os.path.exists(path):
            with open(os.devnull, 'w') as devnull:
                path = subprocess.run(
                    f"where {executable}", 
                    capture_output=True, 
                    shell=True,
                    stdout=devnull,
                    stderr=devnull
                ).stdout.decode().strip()
            
            if not path:
                self.log_with_emoji(f"{executable} not found. Install ffmpeg and add to PATH", logging.ERROR, 'ERROR')
                raise FileNotFoundError(
                    f"{executable} not found. Please install ffmpeg and add to PATH or place in the same directory as this script."
                )
        
        self.log_with_emoji(f"Found {executable} at: {path}", emoji_type='SETTINGS')
        return path

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
            self.log_with_emoji(f"Keeping temporary file: {os.path.basename(file_path)}", emoji_type='FILE')

    def _clean_temp_files(self):
        if not self.clean_temp_files:
            self.log_with_emoji("Skipping temp files cleanup (disabled in settings)", emoji_type='CLEANUP')
            return

        if not self.temp_folder or not os.path.exists(self.temp_folder):
            self.log_with_emoji("No temp folder to clean", emoji_type='CLEANUP')
            return

        try:
            self.log_with_emoji("Starting temp files cleanup...", emoji_type='CLEANUP')
            
            deleted_files = 0
            deleted_folders = 0
            
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
                            deleted_files += 1
                            self.log_with_emoji(f"Deleted temp file: {os.path.basename(file)}", emoji_type='FILE')
                        except Exception as e:
                            self.log_with_emoji(f"Error deleting {file}: {str(e)}", logging.WARNING)
            
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
                                deleted_files += 1
                                self.log_with_emoji(f"Deleted temp file: {file}", emoji_type='FILE')
                        except Exception as e:
                            self.log_with_emoji(f"Error deleting file {file}: {str(e)}", logging.WARNING)
                
                try:
                    if not os.listdir(root):
                        os.rmdir(root)
                        deleted_folders += 1
                        self.log_with_emoji(f"Deleted empty folder: {root}", emoji_type='CLEANUP')
                except Exception as e:
                    self.log_with_emoji(f"Error deleting folder {root}: {str(e)}", logging.WARNING)

            self.log_with_emoji(f"Cleanup complete. Deleted {deleted_files} files and {deleted_folders} folders", emoji_type='COMPLETE')

        except Exception as e:
            self.log_with_emoji(f"Cleanup error: {str(e)}", logging.ERROR, 'ERROR')

    def _clean_empty_folders(self):
        for folder in list(self.temp_folders):
            try:
                if os.path.exists(folder) and not os.listdir(folder):
                    os.rmdir(folder)
                    self.temp_folders.remove(folder)
                    self.log_with_emoji(f"Deleted empty temp folder: {folder}", emoji_type='CLEANUP')
            except Exception as e:
                self.log_with_emoji(f"Error deleting folder {folder}: {str(e)}", logging.WARNING)

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
        self.log_with_emoji(f"Created output folder: {self.temp_folder}", emoji_type='FILE')
        return self.temp_folder

    def _clean_filename(self, filename):
        return re.sub(r'[\\/*?:"<>|#]', "", filename)

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
            
            self.log_with_emoji(f"Disk space check: {free_gb:.2f}GB free (required: {required_gb}GB)", emoji_type='SETTINGS')
            
            if free_gb < required_gb:
                self.log_with_emoji(f"Insufficient disk space. Required: {required_gb}GB, Available: {free_gb:.2f}GB", logging.ERROR, 'ERROR')
                raise RuntimeError(
                    f"Insufficient disk space. Required: {required_gb}GB, Available: {free_gb:.2f}GB"
                )
        except Exception as e:
            self.log_with_emoji(f"Disk space check failed: {str(e)}", logging.WARNING)

    def format_time(self, seconds):
        hours = math.floor(seconds / 3600)
        seconds %= 3600
        minutes = math.floor(seconds / 60)
        seconds %= 60
        milliseconds = round((seconds - math.floor(seconds)) * 1000)
        seconds = math.floor(seconds)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

    def download_youtube_video(self, youtube_url, output_path, quality='best', progress_callback=None):
        try:
            if progress_callback:
                progress_callback(0, 'download')
                
            self.log_with_emoji(f"Starting download: {youtube_url}", emoji_type='DOWNLOAD', stage='download')
            
            video_path = self.downloader.download(
                youtube_url, 
                output_path, 
                quality=quality,
                progress_callback=lambda p: progress_callback(p, 'download') if progress_callback else None
            )
            
            output_folder = self._create_output_folder(video_path)
            new_path = os.path.join(output_folder, os.path.basename(video_path))
            os.rename(video_path, new_path)
            self._keep_temp_file(new_path)
            
            if progress_callback:
                progress_callback(100, 'download')
                
            self.log_with_emoji(f"Download completed successfully: {os.path.basename(new_path)}", 
                              emoji_type='COMPLETE', stage='download')
            return new_path
        except Exception as e:
            if progress_callback:
                progress_callback(-1, 'download', str(e))
            self.log_with_emoji(f"Download failed: {str(e)}", logging.ERROR, 'ERROR')
            raise RuntimeError(f"Failed to download video: {e}")

    def transcribe(self, audio_path, progress_callback=None):
        """
        Publiczna metoda transkrypcji dla VideoTranslator
        Deleguje zadanie do AudioTranscriber
        """
        return self.transcriber.transcribe(audio_path, progress_callback=progress_callback)

    def generate_subtitle_file(self, language, segments, output_path):
        try:
            base_name = os.path.splitext(os.path.basename(output_path))[0]
            subtitle_file = os.path.join(self.temp_folder, f"{base_name}_subtitles.srt")
            
            self.log_with_emoji("Generating subtitle file...", emoji_type='SUBTITLES', stage='transcribe')
            self.log_with_emoji(f"Output file: {os.path.basename(subtitle_file)}", emoji_type='FILE', stage='transcribe')
            self.log_with_emoji(f"Language: {language}", emoji_type='SUBTITLES', stage='transcribe')
            self.log_with_emoji(f"Segments to process: {len(segments)}", emoji_type='SUBTITLES', stage='transcribe')
            
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
            
            self.log_with_emoji(f"Subtitle file generated: {os.path.basename(subtitle_file)}", emoji_type='COMPLETE', stage='transcribe')
            self.log_with_emoji(f"File size: {os.path.getsize(subtitle_file)/(1024):.2f}KB", emoji_type='FILE', stage='transcribe')
            return subtitle_file
        except Exception as e:
            self.log_with_emoji(f"Subtitle generation error: {str(e)}", logging.ERROR, 'ERROR')
            raise RuntimeError(f"Failed to generate subtitles: {e}")

    def translate_subtitles(self, subtitle_path, from_lang, to_lang, progress_callback=None):
        try:
            if progress_callback:
                progress_callback(0, 'translate')
                
            subs = pysrt.open(subtitle_path)
            
            if not self.installed_languages:
                self._initialize_translation()
            
            self.log_with_emoji(f"Starting translation from {from_lang} to {to_lang}...", emoji_type='TRANSLATE', stage='translate')
            self.log_with_emoji(f"Input file: {os.path.basename(subtitle_path)}", emoji_type='FILE', stage='translate')
            self.log_with_emoji(f"Segments to translate: {len(subs)}", emoji_type='TRANSLATE', stage='translate')
            
            from_lang_obj = next(
                (lang for lang in self.installed_languages if lang.code == from_lang),
                None
            )
            to_lang_obj = next(
                (lang for lang in self.installed_languages if lang.code == to_lang),
                None
            )
            
            if not from_lang_obj or not to_lang_obj:
                self.log_with_emoji(f"No installed translation from {from_lang} to {to_lang}. Attempting installation...", logging.WARNING)
                argostranslate.package.update_package_index()
                available_packages = argostranslate.package.get_available_packages()
                package_to_install = next(
                    (pkg for pkg in available_packages 
                     if pkg.from_code == from_lang and pkg.to_code == to_lang),
                    None
                )
                
                if package_to_install:
                    self.log_with_emoji(f"Installing translation package: {from_lang} -> {to_lang}", emoji_type='SETTINGS', stage='translate')
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
                if progress_callback:
                    progress_callback(-1, 'translate', f"No translation from {from_lang} to {to_lang}")
                self.log_with_emoji(f"No available translation from {from_lang} to {to_lang}", logging.ERROR, 'ERROR')
                raise RuntimeError(f"No translation installed from {from_lang} to {to_lang}")
            
            translation = from_lang_obj.get_translation(to_lang_obj)
            if not translation:
                if progress_callback:
                    progress_callback(-1, 'translate', f"Could not create translation from {from_lang} to {to_lang}")
                self.log_with_emoji(f"Could not create translation from {from_lang} to {to_lang}", logging.ERROR, 'ERROR')
                raise RuntimeError(f"Could not create translation from {from_lang} to {to_lang}")
            
            for i, sub in enumerate(subs):
                if self.cancel_process:
                    self.log_with_emoji("Translation cancelled by user", logging.WARNING, 'ERROR')
                    break
                    
                original_text = sub.text
                sub.text = translation.translate(sub.text)
                
                if i < 3:
                    self.log_with_emoji(f"Sample translation {i+1}:", emoji_type='TRANSLATE', stage='translate')
                    self.log_with_emoji(f"Original: {original_text}", emoji_type='TRANSLATE', stage='translate')
                    self.log_with_emoji(f"Translated: {sub.text}", emoji_type='TRANSLATE', stage='translate')
                
                if progress_callback and i % 10 == 0:
                    progress = (i / len(subs)) * 100
                    progress_callback(progress, 'translate')
            
            base_name = os.path.splitext(os.path.basename(subtitle_path))[0]
            translated_subtitle_path = os.path.join(self.temp_folder, f"{base_name}_subtitles_{to_lang}.srt")
            
            subs.save(translated_subtitle_path, encoding='utf-8')
            self._register_temp_file(translated_subtitle_path)
            
            if progress_callback:
                progress_callback(100, 'translate')
                
            self.log_with_emoji(f"Translation complete. File: {os.path.basename(translated_subtitle_path)}", emoji_type='COMPLETE', stage='translate')
            return translated_subtitle_path
        except Exception as e:
            if progress_callback:
                progress_callback(-1, 'translate', str(e))
            self.log_with_emoji(f"Translation error: {str(e)}", logging.ERROR, 'ERROR')
            raise RuntimeError(f"Translation error: {e}")

    def process_local_video(self, video_path, from_lang="en", to_lang="pl", output_dir=None, progress_callback=None, add_subtitles=False, subtitle_style=None):
        try:
            self.log_with_emoji("Starting local video processing...", emoji_type='PROCESS')
            self.log_with_emoji(f"Input file: {video_path}", emoji_type='FILE')
            self.log_with_emoji(f"Translation: {from_lang} -> {to_lang}", emoji_type='TRANSLATE')
            self.log_with_emoji(f"Add subtitles: {'Yes' if add_subtitles else 'No'}", emoji_type='SUBTITLES')
            
            self._create_output_folder(video_path)
            
            if output_dir:
                self._check_disk_space(output_dir)
            else:
                self._check_disk_space(os.path.dirname(video_path))
            
            self.log_with_emoji("Step 1/6: Extracting audio...", emoji_type='AUDIO', stage='extract_audio')
            audio_path = self.audio_extractor.extract_audio(video_path, progress_callback=progress_callback)
            
            self.log_with_emoji("Step 2/6: Transcribing audio...", emoji_type='TRANSCRIBE', stage='transcribe')
            language, segments = self.transcribe(audio_path, progress_callback)
            
            self.log_with_emoji("Step 3/6: Generating subtitles...", emoji_type='SUBTITLES', stage='transcribe')
            subtitle_path = self.generate_subtitle_file(language, segments, video_path)
            
            self.log_with_emoji("Step 4/6: Translating subtitles...", emoji_type='TRANSLATE', stage='translate')
            translated_subtitle_path = self.translate_subtitles(subtitle_path, from_lang, to_lang, progress_callback)
            
            self.log_with_emoji("Step 5/6: Generating translated audio...", emoji_type='AUDIO', stage='generate_audio')
            translated_audio_path = self.audio_generator.generate_translated_audio(translated_subtitle_path, os.path.join(self.temp_folder, f"{os.path.splitext(os.path.basename(video_path))[0]}_translated_audio.wav"), to_lang, progress_callback)
            
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            final_filename = f"{video_name}_translated.mp4"
            final_video_path = os.path.join(self.temp_folder, final_filename)
            
            self.log_with_emoji("Step 6/6: Replacing audio track...", emoji_type='AUDIO', stage='finalize')
            final_video_path = self.audio_replacer.replace_audio(video_path, translated_audio_path, final_video_path, progress_callback)

            if add_subtitles:
                self.log_with_emoji("Adding subtitles to video...", emoji_type='SUBTITLES', stage='finalize')
                final_with_subs = os.path.join(self.temp_folder, f"{video_name}_with_subs.mp4")
                self.subtitle_burner.burn_subtitles_to_video(final_video_path, translated_subtitle_path, final_with_subs, subtitle_style)
            
            self.log_with_emoji(f"Processing complete. Output file: {final_video_path}", emoji_type='COMPLETE')
            return final_video_path
            
        except Exception as e:
            self.log_with_emoji(f"Processing error: {str(e)}", logging.ERROR, 'ERROR')
            raise
        finally:
            self._clean_temp_files()

    def main(self, youtube_url, from_lang="en", to_lang="pl", output_dir=None, quality='best', progress_callback=None, add_subtitles=False, subtitle_style=None):
        if output_dir is None:
            output_dir = self.script_dir
        
        try:
            self.log_with_emoji("Starting YouTube video translation...", emoji_type='PROCESS')
            self.log_with_emoji(f"URL: {youtube_url}", emoji_type='DOWNLOAD', stage='download')
            self.log_with_emoji(f"Translation: {from_lang} -> {to_lang}", emoji_type='TRANSLATE', stage='translate')
            self.log_with_emoji(f"Quality: {quality}", emoji_type='SETTINGS')
            self.log_with_emoji(f"Add subtitles: {'Yes' if add_subtitles else 'No'}", emoji_type='SUBTITLES')
            
            self._check_disk_space(output_dir)
            
            self.log_with_emoji("Step 1/6: Downloading video...", emoji_type='DOWNLOAD', stage='download')
            video_path = self.download_youtube_video(youtube_url, output_dir, quality, progress_callback)
            
            self.log_with_emoji("Step 2/6: Extracting audio...", emoji_type='AUDIO', stage='extract_audio')
            audio_path = self.audio_extractor.extract_audio(video_path, progress_callback=progress_callback)
            
            self.log_with_emoji("Step 3/6: Transcribing audio...", emoji_type='TRANSCRIBE', stage='transcribe')
            language, segments = self.transcribe(audio_path, progress_callback)
            
            self.log_with_emoji("Step 4/6: Generating subtitles...", emoji_type='SUBTITLES', stage='transcribe')
            subtitle_path = self.generate_subtitle_file(language, segments, video_path)
            
            self.log_with_emoji("Step 5/6: Translating subtitles...", emoji_type='TRANSLATE', stage='translate')
            translated_subtitle_path = self.translate_subtitles(subtitle_path, from_lang, to_lang, progress_callback)
            
            self.log_with_emoji("Step 6/6: Generating translated audio...", emoji_type='AUDIO', stage='generate_audio')
            translated_audio_path = self.audio_generator.generate_translated_audio(translated_subtitle_path, os.path.join(self.temp_folder, f"{os.path.splitext(os.path.basename(video_path))[0]}_translated_audio.wav"), to_lang, progress_callback)
            
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            final_filename = f"{video_name}_translated.mp4"
            final_video_path = os.path.join(self.temp_folder, final_filename)
            
            self.log_with_emoji("Final step: Replacing audio track...", emoji_type='AUDIO', stage='finalize')
            final_video_path = self.audio_replacer.replace_audio(video_path, translated_audio_path, final_video_path, progress_callback)


            if add_subtitles:
                self.log_with_emoji("Adding subtitles to video...", emoji_type='SUBTITLES', stage='finalize')
                final_with_subs = os.path.join(self.temp_folder, f"{video_name}_with_subs.mp4")
                self.subtitle_burner.burn_subtitles_to_video(final_video_path, translated_subtitle_path, final_with_subs, subtitle_style)
            
            self.log_with_emoji(f"Translation complete. Output file: {final_video_path}", emoji_type='COMPLETE')
            return final_video_path
            
        except Exception as e:
            self.log_with_emoji(f"Translation error: {str(e)}", logging.ERROR, 'ERROR')
            raise
        finally:
            self._clean_temp_files()

    def cancel(self):
        self.cancel_process = True
        self.log_with_emoji("Process cancelled by user", logging.WARNING, 'ERROR')
        if self.clean_temp_files:
            self._clean_temp_files()