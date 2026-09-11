"""Load the site's starting content into the database.

Run once after the first deploy:  flask seed
Re-runnable: existing rows are matched on their natural key and updated, so
seeding twice will not duplicate content. `--force` wipes content first.
"""
import json
from pathlib import Path

import click
from flask import current_app

from .extensions import db
from .models import (AdminUser, CaseStudy, CaseStudyResult, Category, Client,
                     Deliverable, Enquiry, Faq, Package, Page, Project, Sector,
                     Service, Setting, Stat, Testimonial)

DATA_FILE = Path(__file__).resolve().parent / 'seed_data.json'


# ── Settings ────────────────────────────────────────────────────────────────
# `value` is the current placeholder; the admin Settings screen is where these
# get their real values. Anything marked TODO still needs replacing.

SETTINGS = [
    # key, label, value, kind, group, help
    ('company_name', 'Company name', 'Designplus Solutions', 'text', 'Identity', ''),
    ('tagline', 'Tagline', 'Your brand, built right.', 'text', 'Identity', ''),
    ('footer_blurb', 'Footer description',
     'Your brand, built right. Full-service creative and digital solutions for businesses across Kenya.',
     'textarea', 'Identity', ''),

    ('email', 'Email address', 'info@designplussolutions.co.ke', 'email', 'Contact', ''),
    ('phone', 'Phone number', '+254 700 000 000', 'tel', 'Contact',
     'TODO — still the placeholder. Shown as typed; the tel: and WhatsApp links strip the spaces automatically.'),
    ('whatsapp', 'WhatsApp number', '+254 700 000 000', 'tel', 'Contact',
     'TODO — leave blank to hide every WhatsApp button on the site.'),
    ('address', 'Street address', 'Your Office Address, Building Name, Floor', 'textarea', 'Contact',
     'TODO — still the placeholder.'),
    ('city', 'City', 'Nairobi, Kenya', 'text', 'Contact', ''),
    ('map_query', 'Google Maps search', 'Designplus Solutions Nairobi Kenya', 'text', 'Contact',
     'What the "Get directions" button searches for.'),

    ('facebook_url', 'Facebook', 'https://www.facebook.com/designplussolutions', 'url', 'Social',
     'Leave blank to hide this link.'),
    ('facebook_handle', 'Facebook handle', '@designplussolutions', 'text', 'Social', ''),
    ('instagram_url', 'Instagram', 'https://www.instagram.com/designplussolutions', 'url', 'Social', ''),
    ('instagram_handle', 'Instagram handle', '@designplussolutions', 'text', 'Social', ''),
    ('linkedin_url', 'LinkedIn', 'https://www.linkedin.com/company/designplussolutions', 'url', 'Social', ''),
    ('linkedin_handle', 'LinkedIn name', 'Designplus Solutions', 'text', 'Social', ''),
    ('x_url', 'X (Twitter)', 'https://x.com/designplussol', 'url', 'Social', ''),
    ('x_handle', 'X handle', '@designplussol', 'text', 'Social', ''),

    ('hours_weekday', 'Monday–Thursday', '8:00 AM – 6:00 PM', 'text', 'Office hours', ''),
    ('hours_friday', 'Friday', '8:00 AM – 5:00 PM', 'text', 'Office hours', ''),
    ('hours_saturday', 'Saturday', '9:00 AM – 1:00 PM', 'text', 'Office hours', ''),
    ('hours_sunday', 'Sunday', 'Closed', 'text', 'Office hours', ''),

    ('response_promise', 'Response promise', 'We typically respond within 2–4 hours during business hours',
     'text', 'Contact page', ''),
]

STATS = [
    ('projects_delivered', '150', '+', 'Projects delivered', 1),
    ('happy_clients', '80', '+', 'Happy clients', 2),
    ('industries_served', '12', '+', 'Industries served', 3),
    ('years_in_business', '7', '+', 'Years in business', 4),
    ('client_retention', '95', '%', 'Client retention rate', 5),
]


def _load():
    return json.loads(DATA_FILE.read_text())


def _upsert(model, match: dict, **fields):
    """Find by natural key or create, then apply fields. Returns the row."""
    row = db.session.scalar(db.select(model).filter_by(**match))
    if row is None:
        row = model(**match)
        db.session.add(row)
    for key, value in fields.items():
        setattr(row, key, value)
    return row


def seed_everything(force: bool = False) -> None:
    data = _load()

    if force:
        click.echo('Wiping existing content (enquiries and admin users are kept)…')
        for model in (CaseStudyResult, CaseStudy, Project, Category, Deliverable,
                      Service, Package, Faq, Client, Sector, Testimonial, Stat,
                      Setting, Page):
            db.session.query(model).delete()
        db.session.commit()

    _seed_admin()
    _seed_settings()
    _seed_pages(data['pages'])
    _seed_services(data['services'])
    _seed_packages(data['packages'])
    _seed_faqs(data['faqs'])
    _seed_portfolio(data['categories'], data['projects'], data['case_studies'])
    _seed_clients(data['sectors'], data['clients'], data['marquee'])
    _seed_testimonials(data['testimonials'])

    db.session.commit()
    click.echo('\nSeed complete.')
    _report()


def _seed_admin():
    if db.session.scalar(db.select(AdminUser).limit(1)):
        return
    email = current_app.config['ADMIN_EMAIL']
    password = current_app.config['ADMIN_PASSWORD']
    if not password:
        click.echo('  ! ADMIN_PASSWORD is not set — skipping admin creation.')
        click.echo('    Set it in .env, or run: flask create-admin <email> <password>')
        return
    user = AdminUser(email=email, name='Designplus Admin')
    user.set_password(password)
    db.session.add(user)
    click.echo(f'  + admin user {email}')


def _seed_settings():
    for position, (key, label, value, kind, group, help_text) in enumerate(SETTINGS):
        existing = db.session.scalar(db.select(Setting).filter_by(key=key))
        # Never clobber a value the client has already edited.
        _upsert(Setting, {'key': key},
                label=label, kind=kind, group=group,
                help_text=help_text, position=position,
                value=existing.value if existing else value)

    for key, value, suffix, label, position in STATS:
        existing = db.session.scalar(db.select(Stat).filter_by(key=key))
        _upsert(Stat, {'key': key}, label=label, position=position,
                value=existing.value if existing else value,
                suffix=existing.suffix if existing else suffix)


def _seed_pages(pages):
    for item in pages:
        _upsert(Page, {'slug': item['slug']},
                nav_label=item['nav_label'],
                title=item['title'],
                meta_description=item['meta_description'],
                position=item['position'])


def _seed_services(services):
    for item in services:
        service = _upsert(
            Service, {'slug': item['slug']},
            title=item['title'],
            short_title=item.get('short_title', ''),
            summary=item.get('summary', ''),
            intro=item['intro'],
            tags='\n'.join(item['tags']),
            icon_svg=item['icon_svg'],
            why_title=item['why_title'],
            why_points='\n'.join(item['why_points']),
            position=item['position'])
        db.session.flush()

        service.deliverables.clear()
        for position, d in enumerate(item['deliverables'], start=1):
            service.deliverables.append(
                Deliverable(title=d['title'], description=d['description'], position=position))


def _seed_packages(packages):
    for item in packages:
        _upsert(Package, {'title': item['title']},
                tier_label=item['tier_label'],
                subtitle=item['subtitle'],
                features='\n'.join(item['features']),
                is_highlighted=item['is_highlighted'],
                position=item['position'])


def _seed_faqs(faqs):
    for item in faqs:
        _upsert(Faq, {'question': item['question']},
                answer=item['answer'], position=item['position'])


def _seed_portfolio(categories, projects, case_studies):
    for item in categories:
        _upsert(Category, {'slug': item['slug']},
                label=item['label'], position=item['position'])
    db.session.flush()

    by_slug = {c.slug: c for c in db.session.scalars(db.select(Category)).all()}

    for item in projects:
        _upsert(Project, {'title': item['title']},
                client_name=item['client_name'],
                location=item['location'],
                service_tag=item['service_tag'],
                result=item['result'],
                category=by_slug.get(item['category']),
                visual_class=item['visual_class'],
                visual_html=item.get('visual_html', ''),
                is_featured=item['is_featured'],
                position=item['position'])
    db.session.flush()

    projects_by_title = {p.title: p for p in db.session.scalars(db.select(Project)).all()}

    # Link each case study back to the project card that shares its client.
    for item in case_studies:
        study = _upsert(CaseStudy, {'anchor': item['anchor']},
                        tag=item['tag'],
                        title=item['title'],
                        client_line=item['client_line'],
                        challenge=item['challenge'],
                        approach=item['approach'],
                        headline_number=item['headline_number'],
                        headline_suffix=item['headline_suffix'],
                        headline_label=item['headline_label'],
                        visual_class=item['visual_class'],
                        is_reversed=item['is_reversed'],
                        position=item['position'])
        client = item['client_line'].split('—')[0].strip()
        study.project = next(
            (p for title, p in projects_by_title.items() if title.startswith(client.split()[0])),
            None)
        db.session.flush()

        study.results.clear()
        for position, r in enumerate(item['results'], start=1):
            study.results.append(CaseStudyResult(
                number=r['number'], suffix=r['suffix'], label=r['label'], position=position))


def _seed_clients(sectors, clients, marquee):
    for item in sectors:
        _upsert(Sector, {'slug': item['slug']},
                label=item['label'], position=item['position'])
    db.session.flush()

    by_slug = {s.slug: s for s in db.session.scalars(db.select(Sector)).all()}
    marquee_names = {m.lower() for m in marquee}

    for item in clients:
        # Marquee uses short display names ("Savanna Foods" for "Savanna Foods Ltd").
        in_marquee = any(item['name'].lower().startswith(m) for m in marquee_names)
        _upsert(Client, {'name': item['name']},
                industry=item['industry'],
                services=item['services'],
                sector=by_slug.get(item['sector']),
                show_in_marquee=in_marquee,
                position=item['position'])


def _seed_testimonials(testimonials):
    for item in testimonials:
        _upsert(Testimonial, {'author': item['author'], 'company': item['company']},
                quote=item['quote'],
                role=item['role'],
                rating=item['rating'],
                is_featured=item['is_featured'],
                # The homepage shows one quote; use the featured one.
                show_on_homepage=item['is_featured'],
                position=item['position'])


def _report():
    counts = [
        ('pages', Page), ('services', Service), ('deliverables', Deliverable),
        ('packages', Package), ('faqs', Faq), ('categories', Category),
        ('projects', Project), ('case studies', CaseStudy), ('sectors', Sector),
        ('clients', Client), ('testimonials', Testimonial), ('stats', Stat),
        ('settings', Setting), ('enquiries', Enquiry), ('admin users', AdminUser),
    ]
    for label, model in counts:
        click.echo(f'  {label:15} {db.session.query(model).count()}')
