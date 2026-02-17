"""
AjayaDesign Automation — Email service (Gmail SMTP).

Setup:
1. Go to https://myaccount.google.com/apppasswords
2. Generate an App Password for "Mail"
3. Set SMTP_EMAIL and SMTP_APP_PASSWORD in .env / docker-compose
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from api.config import settings

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


async def send_email(
    to: str,
    subject: str,
    body_html: str,
    reply_to: str | None = None,
) -> dict:
    """
    Send an email via Gmail SMTP.
    Returns {"success": True/False, "message": "..."}
    """
    sender = settings.smtp_email
    password = settings.smtp_app_password

    if not sender or not password:
        logger.warning("SMTP not configured — skipping email send")
        return {"success": False, "message": "SMTP credentials not configured. Set SMTP_EMAIL and SMTP_APP_PASSWORD."}

    msg = MIMEMultipart("alternative")
    msg["From"] = f"AjayaDesign <{sender}>"
    msg["To"] = to
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to

    # Plain-text fallback
    plain_text = body_html.replace("<br>", "\n").replace("<br/>", "\n")
    # Strip HTML tags for plain text
    import re
    plain_text = re.sub(r"<[^>]+>", "", plain_text)

    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(sender, password)
            server.sendmail(sender, [to], msg.as_string())

        logger.info(f"✅ Email sent to {to}: {subject}")
        return {"success": True, "message": f"Email sent to {to}"}

    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP auth failed: {e}")
        return {"success": False, "message": "SMTP authentication failed. Check your App Password."}
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return {"success": False, "message": f"Email failed: {str(e)}"}


def build_contract_email(
    client_name: str,
    project_name: str,
    sign_url: str,
    provider_name: str = "AjayaDesign",
) -> tuple[str, str]:
    """Build a contract signing invitation email. Returns (subject, html_body)."""
    subject = f"Contract for {project_name} — Please Review & Sign"
    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px;">
      <div style="text-align: center; margin-bottom: 32px;">
        <h1 style="color: #111; font-size: 24px; margin: 0;">📝 Contract Ready for Review</h1>
        <p style="color: #666; margin-top: 8px;">from {provider_name}</p>
      </div>

      <div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
        <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0;">
          Hi <strong>{client_name}</strong>,
        </p>
        <p style="color: #333; font-size: 16px; line-height: 1.6;">
          Your contract for <strong>{project_name}</strong> is ready for review and signing.
          Please click the button below to view the full contract, review the terms,
          and sign electronically.
        </p>
      </div>

      <div style="text-align: center; margin: 32px 0;">
        <a href="{sign_url}" style="display: inline-block; background: #6366f1; color: white; text-decoration: none; padding: 14px 32px; border-radius: 8px; font-size: 16px; font-weight: 600;">
          Review & Sign Contract →
        </a>
      </div>

      <p style="color: #9ca3af; font-size: 13px; text-align: center; margin-top: 32px;">
        If you have any questions, reply to this email or contact us at ajayadesign@gmail.com
      </p>
      <p style="color: #d1d5db; font-size: 11px; text-align: center; margin-top: 16px;">
        {provider_name} · 13721 Andrew Abernathy Pass, Manor, TX 78653
      </p>
    </div>
    """
    return subject, html


# PayPal fee config (must match frontend)
PAYPAL_ME = "ajayadesign"
PAYPAL_FEE_PERCENT = 0.0349   # 3.49%
PAYPAL_FEE_FIXED = 0.49


def _paypal_gross(net: float) -> float:
    """Calculate gross so seller nets exactly `net` after PayPal fees."""
    import math
    return math.ceil((net + PAYPAL_FEE_FIXED) / (1 - PAYPAL_FEE_PERCENT) * 100) / 100


def _build_paypal_button_html(total_amount_str: str, payment_method: str) -> str:
    """Return a PayPal payment button HTML block for the invoice email."""
    if payment_method and payment_method.lower() != "paypal":
        return ""
    try:
        net = float(total_amount_str.replace(",", "").replace("$", ""))
    except (ValueError, TypeError):
        return ""
    if net <= 0:
        return ""
    gross = _paypal_gross(net)
    fee = gross - net
    link = f"https://paypal.me/{PAYPAL_ME}/{gross:.2f}USD"
    return f"""
      <div style="text-align: center; margin-bottom: 24px;">
        <a href="{link}" target="_blank"
           style="display: inline-block; background: #0070ba; color: #fff; font-size: 16px;
                  font-weight: 700; text-decoration: none; padding: 14px 40px;
                  border-radius: 8px; letter-spacing: 0.5px;">
          Pay ${gross:.2f} with PayPal
        </a>
        <p style="color: #888; font-size: 11px; margin-top: 8px;">
          Includes ${fee:.2f} processing fee &middot; Invoice total: ${net:.2f}
        </p>
      </div>
    """


def build_invoice_email(
    client_name: str,
    invoice_number: str,
    total_amount: str,
    due_date: str,
    payment_method: str,
    items_html: str,
    provider_name: str = "AjayaDesign",
) -> tuple[str, str]:
    """Build an invoice email. Returns (subject, html_body)."""
    subject = f"Invoice {invoice_number} from {provider_name}"
    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px;">
      <div style="text-align: center; margin-bottom: 32px;">
        <h1 style="color: #111; font-size: 24px; margin: 0;">💰 Invoice {invoice_number}</h1>
        <p style="color: #666; margin-top: 8px;">from {provider_name}</p>
      </div>

      <div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
        <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0;">
          Hi <strong>{client_name}</strong>,
        </p>
        <p style="color: #333; font-size: 16px; line-height: 1.6;">
          Here is your invoice for web design services.
        </p>

        {items_html}

        <div style="border-top: 2px solid #e5e7eb; margin-top: 16px; padding-top: 16px;">
          <table style="width: 100%;">
            <tr>
              <td style="font-size: 18px; font-weight: 700; color: #111;">Total Due</td>
              <td style="text-align: right; font-size: 18px; font-weight: 700; color: #111;">${total_amount}</td>
            </tr>
            <tr>
              <td style="font-size: 13px; color: #666;">Due Date</td>
              <td style="text-align: right; font-size: 13px; color: #666;">{due_date}</td>
            </tr>
            <tr>
              <td style="font-size: 13px; color: #666;">Payment Method</td>
              <td style="text-align: right; font-size: 13px; color: #666;">{payment_method.title() if payment_method else 'See below'}</td>
            </tr>
          </table>
        </div>
      </div>

      <div style="background: #fef3c7; border: 1px solid #fcd34d; border-radius: 8px; padding: 16px; margin-bottom: 24px;">
        <p style="color: #92400e; font-size: 14px; margin: 0; font-weight: 600;">Payment Instructions</p>
        <p style="color: #92400e; font-size: 13px; margin-top: 8px;">
          Please send payment via <strong>{payment_method.title() if payment_method else 'your preferred method'}</strong>.
          If you have questions about payment, reply to this email.
        </p>
      </div>

      {_build_paypal_button_html(total_amount, payment_method)}

      <p style="color: #9ca3af; font-size: 13px; text-align: center; margin-top: 32px;">
        {provider_name} · 13721 Andrew Abernathy Pass, Manor, TX 78653
      </p>
    </div>
    """
    return subject, html


def build_signed_notification_email(
    contract_short_id: str,
    client_name: str,
    project_name: str,
    signed_at: str,
) -> tuple[str, str]:
    """Notification to admin that a contract was signed. Returns (subject, html)."""
    subject = f"✅ Contract {contract_short_id} signed by {client_name}"
    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px;">
      <h1 style="color: #059669; text-align: center;">✅ Contract Signed!</h1>
      <div style="background: #ecfdf5; border: 1px solid #6ee7b7; border-radius: 12px; padding: 24px; margin: 24px 0;">
        <p style="margin: 0 0 8px;"><strong>Contract:</strong> #{contract_short_id}</p>
        <p style="margin: 0 0 8px;"><strong>Client:</strong> {client_name}</p>
        <p style="margin: 0 0 8px;"><strong>Project:</strong> {project_name}</p>
        <p style="margin: 0;"><strong>Signed At:</strong> {signed_at}</p>
      </div>
      <p style="color: #666; font-size: 14px; text-align: center;">
        You can view the signed contract in your admin dashboard.
      </p>
    </div>
    """
    return subject, html
