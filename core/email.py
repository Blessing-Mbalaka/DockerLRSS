"""
Email utility functions for CHIETA LMS
Handles all email communications with proper logging and error handling
"""

import logging
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def check_smtp(timeout=None):
    """
    Open (and close) a real connection to the configured mail server.

    Returns (ok: bool, message: str). Never raises, so it is safe to call from
    health checks, management commands and admin pages.
    """
    backend = settings.EMAIL_BACKEND
    if 'smtp' not in backend:
        return False, f"Email backend is '{backend}', so no real emails will be sent."
    try:
        from django.core.mail import get_connection
        connection = get_connection(timeout=timeout or settings.EMAIL_TIMEOUT)
        connection.open()
        connection.close()
        return True, f"SMTP OK ({settings.EMAIL_HOST}:{settings.EMAIL_PORT})."
    except Exception as exc:
        return False, (
            f"SMTP connection to {settings.EMAIL_HOST}:{settings.EMAIL_PORT} failed: "
            f"{exc.__class__.__name__}: {exc}"
        )


def safe_send(subject, message, recipients, html_message=None):
    """
    Send an email and report the outcome instead of hiding failures.

    Returns (ok: bool, error: str). Failures are logged and never raised.
    """
    if isinstance(recipients, str):
        recipients = [recipients]
    try:
        sent = send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipients,
            fail_silently=False,
            html_message=html_message,
        )
        if not sent:
            raise RuntimeError("Mail backend reported 0 messages sent")
        return True, ""
    except Exception as exc:
        logger.error("Email '%s' to %s failed: %s", subject, recipients, exc)
        return False, f"{exc.__class__.__name__}: {exc}"


def send_account_creation_email(email, first_name, password):
    """
    Send account creation email with credentials to new user
    
    Args:
        email (str): User's email address
        first_name (str): User's first name
        password (str): Temporary password
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        subject = 'Your CHIETA LMS Account'
        
        # Plain text message
        message = f"""Hello {first_name},

Your account has been created for the CHIETA Learning Management System.

Login Credentials:
Username: {email}
Password: {password}

Important: Please change your password after logging in for security purposes.

If you did not request this account, please contact support immediately.

Best regards,
CHIETA LMS Team
"""
        
        # HTML message (optional - looks more professional)
        html_message = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c3e50;">Welcome to CHIETA LMS</h2>
                    <p>Hello {first_name},</p>
                    <p>Your account has been created successfully.</p>
                    
                    <div style="background-color: #f4f4f4; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="margin-top: 0;">Login Credentials:</h3>
                        <p><strong>Username:</strong> {email}</p>
                        <p><strong>Password:</strong> {password}</p>
                    </div>
                    
                    <p style="color: #e74c3c;"><strong>Important:</strong> Please change your password after logging in.</p>
                    
                    <p>If you did not request this account, please contact support immediately.</p>
                    
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                    <p style="color: #7f8c8d; font-size: 12px;">
                        This is an automated message from CHIETA LMS. Please do not reply to this email.
                    </p>
                </div>
            </body>
        </html>
        """
        
        # Send email with both plain text and HTML versions
        email_message = EmailMultiAlternatives(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email]
        )
        email_message.attach_alternative(html_message, "text/html")
        email_message.send(fail_silently=False)
        
        logger.info(f"Account creation email sent successfully to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send account creation email to {email}: {str(e)}")
        return False


def send_registration_pending_email(email, first_name):
    """Tell a new registrant their request was received and awaits activation."""
    ok, _ = safe_send(
        'Your CHIETA LMS registration was received',
        f"Hello {first_name or ''},\n\n"
        "Thank you for registering for the CHIETA Learning Management System.\n"
        "Your account is pending activation by an administrator. "
        "You will receive another email once it has been activated.\n\n"
        "This is an automated message from CHIETA LMS.",
        [email],
    )
    return ok


def send_account_activation_email(email, first_name):
    """
    Send notification when admin activates a user's account
    
    Args:
        email (str): User's email address
        first_name (str): User's first name
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        subject = 'Your CHIETA LMS Account Has Been Activated'
        
        message = f"""Hello {first_name},

Good news! Your CHIETA LMS account has been activated by an administrator.

You can now log in using your credentials at: {settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'your LMS portal'}

If you have any questions, please contact support.

Best regards,
CHIETA LMS Team
"""
        
        html_message = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #27ae60;">Account Activated!</h2>
                    <p>Hello {first_name},</p>
                    <p>Good news! Your CHIETA LMS account has been activated.</p>
                    <p>You can now log in and access all available resources.</p>
                    
                    <div style="margin: 30px 0; text-align: center;">
                        <a href="{settings.SITE_URL if hasattr(settings, 'SITE_URL') else '#'}" 
                           style="background-color: #27ae60; color: white; padding: 12px 30px; 
                                  text-decoration: none; border-radius: 5px; display: inline-block;">
                            Login Now
                        </a>
                    </div>
                    
                    <p>If you have any questions, please contact support.</p>
                    
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                    <p style="color: #7f8c8d; font-size: 12px;">
                        This is an automated message from CHIETA LMS.
                    </p>
                </div>
            </body>
        </html>
        """
        
        email_message = EmailMultiAlternatives(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email]
        )
        email_message.attach_alternative(html_message, "text/html")
        email_message.send(fail_silently=False)
        
        logger.info(f"Account activation email sent successfully to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send account activation email to {email}: {str(e)}")
        return False


def send_password_reset_email(email, first_name, reset_link):
    """
    Send password reset link to user
    
    Args:
        email (str): User's email address
        first_name (str): User's first name
        reset_link (str): Password reset URL
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        subject = 'Password Reset Request - CHIETA LMS'
        
        message = f"""Hello {first_name},

We received a request to reset your password for your CHIETA LMS account.

Click the link below to reset your password:
{reset_link}

This link will expire in 24 hours for security reasons.

If you did not request this reset, please ignore this email or contact support if you have concerns.

Best regards,
CHIETA LMS Team
"""
        
        html_message = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c3e50;">Password Reset Request</h2>
                    <p>Hello {first_name},</p>
                    <p>We received a request to reset your password.</p>
                    
                    <div style="margin: 30px 0; text-align: center;">
                        <a href="{reset_link}" 
                           style="background-color: #3498db; color: white; padding: 12px 30px; 
                                  text-decoration: none; border-radius: 5px; display: inline-block;">
                            Reset Password
                        </a>
                    </div>
                    
                    <p style="color: #e74c3c; font-size: 14px;">
                        <strong>Note:</strong> This link will expire in 24 hours.
                    </p>
                    
                    <p>If you did not request this reset, please ignore this email.</p>
                    
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                    <p style="color: #7f8c8d; font-size: 12px;">
                        This is an automated message from CHIETA LMS.
                    </p>
                </div>
            </body>
        </html>
        """
        
        email_message = EmailMultiAlternatives(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email]
        )
        email_message.attach_alternative(html_message, "text/html")
        email_message.send(fail_silently=False)
        
        logger.info(f"Password reset email sent successfully to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {str(e)}")
        return False


def send_notification_email(email, subject, message_text, html_content=None):
    """
    Generic notification email sender
    
    Args:
        email (str): Recipient's email address
        subject (str): Email subject
        message_text (str): Plain text message
        html_content (str, optional): HTML version of message
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        if html_content:
            email_message = EmailMultiAlternatives(
                subject,
                message_text,
                settings.DEFAULT_FROM_EMAIL,
                [email]
            )
            email_message.attach_alternative(html_content, "text/html")
            email_message.send(fail_silently=False)
        else:
            send_mail(
                subject,
                message_text,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
        
        logger.info(f"Notification email sent successfully to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send notification email to {email}: {str(e)}")
        return False


def send_assessment_notification(email, first_name, assessment_name, due_date=None):
    """
    Send notification about new assessment availability
    
    Args:
        email (str): Student's email address
        first_name (str): Student's first name
        assessment_name (str): Name of the assessment
        due_date (datetime, optional): Assessment due date
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        subject = f'New Assessment Available: {assessment_name}'
        
        due_date_text = f"\n\nDue Date: {due_date.strftime('%B %d, %Y')}" if due_date else ""
        
        message = f"""Hello {first_name},

A new assessment is now available for you to complete:

Assessment: {assessment_name}{due_date_text}

Please log in to your CHIETA LMS account to access the assessment.

Good luck!

Best regards,
CHIETA LMS Team
"""
        
        html_message = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c3e50;">New Assessment Available</h2>
                    <p>Hello {first_name},</p>
                    <p>A new assessment is now available:</p>
                    
                    <div style="background-color: #f4f4f4; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="margin-top: 0;">{assessment_name}</h3>
                        {f'<p><strong>Due Date:</strong> {due_date.strftime("%B %d, %Y")}</p>' if due_date else ''}
                    </div>
                    
                    <div style="margin: 30px 0; text-align: center;">
                        <a href="{settings.SITE_URL if hasattr(settings, 'SITE_URL') else '#'}" 
                           style="background-color: #3498db; color: white; padding: 12px 30px; 
                                  text-decoration: none; border-radius: 5px; display: inline-block;">
                            Access Assessment
                        </a>
                    </div>
                    
                    <p>Good luck!</p>
                    
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                    <p style="color: #7f8c8d; font-size: 12px;">
                        This is an automated message from CHIETA LMS.
                    </p>
                </div>
            </body>
        </html>
        """
        
        email_message = EmailMultiAlternatives(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email]
        )
        email_message.attach_alternative(html_message, "text/html")
        email_message.send(fail_silently=False)
        
        logger.info(f"Assessment notification email sent successfully to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send assessment notification to {email}: {str(e)}")
        return False
