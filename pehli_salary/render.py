from __future__ import annotations

from pathlib import Path

from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont

from pehli_salary.config import OUTBOX
from pehli_salary.queue import QueueItem

BG = (26, 20, 16)
CARD = (42, 33, 24)
ACCENT = (232, 165, 75)
TEXT = (244, 232, 212)
MUTE = (168, 152, 128)
FONT_REG = "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"
DEV_BOLD = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"


def render_item(item: QueueItem, outbox: Path = OUTBOX) -> Path:
    work = outbox / item.id
    work.mkdir(parents=True, exist_ok=True)
    chunks = item.caption_chunks()
    audio_path = work / "voice.mp3"
    _tts(item.narration(), audio_path)
    duration = _mp3_duration_seconds(audio_path)
    per = max(duration / max(len(chunks), 1), 1.6)
    frames = []
    for idx, chunk in enumerate(chunks):
        frame = work / f"frame_{idx:02d}.png"
        _draw_frame(item, chunk, idx, len(chunks), frame)
        frames.append((frame, per))
    video_path = work / f"{item.id}.mp4"
    _stitch(frames, audio_path, video_path, item.kind)
    return video_path


def _tts(text: str, dest: Path) -> None:
    # Indian English TLD; Hinglish words stay as-is.
    gTTS(text=text, lang="en", tld="co.in", slow=False).save(str(dest))


def _mp3_duration_seconds(path: Path) -> float:
    import subprocess

    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(probe.stdout.strip())


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size=size)


def _draw_frame(item: QueueItem, caption: str, idx: int, total: int, dest: Path) -> None:
    w, h = (1920, 1080) if item.kind == "longform" else (1080, 1920)
    img = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(img)
    margin = 72 if item.kind == "short" else 96
    draw.rounded_rectangle(
        (margin, int(h * 0.22), w - margin, int(h * 0.78)),
        radius=36,
        fill=CARD,
    )
    brand = _font(FONT_BOLD, 28 if item.kind == "short" else 32)
    draw.text((margin + 28, int(h * 0.24)), "PEHLI SALARY CLUB", font=brand, fill=ACCENT)
    cap_font = _pick_font(caption, 56 if item.kind == "short" else 48)
    wrapped = _wrap(draw, caption, cap_font, w - 2 * margin - 80)
    ty = int(h * 0.40)
    for line in wrapped:
        draw.text((margin + 40, ty), line, font=cap_font, fill=TEXT)
        ty += cap_font.size + 12
    footer = _font(FONT_REG, 24)
    draw.text(
        (margin + 28, int(h * 0.72)),
        f"{idx + 1}/{total}  ·  {item.publish_on.isoformat()}",
        font=footer,
        fill=MUTE,
    )
    img.save(dest, "PNG")


def _pick_font(text: str, size: int) -> ImageFont.FreeTypeFont:
    if any(ord(ch) > 127 for ch in text):
        try:
            return _font(DEV_BOLD, size)
        except OSError:
            pass
    return _font(FONT_BOLD, size)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        trial = " ".join([*current, word])
        if draw.textlength(trial, font=font) <= max_width or not current:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines[:6]


def _stitch(frames: list[tuple[Path, float]], audio: Path, dest: Path, kind: str) -> None:
    import subprocess
    import tempfile

    size = "1080x1920" if kind == "short" else "1920x1080"
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as listing:
        for frame, dur in frames:
            listing.write(f"file '{frame.resolve()}'\n")
            listing.write(f"duration {dur:.3f}\n")
        listing.write(f"file '{frames[-1][0].resolve()}'\n")
        list_path = listing.name
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        list_path,
        "-i",
        str(audio),
        "-vf",
        f"scale={size},format=yuv420p",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        "-movflags",
        "+faststart",
        str(dest),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    Path(list_path).unlink(missing_ok=True)
