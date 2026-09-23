# InPursuit jobs growth

Gets [inpursuit.co.in/jobs](https://inpursuit.co.in/jobs/) into the places that already send this channel traffic, and tells search engines when a role is new or updated.

This does not buy visits or post the same role on a loop. Each new role is posted once. A short list of open roles goes out on Monday and Thursday. Search pings run only when a role's modified time changes.

## One-time on the WordPress site

1. Upload `site/mu-plugins/inpursuit-jobs-discovery.php` to `wp-content/mu-plugins/` on Hostinger (create the folder if it is missing). It adds a canonical URL and an ItemList on `/jobs/`, and cleans HTML entities inside each role's JobPosting title.
2. Upload `site/f3c8e1a94b6d4027c5e8a1d09b7f6c2e.txt` to the site root so it is available at `https://inpursuit.co.in/f3c8e1a94b6d4027c5e8a1d09b7f6c2e.txt`. IndexNow rejects pings until that file is live.
3. Or add GitHub Actions secrets `HOSTINGER_FTP_HOST`, `HOSTINGER_FTP_USERNAME`, and `HOSTINGER_FTP_PASSWORD`. The jobs-growth workflow will copy both files over FTP.
4. In Google Search Console, confirm `inpursuit.co.in` is verified. Optional: add a service account as an owner and store its JSON in the GitHub secret `GOOGLE_INDEXING_SA_JSON`. Without that secret, Google pings are skipped and IndexNow still runs.

## What runs automatically

Workflow: `.github/workflows/jobs-growth.yml` at 10:00 IST.

| Step | What it does |
| --- | --- |
| Audit | Fetches `/jobs/` and each role. Prints missing canonical, ItemList, JobPosting fields, expired `validThrough`, HTML entities in titles, and salary claims with no `baseSalary`. |
| Promote | Posts up to 2 new roles to the Telegram channel with links to the role and to `/jobs/`. |
| Digest | Monday and Thursday, one message listing open roles, all linking to the site. |
| IndexNow | Pings changed role URLs plus the hub after the key file is on the site. |

State is `channel/jobs_promoted.json`. The workflow commits it so a role is not posted twice.

Uses the same Telegram secrets as [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md).

## Manual commands

```bash
pip install -r requirements.txt
export PYTHONPATH=.
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_CHANNEL_ID=@contentlovers108

python -m pehli_salary.cli jobs audit
python -m pehli_salary.cli jobs promote --dry-run
python -m pehli_salary.cli jobs promote --limit 1
```

Titles that say "50 LPA" without a `baseSalary` field stay a warning. Put the real pay into the JobPosting schema on the site, or take the number out of the title. Google drops listings it reads as misleading.
