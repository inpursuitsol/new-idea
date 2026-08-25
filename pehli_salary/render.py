from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from pehli_salary.config import OUTBOX
from pehli_salary.queue import QueueItem
from pehli_salary.voice import synthesize

PAPER = (232, 220, 196)
RULE = (196, 176, 150)
INK = (36, 32, 28)
MUTE = (92, 78, 64)
HIGHLIGHT = (255, 224, 102)
STICKY = (255, 239, 170)
FONT_REG = "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"
FONT_ITAL = "/usr/share/fonts/truetype/noto/NotoSans-Italic.ttf"
DEV_BOLD = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"


def render_item(item: QueueItem, outbox: Path = OUTBOX) -> Path:
    work = outbox / item.id
    work.mkdir(parents=True, exist_ok=True)
    chunks = item.caption_chunks()
    audio_path = work / "voice.mp3"
    synthesize(item, audio_path)
    duration = _media_duration_seconds(audio_path)
    per = max(duration / max(len(chunks), 1), 1.35)
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
    rng = random.Random(f"{item.id}:{idx}:{caption}")
    w, h = (1920, 1080) if item.kind == "longform" else (1080, 1920)
    img = Image.new("RGB", (w, h), PAPER)
    draw = ImageDraw.Draw(img)
    _ruled_paper(draw, w, h, rng)
    if idx == 0:
        sticky = _font(FONT_ITAL, 26)
        draw.rectangle((48, 56, 420, 118), fill=STICKY)
        draw.text((62, 72), "phone notes, not a lecture", font=sticky, fill=MUTE)
    cap_font = _pick_font(caption, 62 if item.kind == "short" else 50)
    wrapped = _wrap(draw, caption, cap_font, w - 160)
    base_y = int(h * (0.34 + rng.uniform(-0.03, 0.04)))
    x = 80 + rng.randint(-8, 18)
    for line in wrapped:
        bbox_w = int(draw.textlength(line, font=cap_font))
        hy = base_y + cap_font.size - 8
        if any(ch.isdigit() for ch in line):
            draw.rectangle((x - 8, base_y + 6, x + bbox_w + 12, hy + 10), fill=HIGHLIGHT)
        draw.text((x, base_y), line, font=cap_font, fill=INK)
        base_y += cap_font.size + 18 + rng.randint(-2, 4)
    if idx == total - 1:
        small = _font(FONT_ITAL, 28)
        draw.text((80, h - 160), "pehli salary club", font=small, fill=MUTE)
    img = img.rotate(rng.uniform(-0.7, 0.7), resample=Image.Resampling.BICUBIC, fillcolor=PAPER)
    img = ImageEnhance.Contrast(img).enhance(0.96)
    img = img.filter(ImageFilter.SMOOTH)
    _speckle(img, rng)
    img.save(dest, "PNG")


def _ruled_paper(draw: ImageDraw.ImageDraw, w: int, h: int, rng: random.Random) -> None:
    for y in range(140, h - 80, 54):
        draw.line((48, y, w - 48, y), fill=RULE, width=2)
    draw.line((110, 40, 118, h - 40), fill=(214, 120, 110), width=3)


def _speckle(img: Image.Image, rng: random.Random) -> None:
    px = img.load()
    w, h = img.size
    for _ in range(1800):
        x = rng.randint(0, w - 1)
        y = rng.randint(0, h - 1)
        r, g, b = px[x, y]
        d = rng.randint(-18, 12)
        px[x, y] = (
            max(0, min(255, r + d)),
            max(0, min(255, g + d)),
            max(0, min(255, b + d)),
        )


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
    return lines[:5]


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
        f"scale={size},format=yuv420p,noise=alls=8:allf=t+u",
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
