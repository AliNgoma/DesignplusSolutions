"""Enquiry notification email.

Best-effort by design: the enquiry is already committed before this runs, so a
mail server outage costs a notification, never a lead.
"""
import logging
import smtplib
from email.message import EmailMessage

from flask import current_app

log = logging.getLogger(__name__)


def notify_new_enquiry(enquiry) -> bool:
    cfg = current_app.config
    recipient = cfg.get('NOTIFY_EMAIL')
    host = cfg.get('SMTP_HOST')

    if not (host and recipient):
        log.info('SMTP not configured; enquiry %s saved without notification.', enquiry.id)
        return False

    body = '\n'.join([
        f'Name:     {enquiry.name}',
        f'Company:  {enquiry.company or "—"}',
        f'Email:    {enquiry.email}',
        f'Phone:    {enquiry.phone or "—"}',
        f'Service:  {enquiry.service or "—"}',
        f'Budget:   {enquiry.budget or "—"}',
        f'Heard via:{enquiry.heard_from or "—"}',
        '',
        enquiry.message,
        '',
        f'{cfg["SITE_URL"]}/admin/enquiries/{enquiry.id}',
    ])

    msg = EmailMessage()
    msg['Subject'] = f'New enquiry — {enquiry.name}'
    msg['From'] = cfg.get('SMTP_USER') or recipient
    msg['To'] = recipient
    msg['Reply-To'] = enquiry.email
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, cfg['SMTP_PORT'], timeout=10) as server:
            server.starttls()
            if cfg.get('SMTP_USER'):
                server.login(cfg['SMTP_USER'], cfg['SMTP_PASSWORD'])
            server.send_message(msg)
        return True
    except Exception:  # noqa: BLE001 — never let mail failure surface to the visitor
        log.exception('Could not send notification for enquiry %s', enquiry.id)
        return False
