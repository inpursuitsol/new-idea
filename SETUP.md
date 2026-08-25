# What you need to do (once) so posting runs without me

I cannot log into Google or YouTube as you. After the steps below, GitHub Actions renders the next video and uploads it on the IST calendar by itself.

Fully automated **and** “this is clearly a real person on camera” is not the same job. Camera + your voice is the most human. If you skip the camera, use **your voice notes** in `channel/voiceovers/` (step 8). Neural TTS is the fallback; it is better than Google’s old gTTS, still not your throat.

Do **not** buy views, comments, or subscribers. That bans the channel before ads.

---

## What I need from you (checklist)

| # | You give me / set this | Why |
| --- | --- | --- |
| 1 | A Google account you control | Owns the Cloud project and the channel |
| 2 | YouTube channel **@Contentlovers108** (already created) | Place videos go. Do not open a second channel. |
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

### 1. Use the channel you already have — @Contentlovers108

Do **not** create a new channel and do **not** switch Google accounts.

1. Open [youtube.com/@Contentlovers108](https://www.youtube.com/@Contentlovers108) while signed into the Google account that owns it (Studio currently shows the channel as **Anand** — that is fine).
2. Confirm Studio → your photo → you can upload. That same login is what OAuth in step 4 must use. If you have several channels on the account, pick **Contentlovers108** in the channel switcher before you allow access.
3. Keep the handle `@Contentlovers108`. You do not need `@pehlisalary`.
4. Optional, later: change the **display name** from Anand to something clearer (`Contentlovers108` or `Pehli Salary Club`). Handle can stay. Skip this if you do not care.
5. Do **not** add a face clone, a stock “Indian businessman” AI avatar, or someone else’s photos.

### 2. YouTube Studio, 15 minutes, so it does not look like a bot farm

You land on **Dashboard** (house icon, currently selected). Name, description, icon, and banner are **not** on those cards. Use the **left sidebar**.

**A. Look and About (Customization)**

1. Left sidebar, near the bottom, wand / sparkle icon: **Customization**.
2. Open the **Profile** tab (sometimes labelled **Branding**).
   - **Picture** = channel icon. Phone photo of a notebook. Not a Canva finance logo.
   - **Banner image** = 2560×1440 desk photo. No neon AI gradient.
3. Open the **Basic info** tab.
   - **Name**: leave **Anand**. Do not create a second channel for “Pehli Salary Club”.
   - **Handle**: keep `@Contentlovers108` if that is already set.
   - **Description**: paste or merge:

     > Pehli naukri, pehle 5 saal. CTC vs in-hand, PF, HRA, UPI leaks, ghar ka UPI. Main CA nahi hoon. Jo maine khud seekha, wahi. Tumhara number alag ho sakta hai.

   - **Links**: none, or only LinkedIn if it is really you.
4. Click **Publish** at the top right if Studio asks.

**B. Kids flag, country, language (Settings gear)**

1. Left sidebar, **very bottom**: gear **Settings**. A pop-up opens. This is not Customization.
2. Left of the pop-up: **Channel** → **Basic info** → **Country**: India.
3. Same pop-up: **Channel** → **Advanced settings** → audience / made for kids: this channel is **not** made for kids.
4. Same pop-up: **Upload defaults** → **Audience**: **No, it's not made for kids**.
5. **Upload defaults** → title/description language: Hindi or English is fine (Hinglish videos still work).
6. Save / Done.

Dashboard cards (Latest video, 0 views, Partner Program news) can be ignored for this step.

### 3. Google Cloud project + YouTube API

1. Open [Google Cloud Console](https://console.cloud.google.com/) with the **same** Google account that owns the channel.
2. **New project**, name `contentlovers108-uploader` (any name; this is the API project, not the YouTube title).
3. **APIs & Services → Enable APIs** → enable **YouTube Data API v3**.
4. **OAuth consent screen**:
   - User type: **External**.
   - App name: `Contentlovers108 Uploader`.
   - User support email: yours.
   - Developer contact: yours.
   - Scopes: add `https://www.googleapis.com/auth/youtube.upload`.
   - **Test users**: add the Gmail that owns the YouTube channel. Until Google verifies the app, **only test users** can auth. For a one-person channel, stay in Testing forever. That is normal.
5. **Credentials → Create credentials → OAuth client ID**:
   - Application type: **Desktop app**.
   - Download JSON. Save it locally as `client_secret.json`. Never commit it. It is already gitignored.

### 4. Generate the refresh token on the Chromebook (once)

You only have a Chromebook. That is enough. Do **not** wait for a Windows/Mac PC.

Google login must happen in a browser that can reach Linux `localhost`. Chrome OS Chrome usually cannot. Install **Chromium inside Penguin**, then run `auth` there. Linux GUI apps open as normal Chromebook windows.

**A. One-time Penguin packages**

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv git chromium ffmpeg fonts-noto-core
```

If `chromium` is not found, try `chromium-browser` or `firefox-esr`. You need any GUI browser **inside Linux**, not the Chromebook’s top-of-screen Chrome.

**B. Put the OAuth JSON where Linux can see it**

In Chrome OS Files, download `client_secret.json` into **Downloads**. Penguin sees that as:

`/mnt/chromeos/MyFiles/Downloads/client_secret.json`

**C. Use a new folder.** Your existing `~/new-idea` has other files (Nifty CSVs, PHP). Do not switch branches there. Leave that folder alone.

Do these **one at a time**. After each, you should see something like the “You should see” line. If you do not, stop and paste that terminal text back.

**Step 1 — tools**

```bash
sudo apt update
sudo apt install -y python3-venv python3-full git chromium
```

You should see lots of “Get:” / “Unpacking” lines, then the prompt again. If `chromium` fails, run: `sudo apt install -y firefox-esr`

**Step 2 — new empty folder (not ~/new-idea)**

```bash
cd ~
git clone -b cursor/pehli-salary-youtube-bbab https://github.com/inpursuitsol/new-idea.git youtube-uploader
cd youtube-uploader
ls
```

You should see `SETUP.md`, `requirements.txt`, `pehli_salary`. You should **not** see `admin-applications.php` or `scans/`.

**Step 3 — free space, then a small install**

Linux on a Chromebook is tiny. A full `requirements.txt` install can fill the disk (`No space left on device`). Login only needs two Google packages.

```bash
cd ~
rm -rf ~/youtube-uploader/.venv
rm -rf ~/.cache/pip
sudo apt-get clean
sudo apt-get autoremove -y
df -h ~
```

`Avail` (or “Available”) for `/home` should be more than about **500M**. If it is still almost 0:

Chromebook **Settings → Advanced → Developers → Linux → Change disk size** — make it bigger (8 GB or more) → restart Linux → open Penguin again.

Then:

```bash
cd ~/youtube-uploader
git fetch origin
git checkout -B cursor/pehli-salary-youtube-bbab origin/cursor/pehli-salary-youtube-bbab
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-auth.txt
```

The prompt should show `(.venv)`. This install is small. Do **not** run `pip install -r requirements.txt` on the Chromebook.

**Step 4 — Google JSON into Linux**

Chrome OS **Files** app (the folder icon, not the terminal):

1. Find the file you downloaded from Google Cloud. Name starts with `client_secret_` and ends with `.json`.
2. Right-click it → **Move to Linux files** (or drag it onto **Linux files** in the left column).
3. If you do not see **Linux files**, turn on Linux: Settings → Advanced → Developers → Linux.

Back in the **same** terminal (prompt still has `(.venv)`):

```bash
cd ~/youtube-uploader
ls ~
find ~ -name '*client_secret*' 2>/dev/null
```

You should see a path printed. Copy that file in:

```bash
cp ~/client_secret_*.json ~/youtube-uploader/client_secret.json
```

If `cp` says “cannot stat”, the JSON is in a subfolder. Run `find ~ -name '*client_secret*'` and use **that full path**:

```bash
cp "/the/full/path/from/find.json" ~/youtube-uploader/client_secret.json
```

**Step 5 — Google login**

```bash
cd ~/youtube-uploader
source .venv/bin/activate
export PYTHONPATH=.
python -m pehli_salary.cli auth --client-secrets client_secret.json --port 8080
```

A Linux browser window should open. Sign in as **@Contentlovers108**. Click Allow.

You should see: `Wrote .../token.json`

**Step 6 — print the three secrets** (venv still on)

```bash
cd ~/youtube-uploader
source .venv/bin/activate
python - <<'PY'
import json
from pathlib import Path
data = json.loads(Path("token.json").read_text())
print("YOUTUBE_CLIENT_ID=", data["client_id"])
print("YOUTUBE_CLIENT_SECRET=", data["client_secret"])
print("YOUTUBE_REFRESH_TOKEN=", data["refresh_token"])
PY
```

Put those three lines into GitHub → Settings → Secrets → Actions (step 5 below).

Never run `git checkout` inside the old `~/new-idea` folder. That is a different project.

**If no browser window opens:** the terminal still prints a `https://accounts.google.com/...` link. In Penguin type `chromium` (or `firefox-esr`) so a Linux window appears, then paste that link **into that window**, not into Chrome OS Chrome.

**If there is no Linux browser:** Chromebook Settings → Advanced → Developers → Linux → Port forwarding → TCP **8080**, then from `~/youtube-uploader` with venv on:

```bash
python -m pehli_salary.cli auth --client-secrets client_secret.json --port 8080 --no-browser
```

Paste the printed URL into Chrome OS Chrome. After Allow it must open `http://127.0.0.1:8080`.

You only need this login once. After secrets are on GitHub, daily posting does not use Penguin at all.

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
| `uploadScope` / 403 | API not enabled, or you authed a different Google account / a different channel than **@Contentlovers108** |
| Quota | Default is enough for 1–2 uploads/day; do not burst |
| Video looks empty / no audio | ffmpeg on the runner; already installed in the workflow |
| Token dies after ~7 days | Only happens if the OAuth app stays in Testing **and** Google rotates; re-run step 4 and update the secret. Publishing the app for production (only you using it) also works if you are willing to go through Google’s form. |

When steps 1–6 are done, reply with “secrets are in” and I can trigger a real upload for the next dated item.
