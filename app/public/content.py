"""Query helpers shared by the public routes and the template context."""
from ..extensions import db
from ..models import (CaseStudy, Category, Client, Faq, Package, Page, Project,
                      Sector, Service, Stat, Testimonial)


def settings_map() -> dict:
    """All settings as a plain dict, so templates can do `settings.phone`."""
    from ..models import Setting
    rows = db.session.scalars(db.select(Setting)).all()
    return {row.key: row.value for row in rows}


def navigation():
    return db.session.scalars(
        db.select(Page).order_by(Page.position)).all()


def get_page(slug: str) -> Page | None:
    return db.session.scalar(db.select(Page).filter_by(slug=slug))


def stats(keys: list[str] | None = None):
    query = db.select(Stat).order_by(Stat.position)
    if keys:
        query = query.where(Stat.key.in_(keys))
    rows = db.session.scalars(query).all()
    if not keys:
        return rows
    # Preserve the order the caller asked for.
    by_key = {row.key: row for row in rows}
    return [by_key[k] for k in keys if k in by_key]


def published_services():
    return db.session.scalars(
        db.select(Service).where(Service.is_published.is_(True))
        .order_by(Service.position)).all()


def published_packages():
    return db.session.scalars(
        db.select(Package).where(Package.is_published.is_(True))
        .order_by(Package.position)).all()


def published_faqs():
    return db.session.scalars(
        db.select(Faq).where(Faq.is_published.is_(True)).order_by(Faq.position)).all()


def published_projects():
    return db.session.scalars(
        db.select(Project).where(Project.is_published.is_(True))
        .order_by(Project.position)).all()


def published_case_studies():
    return db.session.scalars(
        db.select(CaseStudy).where(CaseStudy.is_published.is_(True))
        .order_by(CaseStudy.position)).all()


def categories_with_counts():
    """Filter tabs need a live count, not the hardcoded numbers of before."""
    cats = db.session.scalars(db.select(Category).order_by(Category.position)).all()
    counts = {
        cat.id: sum(1 for p in cat.projects if p.is_published) for cat in cats
    }
    return [(cat, counts.get(cat.id, 0)) for cat in cats if counts.get(cat.id, 0)]


def sectors_with_clients():
    return db.session.scalars(db.select(Sector).order_by(Sector.position)).all()


def published_clients():
    return db.session.scalars(
        db.select(Client).where(Client.is_published.is_(True))
        .order_by(Client.position)).all()


def marquee_clients():
    return [c for c in published_clients() if c.show_in_marquee]


def published_testimonials():
    return db.session.scalars(
        db.select(Testimonial).where(Testimonial.is_published.is_(True))
        .order_by(Testimonial.position)).all()


def homepage_testimonial():
    return db.session.scalar(
        db.select(Testimonial)
        .where(Testimonial.is_published.is_(True),
               Testimonial.show_on_homepage.is_(True))
        .order_by(Testimonial.position))
