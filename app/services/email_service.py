"""
Email Service for sending credentials and notifications
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app

logger = logging.getLogger(__name__)


def send_welcome_email(email, username, role, set_password_link, clinic_name=None):
    """
    Send welcome email with link to set password (first time login)
    
    Args:
        email: User's email address
        username: Login username
        role: User role (doctor, receptionist)
        set_password_link: Link to set password
        clinic_name: Name of the clinic (optional)
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Get email config
        mail_server = current_app.config.get('MAIL_SERVER')
        mail_port = current_app.config.get('MAIL_PORT')
        mail_use_tls = current_app.config.get('MAIL_USE_TLS')
        mail_username = current_app.config.get('MAIL_USERNAME')
        mail_password = current_app.config.get('MAIL_PASSWORD')
        mail_sender = current_app.config.get('MAIL_DEFAULT_SENDER')
        
        # Check if email is configured
        if not mail_username or not mail_password:
            logger.warning("Email not configured. Skipping welcome email.")
            return False
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Welcome to Clinic Management System - Set Your Password'
        msg['From'] = mail_sender
        msg['To'] = email
        
        # Plain text version
        text = f"""
Welcome to Clinic Management System!

Your account has been created successfully.

Account Details:
----------------
Username: {username}
Role: {role.title()}
{f'Clinic: {clinic_name}' if clinic_name else ''}

To complete your account setup, please set your password by clicking the link below:
{set_password_link}

This link will expire in 24 hours.

If you did not request this account, please contact the administrator.

Best regards,
Clinic Management System
        """
        
        # HTML version
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #4a90a4; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border: 1px solid #ddd; }}
        .details {{ background: white; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #4a90a4; }}
        .details table {{ width: 100%; }}
        .details td {{ padding: 8px 0; }}
        .details td:first-child {{ font-weight: bold; width: 100px; }}
        .button {{ display: inline-block; background: #27ae60; color: white; padding: 15px 40px; text-decoration: none; border-radius: 5px; margin: 20px 0; font-size: 16px; }}
        .button:hover {{ background: #219a52; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
        .warning {{ background: #fff3cd; padding: 15px; border-radius: 5px; margin-top: 20px; font-size: 13px; }}
        .link-text {{ word-break: break-all; background: #eee; padding: 10px; border-radius: 5px; font-size: 12px; margin-top: 15px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏥 Welcome!</h1>
        </div>
        <div class="content">
            <h2>Your account has been created</h2>
            <p>You have been added to the Clinic Management System. Please set your password to complete your account setup.</p>
            
            <div class="details">
                <table>
                    <tr>
                        <td>Username:</td>
                        <td><strong>{username}</strong></td>
                    </tr>
                    <tr>
                        <td>Role:</td>
                        <td><strong>{role.title()}</strong></td>
                    </tr>
                    {f'<tr><td>Clinic:</td><td><strong>{clinic_name}</strong></td></tr>' if clinic_name else ''}
                </table>
            </div>
            
            <center>
                <a href="{set_password_link}" class="button">Set Your Password</a>
            </center>
            
            <p class="link-text">Or copy this link: {set_password_link}</p>
            
            <div class="warning">
                ⏰ <strong>This link will expire in 24 hours.</strong><br>
                If you did not request this account, please ignore this email.
            </div>
        </div>
        <div class="footer">
            <p>© 2026 Clinic Management System</p>
        </div>
    </div>
</body>
</html>
        """
        
        # Attach parts
        part1 = MIMEText(text, 'plain')
        part2 = MIMEText(html, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        # Send email
        with smtplib.SMTP(mail_server, mail_port) as server:
            if mail_use_tls:
                server.starttls()
            server.login(mail_username, mail_password)
            server.sendmail(mail_sender, email, msg.as_string())
        
        logger.info(f"Welcome email sent to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send welcome email to {email}: {e}")
        return False


def send_password_reset_email(email, reset_link, user_name):
    """
    Send password reset link to user
    
    Args:
        email: User's email address
        reset_link: Password reset URL with token
        user_name: User's name for personalization
    
    Returns:
        bool: True if email sent successfully
    """
    try:
        mail_server = current_app.config.get('MAIL_SERVER')
        mail_port = current_app.config.get('MAIL_PORT')
        mail_use_tls = current_app.config.get('MAIL_USE_TLS')
        mail_username = current_app.config.get('MAIL_USERNAME')
        mail_password = current_app.config.get('MAIL_PASSWORD')
        mail_sender = current_app.config.get('MAIL_DEFAULT_SENDER')
        
        if not mail_username or not mail_password:
            logger.warning("Email not configured. Skipping password reset email.")
            return False
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Password Reset - Clinic Management System'
        msg['From'] = mail_sender
        msg['To'] = email
        
        # Plain text version
        text = f"""
Hello {user_name},

You requested to reset your password for Clinic Management System.

Click the link below to reset your password:
{reset_link}

This link will expire in 1 hour.

If you did not request this, please ignore this email.

Best regards,
Clinic Management System
        """
        
        # HTML version
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #4a90a4; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border: 1px solid #ddd; }}
        .button {{ display: inline-block; background: #4a90a4; color: white; padding: 15px 40px; text-decoration: none; border-radius: 5px; margin: 20px 0; font-size: 16px; }}
        .button:hover {{ background: #357a8c; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
        .warning {{ background: #fff3cd; padding: 15px; border-radius: 5px; margin-top: 20px; font-size: 13px; }}
        .link-text {{ word-break: break-all; background: #eee; padding: 10px; border-radius: 5px; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 Password Reset</h1>
        </div>
        <div class="content">
            <h2>Hello {user_name},</h2>
            <p>You requested to reset your password for Clinic Management System.</p>
            <p>Click the button below to reset your password:</p>
            
            <center>
                <a href="{reset_link}" class="button">Reset Password</a>
            </center>
            
            <p>Or copy and paste this link in your browser:</p>
            <p class="link-text">{reset_link}</p>
            
            <div class="warning">
                ⏰ <strong>This link will expire in 1 hour.</strong><br>
                If you did not request this password reset, please ignore this email.
            </div>
        </div>
        <div class="footer">
            <p>© 2026 Clinic Management System</p>
        </div>
    </div>
</body>
</html>
        """
        
        part1 = MIMEText(text, 'plain')
        part2 = MIMEText(html, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        with smtplib.SMTP(mail_server, mail_port) as server:
            if mail_use_tls:
                server.starttls()
            server.login(mail_username, mail_password)
            server.sendmail(mail_sender, email, msg.as_string())
        
        logger.info(f"Password reset email sent to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {e}")
        return False


def send_email(to_email, subject, body_text, body_html=None):
    """
    Generic email sending function
    
    Args:
        to_email: Recipient email
        subject: Email subject
        body_text: Plain text body
        body_html: HTML body (optional)
    
    Returns:
        bool: True if sent successfully
    """
    try:
        mail_server = current_app.config.get('MAIL_SERVER')
        mail_port = current_app.config.get('MAIL_PORT')
        mail_use_tls = current_app.config.get('MAIL_USE_TLS')
        mail_username = current_app.config.get('MAIL_USERNAME')
        mail_password = current_app.config.get('MAIL_PASSWORD')
        mail_sender = current_app.config.get('MAIL_DEFAULT_SENDER')
        
        if not mail_username or not mail_password:
            logger.warning("Email not configured")
            return False
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = mail_sender
        msg['To'] = to_email
        
        msg.attach(MIMEText(body_text, 'plain'))
        if body_html:
            msg.attach(MIMEText(body_html, 'html'))
        
        with smtplib.SMTP(mail_server, mail_port) as server:
            if mail_use_tls:
                server.starttls()
            server.login(mail_username, mail_password)
            server.sendmail(mail_sender, to_email, msg.as_string())
        
        logger.info(f"Email sent to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False
