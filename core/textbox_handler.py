import logging

class TextboxHandler(logging.Handler):
    """Handler wyświetlający logi w interfejsie GUI z kolorami etapów"""
    def __init__(self, textbox):
        super().__init__()
        self.textbox = textbox
        self.stage_colors = {
            'download': '#3498DB',    # Niebieski
            'extract_audio': '#2ECC71',  # Zielony
            'transcribe': '#9B59B6',  # Fioletowy
            'translate': '#F39C12',   # Pomarańczowy
            'generate_audio': '#1ABC9C',  # Turkusowy
            'finalize': '#16A085',    # Ciemny turkus
            'default': '#FFFFFF'      # Biały
        }
        
        self.level_colors = {
            'INFO': '#2ECC71',
            'WARNING': '#F39C12',
            'ERROR': '#E74C3C',
            'DEBUG': '#3498DB',
            'CRITICAL': '#8E44AD'
        }

        self.emoji_map = {
            'INFO': 'ℹ️',
            'WARNING': '⚠️',
            'ERROR': '❌',
            'DEBUG': '🐛',
            'CRITICAL': '💥',
            'START': '🚀',
            'COMPLETE': '✅',
            'DOWNLOAD': '⏬',
            'TRANSCRIBE': '🎙️',
            'TRANSLATE': '🌐',
            'AUDIO': '🔊',
            'SUBTITLES': '📜',
            'FILE': '📁',
            'SETTINGS': '⚙️',
            'PROCESS': '🔄',
            'CLEANUP': '🧹',
            'SYSTEM': '💻'
        }

        # Konfiguracja tagów dla każdego etapu i poziomu
        for stage, color in self.stage_colors.items():
            self.textbox.tag_config(stage, foreground=color)
        for level, color in self.level_colors.items():
            self.textbox.tag_config(level, foreground=color)

    def emit(self, record):
        msg = self.format(record)
        level = record.levelname
        
        # Określ kolor na podstawie etapu lub poziomu logu
        stage = getattr(record, 'stage', '').lower()
        color = self.level_colors.get(level, self.stage_colors.get(stage, self.stage_colors['default']))
        
        emoji = self.emoji_map.get(level, '')
        if hasattr(record, 'emoji_type'):
            emoji = f"{emoji} {self.emoji_map.get(record.emoji_type, '')}"

        def append():
            self.textbox.configure(state="normal")
            tag_name = stage if stage else level
            
            log_entry = f"[{stage.upper()}] {emoji} {msg}\n" if stage else f"{emoji} {msg}\n"
            
            self.textbox.insert("end", log_entry, tag_name)
            self.textbox.configure(state="disabled")
            self.textbox.see("end")
        
        self.textbox.after(0, append)