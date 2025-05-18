import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import glob
from core.colored_formatter import ColoredFormatter

class LoggingManager:
    def __init__(self, script_dir, app_name='YouTubeTranslator'):
        self.script_dir = script_dir
        self.app_name = app_name
        self.log_file = None
        self.logger = None
        
    def initialize(self):
        """Konfiguruje system logowania do pliku i konsoli"""
        self.logger = logging.getLogger(self.app_name)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        
        # Utwórz folder logs jeśli nie istnieje
        self.logs_dir = os.path.join(self.script_dir, 'logs')
        os.makedirs(self.logs_dir, exist_ok=True)
        
        # Plik logów z datą w nazwie
        log_filename = f"translation_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
        self.log_file = os.path.join(self.logs_dir, log_filename)
        
        # Rotating file handler (5 plików po 1MB każdy)
        file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        
        # Format dla pliku logów
        file_formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        # Handler do konsoli (dla GUI)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(ColoredFormatter())
        
        # Dodaj oba handlery
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Wyczyść stare logi
        self._clean_old_logs(keep_last=5)
        
        self.log_with_emoji(f"Logging initialized. Log file: {self.log_file}", emoji_type='SYSTEM')
        return self.logger

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

    def log_with_emoji(self, message, level=logging.INFO, emoji_type=None, stage=None):
        """Funkcja pomocnicza do logowania z emoji i kolorem etapu"""
        if self.logger is not None:
            extra = {'emoji_type': emoji_type} if emoji_type else {}
            if stage:
                extra['stage'] = stage
            self.logger.log(level, message, extra=extra)