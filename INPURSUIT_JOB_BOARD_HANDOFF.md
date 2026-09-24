# InPursuit job board — handoff for the next GitHub repo

Copy this file into the new repository. Read it before writing code.

## Product

Build **InPursuit** (`https://inpursuit.co.in`) into a real job marketplace for India: candidates find a role and apply on the site; employers post a role and receive CVs. The bar is Instahyre / Naukri, not a Telegram channel.

Owner: Anand Rao (`anandnageshrao@gmail.com`). Site is WordPress on Hostinger (LiteSpeed, PHP 8.3). Custom post type `job`, REST at `https://inpursuit.co.in/wp-json/wp/v2/job`. Apply lives on each job page (`multipart/form-data`). Candidate URL: `/profile/`. Employer URL: `/for-employers/`. Jobs hub: `/jobs/`.

This old repo (`inpursuitsol/new-idea`) is a YouTube/Telegram content bot (Pehli Salary Club / Contentlovers108). **Do not keep growing the job board from that bot.** Use a new repo whose source of truth is the WordPress site (theme, plugin, or a headless app that talks to WP).

## End goal (what “done” means)

1. A person searching Google for `{role} jobs {city}` can land on an InPursuit page and apply.
2. A candidate can save one profile (CV + skills + city) and reuse it.
3. An employer can post a job without Anand typing it in wp-admin.
4. Inventory grows every week (real openings, not scraped FreeJobAlert posts).
5. Google for Jobs can list each opening (valid `JobPosting` JSON-LD, real salary or no LPA in the title, `validThrough` in the future).

Telegram `@contentlovers108` has **no followers**. It is not a growth channel. Do not spend time posting jobs there.

## What already exists on the live site

Homepage copy already says “Search jobs. Apply on this site.” with Latest openings, Create your profile, Build your team.

As of 23 Sep 2026 there were **11 published jobs**. Public sitemap: `https://inpursuit.co.in/jobs-sitemap.xml` and `https://inpursuit.co.in/wp-sitemap-posts-job-1.xml`. `robots.txt` already points at both.

Known listing problems (still true until the mu-plugin is on Hostinger, and some stay even after):

- `/jobs/` has no canonical URL and no ItemList / CollectionPage JSON-LD.
- JobPosting titles contain HTML entities (`&#8211;`).
- Four titles claim 35–50 LPA with no `baseSalary` (Google will treat that as misleading).
- `HR Executive` (id 61) has **empty** post content. The plugin cannot invent a JD.
- `Python Django Developer` description is very short.
- Typo in slug: `react-front-end-developer-hyderbad-40-lpa`.

Two roles were already posted to Telegram (ignore for growth): job ids **75** and **71**.

## What already exists in `inpursuitsol/new-idea`

Merged to `main` (PR 14, later commits through `d004e16`):

| Path | Why it matters |
| --- | --- |
| `site/mu-plugins/inpursuit-jobs-discovery.php` | Must be uploaded to `wp-content/mu-plugins/` on Hostinger. Adds hub canonical + ItemList; decodes JobPosting titles; fills `baseSalary` from “N LPA” in the title; pads short descriptions. |
| `site/f3c8e1a94b6d4027c5e8a1d09b7f6c2e.txt` | IndexNow key. Must live at `https://inpursuit.co.in/f3c8e1a94b6d4027c5e8a1d09b7f6c2e.txt`. Still **404**. |
| `pehli_salary/site_jobs.py` | Live audit of hub + JobPosting pages (`python -m pehli_salary.cli jobs audit`). |
| `pehli_salary/jobs_promote.py` | Telegram + IndexNow. Do not treat as the product. |
| `.github/workflows/jobs-growth.yml` | Daily 10:00 IST audit/promote; FTP deploy **only if** `HOSTINGER_FTP_*` secrets exist. They do not. |
| `JOBS_GROWTH.md` | Setup notes for that workflow. |

`pytest` in that repo: 35 passed.

## What the last agent could not do (no logins)

No Hostinger FTP/SSH, no WordPress application password, no Google Search Console. GitHub had Telegram secrets (posts went out) but empty `HOSTINGER_FTP_HOST` / `USERNAME` / `PASSWORD` and empty `GOOGLE_INDEXING_SA_JSON`.

FTP port 21 on `inpursuit.co.in` is open. That is enough to upload the two files **once those secrets or a WP/SSH login exist in the new environment**.

## What to build in the new GitHub (in order)

### 0. Access in the new environment

Put these in GitHub Actions / Cursor secrets so the agent can finish without asking again:

- `HOSTINGER_FTP_HOST`, `HOSTINGER_FTP_USERNAME`, `HOSTINGER_FTP_PASSWORD` (or SSH)
- WordPress application password (`WORDPRESS_USER`, `WORDPRESS_APP_PASSWORD`) for REST writes
- Optional: Google Search Console / Indexing API JSON

Then upload the two files from `new-idea` (`inpursuit-jobs-discovery.php` and the IndexNow `.txt`). Verify:

- `https://inpursuit.co.in/f3c8e1a94b6d4027c5e8a1d09b7f6c2e.txt` returns the key
- View-source of `/jobs/` has `rel=canonical` and CollectionPage/ItemList JSON-LD
- A role with “50 LPA” in the title has `baseSalary` in JobPosting

Fix or unpublish **HR Executive** (empty body). Remove LPA from titles unless the salary is real and in schema.

### 1. Search inventory (this is how Naukri-scale starts)

Do not only improve `/jobs/`. Generate indexable pages for queries people already type:

- `/jobs/{city}/` e.g. Hyderabad, Bangalore
- `/jobs/{role-slug}/` e.g. python-developer, accountant
- `/jobs/{role-slug}/{city}/`

Each page needs unique title, unique copy, a list of matching live jobs, canonical, ItemList, and no thin doorway spam. One real job can appear on several of these pages.

Submit `https://inpursuit.co.in/wp-sitemap.xml` and `https://inpursuit.co.in/jobs-sitemap.xml` in Search Console after verify.

### 2. Candidate graph (Instahyre’s actual product)

`/profile/` should store: name, email, phone, city, role, years, skills, CV file. After apply, reuse that profile on the next job. One row in the database per person, not a loose PDF per form submit.

### 3. Employer supply

`/for-employers/` must create a `job` post (title, city, employment type, salary optional, JD, `validThrough`) and email CVs to that employer. Without this, the board cannot pass a few dozen hand-typed roles.

Never scrape Naukri/LinkedIn or buy CV dumps. Never invent 50 LPA.

### 4. Distribution after pages exist

Google for Jobs via correct `JobPosting` schema is the main channel. Then: college placement cells, WhatsApp groups, and only later paid. Do not buy traffic or fake CVs.

## Copy these files into the new repo

From `https://github.com/inpursuitsol/new-idea` (`main`):

- `site/mu-plugins/inpursuit-jobs-discovery.php`
- `site/f3c8e1a94b6d4027c5e8a1d09b7f6c2e.txt`
- `pehli_salary/site_jobs.py` (audit logic; rewrite to drop Telegram)
- this file

Leave behind: YouTube renderer, Telegram RSS from FreeJobAlert, Pehli Salary queue.

## First prompt to paste in the new repo

> Complete the InPursuit job board on inpursuit.co.in. Goal: candidates apply on-site and employers post on-site, ranked in Google like a small Instahyre/Naukri — not Telegram. Read INPURSUIT_JOB_BOARD_HANDOFF.md. First: upload the mu-plugin and IndexNow key using Hostinger/WordPress secrets; confirm /jobs/ has canonical + ItemList and LPA jobs have baseSalary. Then ship city/role archive pages, a reusable candidate profile, and employer job posting. Do not post to Telegram. Do not scrape other boards.

## Success checks

- `/jobs/` and at least one `{role} in {city}` URL return 200 with unique titles.
- JobPosting JSON-LD on a live role has decoded title, `datePosted`, `hiringOrganization`, `jobLocation` IN, future `validThrough`, and `baseSalary` if pay is advertised.
- A test apply creates a stored profile (not only an email).
- A test employer post creates a public `job` URL in the sitemap.
- Search Console property verified; sitemaps submitted. IndexNow key URL 200.
