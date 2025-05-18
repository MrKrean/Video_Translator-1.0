import os
import subprocess
import logging
from core.colored_formatter import ColoredFormatter

class AudioReplacer:
    def __init__(self, ffmpeg_path, ffprobe_path, logger=None):
        """
        Inicjalizacja AudioReplacer
        
        Args:
            ffmpeg_path (str): Ścieżka do pliku wykonywalnego ffmpeg
            ffprobe_path (str): Ścieżka do pliku wykonywalnego ffprobe
            logger (logging.Logger, optional): Obiekt loggera. Domyślnie None.
        """
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.logger = logger or self._setup_default_logger()
        
    def _setup_default_logger(self):
        """Konfiguruje domyślny logger jeśli nie został dostarczony"""
        logger = logging.getLogger('AudioReplacer')
        logger.setLevel(logging.INFO)
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(ColoredFormatter())
        
        logger.addHandler(console_handler)
        return logger
    
    def log_with_emoji(self, message, level=logging.INFO, emoji_type=None, stage=None):
        """Funkcja pomocnicza do logowania z emoji i kolorem etapu"""
        extra = {'emoji_type': emoji_type} if emoji_type else {}
        if stage:
            extra['stage'] = stage
        self.logger.log(level, message, extra=extra)
    
    def replace_audio(self, video_path, audio_path, output_path, progress_callback=None):
        """
        Zamienia ścieżkę dźwiękową w pliku wideo
        
        Args:
            video_path (str): Ścieżka do pliku wideo
            audio_path (str): Ścieżka do nowego pliku audio
            output_path (str): Ścieżka do pliku wynikowego
            progress_callback (function, optional): Funkcja callback do śledzenia postępu
            
        Returns:
            str: Ścieżka do pliku wynikowego
            
        Raises:
            RuntimeError: Jeśli wystąpi błąd podczas procesu
        """
        try:
            if progress_callback:
                progress_callback(0, 'finalize')
            
            self.log_with_emoji("Replacing audio track...", emoji_type='AUDIO', stage='finalize')
            self.log_with_emoji(f"Video: {os.path.basename(video_path)}", emoji_type='FILE', stage='finalize')
            self.log_with_emoji(f"Audio: {os.path.basename(audio_path)}", emoji_type='FILE', stage='finalize')
            self.log_with_emoji(f"Output: {os.path.basename(output_path)}", emoji_type='FILE', stage='finalize')
            
            # Sprawdzenie czy pliki wejściowe istnieją
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video file not found: {video_path}")
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
            # Tworzenie folderu wyjściowego jeśli nie istnieje
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
            
            # Komenda FFmpeg do zamiany dźwięku
            cmd = [
                self.ffmpeg_path,
                "-i", video_path,
                "-i", audio_path,
                "-c:v", "copy",          # Kopiuj strumień wideo bez zmian
                "-map", "0:v:0",        # Użyj wideo z pierwszego pliku
                "-map", "1:a:0",         # Użyj audio z drugiego pliku
                "-shortest",             # Dostosuj długość do krótszego pliku
                "-y",                   # Nadpisz plik wyjściowy bez pytania
                output_path,
            ]
            
            # Uruchomienie FFmpeg
            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            if progress_callback:
                progress_callback(100, 'finalize')
            
            self.log_with_emoji(f"Audio replaced successfully: {os.path.basename(output_path)}", 
                              emoji_type='COMPLETE', stage='finalize')
            return output_path
            
        except subprocess.CalledProcessError as e:
            error_msg = f"FFmpeg error during audio replacement: {str(e)}"
            if progress_callback:
                progress_callback(-1, 'finalize', error_msg)
            self.log_with_emoji(error_msg, logging.ERROR, 'ERROR')
            raise RuntimeError(error_msg)
            
        except Exception as e:
            error_msg = f"Failed to replace audio: {str(e)}"
            if progress_callback:
                progress_callback(-1, 'finalize', error_msg)
            self.log_with_emoji(error_msg, logging.ERROR, 'ERROR')
            raise RuntimeError(error_msg)