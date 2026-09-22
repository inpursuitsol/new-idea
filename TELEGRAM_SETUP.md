# Telegram channel setup (Contentlovers108)

Channel: https://t.me/contentlovers108  
Bot: @pehlisalary_poster_bot

## One-time checklist

1. Bot is **administrator** on the channel with **Post messages** ON.
2. GitHub Actions secrets (repo → Settings → Secrets → Actions):
   - `TELEGRAM_BOT_TOKEN` — from @BotFather (never commit this)
   - `TELEGRAM_CHANNEL_ID` — `@contentlovers108`
3. Enable **Actions** on the repo.

## What posts automatically

| Type | When | Source |
| --- | --- | --- |
| 💰 TIP | Tue / Thu / Sat **11:11 IST** (cron runs daily; Python skips other days) | `channel/queue.yaml` shorts |
| 📢 JOB | Every 6 hours (new items only, max 1 per run) | `channel/telegram_sources.yaml` RSS |

Posted job/tip IDs are stored in `channel/telegram_posted.json` (committed to git after each run) so the same alert is not reposted.

Posts are free. Job links use an aggregator feed — each post says to verify on the official site.

## Manual commands

```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_CHANNEL_ID=@contentlovers108
export PYTHONPATH=.

# Preview without posting
python -m pehli_salary.cli telegram post-tip --id s001 --dry-run

# Post one tip now
python -m pehli_salary.cli telegram post-tip --id s001

# Tip (if Tue/Thu/Sat) + poll jobs
python -m pehli_salary.cli telegram post-due
```

## GitHub Action

Workflow: `.github/workflows/telegram.yml`

Run manually: Actions → **Telegram channel posts** → Run workflow → set `dry_run` to `true` first.
