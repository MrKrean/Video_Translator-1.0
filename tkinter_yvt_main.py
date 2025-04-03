import os
import sys
import math
import pysrt
import ffmpeg
import yt_dlp
import subprocess
import tkinter as tk
from PIL import Image
from gtts import gTTS
from pydub.utils import which
import argostranslate.package
from pydub import AudioSegment
import argostranslate.translate
from tkinter import ttk, filedialog, messagebox
from moviepy import VideoFileClip, AudioFileClip

# Set paths to ffmpeg and ffprobe relative to script location
script_dir = os.path.dirname(os.path.abspath(__file__))
ffmpeg_path = os.path.join(script_dir, "ffmpeg.exe")
ffprobe_path = os.path.join(script_dir, "ffprobe.exe")
ffplay_path = os.path.join(script_dir, "ffplay.exe")

# Configure pydub
AudioSegment.converter = ffmpeg_path
AudioSegment.ffprobe = ffprobe_path


# --------------- HELPER CLASSES AND FUNCTIONS ---------------

def format_time(seconds):
    """Format time in seconds to HH:MM:SS,MS format"""
    hours = math.floor(seconds / 3600)
    seconds %= 3600
    minutes = math.floor(seconds / 60)
    seconds %= 60
    milliseconds = round((seconds - math.floor(seconds)) * 1000)
    seconds = math.floor(seconds)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


# --------------- VIDEO DOWNLOAD AND PROCESSING FUNCTIONS ---------------
def download_youtube_video(youtube_url, output_path, progress_callback):
    """Download video from YouTube using yt-dlp"""
    try:
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': os.path.join(output_path, 'youtube_video.%(ext)s'),
            'ffmpeg_location': ffmpeg_path,
            'progress_hooks': [
                lambda d: progress_callback(10 + (d.get('downloaded_bytes', 0) / d.get('total_bytes', 1) * 30))],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(youtube_url, download=True)
            video_filename = ydl.prepare_filename(info_dict)
        return video_filename
    except Exception as e:
        raise RuntimeError(f"Failed to download video: {e}")


def extract_audio(video_path, progress_callback):
    try:
        extracted_audio = video_path.replace(".mp4", "_extracted_audio.wav")
        stream = ffmpeg.input(video_path)
        stream = ffmpeg.output(stream, extracted_audio)
        ffmpeg.run(stream, overwrite_output=True, cmd=ffmpeg_path)
        progress_callback(50)
        return extracted_audio
    except Exception as e:
        raise RuntimeError(f"Failed to extract audio: {e}")


# --------------- TRANSCRIPTION AND TRANSLATION FUNCTIONS ---------------
def transcribe(audio_path, progress_callback):
    """Transcribe audio to text using Whisper model"""
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("small", device="cpu")
        segments, info = model.transcribe(audio_path)
        language = info.language
        progress_callback(60)
        return language, [{"start": segment.start, "end": segment.end, "text": segment.text} for segment in segments]
    except Exception as e:
        raise RuntimeError(f"Transcription failed: {e}")


def generate_subtitle_file(language, segments, output_path):
    """Generate subtitle file (.srt) from transcription"""
    subtitle_file = output_path.replace(".mp4", "_subtitles.srt")
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


def translate_subtitles(subtitle_path, from_lang, to_lang, progress_callback):
    """Translate subtitle file from one language to another"""
    try:
        subs = pysrt.open(subtitle_path)

        # Update package index and get available translations
        argostranslate.package.update_package_index()
        available_packages = argostranslate.package.get_available_packages()

        # Find the appropriate translation package
        package_to_install = next(
            filter(
                lambda x: x.from_code == from_lang and x.to_code == to_lang, available_packages
            )
        )

        # Install the translation package if not already installed
        argostranslate.package.install_from_path(package_to_install.download())

        # Translate subtitles
        for sub in subs:
            sub.text = argostranslate.translate.translate(sub.text, from_lang, to_lang)

        translated_subtitle_path = subtitle_path.replace(".srt", f"_{to_lang}.srt")
        subs.save(translated_subtitle_path, encoding='utf-8')
        progress_callback(80)
        return translated_subtitle_path
    except Exception as e:
        raise RuntimeError(f"Translation failed: {e}")


def generate_translated_audio(subtitle_path, output_path, to_lang="pl", progress_callback=None):
    """Generate translated audio based on subtitles"""
    try:
        subs = pysrt.open(subtitle_path)
        combined = AudioSegment.silent(duration=0)

        for sub in subs:
            start_time = sub.start.ordinal / 1000.0
            tts = gTTS(sub.text, lang=to_lang)
            tts.save('temp.mp3')
            audio = AudioSegment.from_mp3('temp.mp3')
            silent_duration = max(0, start_time * 1000 - len(combined))
            combined += AudioSegment.silent(duration=silent_duration)
            combined += audio

            if progress_callback:
                current_progress = 90 * (sub.index / len(subs))
                progress_callback(current_progress)

        translated_audio_path = output_path.replace(".mp4", "_translated_audio.wav")
        combined.export(translated_audio_path, format='wav')
        os.remove('temp.mp3')

        if progress_callback:
            progress_callback(95)
        return translated_audio_path
    except Exception as e:
        raise RuntimeError(f"Audio generation failed: {e}")


def replace_audio(video_path, audio_path, output_path, progress_callback=None):
    """Replace audio track in video using ffmpeg"""
    try:
        if progress_callback:
            progress_callback(96)

        # Create ffmpeg command
        command = [
            ffmpeg_path,
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            "-y",
            output_path,
        ]

        # Run ffmpeg
        subprocess.run(command, check=True, creationflags=subprocess.CREATE_NO_WINDOW)

        if progress_callback:
            progress_callback(100)

        return output_path
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Audio replacement failed: {e}")


# --------------- MAIN FUNCTION AND INTERFACE ---------------
def main(youtube_url, from_lang="en", to_lang="pl", output_dir=None, progress_callback=None):
    """Main function that performs the video translation process"""
    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(__file__))

    try:
        # Step 1: Download YouTube video
        progress_callback(10) if progress_callback else None
        print("Downloading YouTube video...")
        video_path = download_youtube_video(youtube_url, output_dir, progress_callback)

        # Step 2: Extract audio
        progress_callback(40) if progress_callback else None
        print("Extracting audio...")
        audio_path = extract_audio(video_path, progress_callback)

        # Step 3: Transcribe audio
        progress_callback(50) if progress_callback else None
        print("Transcribing audio...")
        language, segments = transcribe(audio_path, progress_callback)

        # Step 4: Generate subtitles
        progress_callback(60) if progress_callback else None
        print("Generating subtitles...")
        subtitle_path = generate_subtitle_file(language, segments, video_path)

        # Step 5: Translate subtitles
        progress_callback(70) if progress_callback else None
        print("Translating subtitles...")
        translated_subtitle_path = translate_subtitles(subtitle_path, from_lang, to_lang, progress_callback)

        # Step 6: Generate translated audio
        progress_callback(80) if progress_callback else None
        print("Generating translated audio...")
        translated_audio_path = generate_translated_audio(translated_subtitle_path, video_path, to_lang,
                                                          progress_callback)

        # Step 7: Replace audio in video
        progress_callback(95) if progress_callback else None
        print("Replacing audio track...")
        final_video_path = replace_audio(
            video_path,
            translated_audio_path,
            os.path.join(output_dir, f"translated_video_{to_lang}.mp4"),
            progress_callback
        )

        print(f"Translated video saved as: {final_video_path}")
        return final_video_path

    except Exception as e:
        raise RuntimeError(str(e))


# --------------- USER INTERFACE ---------------
class YouTubeTranslatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Video Translator")

        # Language dictionary
        self.language_codes = {
            "English": "en",
            "Polish": "pl",
            "Spanish": "es",
            "French": "fr",
            "German": "de",
            "Italian": "it",
            "Japanese": "ja",
            "Russian": "ru"
        }
        self.languages = list(self.language_codes.keys())

        # Configure interface
        self.setup_ui()

    def setup_ui(self):
        """Set up the user interface"""
        # Configure grid
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=3)

        # URL Entry
        url_label = tk.Label(self.root, text="YouTube URL:")
        url_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.url_entry = tk.Entry(self.root, width=50)
        self.url_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        # Language Selection
        from_lang_label = tk.Label(self.root, text="Source Language:")
        from_lang_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.from_lang_combobox = ttk.Combobox(self.root, values=self.languages, width=20)
        self.from_lang_combobox.set("English")
        self.from_lang_combobox.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        to_lang_label = tk.Label(self.root, text="Target Language:")
        to_lang_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.to_lang_combobox = ttk.Combobox(self.root, values=self.languages, width=20)
        self.to_lang_combobox.set("Polish")
        self.to_lang_combobox.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        # Output Directory
        self.output_dir_label = tk.Label(self.root, text="No folder selected", fg="blue")
        self.output_dir_label.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        output_dir_button = tk.Button(self.root, text="Select Output Folder", command=self.choose_output_dir)
        output_dir_button.grid(row=4, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        # Start Button
        start_button = tk.Button(self.root, text="Start Translation", command=self.start_process)
        start_button.grid(row=5, column=0, columnspan=2, pady=10)

        # Progress Bar
        self.progress_bar = ttk.Progressbar(self.root, length=400, mode="determinate", maximum=100)
        self.progress_bar.grid(row=6, column=0, columnspan=2, padx=10, pady=10)

        # Status Label
        self.status_label = tk.Label(self.root, text="Ready", fg="green")
        self.status_label.grid(row=7, column=0, columnspan=2, padx=10, pady=5)

    def choose_output_dir(self):
        """Let user choose output directory"""
        output_dir = filedialog.askdirectory()
        if output_dir:
            self.output_dir_label.config(text=output_dir)
        else:
            self.output_dir_label.config(text="No folder selected")

    def start_process(self):
        """Start the translation process"""
        youtube_url = self.url_entry.get()
        from_lang = self.language_codes[self.from_lang_combobox.get()]
        to_lang = self.language_codes[self.to_lang_combobox.get()]
        output_dir = self.output_dir_label.cget("text")

        if not youtube_url:
            messagebox.showerror("Error", "Please enter a YouTube URL.")
            return

        if output_dir == "No folder selected":
            output_dir = None

        # Disable UI during processing
        self.set_ui_state(disabled=True)
        self.status_label.config(text="Processing...", fg="blue")
        self.progress_bar["value"] = 0

        # Run the process in a separate thread to keep UI responsive
        import threading
        threading.Thread(
            target=self.run_translation_process,
            args=(youtube_url, from_lang, to_lang, output_dir),
            daemon=True
        ).start()

    def run_translation_process(self, youtube_url, from_lang, to_lang, output_dir):
        """Run the translation process in a separate thread"""
        try:
            final_path = main(
                youtube_url,
                from_lang,
                to_lang,
                output_dir,
                progress_callback=self.update_progress
            )

            self.status_label.config(text=f"Success! Saved to: {final_path}", fg="green")
            messagebox.showinfo("Success", f"Translated video saved to:\n{final_path}")

        except Exception as e:
            self.status_label.config(text="Error occurred", fg="red")
            messagebox.showerror("Error", str(e))

        finally:
            self.set_ui_state(disabled=False)

    def update_progress(self, value):
        """Update progress bar"""
        self.progress_bar["value"] = value
        self.root.update_idletasks()

    def set_ui_state(self, disabled=True):
        """Enable or disable UI elements"""
        state = "disabled" if disabled else "normal"
        self.url_entry.config(state=state)
        self.from_lang_combobox.config(state=state)
        self.to_lang_combobox.config(state=state)
        self.output_dir_label.config(state=state)


# --------------- MAIN PROGRAM ---------------
if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeTranslatorApp(root)
    root.mainloop()