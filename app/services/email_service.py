"""
Email Service for sending credentials and notifications
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app

logger = logging.getLogger(__name__)


def send_credentials_email(email, username, password, role, clinic_name=None):
    """
    Send login credentials to newly created user
    
    Args:
        email: User's email address
        username: Login username
        password: Login password (plain text, before hashing)
        role: User role (doctor, receptionist)
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
            logger.warning("Email not configured. Skipping credential email.")
            return False
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Your Clinic Management System Login Credentials'
        msg['From'] = mail_sender
        msg['To'] = email
        
        # Plain text version
        text = f"""
Welcome to Clinic Management System!

Your account has been created successfully.

Login Credentials:
-----------------
Username: {username}
Password: {password}
Role: {role.title()}
{f'Clinic: {clinic_name}' if clinic_name else ''}

Login URL: http://129.121.75.225

Please change your password after first login.

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
        .credentials {{ background: white; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #4a90a4; }}
        .credentials table {{ width: 100%; }}
        .credentials td {{ padding: 8px 0; }}
        .credentials td:first-child {{ font-weight: bold; width: 100px; }}
        .button {{ display: inline-block; background: #4a90a4; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
        .warning {{ background: #fff3cd; padding: 10px; border-radius: 5px; margin-top: 20px; font-size: 13px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏥 Clinic Management System</h1>
        </div>
        <div class="content">
            <h2>Welcome!</h2>
            <p>Your account has been created successfully. Below are your login credentials:</p>
            
            <div class="credentials">
                <table>
                    <tr>
                        <td>Username:</td>
                        <td><strong>{username}</strong></td>
                    </tr>
                    <tr>
                        <td>Password:</td>
                        <td><strong>{password}</strong></td>
                    </tr>
                    <tr>
                        <td>Role:</td>
                        <td><strong>{role.title()}</strong></td>
                    </tr>
                    {f'<tr><td>Clinic:</td><td><strong>{clinic_name}</strong></td></tr>' if clinic_name else ''}
                </table>
            </div>
            
            <center>
                <a href="http://129.121.75.225" class="button">Login Now</a>
            </center>
            
            <div class="warning">
                ⚠️ <strong>Important:</strong> Please change your password after your first login for security purposes.
            </div>
        </div>
        <div class="footer">
            <p>If you did not request this account, please contact the administrator.</p>
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
        
        logger.info(f"Credentials email sent to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send credentials email to {email}: {e}")
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
