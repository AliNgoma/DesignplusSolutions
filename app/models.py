"""Database models.

Everything the admin can edit lives here. Content models share three
conventions: `position` for manual ordering, `is_published` for hiding a row
from the public site without deleting it, and a `__str__` used in admin lists.
"""
from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def _now():
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class AdminUser(UserMixin, TimestampMixin, db.Model):
    __tablename__ = 'admin_users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False, default='Administrator')
    password_hash = db.Column(db.String(255), nullable=False)
    last_login_at = db.Column(db.DateTime(timezone=True))

    def set_password(self, raw: str) -> None:
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password_hash, raw)

    def __str__(self):
        return self.email


class Setting(db.Model):
    """Single-value site settings — contact details, social links, form target.

    Kept as rows rather than columns so a new setting needs no migration.
    """
    __tablename__ = 'settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, default='', nullable=False)
    label = db.Column(db.String(160), nullable=False)
    help_text = db.Column(db.String(400), default='', nullable=False)
    group = db.Column(db.String(60), default='General', nullable=False)
    kind = db.Column(db.String(20), default='text', nullable=False)  # text|textarea|url|email|tel
    position = db.Column(db.Integer, default=0, nullable=False)

    def __str__(self):
        return self.key


class Page(TimestampMixin, db.Model):
    """Per-page SEO. One row per public route."""
    __tablename__ = 'pages'

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(60), unique=True, nullable=False, index=True)
    nav_label = db.Column(db.String(60), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    meta_description = db.Column(db.Text, default='', nullable=False)
    og_title = db.Column(db.String(200), default='', nullable=False)
    og_description = db.Column(db.Text, default='', nullable=False)
    og_image = db.Column(db.String(300), default='', nullable=False)
    is_indexed = db.Column(db.Boolean, default=True, nullable=False)
    position = db.Column(db.Integer, default=0, nullable=False)

    @property
    def social_title(self):
        return self.og_title or self.title

    @property
    def social_description(self):
        return self.og_description or self.meta_description

    def __str__(self):
        return self.nav_label


class Stat(db.Model):
    """The 150+/80+/7+ figures, which appeared hardcoded on four pages."""
    __tablename__ = 'stats'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(60), unique=True, nullable=False, index=True)
    value = db.Column(db.String(20), nullable=False)
    suffix = db.Column(db.String(10), default='+', nullable=False)
    label = db.Column(db.String(120), nullable=False)
    position = db.Column(db.Integer, default=0, nullable=False)

    def __str__(self):
        return f'{self.value}{self.suffix} {self.label}'


class Service(TimestampMixin, db.Model):
    __tablename__ = 'services'

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False)
    short_title = db.Column(db.String(80), default='', nullable=False)
    summary = db.Column(db.Text, default='', nullable=False)      # homepage card
    intro = db.Column(db.Text, default='', nullable=False)        # services page
    tags = db.Column(db.Text, default='', nullable=False)         # newline separated
    icon_svg = db.Column(db.Text, default='', nullable=False)
    why_title = db.Column(db.String(200), default='', nullable=False)
    why_points = db.Column(db.Text, default='', nullable=False)   # newline separated
    position = db.Column(db.Integer, default=0, nullable=False)
    is_published = db.Column(db.Boolean, default=True, nullable=False)

    deliverables = db.relationship(
        'Deliverable', back_populates='service', cascade='all, delete-orphan',
        order_by='Deliverable.position', lazy='selectin')

    @property
    def tag_list(self):
        return [t.strip() for t in self.tags.splitlines() if t.strip()]

    @property
    def why_list(self):
        return [t.strip() for t in self.why_points.splitlines() if t.strip()]

    @property
    def number(self):
        """Display index (01, 02 …) derived from ordering, never stored."""
        return f'{self.position:02d}'

    def __str__(self):
        return self.title


class Deliverable(db.Model):
    __tablename__ = 'deliverables'

    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, default='', nullable=False)
    position = db.Column(db.Integer, default=0, nullable=False)

    service = db.relationship('Service', back_populates='deliverables')

    def __str__(self):
        return self.title


class Package(TimestampMixin, db.Model):
    __tablename__ = 'packages'

    id = db.Column(db.Integer, primary_key=True)
    tier_label = db.Column(db.String(60), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    subtitle = db.Column(db.Text, default='', nullable=False)
    features = db.Column(db.Text, default='', nullable=False)  # newline separated
    is_highlighted = db.Column(db.Boolean, default=False, nullable=False)
    position = db.Column(db.Integer, default=0, nullable=False)
    is_published = db.Column(db.Boolean, default=True, nullable=False)

    @property
    def feature_list(self):
        return [f.strip() for f in self.features.splitlines() if f.strip()]

    def __str__(self):
        return self.title


class Faq(TimestampMixin, db.Model):
    __tablename__ = 'faqs'

    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(300), nullable=False)
    answer = db.Column(db.Text, nullable=False)
    position = db.Column(db.Integer, default=0, nullable=False)
    is_published = db.Column(db.Boolean, default=True, nullable=False)

    def __str__(self):
        return self.question


class Category(db.Model):
    """Portfolio filter categories."""
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(60), unique=True, nullable=False, index=True)
    label = db.Column(db.String(80), nullable=False)
    position = db.Column(db.Integer, default=0, nullable=False)

    projects = db.relationship('Project', back_populates='category', lazy='selectin')

    def __str__(self):
        return self.label


class Project(TimestampMixin, db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    client_name = db.Column(db.String(160), default='', nullable=False)
    location = db.Column(db.String(120), default='', nullable=False)
    service_tag = db.Column(db.String(120), default='', nullable=False)
    result = db.Column(db.Text, default='', nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    image = db.Column(db.String(300), default='', nullable=False)
    image_alt = db.Column(db.String(300), default='', nullable=False)
    # Falls back to the hand-built CSS artwork when no image is uploaded.
    visual_class = db.Column(db.String(60), default='', nullable=False)
    visual_html = db.Column(db.Text, default='', nullable=False)
    is_featured = db.Column(db.Boolean, default=False, nullable=False)
    position = db.Column(db.Integer, default=0, nullable=False)
    is_published = db.Column(db.Boolean, default=True, nullable=False)

    category = db.relationship('Category', back_populates='projects')
    case_study = db.relationship(
        'CaseStudy', back_populates='project', uselist=False, lazy='selectin')

    @property
    def client_line(self):
        return ' · '.join(p for p in (self.client_name, self.location) if p)

    def __str__(self):
        return self.title


class CaseStudy(TimestampMixin, db.Model):
    __tablename__ = 'case_studies'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='SET NULL'), nullable=True)
    anchor = db.Column(db.String(80), unique=True, nullable=False, index=True)
    tag = db.Column(db.String(160), default='', nullable=False)
    title = db.Column(db.String(300), nullable=False)
    client_line = db.Column(db.String(200), default='', nullable=False)
    challenge = db.Column(db.Text, default='', nullable=False)
    approach = db.Column(db.Text, default='', nullable=False)
    headline_number = db.Column(db.String(20), default='', nullable=False)
    headline_suffix = db.Column(db.String(10), default='', nullable=False)
    headline_label = db.Column(db.String(120), default='', nullable=False)
    visual_class = db.Column(db.String(60), default='cs-visual-1', nullable=False)
    is_reversed = db.Column(db.Boolean, default=False, nullable=False)
    position = db.Column(db.Integer, default=0, nullable=False)
    is_published = db.Column(db.Boolean, default=True, nullable=False)

    project = db.relationship('Project', back_populates='case_study')
    results = db.relationship(
        'CaseStudyResult', back_populates='case_study', cascade='all, delete-orphan',
        order_by='CaseStudyResult.position', lazy='selectin')

    def __str__(self):
        return self.title


class CaseStudyResult(db.Model):
    __tablename__ = 'case_study_results'

    id = db.Column(db.Integer, primary_key=True)
    case_study_id = db.Column(
        db.Integer, db.ForeignKey('case_studies.id', ondelete='CASCADE'), nullable=False)
    number = db.Column(db.String(20), nullable=False)
    suffix = db.Column(db.String(10), default='', nullable=False)
    label = db.Column(db.String(120), nullable=False)
    position = db.Column(db.Integer, default=0, nullable=False)

    case_study = db.relationship('CaseStudy', back_populates='results')

    def __str__(self):
        return f'{self.number}{self.suffix} {self.label}'


class Sector(db.Model):
    __tablename__ = 'sectors'

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(60), unique=True, nullable=False, index=True)
    label = db.Column(db.String(120), nullable=False)
    position = db.Column(db.Integer, default=0, nullable=False)

    clients = db.relationship(
        'Client', back_populates='sector', order_by='Client.position', lazy='selectin')

    def __str__(self):
        return self.label


class Client(TimestampMixin, db.Model):
    __tablename__ = 'clients'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    industry = db.Column(db.String(160), default='', nullable=False)
    services = db.Column(db.String(200), default='', nullable=False)
    sector_id = db.Column(db.Integer, db.ForeignKey('sectors.id'), nullable=True)
    logo = db.Column(db.String(300), default='', nullable=False)
    show_in_marquee = db.Column(db.Boolean, default=True, nullable=False)
    position = db.Column(db.Integer, default=0, nullable=False)
    is_published = db.Column(db.Boolean, default=True, nullable=False)

    sector = db.relationship('Sector', back_populates='clients')

    def __str__(self):
        return self.name


class Testimonial(TimestampMixin, db.Model):
    __tablename__ = 'testimonials'

    id = db.Column(db.Integer, primary_key=True)
    quote = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(160), default='', nullable=False)
    company = db.Column(db.String(160), default='', nullable=False)
    rating = db.Column(db.Integer, default=5, nullable=False)
    is_featured = db.Column(db.Boolean, default=False, nullable=False)
    show_on_homepage = db.Column(db.Boolean, default=False, nullable=False)
    position = db.Column(db.Integer, default=0, nullable=False)
    is_published = db.Column(db.Boolean, default=True, nullable=False)

    @property
    def attribution(self):
        return ', '.join(p for p in (self.role, self.company) if p)

    def __str__(self):
        return f'{self.author} — {self.quote[:40]}…'


class Enquiry(db.Model):
    __tablename__ = 'enquiries'

    STATUSES = ('new', 'in_progress', 'quoted', 'won', 'closed')

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False, index=True)
    name = db.Column(db.String(160), nullable=False)
    company = db.Column(db.String(160), default='', nullable=False)
    email = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(60), default='', nullable=False)
    service = db.Column(db.String(80), default='', nullable=False)
    budget = db.Column(db.String(80), default='', nullable=False)
    message = db.Column(db.Text, nullable=False)
    heard_from = db.Column(db.String(120), default='', nullable=False)
    status = db.Column(db.String(20), default='new', nullable=False, index=True)
    internal_notes = db.Column(db.Text, default='', nullable=False)
    # Kept for spam triage, never displayed publicly.
    source_ip = db.Column(db.String(60), default='', nullable=False)

    @property
    def is_new(self):
        return self.status == 'new'

    def __str__(self):
        return f'{self.name} <{self.email}>'


def latest_enquiry_count():
    """Unread badge for the admin nav."""
    return db.session.scalar(
        db.select(func.count(Enquiry.id)).where(Enquiry.status == 'new')) or 0
