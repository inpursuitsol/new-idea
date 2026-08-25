from __future__ import annotations

from datetime import date
from pathlib import Path

from pehli_salary.queue import QueueItem
from pehli_salary.render import _draw_frame, _stitch


def test_frame_and_stitch(tmp_path: Path):
    item = QueueItem(
        id="t01",
        kind="short",
        publish_on=date(2026, 8, 27),
        title="Test",
        hook="Hook",
        beats=["Beat"],
        cta="Go",
        tags=[],
    )
    frame = tmp_path / "f.png"
    _draw_frame(item, "Pehli salary aayi kahan gayi", 0, 1, frame)
    assert frame.stat().st_size > 1000

    audio = tmp_path / "a.aac"
    import subprocess

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=mono",
            "-t",
            "2",
            str(audio),
        ],
        check=True,
        capture_output=True,
    )
    dest = tmp_path / "out.mp4"
    _stitch([(frame, 2.0)], audio, dest, "short")
    assert dest.exists() and dest.stat().st_size > 1000
