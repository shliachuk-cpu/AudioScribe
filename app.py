import threading
import traceback
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from transcriber import ParakeetTranscriber


class App:
    def __init__(self, root: tk.Tk):
        self.is_running = False
        self.cancel_requested = False
        self.start_time = None
        self.root = root
        self.root.title("Parakeet V3 Transcriber")
        self.root.geometry("900x600")

        self.transcriber = ParakeetTranscriber()
        self.selected_file = None

        # preload model in background to avoid first-run delay
        threading.Thread(target=self.transcriber._load_model, daemon=True).start()

        self.status_var = tk.StringVar(value="Выберите аудиофайл")

        self._build_ui()

    def _build_ui(self):
        frame = tk.Frame(self.root, padx=12, pady=12)
        frame.pack(fill="both", expand=True)

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("TButton", font=("Arial", 11), padding=6)
        style.configure("TLabel", font=("Arial", 11))

        file_box = ttk.LabelFrame(frame, text="Файл")
        file_box.pack(fill="x", pady=(0, 10))

        self.file_label = ttk.Label(file_box, text="Файл не выбран", anchor="w")
        self.file_label.pack(fill="x", padx=10, pady=(6,2))

        formats = ttk.Label(
            file_box,
            text="Поддерживаемые форматы: mp3, wav, flac, m4a, aac, ogg, wma, mp4, mkv, mov, avi",
            foreground="gray",
        )
        formats.pack(fill="x", padx=10, pady=(0,6))

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(0,10))

        self.open_btn = ttk.Button(buttons, text="Открыть аудио", command=self.select_file)
        self.open_btn.pack(side="left", padx=(0,6))

        self.run_btn = ttk.Button(
            buttons, text="Транскрибировать", command=self.start_transcription
        )
        self.run_btn.pack(side="left", padx=6)

        self.cancel_btn = ttk.Button(
            buttons, text="Отмена", command=self.cancel_transcription, state="disabled"
        )
        self.cancel_btn.pack(side="left", padx=6)

        self.save_btn = ttk.Button(buttons, text="Сохранить TXT", command=self.save_text)
        self.save_btn.pack(side="left", padx=6)

        self.copy_btn = ttk.Button(buttons, text="Копировать", command=self.copy_text)
        self.copy_btn.pack(side="left", padx=6)

        self.status_label = ttk.Label(frame, textvariable=self.status_var, anchor="w")
        self.status_label.pack(fill="x", pady=(0, 8))

        self.progress = ttk.Progressbar(frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", pady=(0, 10))

        text_box = ttk.LabelFrame(frame, text="Транскрипция")
        text_box.pack(fill="both", expand=True)

        text_frame = ttk.Frame(text_box)
        text_frame.pack(fill="both", expand=True, padx=8, pady=8)

        scrollbar = ttk.Scrollbar(text_frame)

        self.text = tk.Text(
            text_frame,
            wrap="word",
            yscrollcommand=scrollbar.set,
            font=("Arial", 12),
            padx=10,
            pady=10,
        )

        scrollbar.config(command=self.text.yview)

        scrollbar.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)

    def select_file(self):
        path = filedialog.askopenfilename(
            title="Выберите аудиофайл",
            filetypes=[
                (
                    "Audio / Video files",
                    "*.mp3 *.wav *.flac *.m4a *.aac *.ogg *.wma *.aiff *.mp4 *.mkv *.mov *.avi",
                ),
                ("Audio files", "*.mp3 *.wav *.flac *.m4a *.aac *.ogg *.wma *.aiff"),
                ("Video files", "*.mp4 *.mkv *.mov *.avi"),
                ("All files", "*.*"),
            ],
        )

        if not path:
            return

        self.selected_file = str(Path(path))
        self.file_label.config(text=f"Файл: {Path(path).name}")
        self.status_var.set("Файл выбран. Можно запускать транскрибацию.")

    def start_transcription(self):
        if self.is_running:
            return

        if not self.selected_file:
            messagebox.showwarning("Нет файла", "Сначала выберите аудиофайл.")
            return

        if not Path(self.selected_file).exists():
            messagebox.showerror("Ошибка", "Файл не найден.")
            return

        self.is_running = True
        self.cancel_requested = False
        self.start_time = time.time()

        self.progress["value"] = 0
        self.run_btn.config(state="disabled")
        self.open_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")

        self.status_var.set("Транскрибация началась...")
        self.text.delete("1.0", tk.END)

        thread = threading.Thread(target=self._transcribe_worker, daemon=True)
        thread.start()

    def _transcribe_worker(self):
        try:
            result = self.transcriber.transcribe(
                self.selected_file, progress_callback=self._on_chunk_progress
            )

            self.root.after(
                0, self._on_success, result.text, result.device, result.model_name
            )

        except Exception as e:
            if str(e) == "TRANSCRIPTION_CANCELLED":
                self.root.after(0, self._on_cancelled)
            else:
                details = "".join(traceback.format_exception(type(e), e, e.__traceback__))
                self.root.after(0, self._on_error, details)

    def _on_chunk_progress(self, index: int, total: int):
        if self.cancel_requested:
            raise RuntimeError("TRANSCRIPTION_CANCELLED")

        percent = int(index / total * 100)

        elapsed = time.time() - self.start_time if self.start_time else 0
        avg_per_chunk = elapsed / index if index else 0
        remaining = avg_per_chunk * (total - index)

        mins = int(remaining // 60)
        secs = int(remaining % 60)

        def update():
            eta = f"{mins:02d}:{secs:02d}"
            self.status_var.set(
                f"Транскрибация: чанк {index}/{total} • осталось ~ {eta}"
            )
            self.progress["value"] = percent

        self.root.after(0, update)

    def _on_success(self, text: str, device: str, model_name: str):
        self.text.insert("1.0", text)

        self.progress["value"] = 100
        self.status_var.set(f"Готово. Модель: {model_name}. Устройство: {device}.")

        self.run_btn.config(state="normal")
        self.open_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")
        self.is_running = False

    def _on_error(self, error: str):
        self.status_var.set("Ошибка транскрибации")

        self.run_btn.config(state="normal")
        self.open_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")

        self.is_running = False

        messagebox.showerror("Ошибка", error)

    def _on_cancelled(self):
        self.status_var.set("Транскрибация отменена")
        self.run_btn.config(state="normal")
        self.open_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")
        self.is_running = False

    def save_text(self):
        content = self.text.get("1.0", tk.END).strip()

        if not content:
            messagebox.showwarning("Нет текста", "Сначала выполните транскрибацию.")
            return

        default_name = "transcript.txt"

        if self.selected_file:
            default_name = f"{Path(self.selected_file).stem}.txt"

        path = filedialog.asksaveasfilename(
            title="Сохранить текст",
            defaultextension=".txt",
            initialfile=default_name,
            filetypes=[("Text", "*.txt")],
        )

        if not path:
            return

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        self.status_var.set(f"Текст сохранен: {path}")

    def clear_text(self):
        self.text.delete("1.0", tk.END)

    def copy_text(self):
        content = self.text.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning("Нет текста", "Нечего копировать.")
            return

        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self.root.update()
        self.status_var.set("Текст скопирован в буфер обмена")

    def cancel_transcription(self):
        if self.is_running:
            self.cancel_requested = True
            self.status_var.set("Отмена транскрибации...")


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()