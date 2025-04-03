import os
import sys
import math
import re
import pysrt
import ffmpeg
import yt_dlp
import logging
import platform
import subprocess
import customtkinter as ctk
from PIL import Image
from gtts import gTTS
from pydub.utils import which
import argostranslate.package
from pydub import AudioSegment
import argostranslate.translate
from tkinter import filedialog, messagebox
from moviepy import VideoFileClip, AudioFileClip

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='youtube_translator.log',
    filemode='a'
)

# Konfiguracja wyglądu
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class YouTubeTranslator:
    def __init__(self):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.ffmpeg_path = self._get_ffmpeg_path("ffmpeg")
        self.ffprobe_path = self._get_ffmpeg_path("ffprobe")
        
        AudioSegment.converter = self.ffmpeg_path
        AudioSegment.ffprobe = self.ffprobe_path
        
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
        
        self.cancel_process = False

    def _get_ffmpeg_path(self, executable):
        if platform.system() == "Windows":
            executable += ".exe"
        
        path = os.path.join(self.script_dir, executable)
        
        if not os.path.exists(path):
            path = which(executable)
            if not path:
                raise FileNotFoundError(
                    f"{executable} not found. Please install ffmpeg and add to PATH "
                    f"or place in the same directory as this script."
                )
        return path

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

    def _clean_filename(self, filename):
        return re.sub(r'[\\/*?:"<>|]', "", filename)

    def format_time(self, seconds):
        hours = math.floor(seconds / 3600)
        seconds %= 3600
        minutes = math.floor(seconds / 60)
        seconds %= 60
        milliseconds = round((seconds - math.floor(seconds))) * 1000
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
            
            if quality == 'best':
                ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            elif quality == '1080p':
                ydl_opts['format'] = 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            elif quality == '720p':
                ydl_opts['format'] = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            elif quality == '480p':
                ydl_opts['format'] = 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            elif quality == '360p':
                ydl_opts['format'] = 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            elif quality == '240p':
                ydl_opts['format'] = 'bestvideo[height<=240][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            elif quality == '144p':
                ydl_opts['format'] = 'bestvideo[height<=144][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(youtube_url, download=True)
                video_filename = ydl.prepare_filename(info_dict)
                
            return video_filename
        except Exception as e:
            logging.error(f"Video download failed: {str(e)}")
            raise RuntimeError(f"Failed to download video: {e}")

    def _download_progress(self, d, progress_callback):
        if self.cancel_process:
            raise RuntimeError("Process cancelled by user")
        
        if progress_callback and d['status'] == 'downloading':
            percent = 10 + (d.get('downloaded_bytes', 0) / d.get('total_bytes', 1) * 30)
            progress_callback(percent)

    def extract_audio(self, video_path, progress_callback=None):
        try:
            base_name = os.path.splitext(video_path)[0]
            extracted_audio = f"{base_name}_extracted_audio.wav"
            
            if os.path.exists(extracted_audio):
                os.remove(extracted_audio)
                
            (
                ffmpeg.input(video_path)
                .output(extracted_audio, ac=1, ar=16000)
                .overwrite_output()
                .run(cmd=self.ffmpeg_path, quiet=True)
            )
            
            if progress_callback:
                progress_callback(50)
                
            return extracted_audio
        except ffmpeg.Error as e:
            logging.error(f"FFmpeg error: {e.stderr.decode()}")
            raise RuntimeError(f"Failed to extract audio: {e}")
        except Exception as e:
            logging.error(f"Audio extraction failed: {str(e)}")
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
            raise RuntimeError("faster-whisper not installed. Please install it with: pip install faster-whisper")
        except Exception as e:
            logging.error(f"Transcription failed: {str(e)}")
            raise RuntimeError(f"Transcription failed: {e}")

    def generate_subtitle_file(self, language, segments, output_path):
        try:
            base_name = os.path.splitext(output_path)[0]
            subtitle_file = f"{base_name}_subtitles.srt"
            
            subs = pysrt.SubRipFile()
            
            for index, segment in enumerate(segments):
                sub = pysrt.SubRipItem()
                sub.index = index + 1
                
                # Replace from_seconds with direct time calculation
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
            return subtitle_file
        except Exception as e:
            logging.error(f"Subtitle generation failed: {str(e)}")
            raise RuntimeError(f"Failed to generate subtitles: {e}")

    def translate_subtitles(self, subtitle_path, from_lang, to_lang, progress_callback=None):
        try:
            subs = pysrt.open(subtitle_path)
            
            argostranslate.package.update_package_index()
            available_packages = argostranslate.package.get_available_packages()
            
            package_to_install = next(
                (pkg for pkg in available_packages 
                 if pkg.from_code == from_lang and pkg.to_code == to_lang),
                None
            )
            
            if not package_to_install:
                raise RuntimeError(f"No translation package available for {from_lang} to {to_lang}")
            
            argostranslate.package.install_from_path(package_to_install.download())
            
            for i, sub in enumerate(subs):
                if self.cancel_process:
                    break
                    
                sub.text = argostranslate.translate.translate(sub.text, from_lang, to_lang)
                
                if progress_callback and i % 10 == 0:
                    progress = 70 + (i / len(subs) * 10)
                    progress_callback(progress)
            
            base_name = os.path.splitext(subtitle_path)[0]
            translated_subtitle_path = f"{base_name}_{to_lang}.srt"
            
            subs.save(translated_subtitle_path, encoding='utf-8')
            
            if progress_callback:
                progress_callback(80)
                
            return translated_subtitle_path
        except Exception as e:
            logging.error(f"Translation failed: {str(e)}")
            raise RuntimeError(f"Translation failed: {e}")

    def generate_translated_audio(self, subtitle_path, output_path, to_lang="en", progress_callback=None):
        try:
            subs = pysrt.open(subtitle_path)
            combined = AudioSegment.silent(duration=0)
            temp_files = []
            
            for i, sub in enumerate(subs):
                if self.cancel_process:
                    break
                    
                start_time = sub.start.ordinal / 1000.0
                temp_file = f"temp_{i}.mp3"
                
                try:
                    tts = gTTS(sub.text, lang=to_lang)
                    tts.save(temp_file)
                    temp_files.append(temp_file)
                    
                    audio = AudioSegment.from_mp3(temp_file)
                    silent_duration = max(0, start_time * 1000 - len(combined))
                    combined += AudioSegment.silent(duration=silent_duration)
                    combined += audio
                    
                    if progress_callback and i % 5 == 0:
                        progress = 80 + (i / len(subs) * 15)
                        progress_callback(progress)
                except Exception as e:
                    logging.warning(f"Failed to generate TTS for segment {i}: {str(e)}")
                    continue
            
            base_name = os.path.splitext(output_path)[0]
            translated_audio_path = f"{base_name}_translated_audio.wav"
            
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
            logging.error(f"Audio generation failed: {str(e)}")
            raise RuntimeError(f"Audio generation failed: {e}")

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
            
            if progress_callback:
                progress_callback(100)
            
            return output_path
        except subprocess.CalledProcessError as e:
            logging.error(f"FFmpeg error: {e.stderr.decode()}")
            raise RuntimeError(f"Audio replacement failed: {e}")
        except Exception as e:
            logging.error(f"Audio replacement failed: {str(e)}")
            raise RuntimeError(f"Audio replacement failed: {e}")

    def process_local_video(self, video_path, from_lang="en", to_lang="pl", output_dir=None, progress_callback=None):
        if output_dir is None:
            output_dir = os.path.dirname(video_path)
        
        try:
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
            final_filename = f"{video_name}_translated_{to_lang}.mp4"
            final_video_path = os.path.join(output_dir, final_filename)
            
            final_video_path = self.replace_audio(
                video_path, 
                translated_audio_path, 
                final_video_path, 
                progress_callback
            )
            
            logging.info(f"Translated video saved as: {final_video_path}")
            return final_video_path
            
        except Exception as e:
            logging.error(f"Translation process failed: {str(e)}")
            raise

    def cancel(self):
        self.cancel_process = True

    def main(self, youtube_url, from_lang="en", to_lang="pl", output_dir=None, quality='best', progress_callback=None):
        if output_dir is None:
            output_dir = self.script_dir
        
        try:
            if progress_callback:
                progress_callback(10)
            logging.info(f"Downloading YouTube video with quality: {quality}...")
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
            final_filename = f"{video_name}_translated_{to_lang}.mp4"
            final_video_path = os.path.join(output_dir, final_filename)
            
            final_video_path = self.replace_audio(
                video_path, 
                translated_audio_path, 
                final_video_path, 
                progress_callback
            )
            
            logging.info(f"Translated video saved as: {final_video_path}")
            return final_video_path
            
        except Exception as e:
            logging.error(f"Translation process failed: {str(e)}")
            raise

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
        self.title("YouTube Video Translator")
        self.geometry("700x700")
        self.minsize(700, 500)
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(8, weight=1)
        
        self.setup_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self):
        self.header = ctk.CTkLabel(
            self, 
            text="YouTube Video Translator",
            font=ctk.CTkFont(size=20, weight="bold"))
        self.header.grid(row=0, column=0, columnspan=2, pady=(20, 10))
        
        self.url_label = ctk.CTkLabel(self, text="YouTube URL:")
        self.url_label.grid(row=1, column=0, padx=20, pady=(0, 5), sticky="w")
        
        self.url_entry = ctk.CTkEntry(
            self, 
            width=400, 
            placeholder_text="https://www.youtube.com/watch?v=...")
        self.url_entry.grid(row=1, column=1, padx=20, pady=(0, 10), sticky="ew")
        
        self.language_frame = ctk.CTkFrame(self)
        self.language_frame.grid(row=2, column=0, columnspan=2, padx=20, pady=10, sticky="nsew")
        self.language_frame.grid_columnconfigure(1, weight=1)
        
        self.from_lang_label = ctk.CTkLabel(self.language_frame, text="Source Language:")
        self.from_lang_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.from_lang_combobox = ctk.CTkComboBox(
            self.language_frame, 
            values=list(self.translator.language_codes.keys()),
            width=200)
        self.from_lang_combobox.set("English")
        self.from_lang_combobox.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        
        self.to_lang_label = ctk.CTkLabel(self.language_frame, text="Target Language:")
        self.to_lang_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        self.to_lang_combobox = ctk.CTkComboBox(
            self.language_frame, 
            values=list(self.translator.language_codes.keys()),
            width=200)
        self.to_lang_combobox.set("Polish")
        self.to_lang_combobox.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        
        self.quality_label = ctk.CTkLabel(self.language_frame, text="Video Quality:")
        self.quality_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        
        self.quality_combobox = ctk.CTkComboBox(
            self.language_frame, 
            values=['best', '1080p', '720p', '480p', '360p', '240p', '144p'],
            width=200)
        self.quality_combobox.set("best")
        self.quality_combobox.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        
        self.output_frame = ctk.CTkFrame(self)
        self.output_frame.grid(row=3, column=0, columnspan=2, padx=20, pady=10, sticky="nsew")
        self.output_frame.grid_columnconfigure(1, weight=1)
        
        self.output_dir_button = ctk.CTkButton(
            self.output_frame, 
            text="Select Output Folder",
            command=self.choose_output_dir)
        self.output_dir_button.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.output_dir_display = ctk.CTkLabel(
            self.output_frame, 
            text="No folder selected",
            text_color="white",
            anchor="w")
        self.output_dir_display.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        
        self.local_file_button = ctk.CTkButton(
            self.output_frame, 
            text="Select Local Video File",
            command=self.choose_local_file)
        self.local_file_button.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        self.local_file_display = ctk.CTkLabel(
            self.output_frame, 
            text="No file selected",
            text_color="white",
            anchor="w")
        self.local_file_display.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        self.clear_file_button = ctk.CTkButton(
            self.output_frame,
            text="❌",
            width=28,
            fg_color="transparent",
            hover_color="#d3d3d3",
            command=self.clear_local_file)
        self.clear_file_button.grid(row=1, column=2, padx=(0, 10), pady=5, sticky="e")
        
        self.control_frame = ctk.CTkFrame(self)
        self.control_frame.grid(row=4, column=0, columnspan=2, padx=20, pady=10, sticky="nsew")
        self.control_frame.grid_columnconfigure(3, weight=1)
        
        self.start_button = ctk.CTkButton(
            self.control_frame, 
            text="Start Translation",
            command=self.start_process)
        self.start_button.grid(row=0, column=0, padx=10, pady=5)
        
        self.cancel_button = ctk.CTkButton(
            self.control_frame, 
            text="Cancel",
            fg_color="red",
            hover_color="darkred",
            command=self.cancel_process,
            state="disabled")
        self.cancel_button.grid(row=0, column=1, padx=10, pady=5)
        
        self.open_button = ctk.CTkButton(
            self.control_frame, 
            text="Open Translated Video",
            command=self.open_translated_video,
            state="disabled")
        self.open_button.grid(row=0, column=2, padx=10, pady=5)
        
        self.progress_bar = ctk.CTkProgressBar(self, orientation="horizontal")
        self.progress_bar.set(0)
        self.progress_bar.grid(row=5, column=0, columnspan=2, padx=(20,60), pady=10, sticky="ew")
        
        self.progress_label = ctk.CTkLabel(self, text="0%")
        self.progress_label.grid(row=5, column=1, padx=20, pady=10, sticky="e")
        
        self.status_frame = ctk.CTkFrame(self)
        self.status_frame.grid(row=6, column=0, columnspan=2, padx=20, pady=10, sticky="nsew")
        self.status_frame.grid_columnconfigure(0, weight=1)
        
        self.status_label = ctk.CTkLabel(
            self.status_frame, 
            text="Ready",
            text_color="green",
            anchor="w")
        self.status_label.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        
        self.log_text = ctk.CTkTextbox(self, wrap="word", state="disabled")
        self.log_text.grid(row=7, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="nsew")
        
        self.log_handler = TextboxHandler(self.log_text)
        logging.getLogger().addHandler(self.log_handler)

    def choose_output_dir(self):
        output_dir = filedialog.askdirectory()
        if output_dir:
            self.output_dir_display.configure(text=output_dir)
        else:
            self.output_dir_display.configure(text="No folder selected")

    def choose_local_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Video Files", "*.mp4 *.avi *.mov *.mkv"), ("All Files", "*.*")])
        if file_path:
            self.local_file_display.configure(text=file_path)
            self.output_dir_display.configure(text=os.path.dirname(file_path))
        else:
            self.local_file_display.configure(text="No file selected")

    def clear_local_file(self):
        self.local_file_display.configure(text="No file selected")
        self.output_dir_display.configure(text="No folder selected")

    def start_process(self):
        self.final_video_path = None
        youtube_url = self.url_entry.get().strip()
        local_file_path = self.local_file_display.cget("text")
        from_lang = self.translator.language_codes[self.from_lang_combobox.get()]
        to_lang = self.translator.language_codes[self.to_lang_combobox.get()]
        quality = self.quality_combobox.get()
        output_dir = self.output_dir_display.cget("text")
        
        if not youtube_url and local_file_path == "No file selected":
            messagebox.showerror("Error", "Please enter a YouTube URL or select a local video file.")
            return
        
        if output_dir == "No folder selected":
            output_dir = None
        
        self.set_ui_state(disabled=True)
        self.translator.cancel_process = False
        self.status_label.configure(text="Processing...", text_color="white")
        self.progress_bar.set(0)
        self.progress_label.configure(text="0%")
        
        import threading
        if local_file_path != "No file selected":
            threading.Thread(
                target=self.run_local_video_process,
                args=(local_file_path, from_lang, to_lang, output_dir),
                daemon=True
            ).start()
        else:
            threading.Thread(
                target=self.run_youtube_process,
                args=(youtube_url, from_lang, to_lang, quality, output_dir),
                daemon=True
            ).start()
    
    def run_local_video_process(self, video_path, from_lang, to_lang, output_dir):
        try:
            self.final_video_path = self.translator.process_local_video(
                video_path,
                from_lang,
                to_lang,
                output_dir,
                progress_callback=self.update_progress
            )
            
            self.status_label.configure(
                text=f"Success! Saved to: {os.path.basename(self.final_video_path)}", 
                text_color="green")
            messagebox.showinfo("Success", f"Translated video saved to:\n{self.final_video_path}")
            
        except Exception as e:
            self.final_video_path = None
            self.status_label.configure(text=f"Error: {str(e)}", text_color="red")
            logging.error(f"Process failed: {str(e)}")
            
        finally:
            self.set_ui_state(disabled=False)
            self.translator.cancel_process = False
            
    def run_youtube_process(self, youtube_url, from_lang, to_lang, quality, output_dir):
        try:
            self.final_video_path = self.translator.main(
                youtube_url,
                from_lang,
                to_lang,
                output_dir,
                quality,
                progress_callback=self.update_progress
            )
            
            self.status_label.configure(
                text=f"Success! Saved to: {os.path.basename(self.final_video_path)}", 
                text_color="green")
            messagebox.showinfo("Success", f"Translated video saved to:\n{self.final_video_path}")
            
        except Exception as e:
            self.final_video_path = None
            self.status_label.configure(text=f"Error: {str(e)}", text_color="red")
            logging.error(f"Process failed: {str(e)}")
            
        finally:
            self.set_ui_state(disabled=False)
            self.translator.cancel_process = False

    def open_translated_video(self):
        if self.final_video_path and os.path.exists(self.final_video_path):
            try:
                if platform.system() == "Windows":
                    os.startfile(self.final_video_path)
                elif platform.system() == "Darwin":
                    subprocess.call(("open", self.final_video_path))
                else:
                    subprocess.call(("xdg-open", self.final_video_path))
            except Exception as e:
                messagebox.showerror("Error", f"Could not open file: {str(e)}")
        else:
            messagebox.showwarning("Warning", "Translated video file not found")

    def cancel_process(self):
        self.translator.cancel_process = True
        self.status_label.configure(text="Cancelling...", text_color="orange")
        self.cancel_button.configure(state="disabled")

    def update_progress(self, value):
        self.progress_bar.set(value / 100)
        self.progress_label.configure(text=f"{int(value)}%")
        self.update_idletasks()

    def set_ui_state(self, disabled=True):
        state = "disabled" if disabled else "normal"
        self.url_entry.configure(state=state)
        self.from_lang_combobox.configure(state=state)
        self.to_lang_combobox.configure(state=state)
        self.quality_combobox.configure(state=state)
        self.output_dir_button.configure(state=state)
        self.local_file_button.configure(state=state)
        self.start_button.configure(state=state)
        self.cancel_button.configure(state="normal" if disabled else "disabled")
        self.open_button.configure(state="normal" if self.final_video_path else "disabled")

    def on_close(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.translator.cancel_process = True
            self.destroy()

if __name__ == "__main__":
    app = YouTubeTranslatorApp()
    app.mainloop()