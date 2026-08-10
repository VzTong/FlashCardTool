"""
audio.py
--------
Module phát âm (TTS) cho Vocabulary Trainer.

Chiến lược:
1. Online ưu tiên:
   - edge-tts (giọng Neural tự nhiên)
   - fallback gTTS
2. Offline:
   - pyttsx3
   - Windows SAPI (nếu đang chạy Windows)

Cache file .mp3 theo hash (lang + text) để không gọi TTS lặp lại.
Chạy TTS + phát âm trong thread riêng để không đóng băng UI.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import shutil
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Thư mục cache âm thanh nằm cạnh file này
BASE_DIR = Path(__file__).resolve().parent
# Tạo thư mục cache
AUDIO_DIR = BASE_DIR / "audio_cache"
AUDIO_DIR.mkdir(exist_ok=True)
LOG_FILE = BASE_DIR / "audio.log"

# Nếu không muốn lưu gì:
# AUDIO_DIR = None

# Logger ghi file để debug khi không nghe được
logger = logging.getLogger("vocab_audio")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(fh)

# Lock tránh race condition khi nhiều request cùng lúc
_lock = threading.Lock()

# Nếu ko muốn log ra console, thêm NullHandler để tránh warning "No handlers could be found" -> cmt đoạn trên lại
# logger.addHandler(logging.NullHandler())

def _safe_name(text: str, lang: str) -> Path:
    """
    Tạo tên file cache an toàn từ (lang + text).
    Dùng SHA-256 rút gọn 24 ký tự để tránh trùng và tên file quá dài.
    """
    key = hashlib.sha256(f"{lang}:{text}".encode("utf-8")).hexdigest()[:24]
    return AUDIO_DIR / f"{key}.mp3"


def _edge_tts_sync(text: str, lang: str, output: Path) -> tuple[bool, str]:
    """
    Sinh file âm thanh bằng edge-tts (Microsoft Neural voices).
    Chạy async trong event loop riêng để tránh xung đột với Tkinter.
    """
    try:
        import edge_tts
    except ImportError as exc:
        logger.exception("edge-tts chưa được cài")
        return False, f"edge-tts chưa được cài: {exc}"

    # Voice mặc định
    voice = "ja-JP-NanamiNeural" if lang == "ja" else "en-US-JennyNeural"
    logger.info("Edge TTS: lang=%s voice=%s text=%r", lang, voice, text)

    async def run():
        communicate = edge_tts.Communicate(text=text, voice=voice)
        await communicate.save(str(output))

    try:
        # Không dùng asyncio.run() vì thread này có thể đã có loop
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            loop.run_until_complete(run())
        finally:
            loop.close()
            asyncio.set_event_loop(None)

        if output.exists() and output.stat().st_size > 1024:
            logger.info("TTS generated: %s (%d bytes)", output, output.stat().st_size)
            return True, "Edge TTS"

        logger.error("Edge TTS tạo file rỗng/không tồn tại: %s", output)
        return False, "Edge TTS không tạo được file âm thanh"
    except Exception as exc:
        logger.exception("Edge TTS lỗi")
        try:
            output.unlink(missing_ok=True)
        except Exception:
            pass
        return False, f"Edge TTS lỗi: {exc}"


def _gtts_sync(text: str, lang: str, output: Path) -> tuple[bool, str]:
    """
    Fallback online bằng gTTS (Google Text-to-Speech).
    README yêu cầu hỗ trợ gTTS nên giữ lại.
    """
    try:
        from gtts import gTTS
    except ImportError as exc:
        return False, f"gTTS chưa được cài: {exc}"

    try:
        tts = gTTS(text=text, lang=lang)
        tts.save(str(output))
        if output.exists() and output.stat().st_size > 500:
            logger.info("gTTS generated: %s", output)
            return True, "gTTS"
        return False, "gTTS tạo file rỗng"
    except Exception as exc:
        logger.exception("gTTS lỗi")
        try:
            output.unlink(missing_ok=True)
        except Exception:
            pass
        return False, f"gTTS lỗi: {exc}"


def _play_with_pygame(path: Path) -> tuple[bool, str]:
    """
    Phát MP3 trong nền bằng pygame, không mở cửa sổ player.
    Chờ phát xong rồi quit mixer để tránh treo.
    """
    try:
        import pygame
    except ImportError:
        return False, "pygame chưa được cài"

    try:
        # Init mỗi lần để tránh lỗi device bị chiếm
        if pygame.mixer.get_init() is None:
            pygame.mixer.init()

        pygame.mixer.music.load(str(path))
        pygame.mixer.music.play()

        # Chờ phát xong (không block UI vì đang chạy trong thread SpeechManager)
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

        logger.info("Playing with pygame (silent): %s", path)
        return True, "Đang phát bằng pygame"
    except Exception as exc:
        logger.exception("pygame playback lỗi")
        try:
            pygame.mixer.quit()
        except Exception:
            pass
        return False, f"pygame playback lỗi: {exc}"


def _play_with_os(path: Path) -> tuple[bool, str]:
    """
    Fallback: mở file bằng trình phát mặc định của hệ điều hành.
    (Windows: startfile, Linux: xdg-open, macOS: open)
    """
    try:
        if os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif shutil.which("xdg-open"):
            subprocess.Popen(["xdg-open", str(path)])
        elif shutil.which("open"):
            subprocess.Popen(["open", str(path)])
        else:
            return False, "Không tìm thấy trình phát âm thanh của hệ điều hành"
        logger.info("Opened audio with OS default player: %s", path)
        return True, "Đã mở trình phát âm thanh"
    except Exception as exc:
        logger.exception("OS playback lỗi")
        return False, f"OS playback lỗi: {exc}"


def _pyttsx3_speak(text: str, lang: str) -> tuple[bool, str]:
    """
    Offline TTS bằng pyttsx3.
    Cố gắng chọn voice đúng ngôn ngữ nếu hệ thống có cài.
    """
    try:
        import pyttsx3
    except ImportError as exc:
        return False, f"pyttsx3 chưa được cài: {exc}"

    try:
        engine = pyttsx3.init()
        voices = engine.getProperty("voices")

        for v in voices:
            name = (v.name or "").lower()
            langs = getattr(v, "languages", []) or []
            lang_str = " ".join(str(x) for x in langs).lower()

            if lang == "ja" and (
                "japan" in name or "ja" in lang_str or "japanese" in name
            ):
                engine.setProperty("voice", v.id)
                break
            if lang == "en" and (
                "english" in name or "en_" in lang_str or "en-" in lang_str
            ):
                engine.setProperty("voice", v.id)
                break

        engine.setProperty("rate", 150)
        engine.say(text)
        engine.runAndWait()
        engine.stop()
        return True, "pyttsx3 offline"
    except Exception as exc:
        logger.exception("pyttsx3 lỗi")
        return False, f"pyttsx3 lỗi: {exc}"


def _windows_sapi(text: str, lang: str) -> tuple[bool, str]:
    """
    Offline fallback trên Windows dùng System.Speech (SAPI).
    Chỉ chạy được trên Windows.
    """
    if os.name != "nt":
        return False, "Windows SAPI chỉ có trên Windows"

    ps = r'''
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.Volume = 100
$s.Rate = 0
$target = $env:VOCAB_TEXT
$wanted = $env:VOCAB_LANG
$voiceFound = $false
foreach ($v in $s.GetInstalledVoices()) {
    $info = $v.VoiceInfo
    if ($wanted -eq "ja" -and $info.Culture.Name -like "ja-JP*") {
        $s.SelectVoice($info.Name); $voiceFound = $true; break
    }
    if ($wanted -eq "en" -and $info.Culture.Name -like "en-*") {
        $s.SelectVoice($info.Name); $voiceFound = $true; break
    }
}
if (-not $voiceFound) { Write-Error "Không tìm thấy Windows voice cho $wanted"; exit 2 }
$s.Speak($target)
'''
    env = os.environ.copy()
    env["VOCAB_TEXT"] = text
    env["VOCAB_LANG"] = lang
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode == 0:
            logger.info("Windows SAPI phát thành công")
            return True, "Windows Speech"
        err = (result.stderr or result.stdout or "SAPI failed").strip()
        logger.error("Windows SAPI returncode=%s: %s", result.returncode, err)
        return False, f"Windows Speech lỗi: {err}"
    except Exception as exc:
        logger.exception("Windows SAPI exception")
        return False, f"Windows Speech exception: {exc}"


def _speak_online(text: str, lang: str) -> tuple[bool, str]:
    """
    Pipeline online:
    1. Dùng cache nếu có
    2. edge-tts → gTTS
    3. Phát bằng pygame → OS player
    """
    output = _safe_name(text, lang)
    errors: list[str] = []

    with _lock:
        if output.exists() and output.stat().st_size > 1024:
            logger.info("Using cached audio: %s", output)
        else:
            ok, msg = _edge_tts_sync(text, lang, output)
            if not ok:
                errors.append(msg)
                ok, msg = _gtts_sync(text, lang, output)
                if not ok:
                    errors.append(msg)

        if output.exists() and output.stat().st_size > 500:
            # Chỉ phát bằng pygame (không mở cửa sổ)
            ok, msg = _play_with_pygame(output)
            if ok:
                return True, msg
            errors.append(msg)

            # KHÔNG gọi _play_with_os nữa nếu không muốn hiện player
            # Nếu vẫn muốn fallback (mở player) thì bỏ comment dòng dưới:
            # ok, msg = _play_with_os(output)
            # if ok:
            #     return True, msg
            # errors.append(msg)

    return False, " | ".join(errors) if errors else "Online TTS thất bại"


def _speak_offline(text: str, lang: str) -> tuple[bool, str]:
    """Pipeline offline: pyttsx3 → Windows SAPI."""
    ok, msg = _pyttsx3_speak(text, lang)
    if ok:
        return True, msg
    ok2, msg2 = _windows_sapi(text, lang)
    if ok2:
        return True, msg2
    return False, f"{msg} | {msg2}"


def speak(text: str, language: str, mode: str = "online") -> tuple[bool, str]:
    """
    Hàm phát âm chính (sync).

    Args:
        text: Nội dung cần đọc
        language: "Japanese" | "English"
        mode: "online" | "offline"

    Returns:
        (success, message)
    """
    text = (text or "").strip()
    if not text:
        return False, "Không có nội dung để đọc"

    lang = "ja" if language == "Japanese" else "en"
    logger.info("REQUEST language=%s mode=%s text=%r", language, mode, text)

    if mode == "offline":
        return _speak_offline(text, lang)

    # Online trước, nếu fail thì tự fallback offline
    ok, msg = _speak_online(text, lang)
    if ok:
        return True, msg

    logger.warning("Online failed, fallback offline: %s", msg)
    ok2, msg2 = _speak_offline(text, lang)
    if ok2:
        return True, f"Online lỗi → Offline: {msg2}"
    return False, f"{msg} | {msg2}"


class SpeechManager:
    """
    Wrapper bất đồng bộ cho UI (Tkinter).

    Chạy speak() trong ThreadPoolExecutor để không block main thread.
    Hỗ trợ callback on_done / on_error.
    """

    def __init__(self):
        # max_workers=1 để các request phát âm chạy tuần tự
        self._executor = ThreadPoolExecutor(max_workers=1)

    def speak(
        self,
        text: str,
        language: str,
        mode: str = "online",
        on_done=None,
        on_error=None,
    ):
        """
        Gọi TTS bất đồng bộ.

        Args:
            text: Nội dung
            language: "Japanese" | "English"
            mode: "online" | "offline"
            on_done: callback khi thành công
            on_error: callback(error_message) khi thất bại
        """
        def _run():
            try:
                ok, msg = speak(text, language, mode=mode)
                if ok:
                    if on_done:
                        on_done()
                else:
                    if on_error:
                        on_error(msg)
            except Exception as e:
                logger.exception("SpeechManager error")
                if on_error:
                    on_error(str(e))

        self._executor.submit(_run)