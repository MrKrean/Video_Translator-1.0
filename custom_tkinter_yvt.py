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
import customtkinter as ctk
from PIL import Image
import edge_tts
import asyncio
import argostranslate.package
import argostranslate.translate
from pydub import AudioSegment
from datetime import datetime
from tkinter import filedialog, messagebox
from moviepy import VideoFileClip, AudioFileClip
from tkinter import ttk

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='youtube_translator.log',
    filemode='a'
)

# Konfiguracja wyglądu
ctk.set_default_color_theme("blue")

class YouTubeTranslator:
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

        # Inicjalizacja tłumaczenia
        self._initialize_translation()

    def _initialize_translation(self):
        """Inicjalizuje moduł tłumaczenia i pobiera potrzebne pakiety językowe"""
        try:
            argostranslate.package.update_package_index()
            self.installed_languages = argostranslate.translate.get_installed_languages()
        except Exception as e:
            logging.error(f"Błąd inicjalizacji tłumaczenia: {str(e)}")
            self.installed_languages = []

    def _register_temp_patterns(self):
        """Rejestruje wzorce nazw plików tymczasowych"""
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
            path = subprocess.run(f"where {executable}", capture_output=True, shell=True).stdout.decode().strip()
            if not path:
                raise FileNotFoundError(
                    f"{executable} not found. Please install ffmpeg and add to PATH or place in the same directory as this script."
                )
        return path

    def _register_temp_file(self, file_path):
        """Rejestruje plik tymczasowy do późniejszego usunięcia"""
        if file_path and os.path.exists(file_path):
            self.temp_files_to_keep.discard(file_path)
            base_name = os.path.basename(file_path)
            for pattern in self.temp_file_patterns:
                if re.match(pattern, base_name):
                    self.temp_files_to_keep.discard(file_path)
                    break

    def _keep_temp_file(self, file_path):
        """Oznacza plik jako zachowywany (nie będzie usunięty)"""
        if file_path and os.path.exists(file_path):
            self.temp_files_to_keep.add(file_path)

    def _clean_temp_files(self):
        """Usuwa WSZYSTKIE pliki tymczasowe"""
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
                            logging.info(f"Usunięto plik tymczasowy: {file}")
                        except Exception as e:
                            logging.warning(f"Błąd usuwania {file}: {str(e)}")
            
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
                                logging.info(f"Usunięto plik tymczasowy: {file_path}")
                        except Exception as e:
                            logging.warning(f"Błąd podczas usuwania folderu {file_path}: {str(e)}")
                
                try:
                    if not os.listdir(root):
                        os.rmdir(root)
                except Exception:
                    pass

        except Exception as e:
            logging.error(f"Błąd czyszczenia plików: {str(e)}")

    def _clean_empty_folders(self):
        """Rekursywnie usuwa puste foldery tymczasowe"""
        for folder in list(self.temp_folders):
            try:
                if os.path.exists(folder) and not os.listdir(folder):
                    os.rmdir(folder)
                    self.temp_folders.remove(folder)
                    logging.info(f"Usunięto pusty folder tymczasowy: {folder}")
            except Exception as e:
                logging.warning(f"Błąd podczas usuwania folderu {folder}: {str(e)}")

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
        """Czyści nazwę pliku z niebezpiecznych znaków"""
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
                    f"Niewystarczająca ilość miejsca na dysku. Wymagane: {required_gb}GB, Dostępne: {free_gb:.2f}GB"
                )
        except Exception as e:
            logging.warning(f"Nie można sprawdzić miejsca na dysku: {str(e)}")

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
            raise ValueError("Nieprawidłowy URL YouTube")
        
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
            logging.error(f"Błąd pobierania wideo: {str(e)}")
            raise RuntimeError(f"Nie udało się pobrać wideo: {e}")

    def _download_progress(self, d, progress_callback):
        if self.cancel_process:
            raise RuntimeError("Proces anulowany przez użytkownika")
        
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
            logging.error(f"Błąd FFmpeg: {e.stderr.decode()}")
            raise RuntimeError(f"Nie udało się wyodrębnić audio: {e}")
        except Exception as e:
            logging.error(f"Błąd wyodrębniania audio: {str(e)}")
            raise RuntimeError(f"Nie udało się wyodrębnić audio: {e}")

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
            raise RuntimeError("faster-whisper nie jest zainstalowany. Zainstaluj go komendą: pip install faster-whisper")
        except Exception as e:
            logging.error(f"Błąd transkrypcji: {str(e)}")
            raise RuntimeError(f"Błąd transkrypcji: {e}")

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
            logging.error(f"Błąd generowania napisów: {str(e)}")
            raise RuntimeError(f"Nie udało się wygenerować napisów: {e}")

    def translate_subtitles(self, subtitle_path, from_lang, to_lang, progress_callback=None):
        try:
            subs = pysrt.open(subtitle_path)
            
            # Sprawdź zainstalowane języki
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
                # Spróbuj zainstalować brakujące języki
                argostranslate.package.update_package_index()
                available_packages = argostranslate.package.get_available_packages()
                package_to_install = next(
                    (pkg for pkg in available_packages 
                     if pkg.from_code == from_lang and pkg.to_code == to_lang),
                    None
                )
                
                if package_to_install:
                    argostranslate.package.install_from_path(package_to_install.download())
                    self._initialize_translation()  # Odśwież listę języków
                    
                    from_lang_obj = next(
                        (lang for lang in self.installed_languages if lang.code == from_lang),
                        None
                    )
                    to_lang_obj = next(
                        (lang for lang in self.installed_languages if lang.code == to_lang),
                        None
                    )
            
            if not from_lang_obj or not to_lang_obj:
                raise RuntimeError(f"Brak zainstalowanego tłumaczenia z {from_lang} na {to_lang}")
            
            translation = from_lang_obj.get_translation(to_lang_obj)
            if not translation:
                raise RuntimeError(f"Nie można utworzyć tłumaczenia z {from_lang} na {to_lang}")
            
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
            logging.error(f"Błąd tłumaczenia: {str(e)}")
            raise RuntimeError(f"Błąd tłumaczenia: {e}")

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
                    logging.warning(f"Nie udało się wygenerować TTS dla segmentu {i}: {str(e)}")
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
            logging.error(f"Błąd generowania audio: {str(e)}")
            raise RuntimeError(f"Błąd generowania audio: {e}")

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
            logging.error(f"Błąd FFmpeg: {e.stderr.decode()}")
            raise RuntimeError(f"Nie udało się zastąpić ścieżki audio: {e}")
        except Exception as e:
            logging.error(f"Nie udało się zastąpić ścieżki audio: {str(e)}")
            raise RuntimeError(f"Nie udało się zastąpić ścieżki audio: {e}")

    def burn_subtitles_to_video(self, video_path, subtitle_path, output_path, style=None):
        """Nakłada napisy na wideo z uwzględnieniem wszystkich ustawień stylu"""
        if style is None:
            style = self.subtitle_style

        try:
            subtitle_path_escaped = subtitle_path.replace('\\', '/').replace(':', '\\:').replace("'", "\\'")
            
            # Mapowanie kolorów
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
            
            # Konwersja koloru tekstu
            fontcolor = style['fontcolor']
            if fontcolor.lower() in color_mapping:
                fontcolor = color_mapping[fontcolor.lower()]
            elif fontcolor.startswith('#'):
                fontcolor = f"0x{fontcolor[1:]}"
            else:
                fontcolor = '0xFFFFFF'  # Domyślny biały
            
            # Konwersja koloru tła
            boxcolor = style['boxcolor'].split('@')[0] if '@' in style['boxcolor'] else 'black'
            if boxcolor.lower() in color_mapping:
                boxcolor = color_mapping[boxcolor.lower()]
            elif boxcolor.startswith('#'):
                boxcolor = f"0x{boxcolor[1:]}"
            else:
                boxcolor = '0x000000'  # Domyślny czarny
            
            # Przezroczystość tła
            bg_opacity = style['boxcolor'].split('@')[1] if '@' in style['boxcolor'] else '0.5'
            boxcolor_alpha = f"{boxcolor}{int(float(bg_opacity)*255):02x}"
            
            # Konwersja koloru obramowania
            bordercolor = style['bordercolor']
            if bordercolor.lower() in color_mapping:
                bordercolor = color_mapping[bordercolor.lower()]
            elif bordercolor.startswith('#'):
                bordercolor = f"0x{bordercolor[1:]}"
            else:
                bordercolor = '0x000000'  # Domyślny czarny
            
            # Mapowanie pozycji i wyrównania
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
            
            # Przygotowanie filtra napisów
            subtitle_filter = (
                f"subtitles='{subtitle_path_escaped}':"
                f"force_style='"
                f"Fontname={style.get('fontfamily', 'Arial')},"
                f"Fontsize={style['fontsize']},"
                f"PrimaryColour={fontcolor},"  # Kolor tekstu
                f"BackColour={boxcolor_alpha},"  # Kolor tła z przezroczystością
                f"BorderStyle={style['borderw']},"
                f"OutlineColour={bordercolor},"  # Kolor obramowania
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
            logging.info("Wyodrębnianie audio...")
            audio_path = self.extract_audio(video_path, progress_callback)
            
            if progress_callback:
                progress_callback(50)
            logging.info("Transkrypcja audio...")
            language, segments = self.transcribe(audio_path, progress_callback)
            
            if progress_callback:
                progress_callback(60)
            logging.info("Generowanie napisów...")
            subtitle_path = self.generate_subtitle_file(language, segments, video_path)
            
            if progress_callback:
                progress_callback(70)
            logging.info("Tłumaczenie napisów...")
            translated_subtitle_path = self.translate_subtitles(subtitle_path, language, to_lang, progress_callback)
            
            if progress_callback:
                progress_callback(80)
            logging.info("Generowanie przetłumaczonego audio...")
            translated_audio_path = self.generate_translated_audio(translated_subtitle_path, video_path, to_lang, progress_callback)
            
            if progress_callback:
                progress_callback(95)
            logging.info("Zastępowanie ścieżki audio...")
            
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
            
            logging.info(f"Przetłumaczone wideo zapisano jako: {final_video_path}")
            return final_video_path
            
        except Exception as e:
            logging.error(f"Błąd procesu tłumaczenia: {str(e)}")
            raise
        finally:
            self._clean_temp_files()

    def main(self, youtube_url, from_lang="en", to_lang="pl", output_dir=None, quality='best', progress_callback=None, add_subtitles=False, subtitle_style=None):
        if output_dir is None:
            output_dir = self.script_dir
        
        try:
            if progress_callback:
                progress_callback(10)
            logging.info(f"Pobieranie wideo YouTube w jakości: {quality}...")
            video_path = self.download_youtube_video(youtube_url, output_dir, quality, progress_callback)
            
            if progress_callback:
                progress_callback(40)
            logging.info("Wyodrębnianie audio...")
            audio_path = self.extract_audio(video_path, progress_callback)
            
            if progress_callback:
                progress_callback(50)
            logging.info("Transkrypcja audio...")
            language, segments = self.transcribe(audio_path, progress_callback)
            
            if progress_callback:
                progress_callback(60)
            logging.info("Generowanie napisów...")
            subtitle_path = self.generate_subtitle_file(language, segments, video_path)
            
            if progress_callback:
                progress_callback(70)
            logging.info("Tłumaczenie napisów...")
            translated_subtitle_path = self.translate_subtitles(subtitle_path, from_lang, to_lang, progress_callback)
            
            if progress_callback:
                progress_callback(80)
            logging.info("Generowanie przetłumaczonego audio...")
            translated_audio_path = self.generate_translated_audio(translated_subtitle_path, video_path, to_lang, progress_callback)
            
            if progress_callback:
                progress_callback(95)
            logging.info("Zastępowanie ścieżki audio...")
            
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
            
            logging.info(f"Przetłumaczone wideo zapisano jako: {final_video_path}")
            return final_video_path
            
        except Exception as e:
            logging.error(f"Błąd procesu tłumaczenia: {str(e)}")
            raise
        finally:
            self._clean_temp_files()

    def cancel(self):
        """Anuluje bieżący proces i czyści pliki tymczasowe"""
        self.cancel_process = True
        if self.clean_temp_files:
            self._clean_temp_files()

class TextboxHandler(logging.Handler):
    def __init__(self, textbox):
        super().__init__()
        self.textbox = textbox
        
    def emit(self, record):
        msg = self.format(record)
        
        def append():
            self.textbox.configure(state="normal")
            self.textbox.insert("end", msg + "\n")
            self.textbox.configure(state="disabled")
            self.textbox.see("end")
        
        self.textbox.after(0, append)

class YouTubeTranslatorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.translator = YouTubeTranslator()
        self.final_video_path = None
        
        # Initialize subtitle style with default values
        self.subtitle_style = {
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
        
        # Initialize the subtitles attributes
        self.add_subtitles = False  # For YouTube tab
        self.local_add_subtitles = False  # For Local tab
        self.logs_visible = True
        self.local_logs_visible = True

        # Konfiguracja głównego okna
        self.title("Video Translator")
        self.geometry("850x850")
        self.minsize(850, 850)
        ctk.set_appearance_mode("Dark")
        
        # Ikona aplikacji
        try:
            self.iconbitmap(os.path.join(self.translator.script_dir, "icon_vt.ico"))
        except:
            pass
        
        # Główny układ
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Nagłówek
        self.header_font = ctk.CTkFont(size=24, weight="bold")
        self.header = ctk.CTkLabel(
            self, 
            text="🎬 Video Translator",
            font=self.header_font,
            anchor="center"
        )
        self.header.grid(row=0, column=0, pady=(20, 10), padx=20, sticky="ew")
        
        # Główny kontener z zakładkami
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        
        # Zakładka YouTube
        self.youtube_tab = self.tabview.add("YouTube Video")
        self.setup_youtube_tab()
        
        # Zakładka Plik lokalny
        self.local_tab = self.tabview.add("Local Video")
        self.setup_local_tab()
        
        # Zakładka Ustawienia
        self.settings_tab = self.tabview.add("Settings")
        self.setup_settings_tab()
        
        # Inicjalizacja
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.update_ui_state()

    def setup_youtube_tab(self):
        self.youtube_tab.grid_columnconfigure(0, weight=1)

        # Sekcja URL
        url_frame = ctk.CTkFrame(self.youtube_tab)
        url_frame.grid(row=0, column=0, padx=10, pady=(5, 10), sticky="nsew")
        url_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(url_frame, text="YouTube URL:", font=ctk.CTkFont(weight="bold", size=14)).grid(
            row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        self.url_entry = ctk.CTkEntry(
            url_frame,
            placeholder_text="https://www.youtube.com/watch?v=...",
            font=ctk.CTkFont(size=14)
        )
        self.url_entry.grid(row=0, column=1, padx=10, pady=(10, 5), sticky="ew")

        # Sekcja ustawień
        settings_frame = ctk.CTkFrame(self.youtube_tab)
        settings_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        settings_frame.grid_columnconfigure(1, weight=1)

        # Ustawienia języka
        lang_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        lang_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(lang_frame, text="From:").pack(side="left", padx=(0, 8))

        self.from_lang_combobox = ctk.CTkComboBox(
            lang_frame,
            values=list(self.translator.language_codes.keys()),
            width=200
        )
        self.from_lang_combobox.set("English")
        self.from_lang_combobox.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(lang_frame, text="To:").pack(side="left", padx=(0, 8))

        self.to_lang_combobox = ctk.CTkComboBox(
            lang_frame,
            values=list(self.translator.language_codes.keys()),
            width=200
        )
        self.to_lang_combobox.set("Polish")
        self.to_lang_combobox.pack(side="left")

        # Jakość
        qual_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        qual_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(qual_frame, text="Video Quality:").pack(side="left", padx=(0, 9))
        self.quality_combobox = ctk.CTkComboBox(
            qual_frame,
            values=['best', '1080p', '720p', '480p', '360p', '240p', '144p'],
            width=155
        )
        self.quality_combobox.set("best")
        self.quality_combobox.pack(side="left", padx=(0, 20))

        # Napisy - integracja z ustawieniami napisów
        subtitles_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        subtitles_frame.grid(row=3, column=0, padx=10, pady=5, sticky="w", columnspan=2)

        self.subtitles_checkbox = ctk.CTkCheckBox(
            subtitles_frame,
            text="Add subtitles to video",
            command=self.toggle_subtitles_option
        )
        self.subtitles_checkbox.pack(side="left", padx=(0, 10))

        self.subtitle_settings_button = ctk.CTkButton(
            subtitles_frame,
            text="⚙️",
            width=25,
            hover_color="#525252",
            fg_color="transparent",
            command=self.open_subtitle_settings,
            font=ctk.CTkFont(size=18)
        )
        self.subtitle_settings_button.pack(side="left")

        # Folder wyjściowy
        output_frame = ctk.CTkFrame(self.youtube_tab)
        output_frame.grid(row=4, column=0, padx=10, pady=10, sticky="nsew")
        output_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(output_frame, text="Output Folder:").grid(
            row=0, column=0, padx=10, pady=5, sticky="w") 
        self.output_dir_display = ctk.CTkLabel(
            output_frame,
            text="Default: script directory",
            anchor="w",
            fg_color=("gray90", "gray20"),
            corner_radius=4,
            padx=10,
            height=28
        )
        self.output_dir_display.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        self.output_dir_button = ctk.CTkButton(
            output_frame,
            text="Browse...",
            width=100,
            command=self.choose_output_dir
        )
        self.output_dir_button.grid(row=0, column=2, padx=10, pady=5)

        # Przyciski akcji
        button_frame = ctk.CTkFrame(self.youtube_tab)
        button_frame.grid(row=5, column=0, padx=10, pady=10, sticky="nsew")

        self.start_button = ctk.CTkButton(
            button_frame,
            text="Start Translation",
            command=self.start_youtube_process,
            fg_color="#2aa745",
            hover_color="#22863a",
            width=150
        )
        self.start_button.pack(side="left", padx=10, pady=5)

        # Panel statusu YouTube
        self.youtube_status_frame = ctk.CTkFrame(self.youtube_tab)
        self.youtube_status_frame.grid(row=6, column=0, padx=10, pady=(5, 10), sticky="nsew")
        self.youtube_status_frame.grid_columnconfigure(1, weight=1)

        self.youtube_status_label = ctk.CTkLabel(
            self.youtube_status_frame, 
            text="Status: Ready", 
            text_color="green",
        )
        self.youtube_status_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.youtube_progress_bar = ctk.CTkProgressBar(
            self.youtube_status_frame, 
            width=300, 
            height=10, 
            mode="determinate"
        )
        self.youtube_progress_bar.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        self.youtube_progress_bar.set(0)

        self.cancel_button = ctk.CTkButton(
            self.youtube_status_frame,
            text="Cancel",
            command=self.cancel_process,
            fg_color="#d73a49",
            hover_color="#cb2431",
            state="disabled",
            width=100
        )
        self.cancel_button.grid(row=0, column=2, padx=10, pady=5, sticky="e")

        # Przycisk do otwierania folderu
        self.open_button = ctk.CTkButton(
            button_frame,
            text="Open Output Folder",
            command=self.open_output_folder,
            state="disabled",
            width=150
        )
        self.open_button.pack(side="right", padx=10, pady=5)

        # Konsola logów
        log_frame = ctk.CTkFrame(self.youtube_tab)
        log_frame.grid(row=7, column=0, padx=10, pady=(10, 5), sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)

        # Ramka nagłówka z przyciskiem zwijania
        log_header_frame = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        ctk.CTkLabel(log_header_frame, text="Process Log:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
        
        self.log_toggle_button = ctk.CTkButton(
            log_header_frame,
            text="▲",
            width=30,
            fg_color="transparent",
            hover_color="#525252",
            command=self.toggle_log_visibility,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.log_toggle_button.pack(side="right", padx=5)
        
        self.log_text = ctk.CTkTextbox(
            log_frame,
            wrap="word",
            state="disabled",
            font=ctk.CTkFont(family="Consolas", size=12),
            height=150
        )
        self.log_text.grid(row=1, column=0, padx=5, pady=(0, 5), sticky="nsew")

        # Dodaj handler logów
        self.log_handler = TextboxHandler(self.log_text)
        logging.getLogger().addHandler(self.log_handler)

    def setup_local_tab(self):
        self.local_tab.grid_columnconfigure(0, weight=1)

        # Sekcja pliku
        file_frame = ctk.CTkFrame(self.local_tab)
        file_frame.grid(row=0, column=0, padx=10, pady=(5, 10), sticky="nsew")
        file_frame.grid_columnconfigure(1, weight=1)

        file_label = ctk.CTkLabel(file_frame, text="Video File:", font=ctk.CTkFont(weight="bold", size=14))
        file_label.grid(row=0, column=0, padx=(10, 5), pady=(10, 5), sticky="w")

        self.local_file_display = ctk.CTkLabel(
            file_frame,
            text="No file selected",
            anchor="w",
            fg_color=("gray90", "gray20"),
            corner_radius=4,
            padx=10,
            height=28
        )
        self.local_file_display.grid(row=0, column=1, padx=5, pady=(10, 5), sticky="ew")

        self.local_file_button = ctk.CTkButton(
            file_frame,
            text="Select File",
            command=self.choose_local_file,
            width=100
        )
        self.local_file_button.grid(row=0, column=2, padx=(5, 10), pady=(10, 5), sticky="e")

        # Sekcja ustawień
        settings_frame = ctk.CTkFrame(self.local_tab)
        settings_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        settings_frame.grid_columnconfigure(1, weight=1)

        # Ustawienia języka
        lang_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        lang_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(lang_frame, text="From:").pack(side="left", padx=(0, 8))

        self.local_from_lang_combobox = ctk.CTkComboBox(
            lang_frame,
            values=list(self.translator.language_codes.keys()),
            width=200
        )
        self.local_from_lang_combobox.set("English")
        self.local_from_lang_combobox.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(lang_frame, text="To:").pack(side="left", padx=(0, 8))

        self.local_to_lang_combobox = ctk.CTkComboBox(
            lang_frame,
            values=list(self.translator.language_codes.keys()),
            width=200
        )
        self.local_to_lang_combobox.set("Polish")
        self.local_to_lang_combobox.pack(side="left")

        # Sekcja napisów - w nowej ramce
        subtitles_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        subtitles_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        self.local_subtitles_checkbox = ctk.CTkCheckBox(
            subtitles_frame,
            text="Add subtitles to video",
            command=self.toggle_local_subtitles_option
        )
        self.local_subtitles_checkbox.pack(side="left", padx=(0, 10))

        self.local_subtitle_settings_button = ctk.CTkButton(
            subtitles_frame,
            text="⚙️",
            width=25,
            hover_color="#525252",
            fg_color="transparent",
            command=self.open_subtitle_settings,
            font=ctk.CTkFont(size=18)
        )
        self.local_subtitle_settings_button.pack(side="left")

        # Folder wyjściowy
        output_frame = ctk.CTkFrame(self.local_tab)
        output_frame.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")
        output_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(output_frame, text="Output Folder:").grid(
            row=0, column=0, padx=10, pady=5, sticky="w"
        )

        self.local_output_dir_display = ctk.CTkLabel(
            output_frame,
            text="Same as source file",
            anchor="w",
            fg_color=("gray90", "gray20"),
            corner_radius=4,
            padx=10,
            height=28
        )
        self.local_output_dir_display.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        self.local_output_dir_button = ctk.CTkButton(
            output_frame,
            text="Browse...",
            width=100,
            command=self.choose_local_output_dir
        )
        self.local_output_dir_button.grid(row=0, column=2, padx=10, pady=5)

        # Przyciski akcji
        button_frame = ctk.CTkFrame(self.local_tab)
        button_frame.grid(row=4, column=0, padx=10, pady=10, sticky="nsew")

        self.local_start_button = ctk.CTkButton(
            button_frame,
            text="Start Translation",
            command=self.start_local_process,
            fg_color="#2aa745",
            hover_color="#22863a",
            width=150
        )
        self.local_start_button.pack(side="left", padx=10, pady=5)

        # Panel statusu Local File
        self.local_status_frame = ctk.CTkFrame(self.local_tab)
        self.local_status_frame.grid(row=5, column=0, padx=10, pady=(5, 10), sticky="nsew")
        self.local_status_frame.grid_columnconfigure(1, weight=1)

        self.local_status_label = ctk.CTkLabel(
            self.local_status_frame, 
            text="Status: Ready", 
            text_color="green"
        )
        self.local_status_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.local_progress_bar = ctk.CTkProgressBar(
            self.local_status_frame, 
            width=300, 
            height=10, 
            mode="determinate"
        )
        self.local_progress_bar.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        self.local_progress_bar.set(0)

        self.local_cancel_button = ctk.CTkButton(
            self.local_status_frame,
            text="Cancel",
            command=self.cancel_process,
            fg_color="#d73a49",
            hover_color="#cb2431",
            state="disabled",
            width=100
        )
        self.local_cancel_button.grid(row=0, column=2, padx=10, pady=5, sticky="e")

        # Przycisk do otwierania folderu
        self.local_open_button = ctk.CTkButton(
            button_frame,
            text="Open Output Folder",
            command=self.open_output_folder,
            state="disabled",
            width=150
        )
        self.local_open_button.pack(side="right", padx=10, pady=5)

        # Konsola logów
        log_frame = ctk.CTkFrame(self.local_tab)
        log_frame.grid(row=6, column=0, padx=10, pady=(10, 5), sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)

        # Ramka nagłówka z przyciskiem zwijania
        log_header_frame = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        ctk.CTkLabel(log_header_frame, text="Process Log:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
        
        self.local_log_toggle_button = ctk.CTkButton(
            log_header_frame,
            text="▲",
            width=30,
            fg_color="transparent",
            hover_color="#525252",
            command=self.toggle_local_log_visibility,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.local_log_toggle_button.pack(side="right", padx=5)
        
        self.local_log_text = ctk.CTkTextbox(
            log_frame,
            wrap="word",
            state="disabled",
            font=ctk.CTkFont(family="Consolas", size=12),
            height=150
        )
        self.local_log_text.grid(row=1, column=0, padx=5, pady=(0, 5), sticky="nsew")

        # Dodaj handler logów
        self.local_log_handler = TextboxHandler(self.local_log_text)
        logging.getLogger().addHandler(self.local_log_handler)

    def setup_settings_tab(self):
        self.settings_tab.grid_columnconfigure(0, weight=1)
        
        # Sekcja ogólne
        general_frame = ctk.CTkFrame(self.settings_tab)
        general_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        general_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(general_frame, text="General Settings", font=ctk.CTkFont(weight="bold", size=14)).grid(
            row=0, column=0, padx=10, pady=5, sticky="w", columnspan=2)
        
        # Wygląd
        ctk.CTkLabel(general_frame, text="Appearance Mode:").grid(
            row=1, column=0, padx=10, pady=5, sticky="w")
        
        self.appearance_mode = ctk.CTkComboBox(
            general_frame,
            values=["Light", "Dark"],
            command=self.change_appearance_mode,
            width=200
        )
        self.appearance_mode.set("Dark")
        self.appearance_mode.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        
        # Motyw kolorystyczny
        ctk.CTkLabel(general_frame, text="Color Theme:").grid(
            row=2, column=0, padx=10, pady=5, sticky="w")
        
        self.color_theme = ctk.CTkComboBox(
            general_frame,
            values=["blue", "green", "dark-blue"],
            command=self.change_color_theme,
            width=200
        )
        self.color_theme.set("blue")
        self.color_theme.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        
        # Sekcja napisów
        subtitle_frame = ctk.CTkFrame(self.settings_tab)
        subtitle_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        subtitle_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(subtitle_frame, text="Subtitle Settings", font=ctk.CTkFont(weight="bold", size=14)).grid(
            row=0, column=0, padx=10, pady=5, sticky="w", columnspan=3)
        
        # Font settings
        font_frame = ctk.CTkFrame(subtitle_frame, fg_color="transparent")
        font_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew", columnspan=3)
        
        # Font size
        ctk.CTkLabel(font_frame, text="Font Size:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.fontsize_slider = ctk.CTkSlider(
            font_frame, 
            from_=10, 
            to=50,
            command=lambda v: self.update_subtitle_preview()
        )
        self.fontsize_slider.set(self.subtitle_style['fontsize'])
        self.fontsize_slider.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.fontsize_value = ctk.CTkLabel(font_frame, text=str(self.subtitle_style['fontsize']))
        self.fontsize_value.grid(row=0, column=2, padx=5, pady=5, sticky="w")
        
        # Font color
        ctk.CTkLabel(font_frame, text="Font Color:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.fontcolor_entry = ctk.CTkEntry(font_frame)
        self.fontcolor_entry.insert(0, self.subtitle_style['fontcolor'])
        self.fontcolor_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.fontcolor_button = ctk.CTkButton(
            font_frame,
            text="Pick",
            width=50,
            command=self.pick_font_color
        )
        self.fontcolor_button.grid(row=1, column=2, padx=5, pady=5, sticky="w")
        
        # Font family
        ctk.CTkLabel(font_frame, text="Font Family:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.fontfamily_combobox = ctk.CTkComboBox(
            font_frame,
            values=["Arial", "Helvetica", "Times New Roman", "Courier New", "Verdana"]
        )
        self.fontfamily_combobox.set("Arial")
        self.fontfamily_combobox.grid(row=2, column=1, padx=5, pady=5, sticky="ew", columnspan=2)
        
        # Border settings
        border_frame = ctk.CTkFrame(subtitle_frame, fg_color="transparent")
        border_frame.grid(row=3, column=0, padx=5, pady=5, sticky="nsew", columnspan=3)
        
        # Border width
        ctk.CTkLabel(border_frame, text="Border Width:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.border_width_slider = ctk.CTkSlider(
            border_frame,
            from_=0,
            to=5,
            number_of_steps=5,
            command=lambda v: self.update_subtitle_preview()
        )
        self.border_width_slider.set(self.subtitle_style['borderw'])
        self.border_width_slider.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.border_width_value = ctk.CTkLabel(border_frame, text=str(self.subtitle_style['borderw']))
        self.border_width_value.grid(row=0, column=2, padx=5, pady=5, sticky="w")
        
        # Border color
        ctk.CTkLabel(border_frame, text="Border Color:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.border_color_entry = ctk.CTkEntry(border_frame)
        self.border_color_entry.insert(0, self.subtitle_style['bordercolor'])
        self.border_color_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.border_color_button = ctk.CTkButton(
            border_frame,
            text="Pick",
            width=50,
            command=self.pick_border_color
        )
        self.border_color_button.grid(row=1, column=2, padx=5, pady=5, sticky="w")
        
        # Position and alignment
        pos_frame = ctk.CTkFrame(subtitle_frame, fg_color="transparent")
        pos_frame.grid(row=4, column=0, padx=5, pady=5, sticky="nsew", columnspan=3)
        
        # Position
        ctk.CTkLabel(pos_frame, text="Position:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.position_combobox = ctk.CTkComboBox(
            pos_frame,
            values=["top", "middle", "bottom"],
            command=lambda _: self.update_subtitle_preview()
        )
        self.position_combobox.set(self.subtitle_style['position'])
        self.position_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="ew", columnspan=2)
        
        # Alignment
        ctk.CTkLabel(pos_frame, text="Alignment:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.alignment_combobox = ctk.CTkComboBox(
            pos_frame,
            values=["left", "center", "right"],
            command=lambda _: self.update_subtitle_preview()
        )
        self.alignment_combobox.set("center")
        self.alignment_combobox.grid(row=1, column=1, padx=5, pady=5, sticky="ew", columnspan=2)
        
        # Preview
        preview_frame = ctk.CTkFrame(subtitle_frame)
        preview_frame.grid(row=5, column=0, padx=5, pady=10, sticky="nsew", columnspan=3)
        
        ctk.CTkLabel(preview_frame, text="Preview:", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, padx=5, pady=5, sticky="w")
        
        self.subtitle_preview = ctk.CTkLabel(
            preview_frame,
            text="Sample Subtitle Text",
            fg_color=("gray90", "gray20"),
            corner_radius=4,
            padx=10,
            pady=5
        )
        self.subtitle_preview.grid(row=1, column=0, padx=10, pady=5, sticky="ew", columnspan=3)
        self.update_subtitle_preview()
        
        # Save button
        self.save_subtitle_style_button = ctk.CTkButton(
            subtitle_frame,
            text="Save Subtitle Style",
            command=self.save_subtitle_settings,
            fg_color="#2aa745",
            hover_color="#22863a"
        )
        self.save_subtitle_style_button.grid(row=6, column=0, columnspan=3, pady=10)
        
        # Sekcja zaawansowane
        advanced_frame = ctk.CTkFrame(self.settings_tab)
        advanced_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        advanced_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(advanced_frame, text="Advanced Settings", font=ctk.CTkFont(weight="bold", size=14)).grid(
            row=0, column=0, padx=10, pady=5, sticky="w", columnspan=2)
        
        # Czyszczenie plików tymczasowych
        self.cleanup_checkbox = ctk.CTkCheckBox(
            advanced_frame,
            text="Clean temporary files after processing",
            command=self.toggle_cleanup
        )
        self.cleanup_checkbox.grid(row=1, column=0, padx=10, pady=5, sticky="w", columnspan=2)
        self.cleanup_checkbox.select()
        
        # Ścieżka do FFmpeg
        ctk.CTkLabel(advanced_frame, text="FFmpeg Path:").grid(
            row=2, column=0, padx=10, pady=5, sticky="w")
        
        self.ffmpeg_path_label = ctk.CTkLabel(
            advanced_frame,
            text=self.translator.ffmpeg_path,
            anchor="w",
            fg_color=("gray90", "gray20"),
            corner_radius=4,
            padx=10,
            height=28
        )
        self.ffmpeg_path_label.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        
        # Przycisk resetu
        reset_frame = ctk.CTkFrame(self.settings_tab)
        reset_frame.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")

    def pick_font_color(self):
        color = self.ask_color(self.subtitle_style['fontcolor'])
        if color:
            self.fontcolor_entry.delete(0, "end")
            self.fontcolor_entry.insert(0, color)
            self.update_subtitle_preview()

    def pick_bg_color(self):
        color = self.ask_color("black")
        if color:
            self.bg_color_entry.delete(0, "end")
            self.bg_color_entry.insert(0, color)
            self.update_subtitle_preview()

    def pick_border_color(self):
        color = self.ask_color(self.subtitle_style['bordercolor'])
        if color:
            self.border_color_entry.delete(0, "end")
            self.border_color_entry.insert(0, color)
            self.update_subtitle_preview()

    def ask_color(self, default_color):
        try:
            import tkinter as tk
            from tkinter import colorchooser
            root = tk.Tk()
            root.withdraw()
            color = colorchooser.askcolor(title="Choose color", initialcolor=default_color)
            return color[1] if color else None
        except:
            return None

    def update_subtitle_preview(self):
        try:
            fontsize = int(self.fontsize_slider.get())
            fontcolor = self.fontcolor_entry.get()
            border_width = int(self.border_width_slider.get())
            border_color = self.border_color_entry.get()
        
            self.fontsize_value.configure(text=str(fontsize))
            self.border_width_value.configure(text=str(border_width))
            
            # Update preview label
            self.subtitle_preview.configure(
                text="Sample Subtitle Text",
                font=ctk.CTkFont(size=fontsize),
                text_color=fontcolor,
                fg_color="transparent",  # No background
                corner_radius=0,
            )
        except Exception as e:
            print(f"Error updating preview: {e}")

    def hex_to_rgba(self, hex_color, opacity):
        """Convert hex color to rgba string with opacity"""
        if not hex_color.startswith('#'):
            return hex_color
        
        try:
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
            return f"rgba({r},{g},{b},{opacity})"
        except ValueError:
            print("Invalid hex color", hex_color)
            return hex_color

    def save_subtitle_settings(self):
        fontsize = int(self.fontsize_slider.get())
        fontcolor = self.fontcolor_entry.get()
        border_width = int(self.border_width_slider.get())  # Keep this
        border_color = self.border_color_entry.get()  # Keep this
        position = self.position_combobox.get()
        alignment = self.alignment_combobox.get()
        fontfamily = self.fontfamily_combobox.get()
        
        # Remove the boxcolor and box settings
        self.subtitle_style.update({
            'fontsize': fontsize,
            'fontcolor': fontcolor,
            'borderw': border_width,
            'bordercolor': border_color,
            'position': position,
            'alignment': alignment,
            'fontfamily': fontfamily,
            'box': 0,  # Disable background box
            'boxcolor': 'black@0'  # Make transparent
        })
    
        messagebox.showinfo("Info", "Subtitle style saved successfully")

    def toggle_log_visibility(self):
        if self.logs_visible:
            self.log_text.grid_remove()
            self.log_toggle_button.configure(text="▼")
            self.logs_visible = False
        else:
            self.log_text.grid()
            self.log_toggle_button.configure(text="▲")
            self.logs_visible = True

    def toggle_local_log_visibility(self):
        if self.local_logs_visible:
            self.local_log_text.grid_remove()
            self.local_log_toggle_button.configure(text="▼")
            self.local_logs_visible = False
        else:
            self.local_log_text.grid()
            self.local_log_toggle_button.configure(text="▲")
            self.local_logs_visible = True

    def change_appearance_mode(self, new_mode):
        ctk.set_appearance_mode(new_mode)
    
    def change_color_theme(self, new_theme):
        ctk.set_default_color_theme(new_theme)
    
    def toggle_cleanup(self):
        self.translator.clean_temp_files = self.cleanup_checkbox.get()
    
    def clean_temp_files_now(self):
        self.translator._clean_temp_files()
        messagebox.showinfo("Info", "Temporary files have been cleaned")
    
    def reset_settings(self):
        if messagebox.askyesno("Confirm", "Reset all settings to default?"):
            self.color_theme.set("blue")
            self.cleanup_checkbox.select()
            messagebox.showinfo("Info", "Settings have been reset")
    
    def toggle_subtitles_option(self):
        self.add_subtitles = self.subtitles_checkbox.get()
    
    def toggle_local_subtitles_option(self):
        self.local_add_subtitles = self.local_subtitles_checkbox.get()
    
    def choose_output_dir(self):
        output_dir = filedialog.askdirectory()
        if output_dir:
            self.output_dir_display.configure(text=output_dir)

    def choose_local_output_dir(self):
        output_dir = filedialog.askdirectory()
        if output_dir:
            self.local_output_dir_display.configure(text=output_dir)

    def choose_local_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Video Files", "*.mp4 *.avi *.mov *.mkv"), ("All Files", "*.*")])
        if file_path:
            self.local_file_display.configure(text=file_path)

    def start_youtube_process(self):
        youtube_url = self.url_entry.get().strip()
        from_lang = self.translator.language_codes[self.from_lang_combobox.get()]
        to_lang = self.translator.language_codes[self.to_lang_combobox.get()]
        quality = self.quality_combobox.get()
        output_dir = self.output_dir_display.cget("text")

        if output_dir == "Default: script directory":
            output_dir = None

        if not youtube_url:
            messagebox.showerror("Error", "Please enter a YouTube URL")
            return
        
        self.set_ui_state(disabled=True)
        self.translator.cancel_process = False
        self.youtube_status_label.configure(text="Processing...", text_color="white")
        self.youtube_progress_bar.set(0)
        
        import threading
        threading.Thread(
            target=self.run_youtube_process,
            args=(youtube_url, from_lang, to_lang, quality, output_dir),
            daemon=True
        ).start()

    def start_local_process(self):
        file_path = self.local_file_display.cget("text")
        from_lang = self.translator.language_codes[self.local_from_lang_combobox.get()]
        to_lang = self.translator.language_codes[self.local_to_lang_combobox.get()]
        output_dir = self.local_output_dir_display.cget("text")
        
        if file_path == "No file selected":
            messagebox.showerror("Error", "Please select a video file")
            return
        
        if output_dir == "Same as source file":
            output_dir = None
        
        self.set_ui_state(disabled=True)
        self.translator.cancel_process = False
        self.local_status_label.configure(text="Processing...", text_color="white")
        self.local_progress_bar.set(0)
        
        import threading
        threading.Thread(
            target=self.run_local_process,
            args=(file_path, from_lang, to_lang, output_dir),
            daemon=True
        ).start()
    
    def run_youtube_process(self, youtube_url, from_lang, to_lang, quality, output_dir):
        try:
            self.final_video_path = self.translator.main(
                youtube_url,
                from_lang,
                to_lang,
                output_dir,
                quality,
                progress_callback=self.update_youtube_progress,
                add_subtitles=self.add_subtitles,
                subtitle_style=self.subtitle_style
            )
            
            self.youtube_status_label.configure(
                text=f"Success! Saved to: {os.path.basename(self.final_video_path)}", 
                text_color="green")
            self.open_button.configure(state="normal")
            messagebox.showinfo("Success", f"Translated video saved to:\n{self.final_video_path}")
            
        except Exception as e:
            self.final_video_path = None
            self.youtube_status_label.configure(text=f"Error: {str(e)}", text_color="red")
            logging.error(f"Process failed: {str(e)}")
            
        finally:
            self.set_ui_state(disabled=False)
            self.translator.cancel_process = False

    def run_local_process(self, file_path, from_lang, to_lang, output_dir):
        try:
            self.final_video_path = self.translator.process_local_video(
                file_path,
                from_lang,
                to_lang,
                output_dir,
                progress_callback=self.update_local_progress,
                add_subtitles=self.local_add_subtitles,
                subtitle_style=self.subtitle_style
            )
            
            self.local_status_label.configure(
                text=f"Success! Saved to: {os.path.basename(self.final_video_path)}", 
                text_color="green")
            self.local_open_button.configure(state="normal")
            messagebox.showinfo("Success", f"Translated video saved to:\n{self.final_video_path}")
            
        except Exception as e:
            self.final_video_path = None
            self.local_status_label.configure(text=f"Error: {str(e)}", text_color="red")
            logging.error(f"Process failed: {str(e)}")
            
        finally:
            self.set_ui_state(disabled=False)
            self.translator.cancel_process = False
    
    def cancel_process(self):
        self.translator.cancel_process = True
        self.youtube_status_label.configure(text="Cancelling...", text_color="orange")
        self.local_status_label.configure(text="Cancelling...", text_color="orange")
        self.cancel_button.configure(state="disabled")
        self.local_cancel_button.configure(state="disabled")
    
    def open_output_folder(self):
        if self.final_video_path and os.path.exists(self.final_video_path):
            folder = os.path.dirname(self.final_video_path)
            try:
                if platform.system() == "Windows":
                    os.startfile(folder)
                elif platform.system() == "Darwin":
                    subprocess.call(["open", folder])
                else:
                    subprocess.call(["xdg-open", folder])
            except Exception as e:
                messagebox.showerror("Error", f"Could not open folder: {str(e)}")
        else:
            messagebox.showwarning("Warning", "Output folder not found")
    
    def update_youtube_progress(self, value):
        self.youtube_progress_bar.set(value)
        self.open_button.configure(state="normal" if value >= 100 else "disabled")

    def update_local_progress(self, value):
        self.local_progress_bar.set(value)
        self.local_open_button.configure(state="normal" if value >= 100 else "disabled")

    def set_ui_state(self, disabled=True):
        state = "disabled" if disabled else "normal"
        
        # YouTube Tab
        self.url_entry.configure(state=state)
        self.from_lang_combobox.configure(state=state)
        self.to_lang_combobox.configure(state=state)
        self.quality_combobox.configure(state=state)
        self.output_dir_button.configure(state=state)
        self.start_button.configure(state=state)
        self.cancel_button.configure(state="normal" if disabled else "disabled")
        self.open_button.configure(state="normal" if self.final_video_path else "disabled")
        self.subtitles_checkbox.configure(state=state)
        self.subtitle_settings_button.configure(state=state)
        
        # Local Tab
        self.local_file_button.configure(state=state)
        self.local_from_lang_combobox.configure(state=state)
        self.local_to_lang_combobox.configure(state=state)
        self.local_output_dir_button.configure(state=state)
        self.local_start_button.configure(state=state)
        self.local_cancel_button.configure(state="normal" if disabled else "disabled")
        self.local_open_button.configure(state="normal" if self.final_video_path else "disabled")
        self.local_subtitles_checkbox.configure(state=state)
        
        # Settings Tab
        self.appearance_mode.configure(state=state)
        self.color_theme.configure(state=state)
        self.cleanup_checkbox.configure(state=state)
        self.fontsize_slider.configure(state=state)
        self.fontcolor_entry.configure(state=state)
        self.position_combobox.configure(state=state)
        self.save_subtitle_style_button.configure(state=state)
    
    def update_ui_state(self):
        self.set_ui_state(disabled=False)
    
    def on_close(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            if not self.translator.clean_temp_files:
                keep_files = messagebox.askyesno(
                    "Keep temporary files?",
                    "Do you want to keep temporary files in location:\n" + 
                    (self.translator.temp_folder if self.translator.temp_folder else "Unknown")
                )
                if not keep_files:
                    self.translator.clean_temp_files = True
                    self.translator._clean_temp_files()
            
            self.destroy()

    def open_subtitle_settings(self):
        """Przełącza na zakładkę Settings i podświetla sekcję napisów"""
        self.tabview.set("Settings")
        self.highlight_subtitle_settings()

    def highlight_subtitle_settings(self):
        """Wizualnie podświetla sekcję ustawień napisów"""
        for widget in self.settings_tab.winfo_children():
            if isinstance(widget, ctk.CTkFrame) and "Subtitle Settings" in widget.winfo_children()[0].cget("text"):
                # Zapisz oryginalny kolor
                original_color = widget.cget("fg_color")
                
                # Ustaw tymczasowy kolor podświetlenia
                widget.configure(fg_color=("#e0e0e0", "#404040"))
                
                # Przywróć oryginalny kolor po 3 sekundach
                def reset_color():
                    widget.configure(fg_color=original_color)
                
                self.after(3000, reset_color)
                break

if __name__ == "__main__":
    app = YouTubeTranslatorApp()
    app.mainloop()