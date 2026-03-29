import sys
print("Используется Python:", sys.executable)

import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path
import threading
import subprocess

# ==================== Drag & Drop ====================
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False
    print("❌ tkinterdnd2 не установлен → pip install tkinterdnd2")


from transcriber import ParakeetTranscriber


# ========================================================
#   Главный класс с поддержкой DnD
# ========================================================
class App(ctk.CTk, TkinterDnD.DnDWrapper if DND_AVAILABLE else object):

    def __init__(self):
        # Важно: сначала инициализируем оба родителя
        super().__init__()

        if DND_AVAILABLE:
            self.TkdndVersion = TkinterDnD._require(self)   # Это обязательная строка!

        self.title("Parakeet V3 Transcriber")
        self.geometry("920x680")

        self.transcriber = ParakeetTranscriber()
        self.selected_file = None
        self.is_running = False
        self.model_ready = False
        self.language = "auto"

        self.build_ui()

        # Фоновая загрузка модели
        threading.Thread(target=self.load_model_bg, daemon=True).start()

        # Настройка Drag & Drop
        if DND_AVAILABLE:
            self.after(200, self.setup_drag_drop)
        else:
            self.status.configure(text="⚠ Установите tkinterdnd2 для поддержки Drag & Drop")

    # ----------------------------------------------------- UI
    def build_ui(self):
        self.header = ctk.CTkFrame(self, fg_color="#6C5CE7", height=70)
        self.header.pack(fill="x")

        title = ctk.CTkLabel(
            self.header,
            text="🎙 Parakeet Transcriber",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="white"
        )
        title.pack(pady=20)

        # Дроп-зона (делаем её большой и заметной)
        self.file_card = ctk.CTkFrame(self, fg_color="#2B2D42", corner_radius=15)
        self.file_card.pack(fill="x", padx=25, pady=25)

        self.file_label = ctk.CTkLabel(
            self.file_card,
            text="📂 Перетащите файл сюда\n\nили нажмите кнопку «Открыть файл»\n\nПоддерживаются: mp4, mkv, mov, avi, mp3, wav...",
            font=ctk.CTkFont(size=15),
            text_color="#A0A0A0",
            justify="center"
        )
        self.file_label.pack(expand=True, pady=40)

        # Кнопки
        self.buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.buttons_frame.pack(fill="x", padx=25, pady=8)

        self.open_btn = ctk.CTkButton(self.buttons_frame, text="📂 Открыть файл", 
                                      command=self.select_file, fg_color="#00C853", width=150)
        self.open_btn.pack(side="left", padx=6)

        self.run_btn = ctk.CTkButton(self.buttons_frame, text="🚀 Старт транскрибации", 
                                     command=self.start_transcription, fg_color="#6C5CE7", width=190)
        self.run_btn.pack(side="left", padx=6)

        self.save_btn = ctk.CTkButton(self.buttons_frame, text="💾 TXT", 
                                      command=self.save_text, fg_color="#0984E3", width=110)
        self.save_btn.pack(side="left", padx=6)

        self.pdf_btn = ctk.CTkButton(self.buttons_frame, text="📄 PDF", 
                                     command=self.save_pdf, fg_color="#d63031", width=110)
        self.pdf_btn.pack(side="left", padx=6)

        self.lang_dropdown = ctk.CTkComboBox(
            self.buttons_frame, values=["auto", "ru", "en", "uk", "es"],
            command=self.set_language, width=100
        )
        self.lang_dropdown.set("auto")
        self.lang_dropdown.pack(side="right", padx=10)

        self.status = ctk.CTkLabel(self, text="⏳ Загрузка модели...", text_color="#B0B0B0")
        self.status.pack(anchor="w", padx=30, pady=(5, 0))

        self.progress = ctk.CTkProgressBar(self, progress_color="#6C5CE7")
        self.progress.pack(fill="x", padx=25, pady=12)
        self.progress.set(0)

        self.textbox = ctk.CTkTextbox(self, corner_radius=15, fg_color="#1E1E2F", text_color="white", font=ctk.CTkFont(size=14))
        self.textbox.pack(fill="both", expand=True, padx=25, pady=15)

    # ----------------------------------------------------- DnD Setup
    def setup_drag_drop(self):
        try:
            # Регистрируем дроп на всё главное окно
            self.drop_target_register(DND_FILES)
            self.dnd_bind('<<Drop>>', self.on_drop)

            # Дополнительно на карточку (более заметно)
            self.file_card.drop_target_register(DND_FILES)
            self.file_card.dnd_bind('<<Drop>>', self.on_drop)

            print("✅ Drag & Drop успешно активирован")
            self.file_label.configure(text_color="white")
        except Exception as e:
            print(f"Ошибка DnD: {e}")

    def on_drop(self, event):
        file_path = event.data.strip()

        # Убираем фигурные скобки (tkinterdnd2 их добавляет при пробелах в пути)
        if file_path.startswith('{') and file_path.endswith('}'):
            file_path = file_path[1:-1]

        # Если несколько файлов — берём первый
        if ' ' in file_path:
            file_path = file_path.split()[0]

        if Path(file_path).exists():
            self.set_file(file_path)
        else:
            self.status.configure(text="❌ Не удалось получить путь к файлу")

    # ----------------------------------------------------- Остальные методы (без изменений)
    def load_model_bg(self):
        try:
            self.transcriber._load_model()
            self.model_ready = True
            self.status.configure(text="✅ Модель загружена и готова к работе")
        except Exception as e:
            self.status.configure(text=f"❌ Ошибка модели: {str(e)[:80]}...")

    def select_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("Поддерживаемые файлы", "*.mp4 *.mkv *.mov *.avi *.mp3 *.wav *.ogg *.flac")]
        )
        if path:
            self.set_file(path)

    def set_file(self, path):
        p = Path(path)
        if not p.exists():
            self.status.configure(text="❌ Файл не найден")
            return

        self.selected_file = str(p)
        self.file_label.configure(text=f"📄 Выбран файл:\n{p.name}")

        duration = self.get_duration(str(p))
        self.status.configure(text=f"📂 {p.name} • {duration}")

    def get_duration(self, path):
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", path],
                stdout=subprocess.PIPE, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            sec = float(result.stdout.strip())
            return f"{int(sec//60)}:{int(sec%60):02d}"
        except:
            return "?"

    def set_language(self, value):
        self.language = value

    def start_transcription(self):
        if not self.model_ready:
            self.status.configure(text="⏳ Модель ещё загружается...")
            return
        if not self.selected_file:
            self.status.configure(text="❗ Выберите файл перед запуском")
            return
        if self.is_running:
            return

        self.is_running = True
        self.progress.set(0)
        self.textbox.delete("1.0", "end")
        self.status.configure(text="🎧 Идёт транскрибация...")

        threading.Thread(target=self.worker, daemon=True).start()

    def worker(self):
        try:
            result = self.transcriber.transcribe(self.selected_file, progress_callback=self.on_progress)
            self.after(0, lambda t=result.text: self.on_done(t))
        except Exception as e:
            self.after(0, lambda: self.status.configure(text=f"❌ Ошибка: {e}"))
        finally:
            self.is_running = False

    def on_progress(self, i, total):
        self.after(0, lambda: self.progress.set(i / total))
        self.after(0, lambda: self.status.configure(text=f"Чанк {i} из {total}"))

    def on_done(self, text):
        self.textbox.insert("1.0", text)
        self.progress.set(1.0)
        self.status.configure(text="✅ Транскрибация завершена успешно")

    def save_text(self):
        text = self.textbox.get("1.0", "end").strip()
        if not text:
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if path:
            Path(path).write_text(text, encoding="utf-8")
            self.status.configure(text="💾 TXT сохранён")

    def save_pdf(self):
        from reportlab.platypus import SimpleDocTemplate, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfbase import pdfmetrics
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import mm

        text = self.textbox.get("1.0", "end").strip()
        if not text:
            return

        path = filedialog.asksaveasfilename(defaultextension=".pdf")
        if not path:
            return

    # Регистрируем Arial
        pdfmetrics.registerFont(TTFont("Arial", "arial.ttf"))

    # Стиль текста
        styles = getSampleStyleSheet()
        style = styles["Normal"]
        style.fontName = "Arial"
        style.fontSize = 12
        style.leading = 16  # межстрочный интервал

    # Генерация PDF
        doc = SimpleDocTemplate(
        path,
        pagesize=letter,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

        story = [Paragraph(line.replace("\n", "<br/>"), style) for line in text.split("\n")]

        doc.build(story)

        self.status.configure(text="📄 PDF сохранён")


if __name__ == "__main__":
    app = App()
    app.mainloop()