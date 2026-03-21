import sys
print(sys.executable)

import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path
import threading

from transcriber import ParakeetTranscriber

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Parakeet V3 Transcriber")
        self.geometry("900x600")

        self.transcriber = ParakeetTranscriber()
        self.selected_file = None
        self.is_running = False
        self.model_ready = False

        self.build_ui()

        # загрузка модели в фоне
        threading.Thread(target=self.load_model_bg, daemon=True).start()

    def build_ui(self):

        # ===== HEADER =====
        self.header = ctk.CTkFrame(self, fg_color="#6C5CE7", height=70, corner_radius=0)
        self.header.pack(fill="x")

        title = ctk.CTkLabel(
            self.header,
            text="🎙 Parakeet Transcriber",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="white"
        )
        title.pack(pady=20)

        # ===== FILE CARD =====
        self.file_card = ctk.CTkFrame(self, fg_color="#2B2D42", corner_radius=15)
        self.file_card.pack(fill="x", padx=20, pady=15)

        self.file_label = ctk.CTkLabel(
            self.file_card,
            text="Файл не выбран",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="white"
        )
        self.file_label.pack(anchor="w", padx=15, pady=(10, 5))

        self.file_info = ctk.CTkLabel(
            self.file_card,
            text="mp3 • wav • mp4 • mkv • mov",
            text_color="#A0A0A0"
        )
        self.file_info.pack(anchor="w", padx=15, pady=(0, 10))

        # ===== BUTTONS =====
        self.buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.buttons_frame.pack(fill="x", padx=20, pady=5)

        self.open_btn = ctk.CTkButton(
            self.buttons_frame,
            text="📂 Открыть",
            command=self.select_file,
            fg_color="#00C853",
            hover_color="#00B248"
        )
        self.open_btn.pack(side="left", padx=5)

        self.run_btn = ctk.CTkButton(
            self.buttons_frame,
            text="🚀 Старт",
            command=self.start_transcription,
            fg_color="#6C5CE7",
            hover_color="#5A4BD1"
        )
        self.run_btn.pack(side="left", padx=5)

        self.save_btn = ctk.CTkButton(
            self.buttons_frame,
            text="💾 Сохранить",
            command=self.save_text,
            fg_color="#0984E3"
        )
        self.save_btn.pack(side="left", padx=5)

        self.copy_btn = ctk.CTkButton(
            self.buttons_frame,
            text="📋 Копировать",
            command=self.copy_text,
            fg_color="#636E72"
        )
        self.copy_btn.pack(side="left", padx=5)

        # ===== STATUS =====
        self.status = ctk.CTkLabel(
            self,
            text="⏳ Загрузка модели...",
            text_color="#B0B0B0"
        )
        self.status.pack(anchor="w", padx=25, pady=(10, 0))

        self.progress = ctk.CTkProgressBar(self, progress_color="#6C5CE7")
        self.progress.pack(fill="x", padx=20, pady=10)
        self.progress.set(0)

        # ===== TEXT =====
        self.textbox = ctk.CTkTextbox(
            self,
            corner_radius=15,
            fg_color="#1E1E2F",
            text_color="white"
        )
        self.textbox.pack(fill="both", expand=True, padx=20, pady=15)

    # ===== MODEL LOADING =====

    def load_model_bg(self):
        self.after(0, lambda: self.status.configure(text="⏳ Загрузка модели..."))

        try:
            self.transcriber._load_model()
            self.model_ready = True
            self.after(0, lambda: self.status.configure(text="✅ Модель готова"))

        except Exception as e:
            self.after(0, lambda: self.status.configure(text=f"❌ Ошибка: {e}"))

    # ===== LOGIC =====

    def select_file(self):
        path = filedialog.askopenfilename()

        if not path:
            return

        self.selected_file = path
        self.file_label.configure(text=f"{Path(path).name}")
        self.status.configure(text="📂 Файл выбран")

    def start_transcription(self):
        if self.is_running:
            return

        if not self.selected_file:
            self.status.configure(text="❗ Сначала выбери файл")
            return

        if not self.model_ready:
            self.status.configure(text="⏳ Модель ещё загружается...")
            return

        self.is_running = True
        self.progress.set(0)
        self.textbox.delete("1.0", "end")
        self.status.configure(text="🎧 Подготовка аудио...")

        threading.Thread(target=self.worker, daemon=True).start()

    def worker(self):
        try:
            self.after(0, lambda: self.status.configure(text="🔪 Разбивка на чанки..."))

            result = self.transcriber.transcribe(
                self.selected_file,
                progress_callback=self.on_progress
            )

            self.after(0, lambda: self.on_done(result.text))

        except Exception as e:
            self.after(0, lambda: self.status.configure(text=f"❌ Ошибка: {e}"))

        finally:
            self.is_running = False

    def on_progress(self, i, total):
        percent = i / total

        self.after(0, lambda: self.progress.set(percent))
        self.after(0, lambda: self.status.configure(
            text=f"🧠 Обработка: {i}/{total}"
        ))

    def on_done(self, text):
        self.textbox.insert("1.0", text)
        self.progress.set(1)
        self.status.configure(text="✅ Готово!")

    def save_text(self):
        content = self.textbox.get("1.0", "end").strip()
        if not content:
            return

        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if not path:
            return

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        self.status.configure(text="💾 Сохранено")

    def copy_text(self):
        content = self.textbox.get("1.0", "end").strip()
        if not content:
            return

        self.clipboard_clear()
        self.clipboard_append(content)
        self.status.configure(text="📋 Скопировано")


if __name__ == "__main__":
    app = App()
    app.mainloop()