import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import logging

logger = logging.getLogger(__name__)

def send_gmail(sender_email, app_password, recipient_email, subject, body, attachments=None):
    """
    Sends an email using Gmail SMTP with optional attachments.
    attachments: List of dicts or objects with 'name' and 'content' (bytes)
    """
    if not sender_email or not app_password:
        return False, "Gmail credentials missing."
        
    try:
        # Create a multipart message
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = recipient_email
        message["Subject"] = subject

        # Add body to email
        message.attach(MIMEText(body, "plain"))

        # Add attachments
        if attachments:
            for att in attachments:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(att['content'])
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename= {att['name']}",
                )
                message.attach(part)

        # Create secure connection with server and send email
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, app_password)
            server.sendmail(sender_email, recipient_email, message.as_string())
            
        return True, "Email sent successfully."
    except Exception as e:
        logger.error(f"Gmail Send Error: {e}")
        return False, str(e)

