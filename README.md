# Contentlovers108

Existing YouTube channel: [youtube.com/@Contentlovers108](https://www.youtube.com/@Contentlovers108). Do not create a second channel.

**Show / series on that channel:** first-job money in India (in-hand, PF, HRA, UPI leaks, family UPI, increment). Working title for the playlist: Pehli Salary Club. The theme is still that life, not “only payslips,” and not a new brand account.

Hinglish Shorts plus one Sunday long-form. Written like a cousin on WhatsApp, not a seminar.

## Why this niche

India has a huge first-salary cohort every year. Search demand is practical (Form 16, HRA, PF, CTC) and Shorts demand is emotional (salary vanished in four days). Education category is monetizable once YouTube Partner Program thresholds are hit. The voice is local: rupee amounts, UPI, LIC uncles, canteen vs dabba — not US personal-finance recycled.

This is not a fake-human influencer. No face clone, no bought views, no “I am your CA” act. Description on every video says it is general education, not personal advice.

## Cadence (Asia/Kolkata)

| Slot | When | Format |
| --- | --- | --- |
| Shorts | Tue / Thu / Sat 19:30 IST | Vertical, ~30–50s |
| Long-form | Sunday 10:00 IST | 1920×1080 explainer |

First six weeks of scripts live in `channel/queue.yaml`.

## What this repo does

1. **Plan** — prints the calendar.
2. **Render** — Indian-English TTS + on-screen captions via ffmpeg.
3. **Publish** — YouTube Data API upload, scheduled to the IST slot (or public if the cron fires at/after that time).
4. **GitHub Action** — same publish job on cron.

Live upload cannot happen until you add YouTube OAuth secrets. **You do this once; after that cron posts.** Exact clicks: [SETUP.md](SETUP.md).

## Setup

```bash
python3 -m pip install -r requirements.txt
sudo apt-get install -y ffmpeg fonts-noto-core   # already on this image
export PYTHONPATH=.
python3 -m pehli_salary.cli plan
python3 -m pehli_salary.cli render --id s001
python3 -m pehli_salary.cli publish-due --date 2026-08-27 --dry-run
```

### YouTube OAuth (once)

Follow [SETUP.md](SETUP.md). Short version: Desktop OAuth client → `python3 -m pehli_salary.cli auth` → GitHub Actions secrets `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`.

Until those exist, `publish-due` prints the payload and exits 2 instead of uploading. Drop your own reads in `channel/voiceovers/{id}.mp3` if you want it to sound like you, not TTS.

## Monetization path (policy-safe)

1. Consistency on the calendar above until **1,000 subs** and either **4,000 long-form watch hours** or the current Shorts-view threshold.
2. Turn on ads. Keep the disclaimer. Do not buy subs/views.
3. After YPP: disclosed affiliates only (broker, term insurance lead, salary account). No hidden paid advice.
4. Comments are the research queue — next scripts should answer real first-job questions, not recycle US Twitter finance.

## Voice rules

Do: specific rupees, dates, app names, mid-thought starts, one joke max.  
Don’t: “let’s dive in”, game-changer, fake expertise, shaming people for sending money home.
