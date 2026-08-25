from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from pehli_salary.config import CHANNEL_HANDLE, OUTBOX
from pehli_salary.queue import QueueItem
from pehli_salary.voice import synthesize

BG = (10, 12, 16)
INK = (248, 248, 245)
MUTE = (156, 160, 168)
AMBER = (232, 176, 64)
STROKE = (8, 8, 10)
FONT_REG = "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"
DEV_BOLD = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"


def render_item(item: QueueItem, outbox: Path = OUTBOX) -> Path:
    work = outbox / item.id
    work.mkdir(parents=True, exist_ok=True)
    chunks = item.caption_chunks()
    audio_path = work / "voice.mp3"
    synthesize(item, audio_path)
    duration = _media_duration_seconds(audio_path)
    per = max(duration / max(len(chunks), 1), 1.4)
    frames = []
    for idx, chunk in enumerate(chunks):
        frame = work / f"frame_{idx:02d}.png"
        _draw_frame(item, chunk, idx, len(chunks), frame)
        frames.append((frame, per))
    video_path = work / f"{item.id}.mp4"
    _stitch(frames, audio_path, video_path, item.kind)
    return video_path


def _media_duration_seconds(path: Path) -> float:
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
    draw.rectangle((0, 0, 12, h), fill=AMBER)
    brand = _font(FONT_REG, 22)
    draw.text((48, 72), CHANNEL_HANDLE.upper(), font=brand, fill=MUTE)
    cap_font = _pick_font(caption, 72 if item.kind == "short" else 54)
    wrapped = _wrap(draw, caption.upper(), cap_font, w - 120)
    total_h = len(wrapped) * (cap_font.size + 16)
    y = (h - total_h) // 2
    fill = AMBER if any(ch.isdigit() or ch == "₹" for ch in caption) else INK
    for line in wrapped:
        tw = draw.textlength(line, font=cap_font)
        x = (w - tw) // 2
        _outlined(draw, (x, y), line, cap_font, fill)
        y += cap_font.size + 16
    if idx == total - 1:
        foot = _font(FONT_REG, 26)
        msg = "COMMENT YOUR IN-HAND"
        tw = draw.textlength(msg, font=foot)
        draw.text(((w - tw) // 2, h - 140), msg, font=foot, fill=MUTE)
    img.save(dest, "PNG")


def _outlined(draw: ImageDraw.ImageDraw, xy, text: str, font, fill) -> None:
    x, y = xy
    for dx in (-3, -2, -1, 0, 1, 2, 3):
        for dy in (-3, -2, -1, 0, 1, 2, 3):
            if dx or dy:
                draw.text((x + dx, y + dy), text, font=font, fill=STROKE)
    draw.text((x, y), text, font=font, fill=fill)


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
    return lines[:4]


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
        "-b:a",
        "192k",
        "-shortest",
        "-movflags",
        "+faststart",
        str(dest),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    Path(list_path).unlink(missing_ok=True)
