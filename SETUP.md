# What you need to do (once) so posting runs without me

I cannot log into Google or YouTube as you. After the steps below, GitHub Actions renders the next video and uploads it on the IST calendar by itself.

Fully automated **and** “this is clearly a real person on camera” is not the same job. Camera + your voice is the most human. If you skip the camera, use **your voice notes** in `channel/voiceovers/` (step 8). Neural TTS is the fallback; it is better than Google’s old gTTS, still not your throat.

Do **not** buy views, comments, or subscribers. That bans the channel before ads.

---

## What I need from you (checklist)

| # | You give me / set this | Why |
| --- | --- | --- |
| 1 | A Google account you control | Owns the Cloud project and the channel |
| 2 | A YouTube channel (Brand Account is fine) | Place videos go |
| 3 | YouTube Data API OAuth **Desktop** client | Lets the robot upload |
| 4 | One browser login (`python3 -m pehli_salary.cli auth`) | Creates `refresh_token` |
| 5 | Three GitHub Actions secrets | So cron can upload |
| 6 | Actions enabled on this repo | Cron will not fire otherwise |
| 7 | ~20 min on YouTube Studio (name, About, not-for-kids) | Looks like a channel, not a dump |
| 8 | Optional: your voice as `s001.mp3` etc. | Biggest jump in “not AI” |
| 9 | Optional: 6 phone photos (desk, chai, payslip-blurred, metro, notebook, UPI screenshot with amounts hidden) | B-roll later; skip for now |

I already have scripts, captions, renderer, and the cron workflow in the repo. I do not have items 1–6 until you do them.

---

## Step by step

### 1. Create the YouTube channel

1. Open [youtube.com](https://www.youtube.com) in Chrome, signed into **your** Google account.
2. Click your photo → **Create a channel**.
3. Use a Brand Account if you do not want your legal name on the channel.
4. Name: `Pehli Salary Club` (or Hindi: `पहली सैलरी क्लब`). Handle: something like `@pehlisalary`.
5. Do **not** use a face clone, a stock “Indian businessman” AI avatar, or someone else’s photos.

### 2. YouTube Studio, 15 minutes, so it does not look like a bot farm

1. [studio.youtube.com](https://studio.youtube.com) → **Customization**.
2. **Name**: Pehli Salary Club.
3. **Description** (paste):

   > Pehli naukri, pehle 5 saal. CTC vs in-hand, PF, HRA, UPI leaks, ghar ka UPI. Main CA nahi hoon. Jo maine khud seekha, wahi. Tumhara number alag ho sakta hai.

4. **Links**: none, or only LinkedIn if it is really you.
5. **Channel icon**: a messy notebook photo you take on your phone. Not a Canva “finance logo”.
6. **Banner**: same desk, 2560×1440, no neon AI gradient.
7. **Settings → Channel → Advanced → default upload**: **No, it's not made for kids**.
8. Country: India. Language: Hindi / English mixed is fine.

### 3. Google Cloud project + YouTube API

1. Open [Google Cloud Console](https://console.cloud.google.com/) with the **same** Google account that owns the channel.
2. **New project**, name `pehli-salary-club`.
3. **APIs & Services → Enable APIs** → enable **YouTube Data API v3**.
4. **OAuth consent screen**:
   - User type: **External**.
   - App name: `Pehli Salary Club Uploader`.
   - User support email: yours.
   - Developer contact: yours.
   - Scopes: add `https://www.googleapis.com/auth/youtube.upload`.
   - **Test users**: add the Gmail that owns the YouTube channel. Until Google verifies the app, **only test users** can auth. For a one-person channel, stay in Testing forever. That is normal.
5. **Credentials → Create credentials → OAuth client ID**:
   - Application type: **Desktop app**.
   - Download JSON. Save it locally as `client_secret.json`. Never commit it. It is already gitignored.

### 4. Generate the refresh token on your laptop (once)

You must do this on a machine with a browser. I cannot complete Google’s login for you.

```bash
git clone https://github.com/inpursuitsol/new-idea.git
cd new-idea
git checkout cursor/pehli-salary-youtube-bbab   # or main after merge
python3 -m pip install -r requirements.txt
# put client_secret.json in this folder
PYTHONPATH=. python3 -m pehli_salary.cli auth --client-secrets client_secret.json
```

A browser window opens. Sign in as the **channel owner**. Click Allow.

This writes `token.json` (gitignored). Open it and copy:

- `client_id`
- `client_secret`
- `refresh_token`

If Google says the app is in testing, confirm the account is under Test users (step 3).

### 5. Put secrets on GitHub (this is what actually automates posting)

Repo → **Settings → Secrets and variables → Actions → New repository secret**. Add exactly:

- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`

If you also use Cursor Cloud secrets with the same three names, add them there too so I can publish from an agent run. GitHub secrets are enough for the schedule.

### 6. Turn the schedule on

1. Repo → **Actions**. Enable workflows if GitHub is asking.
2. Open **Publish due Pehli Salary Club video** → **Run workflow**.
3. Leave date empty, set `dry_run` to `true` the first time. You should see a dry-run payload, not an upload.
4. Run again with `dry_run` = `false` and `date` = today’s IST date **only if** a row in `channel/queue.yaml` has `publish_on` equal to that date. Otherwise nothing uploads (by design).
5. After that, cron is:

   - Tue / Thu / Sat **19:30 IST** (Shorts)
   - Sunday **10:00 IST** (long-form)

   GitHub cron can drift by a few minutes. If it fires after the slot, the video goes **public immediately** instead of `publishAt` in the past.

### 7. First real upload, watch it like a stranger

1. Open the video in an incognito window on your phone.
2. If it still sounds like a newsreader, do step 8 before the next slot.
3. Pin a comment in your own words, e.g. `pehli salary kitni thi, in-hand, city ke saath likh`. Bots do not pin messy comments.
4. Reply to the first real comments yourself the same day. That is the highest-ROI “human” work, and it is not automatable without looking fake.

### 8. Optional but strongly recommended: your voice (15 minutes a week)

1. Phone Voice Memos, quiet room, sit a bit close to the mic.
2. Read `spoken:` from `channel/queue.yaml` for that id. Do not perform. If you stumble, keep it.
3. Export `channel/voiceovers/s001.mp3` (same id as the queue row).
4. Commit those mp3s (they are allowed through `.gitignore`). The Action will use them instead of TTS.

One sitting can cover a week (3 Shorts). That is how this stays automated **and** human.

### 9. What you never need to send me

- Your YouTube password.
- Bank / AdSense until YPP actually invites you.
- A face model, ElevenLabs clone of a celebrity, or someone else’s videos.

---

## After it is running: monetization, without looking like a mill

1. Do not change the cadence to 10 Shorts/day. That pattern is how YouTube spots spam now.
2. Once a week, add **one** script from a real comment. Human channels do that; content farms do not.
3. Apply to YPP when you hit the current thresholds (subs + long-form hours **or** Shorts views — check Studio; Google changes this).
4. Ads on. Affiliates only after that, and say so in the description.

## If something fails

| Symptom | Fix |
| --- | --- |
| Action dry-runs even with `dry_run=false` | `YOUTUBE_REFRESH_TOKEN` secret missing or empty |
| OAuth “access denied” | Channel Gmail not in Test users |
| `uploadScope` / 403 | API not enabled, or you authed a different Google account than the channel |
| Quota | Default is enough for 1–2 uploads/day; do not burst |
| Video looks empty / no audio | ffmpeg on the runner; already installed in the workflow |
| Token dies after ~7 days | Only happens if the OAuth app stays in Testing **and** Google rotates; re-run step 4 and update the secret. Publishing the app for production (only you using it) also works if you are willing to go through Google’s form. |

When steps 1–6 are done, reply with “secrets are in” and I can trigger a real upload for the next dated item.
