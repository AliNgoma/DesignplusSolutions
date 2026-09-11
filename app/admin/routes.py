"""Admin blueprint: authentication, dashboard, enquiries, settings and the
generic CRUD driven by resources.RESOURCES.
"""
import csv
import io
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import (Blueprint, Response, abort, current_app, flash, redirect,
                   render_template, request, url_for)
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func, or_
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models import AdminUser, Enquiry, Setting, latest_enquiry_count
from ..storage import save_upload
from .resources import BY_KEY, RESOURCES, groups

bp = Blueprint('admin', __name__, template_folder='../templates/admin')


@bp.app_context_processor
def inject_admin_nav():
    if not current_user.is_authenticated:
        return {}
    return {'admin_groups': groups(), 'new_enquiries': latest_enquiry_count()}


# ── Authentication ──────────────────────────────────────────────────────────

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = db.session.scalar(db.select(AdminUser).filter_by(email=email))

        if user and user.check_password(password):
            login_user(user, remember=bool(request.form.get('remember')))
            user.last_login_at = datetime.now(timezone.utc)
            db.session.commit()
            nxt = request.args.get('next', '')
            # Only ever redirect within this site.
            if not nxt.startswith('/') or nxt.startswith('//'):
                nxt = url_for('admin.dashboard')
            return redirect(nxt)

        # Same message either way, so the form cannot be used to discover
        # which email addresses exist.
        flash('Those details did not match an account.', 'error')

    return render_template('admin/login.html')


@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('Signed out.', 'success')
    return redirect(url_for('admin.login'))


@bp.route('/password', methods=['GET', 'POST'])
@login_required
def password():
    if request.method == 'POST':
        current = request.form.get('current_password', '')
        new = request.form.get('new_password', '')
        confirm = request.form.get('confirm_password', '')

        if not current_user.check_password(current):
            flash('Your current password is not correct.', 'error')
        elif len(new) < 10:
            flash('Choose a password of at least 10 characters.', 'error')
        elif new != confirm:
            flash('The two new passwords do not match.', 'error')
        else:
            current_user.set_password(new)
            db.session.commit()
            flash('Password changed.', 'success')
            return redirect(url_for('admin.dashboard'))

    return render_template('admin/password.html')


# ── Dashboard ───────────────────────────────────────────────────────────────

@bp.route('/')
@login_required
def dashboard():
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent = db.session.scalars(
        db.select(Enquiry).order_by(Enquiry.created_at.desc()).limit(6)).all()

    counts = {
        'new': latest_enquiry_count(),
        'week': db.session.scalar(
            db.select(func.count(Enquiry.id)).where(Enquiry.created_at >= week_ago)) or 0,
        'total': db.session.scalar(db.select(func.count(Enquiry.id))) or 0,
    }

    # Surface the placeholders still standing in for real values.
    todos = db.session.scalars(
        db.select(Setting).where(Setting.help_text.like('TODO%')).order_by(Setting.position)).all()

    return render_template('admin/dashboard.html', recent=recent, counts=counts,
                           todos=todos, resources=RESOURCES)


# ── Enquiries ───────────────────────────────────────────────────────────────

@bp.route('/enquiries')
@login_required
def enquiries():
    status = request.args.get('status', '')
    search = request.args.get('q', '').strip()

    stmt = db.select(Enquiry).order_by(Enquiry.created_at.desc())
    if status in Enquiry.STATUSES:
        stmt = stmt.where(Enquiry.status == status)
    if search:
        like = f'%{search}%'
        stmt = stmt.where(or_(Enquiry.name.ilike(like), Enquiry.email.ilike(like),
                              Enquiry.company.ilike(like), Enquiry.message.ilike(like)))

    rows = db.session.scalars(stmt).all()
    tallies = {s: db.session.scalar(
        db.select(func.count(Enquiry.id)).where(Enquiry.status == s)) or 0
        for s in Enquiry.STATUSES}

    return render_template('admin/enquiries.html', enquiries=rows, status=status,
                           search=search, tallies=tallies)


@bp.route('/enquiries/<int:enquiry_id>', methods=['GET', 'POST'])
@login_required
def enquiry_detail(enquiry_id):
    enquiry = db.session.get(Enquiry, enquiry_id) or abort(404)

    if request.method == 'POST':
        status = request.form.get('status', '')
        if status in Enquiry.STATUSES:
            enquiry.status = status
        enquiry.internal_notes = request.form.get('internal_notes', '')
        db.session.commit()
        flash('Enquiry updated.', 'success')
        return redirect(url_for('admin.enquiry_detail', enquiry_id=enquiry.id))

    # Opening a new enquiry marks it as being dealt with.
    if enquiry.status == 'new':
        enquiry.status = 'in_progress'
        db.session.commit()

    return render_template('admin/enquiry_detail.html', enquiry=enquiry)


@bp.route('/enquiries/<int:enquiry_id>/delete', methods=['POST'])
@login_required
def enquiry_delete(enquiry_id):
    enquiry = db.session.get(Enquiry, enquiry_id) or abort(404)
    db.session.delete(enquiry)
    db.session.commit()
    flash('Enquiry deleted.', 'success')
    return redirect(url_for('admin.enquiries'))


@bp.route('/enquiries.csv')
@login_required
def enquiries_csv():
    rows = db.session.scalars(db.select(Enquiry).order_by(Enquiry.created_at.desc())).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['Received', 'Name', 'Company', 'Email', 'Phone', 'Service',
                     'Budget', 'Heard via', 'Status', 'Message', 'Notes'])
    for e in rows:
        writer.writerow([e.created_at.strftime('%Y-%m-%d %H:%M'), e.name, e.company,
                         e.email, e.phone, e.service, e.budget, e.heard_from,
                         e.status, e.message, e.internal_notes])
    stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    return Response(
        buffer.getvalue(), mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=enquiries-{stamp}.csv'})


# ── Settings ────────────────────────────────────────────────────────────────

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    rows = db.session.scalars(db.select(Setting).order_by(Setting.position)).all()

    if request.method == 'POST':
        for row in rows:
            if row.key in request.form:
                row.value = request.form[row.key].strip()
                # Once a placeholder has a real value, retire the TODO note.
                if row.help_text.startswith('TODO') and row.value and 'Your Office' not in row.value \
                        and '700 000 000' not in row.value:
                    row.help_text = ''
        db.session.commit()
        flash('Settings saved.', 'success')
        return redirect(url_for('admin.settings'))

    grouped: dict[str, list[Setting]] = {}
    for row in rows:
        grouped.setdefault(row.group, []).append(row)
    return render_template('admin/settings.html', grouped=grouped)


# ── Generic CRUD ────────────────────────────────────────────────────────────

def _resource(key):
    return BY_KEY.get(key) or abort(404)


def _save_upload(file_storage) -> str:
    """Store an uploaded image and return its filename, or '' if none."""
    if not file_storage or not file_storage.filename:
        return ''
    name = secure_filename(file_storage.filename)
    suffix = Path(name).suffix.lower()
    if suffix not in current_app.config['ALLOWED_IMAGE_EXTENSIONS']:
        flash(f'{suffix or "That file type"} is not an accepted image format.', 'error')
        return ''
    # Random prefix: keeps the original name readable without letting two
    # uploads of "logo.png" overwrite each other.
    stored = f'{secrets.token_hex(6)}-{name}'
    save_upload(file_storage, stored)
    return stored


def _apply_form(resource, row):
    """Copy submitted values onto the row. Returns a list of error messages."""
    errors = []
    for field in resource.fields:
        if field.kind == 'bool':
            setattr(row, field.name, field.name in request.form)
            continue

        if field.kind == 'image':
            uploaded = _save_upload(request.files.get(field.name))
            if uploaded:
                setattr(row, field.name, uploaded)
            elif request.form.get(f'{field.name}__clear'):
                setattr(row, field.name, '')
            continue

        raw = request.form.get(field.name, '').strip()

        if field.required and not raw:
            errors.append(f'{field.label} is required.')
            continue

        if field.kind == 'number':
            setattr(row, field.name, int(raw) if raw else 0)
        elif field.kind == 'select':
            setattr(row, field.name, int(raw) if raw else None)
        else:
            setattr(row, field.name, raw)
    return errors


@bp.route('/<key>')
@login_required
def resource_list(key):
    resource = _resource(key)
    return render_template('admin/list.html', resource=resource, rows=resource.query())


@bp.route('/<key>/new', methods=['GET', 'POST'])
@login_required
def resource_create(key):
    resource = _resource(key)
    if not resource.can_create:
        abort(404)

    row = resource.model()
    if request.method == 'POST':
        errors = _apply_form(resource, row)
        if errors:
            for message in errors:
                flash(message, 'error')
        else:
            if getattr(row, 'position', None) in (None, 0):
                highest = db.session.scalar(
                    db.select(func.max(resource.model.position))) or 0
                row.position = highest + 1
            db.session.add(row)
            db.session.commit()
            flash(f'{resource.singular} created.', 'success')
            return redirect(url_for('admin.resource_list', key=key))

    return render_template('admin/form.html', resource=resource, row=row, is_new=True)


@bp.route('/<key>/<int:row_id>', methods=['GET', 'POST'])
@login_required
def resource_edit(key, row_id):
    resource = _resource(key)
    row = db.session.get(resource.model, row_id) or abort(404)

    if request.method == 'POST':
        errors = _apply_form(resource, row)
        if errors:
            for message in errors:
                flash(message, 'error')
        else:
            db.session.commit()
            flash(f'{resource.singular} saved.', 'success')
            return redirect(url_for('admin.resource_list', key=key))

    return render_template('admin/form.html', resource=resource, row=row, is_new=False)


@bp.route('/<key>/<int:row_id>/delete', methods=['POST'])
@login_required
def resource_delete(key, row_id):
    resource = _resource(key)
    if not resource.can_delete:
        abort(404)
    row = db.session.get(resource.model, row_id) or abort(404)
    db.session.delete(row)
    db.session.commit()
    flash(f'{resource.singular} deleted.', 'success')
    return redirect(url_for('admin.resource_list', key=key))


@bp.route('/<key>/<int:row_id>/move', methods=['POST'])
@login_required
def resource_move(key, row_id):
    """Swap position with the neighbour in the given direction."""
    resource = _resource(key)
    if not resource.sortable:
        abort(404)
    row = db.session.get(resource.model, row_id) or abort(404)
    direction = request.form.get('direction')

    model = resource.model
    if direction == 'up':
        stmt = (db.select(model).where(model.position < row.position)
                .order_by(model.position.desc()))
    else:
        stmt = (db.select(model).where(model.position > row.position)
                .order_by(model.position))
    neighbour = db.session.scalar(stmt)

    if neighbour:
        row.position, neighbour.position = neighbour.position, row.position
        db.session.commit()

    return redirect(url_for('admin.resource_list', key=key))
