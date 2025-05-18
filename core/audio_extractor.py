import os
import subprocess
import logging
from pydub import AudioSegment

class AudioExtractor:
    def __init__(self, ffmpeg_path, ffprobe_path, logger=None):
        """
        Inicjalizacja ekstraktora audio
        
        :param ffmpeg_path: Ścieżka do ffmpeg
        :param ffprobe_path: Ścieżka do ffprobe
        :param logger: Obiekt loggera (opcjonalny)
        """
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.logger = logger or logging.getLogger(__name__)
        
        # Konfiguracja pydub
        AudioSegment.converter = self.ffmpeg_path
        AudioSegment.ffprobe = self.ffprobe_path

    def extract_audio(self, video_path, output_path=None, audio_format='wav', progress_callback=None):
        """
        Ekstrakcja audio z pliku wideo
        
        :param video_path: Ścieżka do pliku wideo
        :param output_path: Ścieżka wyjściowa (opcjonalna)
        :param audio_format: Format wyjściowy (wav/mp3)
        :param progress_callback: Funkcja callback do śledzenia postępu
        :return: Ścieżka do wyekstrahowanego pliku audio
        """
        try:
            if progress_callback:
                progress_callback(0, 'extract_audio')
                
            base_name = os.path.splitext(os.path.basename(video_path))[0]
            output_path = output_path or os.path.join(
                os.path.dirname(video_path),
                f"{base_name}_extracted_audio.{audio_format}"
            )
            
            if os.path.exists(output_path):
                os.remove(output_path)
                
            self._log_with_emoji(f"Extracting audio from: {os.path.basename(video_path)}", emoji_type='AUDIO')
            self._log_with_emoji(f"Output audio file: {os.path.basename(output_path)}", emoji_type='FILE')
            
            cmd = [
                self.ffmpeg_path,
                '-i', video_path,
                '-ac', '1',          # Mono audio
                '-ar', '16000',      # 16kHz sample rate
                '-y',                # Overwrite output
                output_path
            ]
            
            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            if progress_callback:
                progress_callback(100, 'extract_audio')
                
            self._log_with_emoji("Audio extracted successfully", emoji_type='COMPLETE')
            self._log_with_emoji(f"Audio file size: {os.path.getsize(output_path)/(1024*1024):.2f}MB", emoji_type='FILE')
            return output_path
            
        except subprocess.CalledProcessError as e:
            error_msg = f"FFmpeg error: {str(e)}"
            self._log_with_emoji(error_msg, logging.ERROR, 'ERROR')
            if progress_callback:
                progress_callback(-1, 'extract_audio', error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"Audio extraction error: {str(e)}"
            self._log_with_emoji(error_msg, logging.ERROR, 'ERROR')
            if progress_callback:
                progress_callback(-1, 'extract_audio', error_msg)
            raise RuntimeError(error_msg)

    def convert_audio_format(self, input_path, output_format='mp3', output_path=None):
        """
        Konwersja formatu pliku audio
        
        :param input_path: Ścieżka do pliku wejściowego
        :param output_format: Docelowy format (mp3/wav)
        :param output_path: Ścieżka wyjściowa (opcjonalna)
        :return: Ścieżka do przekonwertowanego pliku
        """
        try:
            if not output_path:
                base_name = os.path.splitext(os.path.basename(input_path))[0]
                output_path = os.path.join(
                    os.path.dirname(input_path),
                    f"{base_name}_converted.{output_format}"
                )
            
            audio = AudioSegment.from_file(input_path)
            audio.export(output_path, format=output_format)
            
            self._log_with_emoji(f"Audio converted to {output_format}: {os.path.basename(output_path)}", emoji_type='COMPLETE')
            return output_path
        except Exception as e:
            self._log_with_emoji(f"Audio conversion error: {str(e)}", logging.ERROR, 'ERROR')
            raise RuntimeError(f"Audio conversion error: {e}")

    def normalize_audio(self, input_path, output_path=None, target_dBFS=-20.0):
        """
        Normalizacja głośności audio
        
        :param input_path: Ścieżka do pliku wejściowego
        :param output_path: Ścieżka wyjściowa (opcjonalna)
        :param target_dBFS: Docelowy poziom głośności
        :return: Ścieżka do znormalizowanego pliku
        """
        try:
            if not output_path:
                base_name = os.path.splitext(os.path.basename(input_path))[0]
                output_path = os.path.join(
                    os.path.dirname(input_path),
                    f"{base_name}_normalized.wav"
                )
            
            audio = AudioSegment.from_file(input_path)
            change_in_dBFS = target_dBFS - audio.dBFS
            normalized = audio.apply_gain(change_in_dBFS)
            normalized.export(output_path, format="wav")
            
            self._log_with_emoji(f"Audio normalized to {target_dBFS} dBFS: {os.path.basename(output_path)}", emoji_type='COMPLETE')
            return output_path
        except Exception as e:
            self._log_with_emoji(f"Audio normalization error: {str(e)}", logging.ERROR, 'ERROR')
            raise RuntimeError(f"Audio normalization error: {e}")

    def _log_with_emoji(self, message, level=logging.INFO, emoji_type=None):
        """Pomocnicza funkcja do logowania z emoji"""
        if self.logger:
            extra = {'emoji_type': emoji_type} if emoji_type else {}
            self.logger.log(level, message, extra=extra)