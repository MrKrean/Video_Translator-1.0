import customtkinter as ctk
from ui.subtitle_settings import SubtitleSettings

class SettingsTab:
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
        
        # Subtitle settings
        self.subtitle_settings = SubtitleSettings(scroll_frame, self.app)
        
        # Advanced settings
        advanced_frame = ctk.CTkFrame(scroll_frame)
        advanced_frame.grid(row=2, column=0, padx=(0, 130), pady=10)
        advanced_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(advanced_frame, text="Advanced Settings", text_color="#3a7ebf", 
                    font=ctk.CTkFont(family="Microsoft Sans Serif", weight="bold", size=15)).grid(
            row=0, column=0, padx=10, pady=5, sticky="w", columnspan=2)
        
        self.cleanup_checkbox = ctk.CTkCheckBox(
            advanced_frame,
            text="Clean temporary files after processing",
            command=self.toggle_cleanup,
            font=self.app.default_font
        )
        self.cleanup_checkbox.grid(row=1, column=0, padx=10, pady=5, sticky="w", columnspan=2)
        self.cleanup_checkbox.select()
        
        ctk.CTkLabel(advanced_frame, text="FFmpeg Path:", font=self.app.default_font).grid(
            row=2, column=0, padx=10, pady=5, sticky="w")
        
        self.ffmpeg_path_label = ctk.CTkLabel(
            advanced_frame,
            text=self.app.translator.ffmpeg_path,
            anchor="w",
            fg_color=("gray90", "gray20"),
            corner_radius=4,
            padx=10,
            height=28,
            font=self.app.default_font
        )
        self.ffmpeg_path_label.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        
        self.open_logs_button = ctk.CTkButton(
            advanced_frame,
            text="Open Logs Folder",
            command=self.app.open_logs_folder,
            width=150,
            font=self.app.default_font
        )
        self.open_logs_button.grid(row=3, column=0, padx=10, pady=5, sticky="w")

    def toggle_cleanup(self):
        self.app.translator.clean_temp_files = self.cleanup_checkbox.get()
        self.app.translator.log_with_emoji(f"Automatic cleanup {'enabled' if self.app.translator.clean_temp_files else 'disabled'}", emoji_type='SETTINGS')