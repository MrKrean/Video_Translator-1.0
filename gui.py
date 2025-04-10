import os
import logging
from logging.handlers import RotatingFileHandler
import platform
import subprocess
import webbrowser
from tkinter import messagebox, filedialog
import customtkinter as ctk
from PIL import Image
from core import VideoTranslator

class EmojiTextHandler(logging.Handler):
    def __init__(self, textbox):
        super().__init__()
        self.textbox = textbox
        self.setup_emoji_mapping()
        self.setup_message_styles()
        self.setup_colors()
        self.setup_tags()

    def setup_emoji_mapping(self):
        self.emoji_map = {
            'INFO': 'ℹ️',
            'WARNING': '⚠️',
            'ERROR': '❌',
            'CRITICAL': '🔥',
            'DEBUG': '🐛',
            'SUCCESS': '✅',
            'PROGRESS': '📊',
            'DOWNLOAD': '📥',
            'TRANSCRIBE': '🎤',
            'TRANSLATE': '🌍',
            'PROCESS': '⚙️',
            'AUDIO': '🎧',
            'VIDEO': '🎬',
            'FILE': '📁',
            'EXTRACT': '🔍',
            'SYNTHESIZE': '🔊',
            'COMBINE': '🔄'
        }

    def setup_message_styles(self):
        self.message_styles = {
            'START': lambda msg: f"🚀 {msg}",
            'COMPLETE': lambda msg: f"🎉 {msg}",
            'FAIL': lambda msg: f"💥 {msg}",
            'STATUS': lambda msg: f"📌 {msg}",
            'FILE': lambda msg: f"📄 {msg}",
            'CONNECTING': lambda msg: f"🔗 {msg}",
            'EXTRACTING': lambda msg: f"🔍 {msg}",
            'SAVING': lambda msg: f"💾 {msg}",
            'CLEANING': lambda msg: f"🧹 {msg}"
        }

    def setup_colors(self):
        self.color_map = {
            'ERROR': '#ff4444',
            'WARNING': '#ffaa33',
            'INFO': '#33b5e5',
            'SUCCESS': '#00C851',
            'DEBUG': '#ffbb33',
            'DOWNLOAD': '#aa66cc',
            'TRANSCRIBE': '#ff8800',
            'TRANSLATE': '#0099cc',
            'PROCESS': '#33b5e5',
            'FILE': '#2bbbad',
            'EXTRACT': '#ff8800',
            'SYNTHESIZE': '#00C851',
            'COMBINE': '#33b5e5'
        }

    def setup_tags(self):
        colors = {
            'error': '#ff4444',
            'warning': '#ffaa33',
            'info': '#33b5e5',
            'success': '#00C851',
            'debug': '#ffbb33',
            'download': '#aa66cc',
            'transcribe': '#ff8800',
            'translate': '#0099cc',
            'process': '#33b5e5',
            'file': '#2bbbad'
        }
        
        for name, color in colors.items():
            self.textbox.tag_config(name, foreground=color)

    def format_message(self, record):
        msg = self.format(record)
        
        # Add emoji based on log level or special keywords
        emoji = self.emoji_map.get(record.levelname, '📝')
        for keyword, emoji_code in self.emoji_map.items():
            if keyword in record.getMessage():
                emoji = emoji_code
                break
        
        msg = f"{emoji} {msg}"
        
        # Apply special styles for keywords
        for prefix, style in self.message_styles.items():
            if prefix in record.getMessage():
                msg = style(msg.replace(prefix, '').strip())
                break
        
        return msg

    def get_message_tag(self, record):
        # Check for special keywords first
        for keyword in ['DOWNLOAD', 'TRANSCRIBE', 'TRANSLATE', 'PROCESS', 'FILE', 
                       'EXTRACT', 'SYNTHESIZE', 'COMBINE']:
            if keyword in record.getMessage():
                return keyword.lower()
        
        # Fall back to level-based tags
        return record.levelname.lower()

    def emit(self, record):
        msg = self.format_message(record)
        tag = self.get_message_tag(record)
        
        def append():
            self.textbox.configure(state="normal")
            self.textbox.insert("end", msg + "\n", tag)
            self.textbox.configure(state="disabled")
            self.textbox.see("end")
        
        self.textbox.after(0, append)

class VideoTranslatorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.translator = VideoTranslator()
        self.final_video_path = None
        
        self.subtitle_style = {
            'fontsize': 24,
            'fontcolor': 'white',
            'boxcolor': 'black@0.5',
            'box': 1,
            'borderw': 1,
            'bordercolor': 'black',
            'position': 'bottom',
            'alignment': 'center',
            'fontfamily': 'Arial'
        }
        
        self.add_subtitles = False
        self.local_add_subtitles = False
        self.logs_visible = True
        self.local_logs_visible = True

        self._setup_ui()
        self._setup_logging()
        self.check_log_file()

    def _setup_logging(self):
        """Configure logging with both console and file output"""
        try:
            # Create logs directory if it doesn't exist
            logs_dir = os.path.join(self.translator.script_dir, "logs")
            os.makedirs(logs_dir, exist_ok=True)
            
            log_file = os.path.join(logs_dir, "video_translator.log")
            
            # Clear existing log file on each start (optional)
            if os.path.exists(log_file):
                open(log_file, 'w').close()
            
            # Main logger configuration
            self.logger = logging.getLogger('youtube')
            self.logger.setLevel(logging.INFO)
            
            # Local logger configuration
            self.local_logger = logging.getLogger('local')
            self.local_logger.setLevel(logging.INFO)
            
            # File handler configuration with rotation
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=5*1024*1024,  # 5 MB
                backupCount=3,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.INFO)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            
            # Add handlers to both loggers
            for logger in [self.logger, self.local_logger]:
                # Clear any existing handlers
                if logger.hasHandlers():
                    logger.handlers.clear()
                
                # Add emoji handler for GUI
                logger.addHandler(EmojiTextHandler(
                    self.log_text if logger == self.logger else self.local_log_text
                ))
                
                # Add file handler
                logger.addHandler(file_handler)
                
                # Prevent propagation to root logger
                logger.propagate = False
            
            self.log_message("START Logging system initialized")
            self.log_message(f"FILE Log file created at: {log_file}")
            
        except Exception as e:
            # Fallback to basic logging if file logging fails
            logging.basicConfig(level=logging.INFO)
            self.logger.error(f"FAIL Could not configure file logging: {str(e)}")

    def check_log_file(self):
        log_file = os.path.join(self.translator.script_dir, "logs", "video_translator.log")
        if os.path.exists(log_file):
            self.log_message(f"STATUS Log file exists at: {log_file}")
            return True
        else:
            self.log_message("WARNING Log file was not created!", level=logging.WARNING)
            return False

    def _setup_ui(self):
        self.title("🎬 Video Translator Pro")
        self.geometry("1000x800")
        self.minsize(900, 700)
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        
        try:
            self.iconbitmap(os.path.join(self.translator.script_dir, "icon_vt.ico"))
        except:
            pass
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self._create_header()
        self._create_tabs()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.update_ui_state()

    def _create_header(self):
        self.header_font = ctk.CTkFont(size=24, weight="bold")
        self.header = ctk.CTkLabel(
            self, 
            text="🎬 Video Translator Pro",
            font=self.header_font,
            anchor="center"
        )
        self.header.grid(row=0, column=0, pady=(20, 10), padx=20, sticky="ew")

    def _create_tabs(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        
        self.youtube_tab = self.tabview.add("YouTube Video")
        self._setup_youtube_tab()
        
        self.local_tab = self.tabview.add("Local Video")
        self._setup_local_tab()
        
        self.settings_tab = self.tabview.add("Settings")
        self._setup_settings_tab()
        
        self.about_tab = self.tabview.add("About & Help ❓")
        self._setup_about_tab()

    def _setup_youtube_tab(self):
        self.youtube_tab.grid_columnconfigure(0, weight=1)
        self.youtube_tab.grid_rowconfigure(0, weight=1)
        
        scroll_frame = ctk.CTkScrollableFrame(self.youtube_tab)
        scroll_frame.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        scroll_frame.grid_columnconfigure(0, weight=1)

        url_frame = ctk.CTkFrame(scroll_frame)
        url_frame.grid(row=0, column=0, padx=10, pady=(5, 10), sticky="nsew")
        url_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(url_frame, text="YouTube URL:", font=ctk.CTkFont(weight="bold", size=14)).grid(
            row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        self.url_entry = ctk.CTkEntry(
            url_frame,
            placeholder_text="https://www.youtube.com/watch?v=...",
            font=ctk.CTkFont(size=14)
        )
        self.url_entry.grid(row=0, column=1, padx=10, pady=(10, 5), sticky="ew")

        settings_frame = ctk.CTkFrame(scroll_frame)
        settings_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        settings_frame.grid_columnconfigure(1, weight=1)

        lang_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        lang_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(lang_frame, text="From:").pack(side="left", padx=(0, 8))

        self.from_lang_combobox = ctk.CTkComboBox(
            lang_frame,
            values=list(self.translator.language_codes.keys()),
            width=200
        )
        self.from_lang_combobox.set("English")
        self.from_lang_combobox.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(lang_frame, text="To:").pack(side="left", padx=(0, 8))

        self.to_lang_combobox = ctk.CTkComboBox(
            lang_frame,
            values=list(self.translator.language_codes.keys()),
            width=200
        )
        self.to_lang_combobox.set("Polish")
        self.to_lang_combobox.pack(side="left")

        qual_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        qual_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(qual_frame, text="Video Quality:").pack(side="left", padx=(0, 9))
        self.quality_combobox = ctk.CTkComboBox(
            qual_frame,
            values=['best', '1080p', '720p', '480p', '360p', '240p', '144p'],
            width=155
        )
        self.quality_combobox.set("best")
        self.quality_combobox.pack(side="left", padx=(0, 20))

        subtitles_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        subtitles_frame.grid(row=3, column=0, padx=10, pady=5, sticky="w", columnspan=2)

        self.subtitles_checkbox = ctk.CTkCheckBox(
            subtitles_frame,
            text="Add subtitles to video",
            command=self.toggle_subtitles_option
        )
        self.subtitles_checkbox.pack(side="left", padx=(0, 10))

        self.subtitle_settings_button = ctk.CTkButton(
            subtitles_frame,
            text="⚙️",
            width=25,
            hover_color="#525252",
            fg_color="transparent",
            command=self.open_subtitle_settings,
            font=ctk.CTkFont(size=18)
        )
        self.subtitle_settings_button.pack(side="left")

        output_frame = ctk.CTkFrame(scroll_frame)
        output_frame.grid(row=4, column=0, padx=10, pady=10, sticky="nsew")
        output_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(output_frame, text="Output Folder:").grid(
            row=0, column=0, padx=10, pady=5, sticky="w") 
        self.output_dir_display = ctk.CTkLabel(
            output_frame,
            text="Default: script directory",
            anchor="w",
            fg_color=("gray90", "gray20"),
            corner_radius=4,
            padx=10,
            height=28
        )
        self.output_dir_display.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        self.output_dir_button = ctk.CTkButton(
            output_frame,
            text="Browse...",
            width=100,
            command=self.choose_output_dir
        )
        self.output_dir_button.grid(row=0, column=2, padx=10, pady=5)

        button_frame = ctk.CTkFrame(scroll_frame)
        button_frame.grid(row=5, column=0, padx=10, pady=10, sticky="nsew")

        self.start_button = ctk.CTkButton(
            button_frame,
            text="Start Translation",
            command=self.start_youtube_process,
            fg_color="#2aa745",
            hover_color="#22863a",
            width=150
        )
        self.start_button.pack(side="left", padx=10, pady=5)

        self.youtube_status_frame = ctk.CTkFrame(scroll_frame)
        self.youtube_status_frame.grid(row=6, column=0, padx=10, pady=(5, 10), sticky="nsew")
        self.youtube_status_frame.grid_columnconfigure(1, weight=1)

        self.youtube_status_label = ctk.CTkLabel(
            self.youtube_status_frame, 
            text="Status: Ready", 
            text_color="green",
        )
        self.youtube_status_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.youtube_progress_bar = ctk.CTkProgressBar(
            self.youtube_status_frame, 
            width=300, 
            height=10, 
            mode="determinate"
        )
        self.youtube_progress_bar.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        self.youtube_progress_bar.set(0)

        self.cancel_button = ctk.CTkButton(
            self.youtube_status_frame,
            text="Cancel",
            command=self.cancel_process,
            fg_color="#d73a49",
            hover_color="#cb2431",
            state="disabled",
            width=100
        )
        self.cancel_button.grid(row=0, column=2, padx=10, pady=5, sticky="e")

        self.open_button = ctk.CTkButton(
            button_frame,
            text="Open Output Folder",
            command=self.open_output_folder,
            state="disabled",
            width=150
        )
        self.open_button.pack(side="right", padx=10, pady=5)

        log_frame = ctk.CTkFrame(scroll_frame)
        log_frame.grid(row=7, column=0, padx=10, pady=(10, 5), sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)

        log_header_frame = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        ctk.CTkLabel(log_header_frame, text="Process Log:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
        
        self.log_toggle_button = ctk.CTkButton(
            log_header_frame,
            text="▲",
            width=30,
            fg_color="transparent",
            hover_color="#525252",
            command=self.toggle_log_visibility,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.log_toggle_button.pack(side="right", padx=5)
        
        self.log_text = ctk.CTkTextbox(
            log_frame,
            wrap="word",
            state="disabled",
            font=ctk.CTkFont(family="Consolas", size=12),
            height=150
        )
        self.log_text.grid(row=1, column=0, padx=5, pady=(0, 5), sticky="nsew")

    def _setup_local_tab(self):
        self.local_tab.grid_columnconfigure(0, weight=1)
        self.local_tab.grid_rowconfigure(0, weight=1)
        
        scroll_frame = ctk.CTkScrollableFrame(self.local_tab)
        scroll_frame.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        scroll_frame.grid_columnconfigure(0, weight=1)

        file_frame = ctk.CTkFrame(scroll_frame)
        file_frame.grid(row=0, column=0, padx=10, pady=(5, 10), sticky="nsew")
        file_frame.grid_columnconfigure(1, weight=1)

        file_label = ctk.CTkLabel(file_frame, text="Video File:", font=ctk.CTkFont(weight="bold", size=14))
        file_label.grid(row=0, column=0, padx=(10, 5), pady=(10, 5), sticky="w")

        self.local_file_display = ctk.CTkLabel(
            file_frame,
            text="No file selected",
            anchor="w",
            fg_color=("gray90", "gray20"),
            corner_radius=4,
            padx=10,
            height=28
        )
        self.local_file_display.grid(row=0, column=1, padx=5, pady=(10, 5), sticky="ew")

        self.local_file_button = ctk.CTkButton(
            file_frame,
            text="Select File",
            command=self.choose_local_file,
            width=100
        )
        self.local_file_button.grid(row=0, column=2, padx=(5, 10), pady=(10, 5), sticky="e")

        settings_frame = ctk.CTkFrame(scroll_frame)
        settings_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        settings_frame.grid_columnconfigure(1, weight=1)

        lang_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        lang_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(lang_frame, text="From:").pack(side="left", padx=(0, 8))

        self.local_from_lang_combobox = ctk.CTkComboBox(
            lang_frame,
            values=list(self.translator.language_codes.keys()),
            width=200
        )
        self.local_from_lang_combobox.set("English")
        self.local_from_lang_combobox.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(lang_frame, text="To:").pack(side="left", padx=(0, 8))

        self.local_to_lang_combobox = ctk.CTkComboBox(
            lang_frame,
            values=list(self.translator.language_codes.keys()),
            width=200
        )
        self.local_to_lang_combobox.set("Polish")
        self.local_to_lang_combobox.pack(side="left")

        subtitles_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        subtitles_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        self.local_subtitles_checkbox = ctk.CTkCheckBox(
            subtitles_frame,
            text="Add subtitles to video",
            command=self.toggle_local_subtitles_option
        )
        self.local_subtitles_checkbox.pack(side="left", padx=(0, 10))

        self.local_subtitle_settings_button = ctk.CTkButton(
            subtitles_frame,
            text="⚙️",
            width=25,
            hover_color="#525252",
            fg_color="transparent",
            command=self.open_subtitle_settings,
            font=ctk.CTkFont(size=18)
        )
        self.local_subtitle_settings_button.pack(side="left")

        output_frame = ctk.CTkFrame(scroll_frame)
        output_frame.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")
        output_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(output_frame, text="Output Folder:").grid(
            row=0, column=0, padx=10, pady=5, sticky="w"
        )

        self.local_output_dir_display = ctk.CTkLabel(
            output_frame,
            text="Same as source file",
            anchor="w",
            fg_color=("gray90", "gray20"),
            corner_radius=4,
            padx=10,
            height=28
        )
        self.local_output_dir_display.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        self.local_output_dir_button = ctk.CTkButton(
            output_frame,
            text="Browse...",
            width=100,
            command=self.choose_local_output_dir
        )
        self.local_output_dir_button.grid(row=0, column=2, padx=10, pady=5)

        button_frame = ctk.CTkFrame(scroll_frame)
        button_frame.grid(row=4, column=0, padx=10, pady=10, sticky="nsew")

        self.local_start_button = ctk.CTkButton(
            button_frame,
            text="Start Translation",
            command=self.start_local_process,
            fg_color="#2aa745",
            hover_color="#22863a",
            width=150
        )
        self.local_start_button.pack(side="left", padx=10, pady=5)

        self.local_status_frame = ctk.CTkFrame(scroll_frame)
        self.local_status_frame.grid(row=5, column=0, padx=10, pady=(5, 10), sticky="nsew")
        self.local_status_frame.grid_columnconfigure(1, weight=1)

        self.local_status_label = ctk.CTkLabel(
            self.local_status_frame, 
            text="Status: Ready", 
            text_color="green"
        )
        self.local_status_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.local_progress_bar = ctk.CTkProgressBar(
            self.local_status_frame, 
            width=300, 
            height=10, 
            mode="determinate"
        )
        self.local_progress_bar.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        self.local_progress_bar.set(0)

        self.local_cancel_button = ctk.CTkButton(
            self.local_status_frame,
            text="Cancel",
            command=self.cancel_process,
            fg_color="#d73a49",
            hover_color="#cb2431",
            state="disabled",
            width=100
        )
        self.local_cancel_button.grid(row=0, column=2, padx=10, pady=5, sticky="e")

        self.local_open_button = ctk.CTkButton(
            button_frame,
            text="Open Output Folder",
            command=self.open_output_folder,
            state="disabled",
            width=150
        )
        self.local_open_button.pack(side="right", padx=10, pady=5)

        log_frame = ctk.CTkFrame(scroll_frame)
        log_frame.grid(row=6, column=0, padx=10, pady=(10, 5), sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)

        log_header_frame = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        ctk.CTkLabel(log_header_frame, text="Process Log:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
        
        self.local_log_toggle_button = ctk.CTkButton(
            log_header_frame,
            text="▲",
            width=30,
            fg_color="transparent",
            hover_color="#525252",
            command=self.toggle_local_log_visibility,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.local_log_toggle_button.pack(side="right", padx=5)
        
        self.local_log_text = ctk.CTkTextbox(
            log_frame,
            wrap="word",
            state="disabled",
            font=ctk.CTkFont(family="Consolas", size=12),
            height=150
        )
        self.local_log_text.grid(row=1, column=0, padx=5, pady=(0, 5), sticky="nsew")

    def _setup_settings_tab(self):
        self.settings_tab.grid_columnconfigure(0, weight=1)
        self.settings_tab.grid_rowconfigure(0, weight=1)
        
        scroll_frame = ctk.CTkScrollableFrame(self.settings_tab)
        scroll_frame.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        scroll_frame.grid_columnconfigure(0, weight=1)
        
        general_frame = ctk.CTkFrame(scroll_frame)
        general_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        general_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(general_frame, text="General Settings", font=ctk.CTkFont(weight="bold", size=14)).grid(
            row=0, column=0, padx=10, pady=5, sticky="w", columnspan=2)
        
        ctk.CTkLabel(general_frame, text="Appearance Mode:").grid(
            row=1, column=0, padx=10, pady=5, sticky="w")
        
        self.appearance_mode = ctk.CTkComboBox(
            general_frame,
            values=["Light", "Dark"],
            command=self.change_appearance_mode,
            width=200
        )
        self.appearance_mode.set("Dark")
        self.appearance_mode.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        
        ctk.CTkLabel(general_frame, text="Color Theme:").grid(
            row=2, column=0, padx=10, pady=5, sticky="w")
        
        self.color_theme = ctk.CTkComboBox(
            general_frame,
            values=["blue", "green", "dark-blue"],
            command=self.change_color_theme,
            width=200
        )
        self.color_theme.set("blue")
        self.color_theme.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        
        subtitle_frame = ctk.CTkFrame(scroll_frame)
        subtitle_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        subtitle_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(subtitle_frame, text="Subtitle Settings", font=ctk.CTkFont(weight="bold", size=14)).grid(
            row=0, column=0, padx=10, pady=5, sticky="w", columnspan=3)
        
        font_frame = ctk.CTkFrame(subtitle_frame, fg_color="transparent")
        font_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew", columnspan=3)
        
        ctk.CTkLabel(font_frame, text="Font Size:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.fontsize_slider = ctk.CTkSlider(
            font_frame, 
            from_=10, 
            to=50,
            command=lambda v: self.update_subtitle_preview()
        )
        self.fontsize_slider.set(self.subtitle_style['fontsize'])
        self.fontsize_slider.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.fontsize_value = ctk.CTkLabel(font_frame, text=str(self.subtitle_style['fontsize']))
        self.fontsize_value.grid(row=0, column=2, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(font_frame, text="Font Color:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.fontcolor_entry = ctk.CTkEntry(font_frame)
        self.fontcolor_entry.insert(0, self.subtitle_style['fontcolor'])
        self.fontcolor_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.fontcolor_button = ctk.CTkButton(
            font_frame,
            text="Pick",
            width=50,
            command=self.pick_font_color
        )
        self.fontcolor_button.grid(row=1, column=2, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(font_frame, text="Font Family:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.fontfamily_combobox = ctk.CTkComboBox(
            font_frame,
            values=["Arial", "Helvetica", "Times New Roman", "Courier New", "Verdana"]
        )
        self.fontfamily_combobox.set("Arial")
        self.fontfamily_combobox.grid(row=2, column=1, padx=5, pady=5, sticky="ew", columnspan=2)
        
        border_frame = ctk.CTkFrame(subtitle_frame, fg_color="transparent")
        border_frame.grid(row=3, column=0, padx=5, pady=5, sticky="nsew", columnspan=3)
        
        ctk.CTkLabel(border_frame, text="Border Width:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.border_width_slider = ctk.CTkSlider(
            border_frame,
            from_=0,
            to=5,
            number_of_steps=5,
            command=lambda v: self.update_subtitle_preview()
        )
        self.border_width_slider.set(self.subtitle_style['borderw'])
        self.border_width_slider.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.border_width_value = ctk.CTkLabel(border_frame, text=str(self.subtitle_style['borderw']))
        self.border_width_value.grid(row=0, column=2, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(border_frame, text="Border Color:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.border_color_entry = ctk.CTkEntry(border_frame)
        self.border_color_entry.insert(0, self.subtitle_style['bordercolor'])
        self.border_color_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.border_color_button = ctk.CTkButton(
            border_frame,
            text="Pick",
            width=50,
            command=self.pick_border_color
        )
        self.border_color_button.grid(row=1, column=2, padx=5, pady=5, sticky="w")
        
        pos_frame = ctk.CTkFrame(subtitle_frame, fg_color="transparent")
        pos_frame.grid(row=4, column=0, padx=5, pady=5, sticky="nsew", columnspan=3)
        
        ctk.CTkLabel(pos_frame, text="Position:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.position_combobox = ctk.CTkComboBox(
            pos_frame,
            values=["top", "middle", "bottom"],
            command=lambda _: self.update_subtitle_preview()
        )
        self.position_combobox.set(self.subtitle_style['position'])
        self.position_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="ew", columnspan=2)
        
        ctk.CTkLabel(pos_frame, text="Alignment:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.alignment_combobox = ctk.CTkComboBox(
            pos_frame,
            values=["left", "center", "right"],
            command=lambda _: self.update_subtitle_preview()
        )
        self.alignment_combobox.set("center")
        self.alignment_combobox.grid(row=1, column=1, padx=5, pady=5, sticky="ew", columnspan=2)
        
        preview_frame = ctk.CTkFrame(subtitle_frame)
        preview_frame.grid(row=5, column=0, padx=5, pady=10, sticky="nsew", columnspan=3)
        
        ctk.CTkLabel(preview_frame, text="Preview:", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, padx=5, pady=5, sticky="w")
        
        self.subtitle_preview = ctk.CTkLabel(
            preview_frame,
            text="Sample Subtitle Text",
            fg_color=("gray90", "gray20"),
            corner_radius=4,
            padx=10,
            pady=5
        )
        self.subtitle_preview.grid(row=1, column=0, padx=10, pady=5, sticky="ew", columnspan=3)
        self.update_subtitle_preview()
        
        button_frame = ctk.CTkFrame(subtitle_frame, fg_color="transparent")
        button_frame.grid(row=6, column=0, columnspan=3, pady=10, sticky="ew")
        button_frame.grid_columnconfigure((0, 1), weight=1)

        self.save_subtitle_style_button = ctk.CTkButton(
            button_frame,
            text="Save Subtitle Style",
            command=self.save_subtitle_settings,
            fg_color="#2aa745",
            hover_color="#22863a",
            width=150
        )
        self.save_subtitle_style_button.pack(side="left", padx=6, pady=5)

        self.reset_subtitle_style_button = ctk.CTkButton(
            button_frame,
            text="Reset to Default",
            command=self.reset_subtitle_settings,
            fg_color="#d73a49",
            hover_color="#cb2431",
            width=150
        )
        self.reset_subtitle_style_button.pack(side="left", padx=15, pady=5)
        
        advanced_frame = ctk.CTkFrame(scroll_frame)
        advanced_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        advanced_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(advanced_frame, text="Advanced Settings", font=ctk.CTkFont(weight="bold", size=14)).grid(
            row=0, column=0, padx=10, pady=5, sticky="w", columnspan=2)
        
        self.cleanup_checkbox = ctk.CTkCheckBox(
            advanced_frame,
            text="Clean temporary files after processing",
            command=self.toggle_cleanup
        )
        self.cleanup_checkbox.grid(row=1, column=0, padx=10, pady=5, sticky="w", columnspan=2)
        self.cleanup_checkbox.select()
        
        ctk.CTkLabel(advanced_frame, text="FFmpeg Path:").grid(
            row=2, column=0, padx=10, pady=5, sticky="w")
        
        self.ffmpeg_path_label = ctk.CTkLabel(
            advanced_frame,
            text=self.translator.ffmpeg_path,
            anchor="w",
            fg_color=("gray90", "gray20"),
            corner_radius=4,
            padx=10,
            height=28
        )
        self.ffmpeg_path_label.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        
        reset_frame = ctk.CTkFrame(scroll_frame)
        reset_frame.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")

    def _setup_about_tab(self):
        self.about_tab.grid_columnconfigure(0, weight=1)
        self.about_tab.grid_rowconfigure(0, weight=1)
        
        scroll_frame = ctk.CTkScrollableFrame(self.about_tab)
        scroll_frame.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        scroll_frame.grid_columnconfigure(0, weight=1)
        
        info_frame = ctk.CTkFrame(scroll_frame)
        info_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        info_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            info_frame, 
            text="🎬 Video Translator Pro", 
            font=ctk.CTkFont(size=20, weight="bold")
        ).grid(row=0, column=0, pady=(10, 5), sticky="w")
        
        ctk.CTkLabel(
            info_frame, 
            text="Version: 1.0.0",
            font=ctk.CTkFont(size=14)
        ).grid(row=1, column=0, pady=(0, 10), sticky="w")
        
        description = (
            "🌍 This application allows you to translate YouTube or local videos between languages\n\n"
            "🔹 Step 1: Extract audio from video\n"
            "🔹 Step 2: Transcribe to text\n"
            "🔹 Step 3: Translate to target language\n"
            "🔹 Step 4: Generate new audio with text-to-speech\n"
            "🔹 Step 5: Combine with original video\n\n"
            "🎯 Features:\n"
            "✅ Multiple language support\n"
            "✅ Customizable subtitles\n"
            "✅ Progress tracking\n"
            "✅ Clean interface"
        )
        ctk.CTkLabel(
            info_frame, 
            text=description,
            justify="left",
            font=ctk.CTkFont(size=12)
        ).grid(row=2, column=0, pady=(0, 10), sticky="w")
        
        help_frame = ctk.CTkFrame(scroll_frame)
        help_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        help_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            help_frame, 
            text="❓ Help & Support", 
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, pady=(10, 5), sticky="w")
        
        instructions = (
            "📌 How to use:\n"
            "1. For YouTube videos: Paste URL, select languages and click Start\n"
            "2. For local videos: Select file, choose languages and click Start\n\n"
            "⚡ Tips:\n"
            "• Use high-quality sources for best results\n"
            "• Larger videos take longer to process\n"
            "• Check subtitle settings before processing\n\n"
            "🔧 Troubleshooting:\n"
            "• Ensure stable internet connection\n"
            "• Verify FFmpeg is installed\n"
            "• Check disk space for large videos\n\n"
            "📧 Contact: support@videotranslator.example.com"
        )
        ctk.CTkLabel(
            help_frame, 
            text=instructions,
            justify="left",
            font=ctk.CTkFont(size=12)
        ).grid(row=1, column=0, pady=(0, 10), sticky="w")
        
        docs_button = ctk.CTkButton(
            help_frame,
            text="📚 Open Online Documentation",
            command=self.open_documentation,
            fg_color="#0366d6",
            hover_color="#0550a8"
        )
        docs_button.grid(row=2, column=0, pady=10, sticky="ew")
        
        footer_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        footer_frame.grid(row=2, column=0, padx=10, pady=10, sticky="sew")
        
        ctk.CTkLabel(
            footer_frame, 
            text="© 2025 Video Translator Pro - All rights reserved",
            font=ctk.CTkFont(size=10)
        ).pack(side="right", padx=10)

    def reset_subtitle_settings(self):
        default_style = {
            'fontsize': 24,
            'fontcolor': 'white',
            'boxcolor': 'black@0.5',
            'box': 1,
            'borderw': 1,
            'bordercolor': 'black',
            'position': 'bottom',
            'alignment': 'center',
            'fontfamily': 'Arial'
        }
        
        self.fontsize_slider.set(default_style['fontsize'])
        self.fontcolor_entry.delete(0, "end")
        self.fontcolor_entry.insert(0, default_style['fontcolor'])
        self.border_width_slider.set(default_style['borderw'])
        self.border_color_entry.delete(0, "end")
        self.border_color_entry.insert(0, default_style['bordercolor'])
        self.position_combobox.set(default_style['position'])
        self.alignment_combobox.set(default_style['alignment'])
        self.fontfamily_combobox.set(default_style['fontfamily'])
        
        self.update_subtitle_preview()
        self.log_message("Subtitle settings reset to default")
        messagebox.showinfo("Info", "Subtitle settings reset to default")

    def pick_font_color(self):
        color = self.ask_color(self.subtitle_style['fontcolor'])
        if color:
            self.fontcolor_entry.delete(0, "end")
            self.fontcolor_entry.insert(0, color)
            self.update_subtitle_preview()
            self.log_message(f"Changed font color to {color}")

    def pick_border_color(self):
        color = self.ask_color(self.subtitle_style['bordercolor'])
        if color:
            self.border_color_entry.delete(0, "end")
            self.border_color_entry.insert(0, color)
            self.update_subtitle_preview()
            self.log_message(f"Changed border color to {color}")

    def ask_color(self, default_color):
        try:
            import tkinter as tk
            from tkinter import colorchooser
            root = tk.Tk()
            root.withdraw()
            color = colorchooser.askcolor(title="Choose color", initialcolor=default_color)
            return color[1] if color else None
        except Exception as e:
            self.log_message(f"FAIL Color picker error: {str(e)}", level=logging.ERROR)
            return None

    def update_subtitle_preview(self):
        try:
            fontsize = int(self.fontsize_slider.get())
            fontcolor = self.fontcolor_entry.get()
            border_width = int(self.border_width_slider.get())
            border_color = self.border_color_entry.get()
            fontfamily = self.fontfamily_combobox.get()
        
            self.fontsize_value.configure(text=str(fontsize))
            self.border_width_value.configure(text=str(border_width))
            
            self.subtitle_preview.configure(
                text="Sample Subtitle Text",
                font=ctk.CTkFont(family=fontfamily, size=fontsize),
                text_color=fontcolor,
                fg_color="transparent",
                corner_radius=0,
            )
        except Exception as e:
            self.log_message(f"FAIL Subtitle preview error: {str(e)}", level=logging.ERROR)

    def save_subtitle_settings(self):
        try:
            fontsize = int(self.fontsize_slider.get())
            fontcolor = self.fontcolor_entry.get()
            border_width = int(self.border_width_slider.get())
            border_color = self.border_color_entry.get()
            position = self.position_combobox.get()
            alignment = self.alignment_combobox.get()
            fontfamily = self.fontfamily_combobox.get()
            
            self.subtitle_style.update({
                'fontsize': fontsize,
                'fontcolor': fontcolor,
                'borderw': border_width,
                'bordercolor': border_color,
                'position': position,
                'alignment': alignment,
                'fontfamily': fontfamily,
                'box': 0,
                'boxcolor': 'black@0'
            })
            
            self.log_message("SAVING Subtitle style saved successfully")
            messagebox.showinfo("Info", "Subtitle style saved successfully")
        except Exception as e:
            self.log_message(f"FAIL Error saving subtitle settings: {str(e)}", level=logging.ERROR)
            messagebox.showerror("Error", f"Could not save settings: {str(e)}")

    def toggle_log_visibility(self):
        if self.logs_visible:
            self.log_text.grid_remove()
            self.log_toggle_button.configure(text="▼")
            self.logs_visible = False
        else:
            self.log_text.grid()
            self.log_toggle_button.configure(text="▲")
            self.logs_visible = True

    def toggle_local_log_visibility(self):
        if self.local_logs_visible:
            self.local_log_text.grid_remove()
            self.local_log_toggle_button.configure(text="▼")
            self.local_logs_visible = False
        else:
            self.local_log_text.grid()
            self.local_log_toggle_button.configure(text="▲")
            self.local_logs_visible = True

    def change_appearance_mode(self, new_mode):
        ctk.set_appearance_mode(new_mode)
        self.log_message(f"Changed appearance mode to {new_mode}")
    
    def change_color_theme(self, new_theme):
        ctk.set_default_color_theme(new_theme)
        self.log_message(f"Changed color theme to {new_theme}")
    
    def toggle_cleanup(self):
        self.translator.clean_temp_files = self.cleanup_checkbox.get()
        status = "ON" if self.translator.clean_temp_files else "OFF"
        self.log_message(f"Temporary files cleanup: {status}")
    
    def toggle_subtitles_option(self):
        self.add_subtitles = self.subtitles_checkbox.get()
        status = "ON" if self.add_subtitles else "OFF"
        self.log_message(f"YouTube subtitles: {status}")
    
    def toggle_local_subtitles_option(self):
        self.local_add_subtitles = self.local_subtitles_checkbox.get()
        status = "ON" if self.local_add_subtitles else "OFF"
        self.log_message(f"Local file subtitles: {status}", is_youtube=False)
    
    def choose_output_dir(self):
        output_dir = filedialog.askdirectory()
        if output_dir:
            self.output_dir_display.configure(text=output_dir)
            self.log_message(f"FILE Set output directory: {output_dir}")

    def choose_local_output_dir(self):
        output_dir = filedialog.askdirectory()
        if output_dir:
            self.local_output_dir_display.configure(text=output_dir)
            self.log_message(f"FILE Set local output directory: {output_dir}", is_youtube=False)

    def choose_local_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Video Files", "*.mp4 *.avi *.mov *.mkv"), ("All Files", "*.*")])
        if file_path:
            self.local_file_display.configure(text=file_path)
            self.log_message(f"FILE Selected local file: {file_path}", is_youtube=False)

    def start_youtube_process(self):
        youtube_url = self.url_entry.get().strip()
        from_lang = self.translator.language_codes[self.from_lang_combobox.get()]
        to_lang = self.translator.language_codes[self.to_lang_combobox.get()]
        quality = self.quality_combobox.get()
        output_dir = self.output_dir_display.cget("text")

        if output_dir == "Default: script directory":
            output_dir = None

        if not youtube_url:
            messagebox.showerror("Error", "Please enter a YouTube URL")
            self.log_message("FAIL No YouTube URL provided", level=logging.ERROR)
            return
        
        self.set_ui_state(disabled=True)
        self.translator.cancel_process = False
        self.youtube_status_label.configure(text="⏳ Processing...", text_color="white")
        self.youtube_progress_bar.set(0)
        
        self.log_message("START Beginning YouTube video processing")
        self.log_message(f"DOWNLOAD YouTube URL: {youtube_url}")
        self.log_message(f"TRANSLATE From {self.from_lang_combobox.get()} to {self.to_lang_combobox.get()}")
        
        import threading
        threading.Thread(
            target=self.run_youtube_process,
            args=(youtube_url, from_lang, to_lang, quality, output_dir),
            daemon=True
        ).start()

    def start_local_process(self):
        file_path = self.local_file_display.cget("text")
        from_lang = self.translator.language_codes[self.local_from_lang_combobox.get()]
        to_lang = self.translator.language_codes[self.local_to_lang_combobox.get()]
        output_dir = self.local_output_dir_display.cget("text")
        
        if file_path == "No file selected":
            messagebox.showerror("Error", "Please select a video file")
            self.log_message("FAIL No local file selected", level=logging.ERROR, is_youtube=False)
            return
        
        if output_dir == "Same as source file":
            output_dir = None
        
        self.set_ui_state(disabled=True)
        self.translator.cancel_process = False
        self.local_status_label.configure(text="⏳ Processing...", text_color="white")
        self.local_progress_bar.set(0)
        
        self.log_message("START Beginning local file processing", is_youtube=False)
        self.log_message(f"FILE Input file: {file_path}", is_youtube=False)
        self.log_message(f"TRANSLATE From {self.local_from_lang_combobox.get()} to {self.local_to_lang_combobox.get()}", is_youtube=False)
        
        import threading
        threading.Thread(
            target=self.run_local_process,
            args=(file_path, from_lang, to_lang, output_dir),
            daemon=True
        ).start()
    
    def run_youtube_process(self, youtube_url, from_lang, to_lang, quality, output_dir):
        try:
            self.log_message("CONNECTING Connecting to YouTube...")
            
            self.final_video_path = self.translator.main(
                youtube_url,
                from_lang,
                to_lang,
                output_dir,
                quality,
                progress_callback=self.update_youtube_progress,
                add_subtitles=self.add_subtitles,
                subtitle_style=self.subtitle_style
            )
            
            self.youtube_status_label.configure(
                text=f"✅ Success!", 
                text_color="green")
            self.open_button.configure(state="normal")
            
            self.log_message(f"FILE Output file: {self.final_video_path}")
            self.log_message("COMPLETE YouTube processing completed successfully!")
            
            messagebox.showinfo("Success", f"🎉 Translated video saved to:\n{self.final_video_path}")
            
        except Exception as e:
            self.final_video_path = None
            error_msg = f"FAIL YouTube processing failed: {str(e)}"
            self.youtube_status_label.configure(text=f"❌ Error: {str(e)}", text_color="red")
            self.log_message(error_msg, level=logging.ERROR)
            
        finally:
            self.set_ui_state(disabled=False)
            self.translator.cancel_process = False

    def run_local_process(self, file_path, from_lang, to_lang, output_dir):
        try:
            self.log_message("EXTRACTING Processing local file...", is_youtube=False)
            
            self.final_video_path = self.translator.process_local_video(
                file_path,
                from_lang,
                to_lang,
                output_dir,
                progress_callback=self.update_local_progress,
                add_subtitles=self.local_add_subtitles,
                subtitle_style=self.subtitle_style
            )
            
            self.local_status_label.configure(
                text=f"✅ Success! Saved to: {os.path.basename(self.final_video_path)}", 
                text_color="green")
            self.local_open_button.configure(state="normal")
            
            self.log_message(f"FILE Output file: {self.final_video_path}", is_youtube=False)
            self.log_message("COMPLETE Local file processing completed successfully!", is_youtube=False)
            
            messagebox.showinfo("Success", f"🎉 Translated video saved to:\n{self.final_video_path}")
            
        except Exception as e:
            self.final_video_path = None
            error_msg = f"FAIL Local processing failed: {str(e)}"
            self.local_status_label.configure(text=f"❌ Error: {str(e)}", text_color="red")
            self.log_message(error_msg, level=logging.ERROR, is_youtube=False)
            
        finally:
            self.set_ui_state(disabled=False)
            self.translator.cancel_process = False
    
    def cancel_process(self):
        self.translator.cancel_process = True
        self.youtube_status_label.configure(text="⏳ Cancelling...", text_color="orange")
        self.local_status_label.configure(text="⏳ Cancelling...", text_color="orange")
        self.cancel_button.configure(state="disabled")
        self.local_cancel_button.configure(state="disabled")
        self.log_message("STATUS Cancelling current process...")
        self.log_message("STATUS Cancelling current process...", is_youtube=False)
    
    def open_output_folder(self):
        if self.final_video_path and os.path.exists(self.final_video_path):
            folder = os.path.dirname(self.final_video_path)
            try:
                if platform.system() == "Windows":
                    os.startfile(folder)
                elif platform.system() == "Darwin":
                    subprocess.call(["open", folder])
                else:
                    subprocess.call(["xdg-open", folder])
                self.log_message(f"FILE Opened output folder: {folder}")
            except Exception as e:
                self.log_message(f"FAIL Could not open folder: {str(e)}", level=logging.ERROR)
                messagebox.showerror("Error", f"Could not open folder: {str(e)}")
        else:
            self.log_message("FAIL Output folder not found", level=logging.ERROR)
            messagebox.showwarning("Warning", "Output folder not found")
    
    def open_documentation(self):
        try:
            webbrowser.open("https://github.com/yourusername/video-translator/wiki")
            self.log_message("OPENED Online documentation")
        except Exception as e:
            self.log_message(f"FAIL Could not open documentation: {str(e)}", level=logging.ERROR)
            messagebox.showerror("Error", f"Could not open documentation: {str(e)}")

    def update_youtube_progress(self, value, stage=""):
        self.youtube_progress_bar.set(value)
        self.open_button.configure(state="normal" if value >= 100 else "disabled")
        
        if stage:
            stage_emoji = {
                'download': '📥',
                'extract': '🔍',
                'transcribe': '🎤',
                'translate': '🌍',
                'synthesize': '🔊',
                'combine': '🎬'
            }.get(stage, '⚙️')
            
            self.log_message(f"PROGRESS {stage_emoji} {stage.capitalize()}: {int(value*100)}%")

    def update_local_progress(self, value, stage=""):
        self.local_progress_bar.set(value)
        self.local_open_button.configure(state="normal" if value >= 100 else "disabled")
        
        if stage:
            stage_emoji = {
                'extract': '🔍',
                'transcribe': '🎤',
                'translate': '🌍',
                'synthesize': '🔊',
                'combine': '🎬'
            }.get(stage, '⚙️')
            
            self.log_message(f"PROGRESS {stage_emoji} {stage.capitalize()}: {int(value*100)}%", is_youtube=False)

    def set_ui_state(self, disabled=True):
        state = "disabled" if disabled else "normal"
        
        # YouTube tab controls
        self.url_entry.configure(state=state)
        self.from_lang_combobox.configure(state=state)
        self.to_lang_combobox.configure(state=state)
        self.quality_combobox.configure(state=state)
        self.output_dir_button.configure(state=state)
        self.start_button.configure(state=state)
        self.cancel_button.configure(state="normal" if disabled else "disabled")
        self.open_button.configure(state="normal" if self.final_video_path else "disabled")
        self.subtitles_checkbox.configure(state=state)
        self.subtitle_settings_button.configure(state=state)
        
        # Local tab controls
        self.local_file_button.configure(state=state)
        self.local_from_lang_combobox.configure(state=state)
        self.local_to_lang_combobox.configure(state=state)
        self.local_output_dir_button.configure(state=state)
        self.local_start_button.configure(state=state)
        self.local_cancel_button.configure(state="normal" if disabled else "disabled")
        self.local_open_button.configure(state="normal" if self.final_video_path else "disabled")
        self.local_subtitles_checkbox.configure(state=state)
        self.local_subtitle_settings_button.configure(state=state)
        
        # Settings tab controls
        self.appearance_mode.configure(state=state)
        self.color_theme.configure(state=state)
        self.cleanup_checkbox.configure(state=state)
        self.fontsize_slider.configure(state=state)
        self.fontcolor_entry.configure(state=state)
        self.fontcolor_button.configure(state=state)
        self.border_width_slider.configure(state=state)
        self.border_color_entry.configure(state=state)
        self.border_color_button.configure(state=state)
        self.position_combobox.configure(state=state)
        self.alignment_combobox.configure(state=state)
        self.fontfamily_combobox.configure(state=state)
        self.save_subtitle_style_button.configure(state=state)
        self.reset_subtitle_style_button.configure(state=state)
    
    def update_ui_state(self):
        self.set_ui_state(disabled=False)
    
    def on_close(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            if not self.translator.clean_temp_files:
                keep_files = messagebox.askyesno(
                    "Keep temporary files?",
                    "Do you want to keep temporary files in location:\n" + 
                    (self.translator.temp_folder if self.translator.temp_folder else "Unknown")
                )
                if not keep_files:
                    self.translator.clean_temp_files = True
                    self.translator._clean_temp_files()
                    self.log_message("CLEANING Temporary files removed")
            
            self.log_message("STATUS Application closing")
            self.destroy()

    def open_subtitle_settings(self):
        self.tabview.set("Settings")
        self.highlight_subtitle_settings()

    def highlight_subtitle_settings(self):
        for widget in self.settings_tab.winfo_children():
            if isinstance(widget, ctk.CTkScrollableFrame):
                for child in widget.winfo_children():
                    if isinstance(child, ctk.CTkFrame):
                        for subchild in child.winfo_children():
                            if isinstance(subchild, ctk.CTkLabel) and hasattr(subchild, 'cget'):
                                try:
                                    if "Subtitle Settings" in subchild.cget("text"):
                                        original_color = child.cget("fg_color")
                                        child.configure(fg_color=("#e0e0e0", "#404040"))
                                        
                                        def reset_color():
                                            child.configure(fg_color=original_color)
                                        
                                        self.after(3000, reset_color)
                                        return
                                except:
                                    continue

    def log_message(self, message, level=logging.INFO, is_youtube=True):
        logger = self.logger if is_youtube else self.local_logger
        if level == logging.INFO:
            logger.info(message)
        elif level == logging.WARNING:
            logger.warning(message)
        elif level == logging.ERROR:
            logger.error(message)
        elif level == logging.DEBUG:
            logger.debug(message)
        else:
            logger.info(message)

if __name__ == "__main__":
    app = VideoTranslatorApp()
    app.mainloop()