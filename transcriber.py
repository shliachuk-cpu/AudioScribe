import os
import shutil
import subprocess
import tempfile
import gc
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Callable, Optional

os.environ.setdefault("NUMBA_DISABLE_JIT", "1")

import torch
import nemo.collections.asr as nemo_asr


@dataclass
class TranscriptionResult:
    text: str
    device: str
    model_name: str


class ParakeetTranscriber:
    def __init__(
        self,
        model_name: str = "nvidia/parakeet-tdt-0.6b-v3",
        chunk_seconds: int = 25,
    ) -> None:
        self.model_name = model_name
        self.device = self._detect_device()
        self.chunk_seconds = max(10, int(chunk_seconds))
        self._model = None

    @staticmethod
    def _detect_device() -> str:
        if torch.cuda.is_available():
            return "cuda"
        mps_backend = getattr(torch.backends, "mps", None)
        if mps_backend and mps_backend.is_available():
            return "mps"
        return "cpu"

    def _load_model(self):
        if self._model is None:
            try:
                self._patch_torch_sampler_for_lhotse()
                model = nemo_asr.models.EncDecRNNTBPEModel.from_pretrained(
                    model_name=self.model_name
                )
                try:
                    model = model.to(self.device)
                except Exception:
                    self.device = "cpu"
                    model = model.to(self.device)
                model.eval()
                self._model = model
            except TypeError as exc:
                if "object.__init__() takes exactly one argument" in str(exc):
                    raise RuntimeError(
                        "Конфликт версий зависимостей (обычно NeMo/Lhotse/Torch).\n"
                        "Используйте отдельное виртуальное окружение и переустановите зависимости:\n"
                        "python3 -m venv .venv\n"
                        "source .venv/bin/activate\n"
                        "python -m pip install -U pip\n"
                        "python -m pip install -r requirements.txt\n\n"
                        f"Диагностика: {self._diagnostics()}"
                    ) from exc
                raise
        return self._model

    @staticmethod
    def _patch_torch_sampler_for_lhotse() -> None:
        """
        Torch (newer versions) may expose Sampler.__init__ as object.__init__.
        Lhotse still calls super().__init__(...) with kwargs, which raises TypeError.
        """
        sampler_init = torch.utils.data.Sampler.__init__
        if sampler_init is object.__init__:
            def _compat_sampler_init(self, *args, **kwargs):
                return None

            torch.utils.data.Sampler.__init__ = _compat_sampler_init

    @staticmethod
    def _diagnostics() -> str:
        packages = [
            "nemo-toolkit",
            "torch",
            "lightning",
            "pytorch-lightning",
            "librosa",
            "numba",
        ]
        parts = []
        for pkg in packages:
            try:
                parts.append(f"{pkg}={metadata.version(pkg)}")
            except metadata.PackageNotFoundError:
                parts.append(f"{pkg}=not-installed")
        return ", ".join(parts)

    @staticmethod
    def _ffmpeg_exists() -> bool:
        return shutil.which("ffmpeg") is not None

    def _prepare_audio_chunks(self, input_path: str) -> tuple[list[str], Optional[str]]:
        if not self._ffmpeg_exists():
            raise RuntimeError(
                "Для обработки аудио нужен ffmpeg. Установите ffmpeg и добавьте в PATH."
            )

        temp_dir = tempfile.mkdtemp(prefix="parakeet_chunks_")
        chunk_pattern = os.path.join(temp_dir, "chunk_%05d.wav")

        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            input_path,
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "segment",
            "-segment_time",
            str(self.chunk_seconds),
            "-reset_timestamps",
            "1",
            "-c:a",
            "pcm_s16le",
            chunk_pattern,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise RuntimeError(f"Ошибка ffmpeg: {proc.stderr.strip()}")

        chunks = sorted(str(p) for p in Path(temp_dir).glob("chunk_*.wav"))
        if not chunks:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise RuntimeError("Не удалось подготовить аудио-чанки для транскрибации.")
        return chunks, temp_dir

    def transcribe(
        self,
        input_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> TranscriptionResult:
        model = self._load_model()
        chunks, temp_dir = self._prepare_audio_chunks(input_path)
        texts = []

        try:
            total = len(chunks)
            for idx, chunk_path in enumerate(chunks, start=1):
                if progress_callback:
                    progress_callback(idx, total)
                try:
                    output = model.transcribe(
                        [chunk_path],
                        batch_size=1,
                        num_workers=0,
                        verbose=False,
                    )
                except (TypeError, RuntimeError) as exc:
                    if self.device == "mps" and self._is_mps_float64_error(exc):
                        model = self._fallback_model_to_cpu(model)
                        output = model.transcribe(
                            [chunk_path],
                            batch_size=1,
                            num_workers=0,
                            verbose=False,
                        )
                    else:
                        raise
                first = output[0]
                chunk_text = first.text if hasattr(first, "text") else str(first)
                chunk_text = chunk_text.strip()
                if chunk_text:
                    texts.append(chunk_text)
                self._release_memory()

            return TranscriptionResult(
                text="\n".join(texts).strip(),
                device=self.device,
                model_name=self.model_name,
            )
        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

    @staticmethod
    def _is_mps_float64_error(exc: Exception) -> bool:
        message = str(exc).lower()
        return "mps tensor" in message and "float64" in message

    def _fallback_model_to_cpu(self, model):
        self.device = "cpu"
        model = model.to("cpu")
        self._release_memory()
        return model

    def _release_memory(self) -> None:
        gc.collect()
        if self.device == "cuda":
            torch.cuda.empty_cache()
        elif self.device == "mps":
            mps = getattr(torch, "mps", None)
            if mps and hasattr(mps, "empty_cache"):
                mps.empty_cache()
