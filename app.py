import threading
import traceback
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from transcriber import ParakeetTranscriber


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Parakeet V3 Transcriber")
        self.root.geometry("860x560")

        self.transcriber = ParakeetTranscriber()
        self.selected_file = None

        self.status_var = tk.StringVar(value="Выберите MP3 файл")

        self._build_ui()

    def _build_ui(self):
        frame = tk.Frame(self.root, padx=12, pady=12)
        frame.pack(fill="both", expand=True)

        top = tk.Frame(frame)
        top.pack(fill="x")

        self.file_label = tk.Label(top, text="Файл не выбран", anchor="w")
        self.file_label.pack(fill="x")

        buttons = tk.Frame(frame, pady=10)
        buttons.pack(fill="x")

        self.open_btn = tk.Button(buttons, text="Открыть MP3", command=self.select_file)
        self.open_btn.pack(side="left")

        self.run_btn = tk.Button(buttons, text="Транскрибировать", command=self.start_transcription)
        self.run_btn.pack(side="left", padx=8)

        self.save_btn = tk.Button(buttons, text="Сохранить TXT", command=self.save_text)
        self.save_btn.pack(side="left")

        self.status_label = tk.Label(frame, textvariable=self.status_var, anchor="w")
        self.status_label.pack(fill="x", pady=(0, 8))

        self.text = tk.Text(frame, wrap="word")
        self.text.pack(fill="both", expand=True)

    def select_file(self):
        path = filedialog.askopenfilename(
            title="Выберите аудиофайл",
            filetypes=[("Audio", "*.mp3 *.wav *.flac"), ("All files", "*.*")],
        )
        if not path:
            return
        self.selected_file = path
        self.file_label.config(text=f"Файл: {path}")
        self.status_var.set("Файл выбран. Можно запускать транскрибацию.")

    def start_transcription(self):
        if not self.selected_file:
            messagebox.showwarning("Нет файла", "Сначала выберите аудиофайл.")
            return

        self.run_btn.config(state="disabled")
        self.open_btn.config(state="disabled")
        self.status_var.set("Загрузка модели и транскрибация...")
        self.text.delete("1.0", tk.END)

        thread = threading.Thread(target=self._transcribe_worker, daemon=True)
        thread.start()

    def _transcribe_worker(self):
        try:
            result = self.transcriber.transcribe(
                self.selected_file, progress_callback=self._on_chunk_progress
            )
            self.root.after(0, self._on_success, result.text, result.device, result.model_name)
        except Exception as e:
            details = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            self.root.after(0, self._on_error, details)

    def _on_chunk_progress(self, index: int, total: int):
        self.root.after(0, self.status_var.set, f"Транскрибация: чанк {index}/{total}...")

    def _on_success(self, text: str, device: str, model_name: str):
        self.text.insert("1.0", text)
        self.status_var.set(f"Готово. Модель: {model_name}. Устройство: {device}.")
        self.run_btn.config(state="normal")
        self.open_btn.config(state="normal")

    def _on_error(self, error: str):
        self.status_var.set("Ошибка транскрибации")
        self.run_btn.config(state="normal")
        self.open_btn.config(state="normal")
        messagebox.showerror("Ошибка", error)

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


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
