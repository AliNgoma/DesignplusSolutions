"""Declarative description of everything the admin can edit.

One registry drives the list, create, edit, delete and reorder views, so every
content type behaves the same way and adding a new one is a few lines here
rather than a new blueprint.
"""
from dataclasses import dataclass, field as dc_field
from typing import Any, Callable

from ..extensions import db
from ..models import (CaseStudy, CaseStudyResult, Category, Client, Deliverable,
                      Faq, Package, Page, Project, Sector, Service, Stat,
                      Testimonial)


@dataclass
class Field:
    name: str
    label: str
    kind: str = 'text'          # text|textarea|code|number|bool|select|image|email|url|tel
    help: str = ''
    required: bool = False
    choices: Callable[[], list] | None = None   # -> [(value, label), …]
    placeholder: str = ''
    rows: int = 4
    # Fields marked advanced are collapsed behind a disclosure in the form.
    advanced: bool = False


@dataclass
class Resource:
    key: str                    # URL segment
    model: Any
    title: str                  # plural, for nav and list heading
    singular: str
    fields: list[Field]
    columns: list[tuple[str, str]]           # (attribute, heading)
    group: str = 'Content'
    order_by: str = 'position'
    can_create: bool = True
    can_delete: bool = True
    sortable: bool = True
    blurb: str = ''
    parent: str | None = None   # attribute holding the parent relation, if any

    def query(self):
        order = getattr(self.model, self.order_by, None)
        stmt = db.select(self.model)
        if order is not None:
            stmt = stmt.order_by(order)
        return db.session.scalars(stmt).all()


# ── Choice helpers ──────────────────────────────────────────────────────────

def _options(model, label_attr='__str__', blank='— none —'):
    def loader():
        rows = db.session.scalars(
            db.select(model).order_by(getattr(model, 'position', model.id))).all()
        items = [('', blank)] if blank is not None else []
        for row in rows:
            label = str(row) if label_attr == '__str__' else getattr(row, label_attr)
            items.append((str(row.id), label))
        return items
    return loader


PUBLISHED = Field('is_published', 'Visible on the site', 'bool',
                  help='Uncheck to hide without deleting.')
POSITION = Field('position', 'Order', 'number',
                 help='Lower numbers appear first.', advanced=True)


RESOURCES: list[Resource] = [
    # ── Portfolio ───────────────────────────────────────────────────────────
    Resource(
        key='projects', model=Project, title='Projects', singular='Project',
        group='Portfolio',
        blurb='The cards on the portfolio grid. A project with a case study links to it.',
        columns=[('title', 'Project'), ('client_name', 'Client'),
                 ('category', 'Category'), ('is_published', 'Live')],
        fields=[
            Field('title', 'Project title', required=True,
                  placeholder='Horizon Logistics — Full brand overhaul'),
            Field('client_name', 'Client name', placeholder='Horizon Logistics Ltd'),
            Field('location', 'Location', placeholder='Nairobi, Kenya'),
            Field('service_tag', 'Service label', placeholder='Brand Identity',
                  help='The small tag shown above the project name.'),
            Field('result', 'Result', 'textarea', rows=3,
                  help='The one-line outcome shown on the card.'),
            Field('category_id', 'Category', 'select', choices=_options(Category)),
            Field('image', 'Photo', 'image',
                  help='Replaces the placeholder artwork. JPG, PNG or WebP, up to 8 MB.'),
            Field('image_alt', 'Photo description', help='For screen readers and SEO.'),
            Field('is_featured', 'Wide card', 'bool',
                  help='Spans two columns on the grid.'),
            PUBLISHED, POSITION,
            Field('visual_class', 'Placeholder artwork class', 'text', advanced=True,
                  help='CSS class for the built-in artwork, used when no photo is set.'),
            Field('visual_html', 'Placeholder artwork markup', 'code', advanced=True, rows=3),
        ]),

    Resource(
        key='case-studies', model=CaseStudy, title='Case studies', singular='Case study',
        group='Portfolio',
        blurb='The long-form write-ups below the portfolio grid.',
        columns=[('title', 'Case study'), ('client_line', 'Client'), ('is_published', 'Live')],
        fields=[
            Field('title', 'Headline', required=True,
                  placeholder='How Horizon Logistics went from invisible to unmistakable'),
            Field('anchor', 'Link anchor', required=True,
                  help='Used in the page URL, e.g. case-horizon. Lower case, no spaces.'),
            Field('project_id', 'Linked project', 'select', choices=_options(Project),
                  help='The portfolio card that links here.'),
            Field('tag', 'Services line', placeholder='Brand Identity · Signage · Web'),
            Field('client_line', 'Client and location',
                  placeholder='Horizon Logistics Ltd — Nairobi, Kenya'),
            Field('challenge', 'The challenge', 'textarea', rows=5),
            Field('approach', 'Our approach', 'textarea', rows=5),
            Field('headline_number', 'Headline figure', placeholder='60'),
            Field('headline_suffix', 'Figure suffix', placeholder='%'),
            Field('headline_label', 'Figure caption', placeholder='More enquiries'),
            Field('is_reversed', 'Mirror the layout', 'bool',
                  help='Puts the artwork on the right. Alternate these down the page.'),
            PUBLISHED, POSITION,
            Field('visual_class', 'Artwork style', 'text', advanced=True,
                  help='cs-visual-1, cs-visual-2 or cs-visual-3.'),
        ]),

    Resource(
        key='case-study-results', model=CaseStudyResult, title='Case study figures',
        singular='Figure', group='Portfolio', parent='case_study',
        blurb='The result pills inside a case study — 60% more enquiries, 22 vehicles branded.',
        columns=[('label', 'Caption'), ('number', 'Figure'), ('case_study', 'Case study')],
        fields=[
            Field('case_study_id', 'Case study', 'select',
                  choices=_options(CaseStudy, blank=None), required=True),
            Field('number', 'Figure', required=True, placeholder='60'),
            Field('suffix', 'Suffix', placeholder='%'),
            Field('label', 'Caption', required=True, placeholder='More client enquiries'),
            POSITION,
        ]),

    Resource(
        key='categories', model=Category, title='Portfolio categories', singular='Category',
        group='Portfolio',
        blurb='The filter buttons above the grid. Counts update themselves.',
        columns=[('label', 'Category'), ('slug', 'Filter value')],
        fields=[
            Field('label', 'Name', required=True, placeholder='Branding'),
            Field('slug', 'Filter value', required=True,
                  help='Lower case, no spaces, e.g. branding.'),
            POSITION,
        ]),

    # ── Services ────────────────────────────────────────────────────────────
    Resource(
        key='services', model=Service, title='Services', singular='Service',
        group='Services',
        blurb='Shown on the homepage, the services page, the footer and the contact form dropdown.',
        columns=[('title', 'Service'), ('slug', 'Anchor'), ('is_published', 'Live')],
        fields=[
            Field('title', 'Full name', required=True, placeholder='Graphic Design'),
            Field('short_title', 'Short name', placeholder='Graphic Design',
                  help='Used where space is tight — footer, overview strip.'),
            Field('slug', 'Anchor', required=True,
                  help='Lower case, no spaces. Also the value used by the contact form.'),
            Field('summary', 'Homepage summary', 'textarea', rows=3,
                  help='The short description on the homepage card.'),
            Field('intro', 'Services page introduction', 'textarea', rows=5),
            Field('tags', 'Tags', 'textarea', rows=3,
                  help='One per line. Shown as pills under the introduction.'),
            Field('why_title', 'Why-choose-us heading',
                  placeholder='Why clients choose us for design'),
            Field('why_points', 'Why-choose-us points', 'textarea', rows=5,
                  help='One per line.'),
            PUBLISHED, POSITION,
            Field('icon_svg', 'Icon', 'code', rows=4, advanced=True,
                  help='Inline SVG. Paste from any icon set; it inherits the surrounding colour.'),
        ]),

    Resource(
        key='deliverables', model=Deliverable, title="What's included", singular='Deliverable',
        group='Services', parent='service',
        blurb='The cards under each service on the services page.',
        columns=[('title', 'Deliverable'), ('service', 'Service')],
        fields=[
            Field('service_id', 'Service', 'select',
                  choices=_options(Service, blank=None), required=True),
            Field('title', 'Title', required=True, placeholder='Logo design'),
            Field('description', 'Description', 'textarea', rows=3),
            POSITION,
        ]),

    Resource(
        key='packages', model=Package, title='Pricing tiers', singular='Tier',
        group='Services',
        columns=[('title', 'Tier'), ('tier_label', 'Label'), ('is_published', 'Live')],
        fields=[
            Field('tier_label', 'Small label', required=True, placeholder='Tier one'),
            Field('title', 'Name', required=True, placeholder='Starter'),
            Field('subtitle', 'Description', 'textarea', rows=3),
            Field('features', 'What it includes', 'textarea', rows=8,
                  help='One per line.'),
            Field('is_highlighted', 'Highlight as most popular', 'bool'),
            PUBLISHED, POSITION,
        ]),

    Resource(
        key='faqs', model=Faq, title='FAQs', singular='Question', group='Services',
        columns=[('question', 'Question'), ('is_published', 'Live')],
        fields=[
            Field('question', 'Question', required=True),
            Field('answer', 'Answer', 'textarea', rows=6, required=True),
            PUBLISHED, POSITION,
        ]),

    # ── Clients ─────────────────────────────────────────────────────────────
    Resource(
        key='clients', model=Client, title='Clients', singular='Client', group='Clients',
        blurb='The roster on the clients page and the scrolling logo band.',
        columns=[('name', 'Client'), ('industry', 'Industry'),
                 ('sector', 'Sector'), ('is_published', 'Live')],
        fields=[
            Field('name', 'Name', required=True, placeholder='Horizon Logistics Ltd'),
            Field('industry', 'Industry', placeholder='Logistics & Transport'),
            Field('services', 'Work we did', placeholder='Branding · Web · Signage'),
            Field('sector_id', 'Sector', 'select', choices=_options(Sector)),
            Field('show_in_marquee', 'Show in the scrolling band', 'bool'),
            PUBLISHED, POSITION,
        ]),

    Resource(
        key='sectors', model=Sector, title='Client sectors', singular='Sector', group='Clients',
        blurb='The tabs on the clients page. "All clients" is generated automatically.',
        columns=[('label', 'Sector'), ('slug', 'Tab id')],
        fields=[
            Field('label', 'Name', required=True, placeholder='Corporates & Finance'),
            Field('slug', 'Tab id', required=True, help='Lower case, no spaces.'),
            POSITION,
        ]),

    Resource(
        key='testimonials', model=Testimonial, title='Testimonials', singular='Testimonial',
        group='Clients',
        columns=[('author', 'Person'), ('company', 'Company'),
                 ('show_on_homepage', 'Homepage'), ('is_published', 'Live')],
        fields=[
            Field('quote', 'Quote', 'textarea', rows=6, required=True,
                  help='Without surrounding quotation marks — the design adds those.'),
            Field('author', 'Name', required=True, placeholder='James Kariuki'),
            Field('role', 'Role', placeholder='CEO'),
            Field('company', 'Company', placeholder='Horizon Logistics Ltd'),
            Field('rating', 'Stars', 'number', help='1 to 5.'),
            Field('is_featured', 'Feature on the clients page', 'bool',
                  help='Shown larger, spanning two columns.'),
            Field('show_on_homepage', 'Use on the homepage', 'bool',
                  help='The homepage shows one quote — the first ticked here.'),
            PUBLISHED, POSITION,
        ]),

    # ── Site ────────────────────────────────────────────────────────────────
    Resource(
        key='pages', model=Page, title='Page SEO', singular='Page', group='Site',
        can_create=False, can_delete=False, sortable=False,
        blurb='Titles and descriptions as they appear in Google and on social cards.',
        columns=[('nav_label', 'Page'), ('title', 'Search title'), ('is_indexed', 'Indexed')],
        fields=[
            Field('title', 'Search title', required=True,
                  help='Shown as the blue link in Google. Around 60 characters works best.'),
            Field('meta_description', 'Search description', 'textarea', rows=3,
                  help='The grey text under the link in Google. Around 155 characters.'),
            Field('og_title', 'Social title',
                  help='Leave blank to reuse the search title.'),
            Field('og_description', 'Social description', 'textarea', rows=3,
                  help='Leave blank to reuse the search description.'),
            Field('og_image', 'Social image', 'image',
                  help='Shown when the page is shared. 1200×630 pixels works best.'),
            Field('is_indexed', 'Allow search engines to index this page', 'bool'),
            Field('nav_label', 'Menu label', advanced=True),
        ]),

    Resource(
        key='stats', model=Stat, title='Headline figures', singular='Figure', group='Site',
        can_create=False, can_delete=False,
        blurb='The 150+ / 80+ / 7+ numbers. Editing one updates every page that shows it.',
        columns=[('label', 'Figure'), ('value', 'Value'), ('suffix', 'Suffix')],
        fields=[
            Field('value', 'Number', required=True, placeholder='150'),
            Field('suffix', 'Suffix', placeholder='+'),
            Field('label', 'Caption', required=True, placeholder='Projects delivered'),
            POSITION,
        ]),
]

BY_KEY = {r.key: r for r in RESOURCES}


def groups():
    """Resources bucketed by their nav group, preserving declaration order."""
    out: dict[str, list[Resource]] = {}
    for resource in RESOURCES:
        out.setdefault(resource.group, []).append(resource)
    return out
