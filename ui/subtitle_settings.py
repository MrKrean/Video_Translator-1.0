import logging
import customtkinter as ctk
from tkinter import messagebox

class SubtitleSettings:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self._setup_ui()

    def _setup_ui(self):
        subtitle_frame = ctk.CTkFrame(self.parent)
        subtitle_frame.grid(row=1, column=0, padx=10, pady=10)
        subtitle_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(subtitle_frame, text="Subtitle Settings", text_color="#3a7ebf", 
                    font=ctk.CTkFont(family="Microsoft Sans Serif", weight="bold", size=15)).grid(
            row=0, column=0, pady=5, sticky="w", columnspan=3)
        
        self.font_frame = ctk.CTkFrame(subtitle_frame, fg_color="transparent")
        self.font_frame.grid(row=1, column=0, padx=(0, 325), pady=5, sticky="nsew", columnspan=3)
        
        # Font size
        ctk.CTkLabel(self.font_frame, text="Font Size:", font=self.app.default_font).grid(row=0, column=0, pady=5, sticky="w")
        self.fontsize_slider = ctk.CTkSlider(
            self.font_frame, 
            from_=10, 
            to=50,
            command=lambda v: self.update_preview()
        )
        self.fontsize_slider.set(self.app.subtitle_style['fontsize'])
        self.fontsize_slider.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.fontsize_value = ctk.CTkLabel(self.font_frame, text=str(self.app.subtitle_style['fontsize']), font=self.app.default_font)
        self.fontsize_value.grid(row=0, column=2, padx=5, pady=5, sticky="w")
        
        # Font color
        ctk.CTkLabel(self.font_frame, text="Font Color:", font=self.app.default_font).grid(row=1, column=0, pady=5, sticky="w")
        self.fontcolor_entry = ctk.CTkEntry(self.font_frame, font=self.app.default_font)
        self.fontcolor_entry.insert(0, self.app.subtitle_style['fontcolor'])
        self.fontcolor_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.fontcolor_button = ctk.CTkButton(
            self.font_frame,
            text="Pick",
            width=50,
            command=self.pick_font_color,
            font=self.app.default_font
        )
        self.fontcolor_button.grid(row=1, column=2, padx=5, pady=5, sticky="w")
        
        # Font family
        ctk.CTkLabel(self.font_frame, text="Font Family:", font=self.app.default_font).grid(row=2, column=0, pady=5, sticky="w")
        self.fontfamily_combobox = ctk.CTkComboBox(
            self.font_frame,
            values=["Arial", "Arial Black", "Times New Roman", "Courier New", "Verdana"],
            font=self.app.default_font
        )
        self.fontfamily_combobox.set("Microsoft Sans Serif")
        self.fontfamily_combobox.grid(row=2, column=1, padx=5, pady=5, sticky="ew", columnspan=2)
        
        # Border settings
        border_frame = ctk.CTkFrame(subtitle_frame, fg_color="transparent")
        border_frame.grid(row=3, column=0, pady=5, sticky="nsew", columnspan=3)
        
        ctk.CTkLabel(border_frame, text="Border Width:", font=self.app.default_font).grid(row=0, column=0, pady=5, sticky="w")
        self.border_width_slider = ctk.CTkSlider(
            border_frame,
            from_=0,
            to=5,
            number_of_steps=5,
            command=lambda v: self.update_preview()
        )
        self.border_width_slider.set(self.app.subtitle_style['borderw'])
        self.border_width_slider.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.border_width_value = ctk.CTkLabel(border_frame, text=str(self.app.subtitle_style['borderw']), font=self.app.default_font)
        self.border_width_value.grid(row=0, column=2, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(border_frame, text="Border Color:", font=self.app.default_font).grid(row=1, column=0, pady=5, sticky="w")
        self.border_color_entry = ctk.CTkEntry(border_frame, font=self.app.default_font)
        self.border_color_entry.insert(0, self.app.subtitle_style['bordercolor'])
        self.border_color_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.border_color_button = ctk.CTkButton(
            border_frame,
            text="Pick",
            width=50,
            command=self.pick_border_color,
            font=self.app.default_font
        )
        self.border_color_button.grid(row=1, column=2, padx=5, pady=5, sticky="w")
        
        # Position and alignment
        pos_frame = ctk.CTkFrame(subtitle_frame, fg_color="transparent")
        pos_frame.grid(row=4, column=0, pady=5, sticky="nsew", columnspan=3)
        
        ctk.CTkLabel(pos_frame, text="Position:", font=self.app.default_font).grid(row=0, column=0, pady=(0, 5), sticky="w")
        self.position_combobox = ctk.CTkComboBox(
            pos_frame,
            values=["top", "middle", "bottom"],
            command=lambda _: self.update_preview(),
            font=self.app.default_font
        )
        self.position_combobox.set(self.app.subtitle_style['position'])
        self.position_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="ew", columnspan=2)
        
        ctk.CTkLabel(pos_frame, text="Alignment:", font=self.app.default_font).grid(row=1, column=0, pady=(0, 5), sticky="w")
        self.alignment_combobox = ctk.CTkComboBox(
            pos_frame,
            values=["left", "center", "right"],
            command=lambda _: self.update_preview(),
            font=self.app.default_font
        )
        self.alignment_combobox.set("center")
        self.alignment_combobox.grid(row=1, column=1, padx=5, pady=5, sticky="ew", columnspan=2)
        
        # Preview
        preview_frame = ctk.CTkFrame(subtitle_frame)
        preview_frame.grid(row=5, column=0, pady=10, sticky="nsew", columnspan=3)
        
        ctk.CTkLabel(preview_frame, text="Preview:", text_color="#3a7ebf", 
                    font=ctk.CTkFont(family="Microsoft Sans Serif", weight="bold")).grid(
            row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.app.subtitle_preview = ctk.CTkLabel(
            preview_frame,
            text="Sample Subtitle Text",
            fg_color=("gray90", "gray20"),
            corner_radius=4,
            padx=10,
            pady=5,
            font=ctk.CTkFont(family="Microsoft Sans Serif", size=self.app.subtitle_style['fontsize'])
        )
        self.app.subtitle_preview.grid(row=1, column=0, padx=10, pady=5, sticky="ew", columnspan=3)
        self.update_preview()
        
        # Buttons
        button_frame = ctk.CTkFrame(subtitle_frame, fg_color="transparent")
        button_frame.grid(row=6, column=0, columnspan=3, pady=10, sticky="ew")
        button_frame.grid_columnconfigure((0, 1), weight=1)

        self.save_subtitle_style_button = ctk.CTkButton(
            button_frame,
            text="Save Subtitle Style",
            command=self.save_settings,
            hover_color="#22863a",
            width=150,
            font=self.app.default_font
        )
        self.save_subtitle_style_button.pack(side="left", padx=(0, 6), pady=5)

        self.reset_subtitle_style_button = ctk.CTkButton(
            button_frame,
            text="Reset to Default",
            command=self.reset_settings,
            fg_color="gray20",
            hover_color="#525252",
            width=150,
            font=self.app.default_font
        )
        self.reset_subtitle_style_button.pack(side="left", padx=(368, 0), pady=5)

    def pick_font_color(self):
        color = self._ask_color(self.app.subtitle_style['fontcolor'])
        if color:
            self.fontcolor_entry.delete(0, "end")
            self.fontcolor_entry.insert(0, color)
            self.update_preview()

    def pick_border_color(self):
        color = self._ask_color(self.app.subtitle_style['bordercolor'])
        if color:
            self.border_color_entry.delete(0, "end")
            self.border_color_entry.insert(0, color)
            self.update_preview()

    def _ask_color(self, default_color):
        try:
            import tkinter as tk
            from tkinter import colorchooser
            root = tk.Tk()
            root.withdraw()
            color = colorchooser.askcolor(title="Choose color", initialcolor=default_color)
            return color[1] if color else None
        except:
            return None

    def update_preview(self):
        try:
            fontsize = int(self.fontsize_slider.get())
            fontcolor = self.fontcolor_entry.get()
            border_width = int(self.border_width_slider.get())
            border_color = self.border_color_entry.get()
        
            self.fontsize_value.configure(text=str(fontsize))
            self.border_width_value.configure(text=str(border_width))
            
            self.app.subtitle_preview.configure(
                text="Sample Subtitle Text",
                font=ctk.CTkFont(family="Microsoft Sans Serif", size=fontsize),
                text_color=fontcolor,
                fg_color="transparent",
                corner_radius=0,
            )
        except Exception as e:
            self.app.translator.log_with_emoji(f"Error updating preview: {e}", logging.WARNING)

    def save_settings(self):
        fontsize = int(self.fontsize_slider.get())
        fontcolor = self.fontcolor_entry.get()
        border_width = int(self.border_width_slider.get())
        border_color = self.border_color_entry.get()
        position = self.position_combobox.get()
        alignment = self.alignment_combobox.get()
        fontfamily = self.fontfamily_combobox.get()
        
        self.app.subtitle_style.update({
            'fontsize': fontsize,
            'fontcolor': fontcolor,
            'borderw': border_width,
            'bordercolor': border_color,
            'position': position,
            'alignment': alignment,
            'fontfamily': 'Arial Black',
            'box': 0,
            'boxcolor': 'black@0'
        })
    
        messagebox.showinfo("Info", "Subtitle style saved successfully")

    def reset_settings(self):
        default_style = {
            'fontsize': 24,
            'fontcolor': 'white',
            'boxcolor': 'black@0.5',
            'box': 1,
            'borderw': 1,
            'bordercolor': 'black',
            'position': 'bottom',
            'alignment': 'center',
            'fontfamily': 'Arial Black'
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
        
        self.update_preview()
        
        messagebox.showinfo("Info", "Subtitle settings reset to default")