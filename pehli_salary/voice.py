from __future__ import annotations

import asyncio
from pathlib import Path

from pehli_salary.queue import QueueItem, voiceover_path

EDGE_VOICE = "en-IN-NeerjaExpressiveNeural"


def synthesize(item: QueueItem, dest: Path) -> Path:
    override = voiceover_path(item)
    if override:
        dest.write_bytes(Path(override).read_bytes())
        return dest
    text = item.narration()
    try:
        _edge_tts(text, dest)
    except Exception:
        from gtts import gTTS

        gTTS(text=text, lang="en", tld="co.in", slow=False).save(str(dest))
    return dest


def _edge_tts(text: str, dest: Path) -> None:
    import edge_tts

    async def _run() -> None:
        comm = edge_tts.Communicate(
            text,
            EDGE_VOICE,
            rate="-4%",
            pitch="-1Hz",
        )
        await comm.save(str(dest))

    asyncio.run(_run())
