import webbrowser
import customtkinter as ctk
from tkinter import messagebox


class AboutTab:
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
        
        # Info section
        info_frame = ctk.CTkFrame(scroll_frame)
        info_frame.grid(row=0, column=0, padx=(0, 320), pady=10)
        info_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            info_frame, 
            text="🎬 Video Translator",
            text_color="#3a7ebf", 
            font=ctk.CTkFont(family="Microsoft Sans Serif", size=20, weight="bold")
        ).grid(row=0, column=0, pady=(10, 5), sticky="w")
        
        ctk.CTkLabel(
            info_frame, 
            text="Version: 1.0.0",
            font=ctk.CTkFont(family="Microsoft Sans Serif", size=14)
        ).grid(row=1, column=0, pady=(0, 10), sticky="w")
        
        description = (
            "This application allows you to translate YouTube or local videos by:\n"
            "1. Extracting the audio\n"
            "2. Transcribing to text\n"
            "3. Translating to target language\n"
            "4. Generating new audio with text-to-speech\n"
            "5. Combining with original video\n\n"
            "Supports multiple languages and subtitle options."
        )
        ctk.CTkLabel(
            info_frame, 
            text=description,
            justify="left",
            font=ctk.CTkFont(family="Microsoft Sans Serif", size=12)
        ).grid(row=2, column=0, pady=(0, 10), sticky="w")
        
        # Help section
        help_frame = ctk.CTkFrame(scroll_frame)
        help_frame.grid(row=1, column=0, padx=(0, 320), pady=10)
        help_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            help_frame, 
            text="❓ Help & Support",
            text_color="#3a7ebf", 
            font=ctk.CTkFont(family="Microsoft Sans Serif", size=16, weight="bold")
        ).grid(row=0, column=0, pady=(10, 5), sticky="w")
        
        instructions = (
            "How to use:\n"
            "- For YouTube videos: Paste URL, select languages and click Start\n"
            "- For local videos: Select file, choose languages and click Start\n\n"
            "Troubleshooting:\n"
            "- Ensure you have stable internet connection\n"
            "- Check FFmpeg is installed and in PATH\n"
            "- For large videos, ensure sufficient disk space\n\n"
            "Contact support: support@videotranslator.example.com"
        )
        ctk.CTkLabel(
            help_frame, 
            text=instructions,
            justify="left",
            font=ctk.CTkFont(family="Microsoft Sans Serif", size=12)
        ).grid(row=1, column=0, pady=(0, 10), sticky="w")
        
        # Documentation button
        docs_button = ctk.CTkButton(
            help_frame,
            text="🌐 Open Online Documentation",
            command=self.open_documentation,
            fg_color="#0366d6",
            hover_color="#0550a8",
            font=self.app.default_font
        )
        docs_button.grid(row=2, column=0, pady=10, sticky="ew")
        
        # Footer
        footer_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        footer_frame.grid(row=2, column=0, padx=10, pady=10)
        
        ctk.CTkLabel(
            footer_frame, 
            text="© 2025 Video Translator App - All rights reserved",
            font=ctk.CTkFont(family="Microsoft Sans Serif", size=10)
        ).pack(side="right", padx=(450, 0))

    def open_documentation(self):
        try:
            webbrowser.open("https://github.com/yourusername/video-translator/wiki")
        except Exception as e:
            messagebox.showerror("Error", f"Could not open documentation: {str(e)}")