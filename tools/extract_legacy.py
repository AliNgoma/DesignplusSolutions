#!/usr/bin/env python3
"""One-off: pull the site's content out of the legacy HTML into seed_data.json.

Run once during the static -> app conversion. The app itself never uses this;
it reads app/seed_data.json. Kept in the repo so the extraction is auditable.

    python3 tools/extract_legacy.py
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEGACY = ROOT / 'legacy'
OUT = ROOT / 'app' / 'seed_data.json'


def read(name):
    return (LEGACY / f'designplus-{name}.html').read_text()


def clean(text):
    """Strip tags, unescape entities, collapse whitespace."""
    text = re.sub(r'<[^>]+>', ' ', text)
    return re.sub(r'\s+', ' ', html.unescape(text)).strip()


# ── Services ────────────────────────────────────────────────────────────────

def extract_services():
    src = read('services')
    services = []

    sections = re.findall(
        r'<section class="service-section" id="([a-z-]+)">(.*?)\n</section>', src, re.S)

    for position, (slug, body) in enumerate(sections, start=1):
        icon = re.search(r'<div class="service-icon-ring">\s*(<svg.*?</svg>)', body, re.S)
        title = re.search(r'<h2>(.*?)</h2>', body, re.S)
        intro = re.search(r'</h2>\s*<p>(.*?)</p>', body, re.S)
        tags = re.findall(r'<span class="service-tag">(.*?)</span>', body)

        deliverables = [
            {'title': clean(t), 'description': clean(d)}
            for t, d in re.findall(
                r'<div class="deliverable-card">\s*<h4>(.*?)</h4>\s*<p>(.*?)</p>', body, re.S)
        ]

        why_title = re.search(r'<div class="why-choose-box">\s*<h4>(.*?)</h4>', body, re.S)
        why_points = re.findall(r'<li>(.*?)</li>', body, re.S)

        services.append({
            'slug': slug,
            'position': position,
            'title': clean(title.group(1)) if title else slug,
            'intro': clean(intro.group(1)) if intro else '',
            'tags': [clean(t) for t in tags],
            'icon_svg': icon.group(1).strip() if icon else '',
            'why_title': clean(why_title.group(1)) if why_title else '',
            'why_points': [clean(p) for p in why_points],
            'deliverables': deliverables,
        })

    # The homepage card copy is a shorter summary of the same service.
    home = read('homepage')
    summaries = {}
    for anchor, inner in re.findall(
            r'<a class="service-card" href="designplus-services\.html#([a-z-]+)">(.*?)</a>',
            home, re.S):
        title = re.search(r'<div class="sc-title">(.*?)</div>', inner, re.S)
        desc = re.search(r'<div class="sc-desc">(.*?)</div>', inner, re.S)
        summaries[anchor] = {
            'short_title': clean(title.group(1)) if title else '',
            'summary': clean(desc.group(1)) if desc else '',
        }

    for service in services:
        service.update(summaries.get(service['slug'], {}))

    return services


def extract_packages():
    src = read('services')
    packages = []
    blocks = re.findall(
        r'<div class="pkg-name">(.*?)</div>\s*'
        r'<div class="pkg-title">(.*?)</div>\s*'
        r'<div class="pkg-subtitle">(.*?)</div>(.*?)<a href="[^"]*" class="pkg-cta ([a-z-]+)"',
        src, re.S)
    for position, (tier, title, subtitle, body, cta_class) in enumerate(blocks, start=1):
        packages.append({
            'position': position,
            'tier_label': clean(tier),
            'title': clean(title),
            'subtitle': clean(subtitle),
            'features': [clean(f) for f in re.findall(r'<li>(.*?)</li>', body, re.S)],
            'is_highlighted': 'gold' in cta_class,
        })
    return packages


def extract_faqs():
    src = read('services')
    faqs = []
    blocks = re.findall(
        r'<button class="faq-q"[^>]*>\s*(.*?)\s*<span class="faq-icon">.*?</span>\s*</button>\s*'
        r'<div class="faq-a"[^>]*>(.*?)</div>', src, re.S)
    for position, (question, answer) in enumerate(blocks, start=1):
        faqs.append({'position': position,
                     'question': clean(question),
                     'answer': clean(answer)})
    return faqs


# ── Portfolio ───────────────────────────────────────────────────────────────

CATEGORY_LABELS = {
    'branding': 'Branding',
    'web': 'Web Design',
    'print': 'Print',
    'social': 'Social Media',
    'signage': 'Signage',
    'seo': 'SEO',
}


def extract_projects():
    src = read('portfolio')
    grid = src[src.index('id="projectsGrid"'):src.index('<!-- CASE STUDIES -->')]
    projects = []

    # Split on the card opening tag: the cards nest several divs, so a lazy
    # `.*?</div>` would stop at the first inner close.
    chunks = re.split(r'(?=<div class="project-card)', grid)[1:]
    cards = []
    for chunk in chunks:
        head = re.match(r'<div class="project-card([^"]*)" data-category="([a-z]+)">', chunk)
        if not head:
            continue
        info_start = chunk.find('<div class="project-info">')
        cards.append((head.group(1), head.group(2),
                      chunk[:info_start], chunk[info_start:]))

    for position, (classes, category, visual, info) in enumerate(cards, start=1):
        tag = re.search(r'<span class="project-service-tag">(.*?)</span>', info, re.S)
        name = re.search(r'<div class="project-name">(.*?)</div>', info, re.S)
        client = re.search(r'<div class="project-client">(.*?)</div>', info, re.S)
        result = re.search(r'<div class="project-result">(.*?)</div>', info, re.S)
        visual_class = re.search(r'project-visual-inner (pv-[a-z0-9-]+)', visual)
        # Each card has its own hand-built CSS artwork; keep it verbatim so the
        # design survives until real photography replaces it.
        inner = re.search(
            r'<div class="project-visual-inner pv-[a-z0-9-]+">(.*?)</div>\s*<div class="project-overlay">',
            visual, re.S)

        client_line = clean(client.group(1)) if client else ''
        client_name, _, location = client_line.partition(' · ')

        projects.append({
            'position': position,
            'title': clean(name.group(1)) if name else '',
            'client_name': client_name.strip(),
            'location': location.strip(),
            'service_tag': clean(tag.group(1)) if tag else '',
            'result': clean(result.group(1)) if result else '',
            'category': category,
            'visual_class': visual_class.group(1) if visual_class else '',
            'visual_html': inner.group(1).strip() if inner else '',
            'is_featured': 'featured' in classes,
        })
    return projects


def extract_case_studies():
    src = read('portfolio')
    studies = []
    blocks = re.findall(r'<div class="case-study">(.*?)\n  </div>', src, re.S)

    for position, body in enumerate(blocks, start=1):
        title = re.search(r'<h3 class="cs-title" id="([a-z-]+)">(.*?)</h3>', body, re.S)
        tag = re.search(r'<div class="cs-tag">(.*?)</div>', body, re.S)
        client = re.search(r'<div class="cs-client">(.*?)</div>', body, re.S)
        big = re.search(r'<div class="cs-big-num"[^>]*>([\d+]+)<span[^>]*>(.*?)</span>', body, re.S)
        big_label = re.search(r'<div class="cs-big-label"[^>]*>(.*?)</div>', body, re.S)
        visual = re.search(r'cs-visual (cs-visual-\d)', body)

        text_blocks = re.findall(
            r'<div class="cs-block-label">(.*?)</div>\s*<p>(.*?)</p>', body, re.S)
        blocks_by_label = {clean(l).lower(): clean(p) for l, p in text_blocks}

        results = [
            {'number': clean(num), 'suffix': clean(suffix), 'label': clean(label)}
            for num, suffix, label in re.findall(
                r'<span class="cs-result-num">(\d+)(?:<span>(.*?)</span>)?</span>\s*'
                r'<span class="cs-result-label">(.*?)</span>', body, re.S)
        ]

        studies.append({
            'position': position,
            'anchor': title.group(1) if title else f'case-{position}',
            'title': clean(title.group(2)) if title else '',
            'tag': clean(tag.group(1)) if tag else '',
            'client_line': clean(client.group(1)) if client else '',
            'challenge': blocks_by_label.get('the challenge', ''),
            'approach': blocks_by_label.get('our approach', ''),
            'headline_number': clean(big.group(1)).lstrip('+') if big else '',
            'headline_suffix': clean(big.group(2)) if big else '',
            'headline_label': clean(big_label.group(1)) if big_label else '',
            'visual_class': visual.group(1) if visual else 'cs-visual-1',
            'is_reversed': 'cs-layout reverse' in body,
            'results': results,
        })
    return studies


# ── Clients ─────────────────────────────────────────────────────────────────

def extract_clients():
    src = read('clients')

    sectors = [
        {'slug': slug, 'label': clean(label), 'position': i}
        for i, (slug, label) in enumerate(
            re.findall(r'id="tab-([a-z]+)"[^>]*data-sector="[a-z]+">(.*?)</button>', src, re.S),
            start=1)
        if slug != 'all'
    ]

    # A client appears in the "all" panel and again in its own sector panel.
    # Collapse that: each client gets one sector, and "all" is rendered live.
    sector_of = {}
    for slug, panel in re.findall(
            r'<div class="sector-panel[^"]*" id="panel-([a-z]+)"(.*?)\n  </div>', src, re.S):
        if slug == 'all':
            continue
        for name in re.findall(r'<div class="client-logo-name">(.*?)</div>', panel, re.S):
            sector_of.setdefault(clean(name), slug)

    all_panel = re.search(
        r'<div class="sector-panel active" id="panel-all"(.*?)\n  </div>', src, re.S).group(1)

    clients = []
    cards = re.split(r'(?=<div class="client-logo-card)', all_panel)[1:]
    for position, card in enumerate(cards, start=1):
        name = re.search(r'<div class="client-logo-name"[^>]*>(.*?)</div>', card, re.S)
        industry = re.search(r'<div class="client-logo-sub"[^>]*>(.*?)</div>', card, re.S)
        services = re.search(r'<div class="client-logo-service"[^>]*>(.*?)</div>', card, re.S)
        if not name:
            continue
        label = clean(name.group(1))
        if 'Your organisation here' in label:
            continue
        clients.append({
            'position': position,
            'name': label,
            'industry': clean(industry.group(1)) if industry else '',
            'services': clean(services.group(1)) if services else '',
            'sector': sector_of.get(label),
        })

    marquee = list(dict.fromkeys(
        clean(n) for n in re.findall(r'<div class="marquee-item">(.*?)</div>', src, re.S)))
    return sectors, clients, sorted(set(marquee))


def extract_testimonials():
    src = read('clients')
    testimonials = []
    for position, (classes, body) in enumerate(
            re.findall(r'<div class="t-card([^"]*)">(.*?)\n    </div>', src, re.S), start=1):
        quote = re.search(r'<div class="t-quote">(.*?)</div>', body, re.S)
        name = re.search(r'<div class="t-name">(.*?)</div>', body, re.S)
        role = re.search(r'<div class="t-role">(.*?)</div>', body, re.S)
        stars = re.search(r'<div class="t-stars">(.*?)</div>', body, re.S)
        if not quote:
            continue
        role_line = clean(role.group(1)) if role else ''
        role_part, _, company = role_line.partition(', ')
        testimonials.append({
            'position': position,
            'quote': clean(quote.group(1)).strip('"'),
            'author': clean(name.group(1)) if name else '',
            'role': role_part.strip(),
            'company': company.strip(),
            'rating': len(clean(stars.group(1))) if stars else 5,
            'is_featured': 'featured' in classes,
        })
    return testimonials


# ── Page metadata ───────────────────────────────────────────────────────────

PAGES = [
    ('home', 'Home', 'homepage'),
    ('about', 'About', 'about'),
    ('services', 'Services', 'services'),
    ('portfolio', 'Portfolio', 'portfolio'),
    ('clients', 'Clients', 'clients'),
    ('contact', 'Contact', 'contact'),
]


def extract_pages():
    pages = []
    for position, (slug, nav_label, filename) in enumerate(PAGES, start=1):
        src = read(filename)
        title = re.search(r'<title>(.*?)</title>', src, re.S)
        desc = re.search(r'<meta name="description" content="(.*?)">', src, re.S)
        pages.append({
            'slug': slug,
            'nav_label': nav_label,
            'position': position,
            'title': html.unescape(title.group(1)) if title else nav_label,
            'meta_description': html.unescape(desc.group(1)) if desc else '',
        })
    return pages


def main():
    sectors, clients, marquee = extract_clients()
    data = {
        'pages': extract_pages(),
        'services': extract_services(),
        'packages': extract_packages(),
        'faqs': extract_faqs(),
        'categories': [{'slug': s, 'label': l, 'position': i}
                       for i, (s, l) in enumerate(CATEGORY_LABELS.items(), start=1)],
        'projects': extract_projects(),
        'case_studies': extract_case_studies(),
        'sectors': sectors,
        'clients': clients,
        'marquee': marquee,
        'testimonials': extract_testimonials(),
    }

    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')

    for key, value in data.items():
        print(f'{key:15} {len(value)}')
    print(f'\nwrote {OUT.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
