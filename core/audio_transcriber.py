from faster_whisper import WhisperModel
import logging
import os

class AudioTranscriber:
    def __init__(self, model_size="small", device="cpu", compute_type="int8", logger=None):
        """
        Inicjalizacja transkrybera audio
        
        :param model_size: Rozmiar modelu Whisper (np. 'tiny', 'base', 'small', 'medium', 'large')
        :param device: Urządzenie do obliczeń ('cpu' lub 'cuda')
        :param compute_type: Typ obliczeń ('int8', 'float16', itp.)
        :param logger: Obiekt loggera
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.logger = logger or logging.getLogger(__name__)
        self.model = None
        
    def load_model(self, models_dir="whisper_models"):
        """Ładowanie modelu Whisper"""
        try:
            self.logger.info("Ładowanie modelu Whisper...")
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                download_root=os.path.join(os.path.dirname(__file__), models_dir)
            )
            self.logger.info("Model Whisper załadowany pomyślnie")
        except Exception as e:
            self.logger.error(f"Błąd podczas ładowania modelu Whisper: {str(e)}")
            raise

    def transcribe(self, audio_path, beam_size=5, progress_callback=None):
        """
        Transkrybuj audio do tekstu
        
        :param audio_path: Ścieżka do pliku audio
        :param beam_size: Rozmiar wiązki dla dekodowania
        :param progress_callback: Funkcja callback do raportowania postępu
        :return: tuple (język, lista segmentów)
        """
        if not self.model:
            self.load_model()
            
        try:
            if progress_callback:
                progress_callback(0, 'transcribe')
                
            self.logger.info(f"Rozpoczynanie transkrypcji: {audio_path}")
            
            segments, info = self.model.transcribe(
                audio_path,
                beam_size=beam_size
            )
            
            language = info.language
            segments_list = []
            
            self.logger.info(f"Wykryty język: {language}")
            
            for i, segment in enumerate(segments):
                segments_list.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text
                })
                
                if progress_callback and i % 5 == 0:
                    progress = (i / (i + 1)) * 100
                    progress_callback(progress, 'transcribe')
                
                if i % 10 == 0:
                    self.logger.info(
                        f"Transkrybowany segment {i}: {segment.text[:50]}..."
                    )
            
            if progress_callback:
                progress_callback(100, 'transcribe')
                
            self.logger.info(
                f"Transkrypcja zakończona. Liczba segmentów: {len(segments_list)}"
            )
            return language, segments_list
            
        except Exception as e:
            self.logger.error(f"Błąd transkrypcji: {str(e)}")
            if progress_callback:
                progress_callback(-1, 'transcribe', str(e))
            raise RuntimeError(f"Błąd transkrypcji: {e}")