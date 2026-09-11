"""Application factory."""
import click
from flask import Flask

from .config import Config
from .extensions import csrf, db, login_manager, migrate


def create_app(config_object=Config) -> Flask:
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(config_object)

    if not app.config['SUPABASE_URL']:
        app.config['UPLOAD_DIR'].mkdir(parents=True, exist_ok=True)
        (app.config['UPLOAD_DIR'].parent / '.gitkeep').touch(exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)

    from . import models  # noqa: F401  (registers the mappings)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(models.AdminUser, int(user_id))

    from .public.routes import bp as public_bp
    from .admin.routes import bp as admin_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')

    _register_context(app)
    _register_errors(app)
    _register_cli(app)
    return app


def _register_context(app: Flask) -> None:
    """Make settings and navigation available to every public template."""
    from . import models
    from .public.content import navigation, settings_map
    from .storage import upload_url

    from datetime import date
    from .public.content import published_services

    app.jinja_env.globals['upload_url'] = upload_url

    @app.context_processor
    def inject_globals():
        return {
            'settings': settings_map(),
            'nav_pages': navigation(),
            'footer_services': published_services(),
            'site_url': app.config['SITE_URL'],
            'current_year': date.today().year,
        }

    @app.template_filter('phone_digits')
    def phone_digits(value):
        """+254 700 000 000 -> 254700000000, for tel: and wa.me links."""
        return ''.join(ch for ch in (value or '') if ch.isdigit())


def _register_errors(app: Flask) -> None:
    from flask import render_template, request

    @app.errorhandler(404)
    def not_found(_):
        if request.path.startswith('/admin'):
            return render_template('admin/error.html', code=404,
                                   message='That admin page does not exist.'), 404
        return render_template('public/404.html'), 404

    @app.errorhandler(500)
    def server_error(_):
        db.session.rollback()
        return render_template('public/500.html'), 500

    @app.errorhandler(413)
    def too_large(_):
        from flask import flash, redirect, url_for
        flash('That file is larger than the 8 MB limit.', 'error')
        return redirect(request.referrer or url_for('admin.dashboard'))


def _register_cli(app: Flask) -> None:
    from .seed import seed_everything

    @app.cli.command('init-db')
    def init_db():
        """Create any tables that do not exist yet.

        Safe to re-run. For schema *changes* after launch use Flask-Migrate
        (`flask db init` once, then `db migrate` / `db upgrade`), which is
        already installed — create_all never alters an existing table.
        """
        db.create_all()
        click.echo('Tables are up to date.')

    @app.cli.command('seed')
    @click.option('--force', is_flag=True, help='Wipe existing content first.')
    def seed_command(force):
        """Load the site's starting content and create the first admin user."""
        seed_everything(force=force)

    @app.cli.command('create-admin')
    @click.argument('email')
    @click.argument('password')
    def create_admin(email, password):
        """Add another admin user."""
        from .models import AdminUser
        if db.session.scalar(db.select(AdminUser).filter_by(email=email)):
            click.echo(f'{email} already exists.')
            return
        user = AdminUser(email=email, name=email.split('@')[0].title())
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f'Created admin {email}.')
