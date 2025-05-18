import logging
import customtkinter as ctk
from tkinter import filedialog, messagebox
from core.textbox_handler import TextboxHandler

class YouTubeTab:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self._setup_ui()

    def _setup_ui(self):
        self.parent.grid_columnconfigure(0, weight=1)
        self.parent.grid_rowconfigure(0, weight=1)

        scroll_frame = ctk.CTkScrollableFrame(self.parent)
        scroll_frame.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        scroll_frame.grid_columnconfigure(0, weight=1)

        # URL Frame
        url_frame = ctk.CTkFrame(scroll_frame)
        url_frame.grid(row=0, column=0, padx=10, pady=(5, 10))
        url_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(url_frame, text="YouTube URL:", text_color="#3a7ebf", 
                    font=ctk.CTkFont(family="Microsoft Sans Serif", weight="bold", size=15)).grid(
            row=0, column=0, padx=10, pady=(10, 5))
        
        self.url_entry = ctk.CTkEntry(
            url_frame,
            placeholder_text="https://www.youtube.com/watch?v=...",
            font=self.app.default_font,
            width=550
        )
        self.url_entry.grid(row=0, column=1, padx=10, pady=(10, 5))

        # Settings Frame
        settings_frame = ctk.CTkFrame(scroll_frame)
        settings_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        settings_frame.grid_columnconfigure(0, weight=1)

        # Language selection
        lang_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        lang_frame.grid(row=0, column=0, padx=5, pady=5)

        ctk.CTkLabel(lang_frame, text="From:", font=self.app.default_font).pack(side="left", padx=(0, 8))

        self.from_lang_combobox = ctk.CTkComboBox(
            lang_frame,
            values=list(self.app.translator.language_codes.keys()),
            width=218,
            font=self.app.default_font
        )
        self.from_lang_combobox.set("English")
        self.from_lang_combobox.pack(side="left", padx=(0, 19))

        ctk.CTkLabel(lang_frame, text="To:", font=self.app.default_font).pack(side="left", padx=(0, 8))

        self.to_lang_combobox = ctk.CTkComboBox(
            lang_frame,
            values=list(self.app.translator.language_codes.keys()),
            width=218,
            font=self.app.default_font
        )
        self.to_lang_combobox.set("Polish")
        self.to_lang_combobox.pack(side="left", padx=(0, 150))

        # Quality selection
        qual_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        qual_frame.grid(row=1, column=0, padx=5, pady=5)

        ctk.CTkLabel(qual_frame, text="Video Quality:", font=self.app.default_font).pack(side="left", padx=(0, 10))
        self.quality_combobox = ctk.CTkComboBox(
            qual_frame,
            values=['best', '1080p', '720p', '480p', '360p', '240p', '144p'],
            width=163,
            font=self.app.default_font
        )
        self.quality_combobox.set("best")
        self.quality_combobox.pack(side="left", padx=(0, 415))

        # Subtitles options
        subtitles_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        subtitles_frame.grid(row=3, column=0, padx=10, pady=5, columnspan=2)

        self.subtitles_checkbox = ctk.CTkCheckBox(
            subtitles_frame,
            text="Add subtitles to video",
            command=self.toggle_subtitles_option,
            font=self.app.default_font
        )
        self.subtitles_checkbox.pack(side="left", padx=(0, 10))

        self.subtitle_settings_button = ctk.CTkButton(
            subtitles_frame,
            text="⚙️",
            width=25,
            hover_color="#525252",
            fg_color="transparent",
            command=self.app.open_subtitle_settings,
            font=ctk.CTkFont(family="Microsoft Sans Serif", size=18)
        )
        self.subtitle_settings_button.pack(side="left", padx=(0, 460))

        # Output directory
        output_frame = ctk.CTkFrame(scroll_frame)
        output_frame.grid(row=4, column=0, pady=10)
        output_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(output_frame, text="Output Folder:", font=self.app.default_font).grid(
            row=0, column=0, pady=5) 
        self.output_dir_display = ctk.CTkLabel(
            output_frame,
            text="Default: script directory",
            anchor="w",
            fg_color=("gray90", "gray20"),
            corner_radius=4,
            padx=10,
            height=28,
            width=465,
            font=self.app.default_font
        )
        self.output_dir_display.grid(row=0, column=1, padx=(11, 10), pady=5)

        self.output_dir_button = ctk.CTkButton(
            output_frame,
            text="Browse...",
            width=100,
            command=self.choose_output_dir,
            font=self.app.default_font
        )
        self.output_dir_button.grid(row=0, column=2, pady=5)

        # Buttons
        button_frame = ctk.CTkFrame(scroll_frame)
        button_frame.grid(row=5, column=0, padx=10, pady=10)

        self.start_button = ctk.CTkButton(
            button_frame,
            text="Start Translation",
            command=self.start_process,
            fg_color="#2aa745",
            hover_color="#22863a",
            width=150,
            font=self.app.default_font
        )
        self.start_button.pack(side="left", padx=(0, 190), pady=5)

        self.open_button = ctk.CTkButton(
            button_frame,
            text="Open Output Folder",
            command=self.app.open_output_folder,
            state="disabled",
            width=150,
            font=self.app.default_font
        )
        self.open_button.pack(side="right", padx=(190, 0), pady=5)

        # Status frame
        self.status_frame = ctk.CTkFrame(scroll_frame)
        self.status_frame.grid(row=6, column=0, padx=10, pady=(5, 10))
        self.status_frame.grid_columnconfigure(1, weight=1)

        self.status_label = ctk.CTkLabel(
            self.status_frame, 
            text="Status: Ready", 
            text_color="#2ECC71",
            font=self.app.default_font
        )
        self.status_label.grid(row=0, column=0, pady=5)

        self.progress_bar = ctk.CTkProgressBar(
            self.status_frame, 
            width=470, 
            height=10, 
            mode="determinate"
        )
        self.progress_bar.grid(row=0, column=1, padx=(10, 10), pady=5)
        self.progress_bar.set(0)

        self.cancel_button = ctk.CTkButton(
            self.status_frame,
            text="Cancel",
            command=self.app.cancel_process,
            fg_color="gray20",
            hover_color="#525252",
            state="disabled",
            width=100,
            font=self.app.default_font
        )
        self.cancel_button.grid(row=0, column=2, pady=5)

        # Logs
        log_frame = ctk.CTkFrame(scroll_frame)
        log_frame.grid(row=7, column=0, padx=10, pady=(10, 5))
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)

        log_header_frame = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header_frame.grid(row=0, column=0, padx=5, pady=5)
        
        ctk.CTkLabel(log_header_frame, text="Process Log:", text_color="#3a7ebf", 
                    font=ctk.CTkFont(family="Microsoft Sans Serif", weight="bold")).pack(side="left", padx=(0, 360))
        
        self.log_toggle_button = ctk.CTkButton(
            log_header_frame,
            text="▲",
            width=30,
            fg_color="transparent",
            hover_color="#525252",
            command=self.toggle_log_visibility,
            font=ctk.CTkFont(family="Microsoft Sans Serif", size=16, weight="bold")
        )
        self.log_toggle_button.pack(side="right", padx=(200, 0))
        
        self.log_text = ctk.CTkTextbox(
            log_frame,
            wrap="word",
            state="disabled",
            font=self.app.mono_font,
            height=250,
            width=529,
            fg_color="gray20"
        )
        self.log_text.grid(row=1, column=0, padx=5, pady=(0, 5), sticky="nsew")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", "[System] Logs initialized. Ready for processing...\n")
        self.log_text.configure(state="disabled")

        self.log_handler = TextboxHandler(self.log_text)
        self.log_handler.setFormatter(logging.Formatter('%(message)s'))
        self.app.translator.logger.addHandler(self.log_handler)

        for level, color in self.log_handler.level_colors.items():
            self.log_text.tag_config(level, foreground=color)

    def toggle_subtitles_option(self):
        self.app.add_subtitles = self.subtitles_checkbox.get()
        self.app.translator.log_with_emoji(f"Subtitles {'enabled' if self.app.add_subtitles else 'disabled'}", emoji_type='SUBTITLES')

    def choose_output_dir(self):
        output_dir = filedialog.askdirectory()
        if output_dir:
            self.output_dir_display.configure(text=output_dir)
            self.app.translator.log_with_emoji(f"Output directory set to: {output_dir}", emoji_type='FILE')

    def toggle_log_visibility(self):
        if hasattr(self, 'logs_visible') and self.logs_visible:
            self.log_text.grid_remove()
            self.log_toggle_button.configure(text="▼")
            self.logs_visible = False
        else:
            self.log_text.grid()
            self.log_toggle_button.configure(text="▲")
            self.logs_visible = True

    def start_process(self):
        youtube_url = self.url_entry.get().strip()
        from_lang = self.app.translator.language_codes[self.from_lang_combobox.get()]
        to_lang = self.app.translator.language_codes[self.to_lang_combobox.get()]
        quality = self.quality_combobox.get()
        output_dir = self.output_dir_display.cget("text")

        if output_dir == "Default: script directory":
            output_dir = None

        if not youtube_url:
            messagebox.showerror("Error", "Please enter a YouTube URL")
            return
        
        self.app.set_ui_state(disabled=True)
        self.app.translator.cancel_process = False
        self.status_label.configure(text="Processing...", text_color="white")
        self.progress_bar.set(0)
        
        import threading
        threading.Thread(
            target=self.app.run_youtube_process,
            args=(youtube_url, from_lang, to_lang, quality, output_dir, self.app.update_progress),
            daemon=True
        ).start()