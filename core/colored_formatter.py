import logging

class ColoredFormatter(logging.Formatter):
    """Formatter dodający kolory i emoji do logów w konsoli"""
    COLORS = {
        'DEBUG': '',
        'INFO': '',
        'WARNING': '',
        'ERROR': '',
        'CRITICAL': ''
    }
    
    EMOJIS = {
        'DEBUG': '🐛 DEBUG',
        'INFO': 'ℹ️ INFO',
        'WARNING': '⚠️ WARNING',
        'ERROR': '❌ ERROR',
        'CRITICAL': '💥 CRITICAL',
        'START': '🚀 START',
        'COMPLETE': '✅ COMPLETE',
        'DOWNLOAD': '⏬ DOWNLOAD',
        'TRANSCRIBE': '🎙️ TRANSCRIBE',
        'TRANSLATE': '🌐 TRANSLATE',
        'AUDIO': '🔊 AUDIO',
        'SUBTITLES': '📜 SUBTITLES',
        'FILE': '📁 FILE',
        'SETTINGS': '⚙️ SETTINGS',
        'PROCESS': '🔄 PROCESS',
        'CLEANUP': '🧹 CLEANUP',
        'SYSTEM': '💻 SYSTEM'
    }

    def format(self, record):
        levelname = record.levelname
        emoji = self.EMOJIS.get(levelname, '')
        
        if hasattr(record, 'emoji_type'):
            emoji = self.EMOJIS.get(record.emoji_type, emoji)
        
        color = self.COLORS.get(levelname, '')
        message = super().format(record)
        return f"{color}{emoji} {message}"