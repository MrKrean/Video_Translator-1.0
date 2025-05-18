import os
import pysrt
import asyncio
import logging
from pydub import AudioSegment
import edge_tts

class AudioGenerator:
    def __init__(self, ffmpeg_path=None, ffprobe_path=None, logger=None):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.logger = logger or logging.getLogger(__name__)
        
        # Ustawienia głosów TTS
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
        
        # Konfiguracja AudioSegment
        if self.ffmpeg_path:
            AudioSegment.converter = self.ffmpeg_path
        if self.ffprobe_path:
            AudioSegment.ffprobe = self.ffprobe_path

    async def _generate_tts_segment(self, text, voice, output_file):
        """Generuje pojedynczy segment TTS"""
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_file)
            return output_file
        except Exception as e:
            self.logger.error(f"Error generating TTS for text: {text[:50]}... Error: {str(e)}")
            raise

    async def generate_all_tts_segments(self, segments, voice, temp_folder):
        """Generuje wszystkie segmenty TTS asynchronicznie"""
        tasks = []
        for i, segment in enumerate(segments):
            temp_file = os.path.join(temp_folder, f"temp_{i}.mp3")
            task = self._generate_tts_segment(segment["text"], voice, temp_file)
            tasks.append(task)
        return await asyncio.gather(*tasks)

    def combine_audio_segments(self, segments_data, temp_files, output_path):
        """Łączy segmenty audio w jeden plik"""
        combined = AudioSegment.silent(duration=0)
        
        for temp_file, segment in zip(temp_files, segments_data):
            try:
                audio = AudioSegment.from_mp3(temp_file)
                silent_duration = max(0, segment["start"] * 1000 - len(combined))
                combined += AudioSegment.silent(duration=silent_duration)
                combined += audio
            except Exception as e:
                self.logger.warning(f"Failed to process segment {temp_file}: {str(e)}")
                continue
        
        combined.export(output_path, format='wav')
        return output_path

    def generate_translated_audio(self, subtitle_path, output_path, to_lang="en", progress_callback=None):
        """Główna metoda generująca przetłumaczony dźwięk"""
        try:
            if progress_callback:
                progress_callback(0, 'generate_audio')
                
            # Wczytanie napisów
            subs = pysrt.open(subtitle_path)
            voice = self.edge_tts_voices.get(to_lang, "en-US-GuyNeural")
            
            self.logger.info(f"Generating translated audio using voice: {voice}")
            self.logger.info(f"Processing {len(subs)} segments")

            # Przygotowanie danych segmentów
            segments_data = [{
                "start": sub.start.ordinal / 1000.0,
                "text": sub.text
            } for sub in subs]

            # Generowanie TTS
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            temp_files = loop.run_until_complete(
                self.generate_all_tts_segments(segments_data, voice, os.path.dirname(output_path))
            )
            loop.close()

            # Łączenie segmentów
            combined_path = self.combine_audio_segments(segments_data, temp_files, output_path)

            # Czyszczenie tymczasowych plików
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                except Exception as e:
                    self.logger.warning(f"Could not remove temp file {temp_file}: {str(e)}")

            if progress_callback:
                progress_callback(100, 'generate_audio')
                
            self.logger.info(f"Successfully generated translated audio: {output_path}")
            return combined_path
            
        except Exception as e:
            if progress_callback:
                progress_callback(-1, 'generate_audio', str(e))
            self.logger.error(f"Audio generation error: {str(e)}")
            raise RuntimeError(f"Audio generation error: {e}")