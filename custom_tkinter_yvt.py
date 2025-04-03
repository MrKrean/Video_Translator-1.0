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
        # Inicjalizacja ścieżek
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.ffmpeg_path = self._get_ffmpeg_path("ffmpeg")
        self.ffprobe_path = self._get_ffmpeg_path("ffprobe")
        
        # Konfiguracja pydub
        AudioSegment.converter = self.ffmpeg_path
        AudioSegment.ffprobe = self.ffprobe_path
        
        # Słownik języków
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
        
        # Flaga anulowania procesu
        self.cancel_process = False

    def _get_ffmpeg_path(self, executable):
        """Pobierz ścieżkę do pliku ffmpeg z uwzględnieniem różnych systemów"""
        if platform.system() == "Windows":
            executable += ".exe"
        
        path = os.path.join(self.script_dir, executable)
        
        if not os.path.exists(path):
            # Sprawdź czy ffmpeg jest w PATH
            path = which(executable)
            if not path:
                raise FileNotFoundError(
                    f"{executable} not found. Please install ffmpeg and add to PATH "
                    f"or place in the same directory as this script."
                )
        return path

    def _validate_youtube_url(self, url):
        """Sprawdź czy URL jest poprawnym linkiem YouTube"""
        patterns = [
            r'(https?://)?(www\.)?youtube\.com/watch\?v=',
            r'(https?://)?(www\.)?youtu\.be/',
            r'(https?://)?(www\.)?youtube\.com/shorts/'
        ]
        return any(re.search(pattern, url) for pattern in patterns)

    def _check_disk_space(self, path, required_gb=2):
        """Sprawdź dostępne miejsce na dysku"""
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
        """Usuń niedozwolone znaki z nazwy pliku"""
        return re.sub(r'[\\/*?:"<>|]', "", filename)

    def format_time(self, seconds):
        """Formatuj czas w sekundach do formatu HH:MM:SS,MS"""
        hours = math.floor(seconds / 3600)
        seconds %= 3600
        minutes = math.floor(seconds / 60)
        seconds %= 60
        milliseconds = round((seconds - math.floor(seconds))) * 1000
        seconds = math.floor(seconds)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

    def download_youtube_video(self, youtube_url, output_path, quality='best', progress_callback=None):
        """Pobierz wideo z YouTube z wybraną jakością"""
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
            
            # Format selection based on quality
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
        """Obsłuż postęp pobierania"""
        if self.cancel_process:
            raise RuntimeError("Process cancelled by user")
        
        if progress_callback and d['status'] == 'downloading':
            percent = 10 + (d.get('downloaded_bytes', 0) / d.get('total_bytes', 1) * 30)
            progress_callback(percent)

    def extract_audio(self, video_path, progress_callback=None):
        """Wyodrębnij audio z wideo"""
        try:
            base_name = os.path.splitext(video_path)[0]
            extracted_audio = f"{base_name}_extracted_audio.wav"
            
            if os.path.exists(extracted_audio):
                os.remove(extracted_audio)
                
            (
                ffmpeg.input(video_path)
                .output(extracted_audio, ac=1, ar=16000)  # Konfiguracja dla Whisper
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
        """Transkrybuj audio na tekst używając Whisper"""
        try:
            from faster_whisper import WhisperModel
            
            model = WhisperModel(
                "small",
                device="cpu",
                compute_type="int8",
                download_root=os.path.join(self.script_dir, "whisper_models")
            )
            
            # Usunięto parametr language="auto" i pozostawiamy automatyczne wykrywanie
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
        """Wygeneruj plik napisów .srt z transkrypcji"""
        try:
            base_name = os.path.splitext(output_path)[0]
            subtitle_file = f"{base_name}_subtitles.srt"
            
            subs = pysrt.SubRipFile()
            
            for index, segment in enumerate(segments):
                sub = pysrt.SubRipItem()
                sub.index = index + 1
                sub.start.seconds = segment["start"]
                sub.end.seconds = segment["end"]
                sub.text = segment["text"]
                subs.append(sub)
            
            subs.save(subtitle_file, encoding='utf-8')
            return subtitle_file
        except Exception as e:
            logging.error(f"Subtitle generation failed: {str(e)}")
            raise RuntimeError(f"Failed to generate subtitles: {e}")

    def translate_subtitles(self, subtitle_path, from_lang, to_lang, progress_callback=None):
        """Przetłumacz napisy z jednego języka na inny"""
        try:
            subs = pysrt.open(subtitle_path)
            
            # Aktualizuj indeks pakietów i pobierz dostępne tłumaczenia
            argostranslate.package.update_package_index()
            available_packages = argostranslate.package.get_available_packages()
            
            # Znajdź odpowiedni pakiet tłumaczenia
            package_to_install = next(
                (pkg for pkg in available_packages 
                 if pkg.from_code == from_lang and pkg.to_code == to_lang),
                None
            )
            
            if not package_to_install:
                raise RuntimeError(f"No translation package available for {from_lang} to {to_lang}")
            
            # Zainstaluj pakiet tłumaczenia jeśli nie jest zainstalowany
            argostranslate.package.install_from_path(package_to_install.download())
            
            # Tłumacz napisy
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
        """Wygeneruj przetłumaczone audio na podstawie napisów"""
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
            
            # Wyczyść tymczasowe pliki
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
        """Zastąp ścieżkę dźwiękową w wideo"""
        try:
            if progress_callback:
                progress_callback(96)
            
            # Utwórz polecenie ffmpeg
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
            
            # Uruchom ffmpeg
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

    def cancel(self):
        """Anuluj bieżący proces"""
        self.cancel_process = True

    def main(self, youtube_url, from_lang="en", to_lang="pl", output_dir=None, quality='best', progress_callback=None):
        """Główna metoda wykonująca proces tłumaczenia wideo"""
        if output_dir is None:
            output_dir = self.script_dir
        
        try:
            # Krok 1: Pobierz wideo z YouTube z wybraną jakością
            if progress_callback:
                progress_callback(10)
            logging.info(f"Downloading YouTube video with quality: {quality}...")
            video_path = self.download_youtube_video(youtube_url, output_dir, quality, progress_callback)
            
            # Krok 2: Wyodrębnij audio
            if progress_callback:
                progress_callback(40)
            logging.info("Extracting audio...")
            audio_path = self.extract_audio(video_path, progress_callback)
            
            # Krok 3: Transkrybuj audio
            if progress_callback:
                progress_callback(50)
            logging.info("Transcribing audio...")
            language, segments = self.transcribe(audio_path, progress_callback)
            
            # Krok 4: Wygeneruj napisy
            if progress_callback:
                progress_callback(60)
            logging.info("Generating subtitles...")
            subtitle_path = self.generate_subtitle_file(language, segments, video_path)
            
            # Krok 5: Przetłumacz napisy
            if progress_callback:
                progress_callback(70)
            logging.info("Translating subtitles...")
            translated_subtitle_path = self.translate_subtitles(subtitle_path, from_lang, to_lang, progress_callback)
            
            # Krok 6: Wygeneruj przetłumaczone audio
            if progress_callback:
                progress_callback(80)
            logging.info("Generating translated audio...")
            translated_audio_path = self.generate_translated_audio(translated_subtitle_path, video_path, to_lang, progress_callback)
            
            # Krok 7: Zastąp audio w wideo
            if progress_callback:
                progress_callback(95)
            logging.info("Replacing audio track...")
            
            # Utwórz nazwę pliku wynikowego
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
    """Niestandardowy handler logów do wyświetlania w CTkTextbox"""
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
        self.title("YouTube Video Translator")
        self.geometry("800x600")
        self.minsize(700, 500)
        
        # Konfiguracja siatki
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(8, weight=1)
        
        # Interfejs użytkownika
        self.setup_ui()
        
        # Powiązanie zdarzenia zamknięcia okna
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self):
        """Konfiguracja interfejsu użytkownika"""
        # Nagłówek
        self.header = ctk.CTkLabel(
            self, 
            text="YouTube Video Translator",
            font=ctk.CTkFont(size=20, weight="bold"))
        self.header.grid(row=0, column=0, columnspan=2, pady=(20, 10))
        
        # URL YouTube
        self.url_label = ctk.CTkLabel(self, text="YouTube URL:")
        self.url_label.grid(row=1, column=0, padx=20, pady=(0, 5), sticky="w")
        
        self.url_entry = ctk.CTkEntry(
            self, 
            width=400, 
            placeholder_text="https://www.youtube.com/watch?v=...")
        self.url_entry.grid(row=1, column=1, padx=20, pady=(0, 10), sticky="ew")
        
        # Języki i jakość
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
        
        # Wybór jakości
        self.quality_label = ctk.CTkLabel(self.language_frame, text="Video Quality:")
        self.quality_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        
        self.quality_combobox = ctk.CTkComboBox(
            self.language_frame, 
            values=['best', '1080p', '720p', '480p', '360p', '240p', '144p'],
            width=200)
        self.quality_combobox.set("best")
        self.quality_combobox.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        
        # Folder wyjściowy
        self.output_frame = ctk.CTkFrame(self)
        self.output_frame.grid(row=3, column=0, columnspan=2, padx=20, pady=10, sticky="nsew")
        self.output_frame.grid_columnconfigure(1, weight=1)
        
        self.output_dir_button = ctk.CTkButton(
            self.output_frame, 
            text="Select Output Folder",
            command=self.choose_output_dir)
        self.output_dir_button.grid(row=0, column=0, padx=10, pady=5)
        
        self.output_dir_display = ctk.CTkLabel(
            self.output_frame, 
            text="No folder selected",
            text_color="blue",
            anchor="w")
        self.output_dir_display.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        
        # Przyciski sterujące
        self.control_frame = ctk.CTkFrame(self)
        self.control_frame.grid(row=4, column=0, columnspan=2, padx=20, pady=10, sticky="nsew")
        
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
        
        # Pasek postępu
        self.progress_bar = ctk.CTkProgressBar(self, orientation="horizontal")
        self.progress_bar.set(0)
        self.progress_bar.grid(row=5, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
        
        self.progress_label = ctk.CTkLabel(self, text="0%")
        self.progress_label.grid(row=5, column=1, padx=20, pady=10, sticky="e")
        
        # Status
        self.status_frame = ctk.CTkFrame(self)
        self.status_frame.grid(row=6, column=0, columnspan=2, padx=20, pady=10, sticky="nsew")
        self.status_frame.grid_columnconfigure(0, weight=1)
        
        self.status_label = ctk.CTkLabel(
            self.status_frame, 
            text="Ready",
            text_color="green",
            anchor="w")
        self.status_label.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        
        # Konsola logów
        self.log_text = ctk.CTkTextbox(self, wrap="word", state="disabled")
        self.log_text.grid(row=7, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="nsew")
        
        # Przekieruj logi do konsoli w aplikacji
        self.log_handler = TextboxHandler(self.log_text)
        logging.getLogger().addHandler(self.log_handler)

    def choose_output_dir(self):
        """Wybierz folder wyjściowy"""
        output_dir = filedialog.askdirectory()
        if output_dir:
            self.output_dir_display.configure(text=output_dir)
        else:
            self.output_dir_display.configure(text="No folder selected")

    def start_process(self):
        """Rozpocznij proces tłumaczenia"""
        youtube_url = self.url_entry.get().strip()
        from_lang = self.translator.language_codes[self.from_lang_combobox.get()]
        to_lang = self.translator.language_codes[self.to_lang_combobox.get()]
        quality = self.quality_combobox.get()
        output_dir = self.output_dir_display.cget("text")
        
        if not youtube_url:
            messagebox.showerror("Error", "Please enter a YouTube URL.")
            return
        
        if output_dir == "No folder selected":
            output_dir = None
        
        # Wyłącz UI podczas przetwarzania
        self.set_ui_state(disabled=True)
        self.translator.cancel_process = False
        self.status_label.configure(text="Processing...", text_color="blue")
        self.progress_bar.set(0)
        self.progress_label.configure(text="0%")
        
        # Uruchom proces w osobnym wątku
        import threading
        threading.Thread(
            target=self.run_translation_process,
            args=(youtube_url, from_lang, to_lang, quality, output_dir),
            daemon=True
        ).start()

    def run_translation_process(self, youtube_url, from_lang, to_lang, quality, output_dir):
        """Uruchom proces tłumaczenia w osobnym wątku"""
        try:
            final_path = self.translator.main(
                youtube_url,
                from_lang,
                to_lang,
                output_dir,
                quality,
                progress_callback=self.update_progress
            )
            
            self.status_label.configure(
                text=f"Success! Saved to: {os.path.basename(final_path)}", 
                text_color="green")
            messagebox.showinfo("Success", f"Translated video saved to:\n{final_path}")
            
        except Exception as e:
            self.status_label.configure(text=f"Error: {str(e)}", text_color="red")
            logging.error(f"Process failed: {str(e)}")
            
        finally:
            self.set_ui_state(disabled=False)
            self.translator.cancel_process = False

    def cancel_process(self):
        """Anuluj bieżący proces"""
        self.translator.cancel_process = True
        self.status_label.configure(text="Cancelling...", text_color="orange")
        self.cancel_button.configure(state="disabled")

    def update_progress(self, value):
        """Aktualizuj pasek postępu"""
        self.progress_bar.set(value / 100)
        self.progress_label.configure(text=f"{int(value)}%")
        self.update_idletasks()

    def set_ui_state(self, disabled=True):
        """Włącz/wyłącz elementy UI"""
        state = "disabled" if disabled else "normal"
        self.url_entry.configure(state=state)
        self.from_lang_combobox.configure(state=state)
        self.to_lang_combobox.configure(state=state)
        self.quality_combobox.configure(state=state)
        self.output_dir_button.configure(state=state)
        self.start_button.configure(state=state)
        self.cancel_button.configure(state="normal" if disabled else "disabled")

    def on_close(self):
        """Obsłuż zamknięcie aplikacji"""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.translator.cancel_process = True
            self.destroy()

if __name__ == "__main__":
    app = YouTubeTranslatorApp()
    app.mainloop()