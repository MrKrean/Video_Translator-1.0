import os
import platform
import subprocess
import customtkinter as ctk
from tkinter import messagebox
from core.main import VideoTranslator
from ui.youtube_tab import YouTubeTab
from ui.local_tab import LocalTab
from ui.settings_tab import SettingsTab
from ui.about_tab import AboutTab

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
            'fontfamily': 'Microsoft Sans Serif'
        }
        
        self.add_subtitles = False
        self.local_add_subtitles = False
        self.logs_visible = True
        self.local_logs_visible = True

        self._setup_appearance()
        self._setup_tabs()
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _setup_appearance(self):
        self.title("Video Translator")
        self.geometry("850x650")
        self.minsize(850, 650)
        self._set_appearance_mode("Dark")
        
        try:
            self.iconbitmap(os.path.join(self.translator.script_dir, "ui", "assets", "icon.ico"))
        except:
            pass
        
        self.default_font = ctk.CTkFont(family="Arial Black", size=12)
        self.header_font = ctk.CTkFont(family="Arial Black", size=24, weight="bold")
        self.mono_font = ctk.CTkFont(family="Arial Black", size=12)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self.header = ctk.CTkLabel(
            self, 
            text="🎬 Video Translator",
            font=self.header_font,
            anchor="center",
            text_color="#3a7ebf"
        )
        self.header.grid(row=0, column=0, pady=(20, 10), padx=20, sticky="ew")

    def _setup_tabs(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        
        # Initialize all tabs
        self.youtube_tab = YouTubeTab(self.tabview.add("YouTube Video"), self)
        self.local_tab = LocalTab(self.tabview.add("Local Video"), self)
        self.settings_tab = SettingsTab(self.tabview.add("Settings"), self)
        self.about_tab = AboutTab(self.tabview.add("About & Help"), self)

    def run_youtube_process(self, youtube_url, from_lang, to_lang, quality, output_dir, progress_callback):
        try:
            self.final_video_path = self.translator.main(
                youtube_url,
                from_lang,
                to_lang,
                output_dir,
                quality,
                progress_callback=progress_callback,
                add_subtitles=self.add_subtitles,
                subtitle_style=self.subtitle_style
            )
            
            self.youtube_tab.status_label.configure(
                text=f"✅ Success!", 
                text_color="#2ECC71")
            self.youtube_tab.open_button.configure(state="normal")
            messagebox.showinfo("Success", f"Translated video saved to:\n{self.final_video_path}")
            
        except Exception as e:
            self.final_video_path = None
            self.youtube_tab.status_label.configure(text=f"Error: {str(e)}", text_color="red")
            
        finally:
            self.set_ui_state(disabled=False)
            self.translator.cancel_process = False

    def run_local_process(self, file_path, from_lang, to_lang, output_dir, progress_callback):
        try:
            self.final_video_path = self.translator.process_local_video(
                file_path,
                from_lang,
                to_lang,
                output_dir,
                progress_callback=progress_callback,
                add_subtitles=self.local_add_subtitles,
                subtitle_style=self.subtitle_style
            )
            
            self.local_tab.status_label.configure(
                text=f"Success! Saved to: {os.path.basename(self.final_video_path)}", 
                text_color="green")
            self.local_tab.open_button.configure(state="normal")
            messagebox.showinfo("Success", f"Translated video saved to:\n{self.final_video_path}")
            
        except Exception as e:
            self.final_video_path = None
            self.local_tab.status_label.configure(text=f"Error:", text_color="red")
            
        finally:
            self.set_ui_state(disabled=False)
            self.translator.cancel_process = False

    def update_progress(self, value, stage=None, error=None):
        if error:
            self.youtube_tab.status_label.configure(text=f"Error in {stage}: {error}", text_color="red")
            self.local_tab.status_label.configure(text=f"Error in {stage}: {error}", text_color="red")
            return
        
        total_progress = 0
        for s, weight in self.translator.progress_stages.items():
            if s == stage:
                break
            total_progress += weight
        
        if stage in self.translator.progress_stages:
            stage_weight = self.translator.progress_stages[stage]
            current_stage_progress = (value / 100) * stage_weight
            total_progress += current_stage_progress
        
        progress = total_progress / 100
        self.youtube_tab.progress_bar.set(progress)
        self.local_tab.progress_bar.set(progress)
        
        if stage:
            status_text = f"{stage.capitalize()}: {int(total_progress)}%"
            self.youtube_tab.status_label.configure(text=status_text)
            self.local_tab.status_label.configure(text=status_text)

    def cancel_process(self):
        self.translator.cancel_process = True
        self.youtube_tab.status_label.configure(text="Cancelling...", text_color="orange")
        self.local_tab.status_label.configure(text="Cancelling...", text_color="orange")
        self.youtube_tab.cancel_button.configure(state="disabled")
        self.local_tab.cancel_button.configure(state="disabled")

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
            except Exception as e:
                messagebox.showerror("Error", f"Could not open folder: {str(e)}")
        else:
            messagebox.showwarning("Warning", "Output folder not found")

    def open_logs_folder(self):
        logs_dir = os.path.join(self.translator.script_dir, "logs")
        if os.path.exists(logs_dir):
            try:
                if platform.system() == "Windows":
                    os.startfile(logs_dir)
                elif platform.system() == "Darwin":
                    subprocess.call(["open", logs_dir])
                else:
                    subprocess.call(["xdg-open", logs_dir])
            except Exception as e:
                messagebox.showerror("Error", f"Could not open logs folder: {str(e)}")
        else:
            messagebox.showinfo("Info", "Logs directory does not exist yet")

    def set_ui_state(self, disabled=True):
        state = "disabled" if disabled else "normal"
        
        # YouTube tab controls
        self.youtube_tab.url_entry.configure(state=state)
        self.youtube_tab.from_lang_combobox.configure(state=state)
        self.youtube_tab.to_lang_combobox.configure(state=state)
        self.youtube_tab.quality_combobox.configure(state=state)
        self.youtube_tab.output_dir_button.configure(state=state)
        self.youtube_tab.start_button.configure(state=state)
        self.youtube_tab.cancel_button.configure(state="normal" if disabled else "disabled")
        self.youtube_tab.open_button.configure(state="normal" if self.final_video_path else "disabled")
        self.youtube_tab.subtitles_checkbox.configure(state=state)
        
        # Local tab controls
        self.local_tab.local_file_button.configure(state=state)
        self.local_tab.from_lang_combobox.configure(state=state)
        self.local_tab.to_lang_combobox.configure(state=state)
        self.local_tab.output_dir_button.configure(state=state)
        self.local_tab.start_button.configure(state=state)
        self.local_tab.cancel_button.configure(state="normal" if disabled else "disabled")
        self.local_tab.open_button.configure(state="normal" if self.final_video_path else "disabled")
        self.local_tab.subtitles_checkbox.configure(state=state)
        
        # Settings tab controls
        self.settings_tab.cleanup_checkbox.configure(state=state)
        self.settings_tab.subtitle_settings.fontsize_slider.configure(state=state)
        self.settings_tab.subtitle_settings.fontcolor_entry.configure(state=state)
        self.settings_tab.subtitle_settings.position_combobox.configure(state=state)
        self.settings_tab.subtitle_settings.save_subtitle_style_button.configure(state=state)
        self.settings_tab.subtitle_settings.reset_subtitle_style_button.configure(state=state)

    def open_subtitle_settings(self):
        self.tabview.set("Settings")
        self._highlight_subtitle_settings()

    def _highlight_subtitle_settings(self):
        for widget in self.settings_tab.parent.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                for child in widget.winfo_children():
                    if isinstance(child, ctk.CTkLabel) and hasattr(child, 'cget'):
                        try:
                            if "Subtitle Settings" in child.cget("text"):
                                original_color = widget.cget("fg_color")
                                widget.configure(fg_color=("#e0e0e0", "#404040"))
                                
                                def reset_color():
                                    widget.configure(fg_color=original_color)
                                
                                self.after(3000, reset_color)
                                return
                        except:
                            continue

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
            
            self.destroy()