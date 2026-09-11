"""Public site routes."""
from flask import (Blueprint, Response, abort, flash, redirect, render_template,
                   request, url_for)

from ..extensions import db
from ..models import Enquiry
from . import content
from .mail import notify_new_enquiry

bp = Blueprint('public', __name__)

# The old .html filenames, so existing links and any indexed URLs keep working.
LEGACY_PATHS = {
    'designplus-homepage.html': 'public.home',
    'designplus-about.html': 'public.about',
    'designplus-services.html': 'public.services',
    'designplus-portfolio.html': 'public.portfolio',
    'designplus-clients.html': 'public.clients',
    'designplus-contact.html': 'public.contact',
}


def _page(slug):
    page = content.get_page(slug)
    if page is None:
        abort(404)
    return page


@bp.route('/')
def home():
    return render_template(
        'public/home.html',
        page=_page('home'),
        services=content.published_services(),
        stats=content.stats(['projects_delivered', 'happy_clients', 'years_in_business']),
        testimonial=content.homepage_testimonial(),
        clients=content.marquee_clients(),
    )


@bp.route('/about')
def about():
    return render_template(
        'public/about.html',
        page=_page('about'),
        stats=content.stats(['projects_delivered', 'happy_clients',
                             'industries_served', 'years_in_business']),
    )


@bp.route('/services')
def services():
    return render_template(
        'public/services.html',
        page=_page('services'),
        services=content.published_services(),
        packages=content.published_packages(),
        faqs=content.published_faqs(),
    )


@bp.route('/portfolio')
def portfolio():
    return render_template(
        'public/portfolio.html',
        page=_page('portfolio'),
        projects=content.published_projects(),
        categories=content.categories_with_counts(),
        case_studies=content.published_case_studies(),
        stats=content.stats(['projects_delivered', 'happy_clients',
                             'industries_served', 'years_in_business']),
    )


@bp.route('/clients')
def clients():
    return render_template(
        'public/clients.html',
        page=_page('clients'),
        sectors=content.sectors_with_clients(),
        all_clients=content.published_clients(),
        marquee=content.marquee_clients(),
        testimonials=content.published_testimonials(),
        stats=content.stats(['happy_clients', 'industries_served',
                             'client_retention', 'years_in_business']),
    )


@bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        return _handle_enquiry()
    return render_template(
        'public/contact.html',
        page=_page('contact'),
        services=content.published_services(),
        preselect=request.args.get('service', ''),
    )


def _handle_enquiry():
    form = request.form

    # Bots fill hidden fields; humans do not. Accept silently so the bot
    # cannot tell it was caught.
    if form.get('website'):
        return redirect(url_for('public.contact', sent=1))

    name = form.get('name', '').strip()
    email = form.get('email', '').strip()
    message = form.get('message', '').strip()

    if not (name and email and message):
        flash('Please fill in your name, email and a short description.', 'error')
        return render_template(
            'public/contact.html', page=_page('contact'),
            services=content.published_services(),
            preselect=form.get('service', ''), submitted=form), 400

    enquiry = Enquiry(
        name=name[:160],
        company=form.get('company', '').strip()[:160],
        email=email[:255],
        phone=form.get('phone', '').strip()[:60],
        service=form.get('service', '').strip()[:80],
        budget=form.get('budget', '').strip()[:80],
        message=message,
        heard_from=form.get('hear', '').strip()[:120],
        source_ip=(request.headers.get('X-Forwarded-For', request.remote_addr) or '')[:60],
    )
    db.session.add(enquiry)
    db.session.commit()

    # A failed notification must not lose the enquiry — it is already saved.
    notify_new_enquiry(enquiry)

    return redirect(url_for('public.contact', sent=1) + '#enquiry')


@bp.route('/favicon.ico')
def favicon():
    """Browsers request this path by convention regardless of the <link> tag."""
    return redirect(url_for('static', filename='favicon.svg'), code=301)


@bp.route('/robots.txt')
def robots():
    lines = ['User-agent: *', 'Disallow: /admin', 'Allow: /', '',
             f'Sitemap: {request.url_root.rstrip("/")}/sitemap.xml']
    return Response('\n'.join(lines) + '\n', mimetype='text/plain')


@bp.route('/sitemap.xml')
def sitemap():
    from flask import current_app
    root = current_app.config['SITE_URL']
    entries = []
    for page in content.navigation():
        if not page.is_indexed:
            continue
        path = url_for(f'public.{page.slug}') if page.slug != 'home' else '/'
        entries.append(f'  <url><loc>{root}{path}</loc></url>')
    body = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + '\n'.join(entries) + '\n</urlset>\n')
    return Response(body, mimetype='application/xml')


@bp.route('/<path:legacy>')
def legacy_redirect(legacy):
    """301 the old .html URLs to their new home."""
    endpoint = LEGACY_PATHS.get(legacy)
    if not endpoint:
        abort(404)
    target = url_for(endpoint)
    if request.query_string:
        target += '?' + request.query_string.decode()
    return redirect(target, code=301)
