# Designplus Solutions — website

A Flask web app. Six public pages rendered from a database, plus a
login-protected admin where the content is managed.

The design is unchanged: the original HTML and CSS became Jinja templates, so
what visitors see is what the static site looked like — only now the copy,
projects, clients, services and SEO come from the database instead of being
typed into six separate files.

```
wsgi.py                     Entry point (gunicorn wsgi:app)
app/
  __init__.py               Application factory, CLI commands
  config.py                 Environment-driven settings
  models.py                 The whole data model
  seed.py                   Loads the starting content
  seed_data.json            That content, extracted from the old HTML
  extensions.py             db, login manager, CSRF
  public/                   The public site (routes, queries, enquiry mail)
  admin/                    Admin blueprint + the resource registry
  templates/                layout/, public/, admin/
  static/                   css/, js/, favicon, img/uploads/
tools/extract_legacy.py     One-off HTML -> seed_data.json extraction
legacy/                     The original static files, kept for reference
```

## Running it locally

You need Python 3.12 and a virtual environment. On Ubuntu the venv module is a
separate package:

```bash
sudo apt install -y python3-venv python3-pip
```

Then, from the project directory:

```bash
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
```

```bash
cp .env.example .env && python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"
```

Paste that key into `.env`, set `ADMIN_PASSWORD` to something you choose, then:

```bash
. .venv/bin/activate && flask --app wsgi init-db && flask --app wsgi seed
```

```bash
. .venv/bin/activate && flask --app wsgi run --debug
```

The site is at <http://localhost:5000> and the admin at
<http://localhost:5000/admin>. Sign in with the `ADMIN_EMAIL` and
`ADMIN_PASSWORD` from `.env`.

Locally the data lives in `instance/designplus.sqlite3`. Delete that file and
re-run `init-db` + `seed` to start over.

## What you can edit from the admin

| Section | Covers |
|---|---|
| **Enquiries** | Every contact form submission, with status, private notes and CSV export |
| **Projects** | The 12 portfolio cards — copy, category, ordering, photo uploads |
| **Case studies** | The three long write-ups, their figures, and which project links to each |
| **Portfolio categories** | The filter buttons. Counts are computed, never typed |
| **Services** | All seven — homepage summary, full introduction, tags, icon |
| **What's included** | The deliverable cards under each service |
| **Pricing tiers** | The three packages and their feature lists |
| **FAQs** | Question and answer, ordering, show/hide |
| **Clients / sectors** | The roster, which sector tab each falls under, the scrolling band |
| **Testimonials** | Quotes, attribution, which one the homepage shows |
| **Page SEO** | Search title, description, social card text and image, per page |
| **Headline figures** | 150+ / 80+ / 12+ / 7+ / 95% — edited once, updated everywhere |
| **Site settings** | Phone, email, WhatsApp, address, socials, opening hours |

Every content row has **Visible on the site** and arrows to reorder it.
Unchecking hides a row without deleting it.

### Still edited in the templates

Some copy is one-off prose rather than a repeating list, so it lives in the
templates rather than the database:

- The hero headline and paragraph on each page
- The About page's story, mission, vision, values and team
- The "Why Designplus" points on the homepage
- The process steps on the services page

These are in `app/templates/public/*.html`. If you would rather manage any of
them from the admin too, they follow the same pattern as the rest — say the
word.

## What happens when someone submits the contact form

1. The browser POSTs to the app. No JavaScript is involved, so it works even if
   scripts fail.
2. A hidden honeypot field catches simple bots; those submissions are dropped
   silently.
3. The enquiry is **written to the database first**, then a notification email
   is attempted. If the mail server is down the enquiry is still safely stored
   and waiting in the admin — the old static form had no such guarantee.
4. The visitor is redirected to a confirmation. It only ever appears after a
   real save.

Notification email is optional. Set `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`
and `NOTIFY_EMAIL` to switch it on. For Gmail, use an
[App Password](https://myaccount.google.com/apppasswords), not the account
password.

## Deploying to Render

1. Push this repository to GitHub.
2. In Render: **New → Blueprint**, point it at the repo. `render.yaml`
   provisions the web service, the Postgres database and a 1 GB disk for
   uploaded images.
3. Set the environment variables Render marks as required:
   - `SITE_URL` — the live origin, e.g. `https://designplussolutions.co.ke`
   - `ADMIN_EMAIL` and `ADMIN_PASSWORD` — the first admin account
4. Deploy. The pre-deploy step creates the tables and seeds the content.
5. Sign in at `/admin` and **change the password immediately** — the one you
   set as an environment variable is visible in the Render dashboard.

The `disk:` block matters. Without it, Render's filesystem is wiped on every
deploy and uploaded images disappear; the database rows would survive but point
at files that no longer exist.

### Changing the schema later

`flask init-db` creates missing tables but never alters existing ones.
Flask-Migrate is already installed for real changes:

```bash
. .venv/bin/activate && flask --app wsgi db init && flask --app wsgi db migrate -m "describe the change" && flask --app wsgi db upgrade
```

Then add `flask --app wsgi db upgrade` to the pre-deploy command in
`render.yaml`.

## URLs

Clean paths replace the old filenames: `/`, `/about`, `/services`,
`/portfolio`, `/clients`, `/contact`. The old `designplus-*.html` URLs 301 to
their new homes, so any existing links and search rankings carry over.
`/robots.txt` and `/sitemap.xml` are generated from the database, and pages
marked non-indexed are excluded from both.

## Before launch

The placeholders from the static site are now settings rows, and the admin
dashboard lists the ones still unfilled:

- **Phone and WhatsApp** — still `+254 700 000 000`
- **Street address** — still `Your Office Address, Building Name, Floor`
- **Social profile URLs** — inferred from the handles shown on the old page;
  confirm each one resolves, or clear it to hide that link
- **A privacy policy page** — the form collects personal data. The old dead
  "Privacy Policy" link was removed rather than left broken; add the page and
  link it from the form note
- **Real photography** — every project still uses the placeholder CSS artwork.
  Upload a photo to any project and it takes over automatically
- **A social share image** — set one per page under Page SEO; the cards fall
  back to plain text summaries until then

## Security notes

- Passwords are hashed with Werkzeug's PBKDF2; the database never stores one.
- Every form that changes something carries a CSRF token, enforced app-wide.
- The login form gives the same message for an unknown email and a wrong
  password, so it cannot be used to enumerate accounts.
- `/admin` is excluded from `robots.txt` and every admin page sends `noindex`.
- Uploads are restricted by extension and capped at 8 MB, and stored under a
  random prefix so two files with the same name cannot collide.
- Session cookies are `HttpOnly` and `SameSite=Lax`, and become `Secure`
  automatically once `SITE_URL` is https.
