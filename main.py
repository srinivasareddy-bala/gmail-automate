import imaplib
import email
import os
from dotenv import load_dotenv
from docsumm_ai import summarize

# --- Configuration ---
load_dotenv()
EMAIL = os.getenv("GMAIL_ACCOUNT")
APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
IMAP_SERVER = "imap.gmail.com"


def get_body(msg):
    """NEW: Extracts the plain text body from an email message object."""
    if msg.is_multipart():
        # Emails are often like ZIP files; we 'walk' through the contents
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get_content_disposition())

            # Only grab the text part, ignore HTML and attachments
            if content_type == "text/plain" and "attachment" not in content_disposition:
                return part.get_payload(decode=True).decode()
    else:
        # Simple emails aren't multipart, so we just grab the content directly
        return msg.get_payload(decode=True).decode()

    return "[No Plain Text Body Found]"


def read_inbox():
    # Connect to Gmail's IMAP server
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)

    try:
        mail.login(EMAIL, APP_PASSWORD)
        mail.select("inbox")  # Connect to the inbox

        # Search for all unread emails
        status, messages = mail.search(None, 'UNSEEN')

        # messages[0] contains a space-separated list of email IDs
        for num in messages[0].split():
            # Fetch the email body (RFC822) for the given ID
            status, data = mail.fetch(num, '(RFC822)')

            for response_part in data:
                if isinstance(response_part, tuple):
                    # Parse the raw bytes into a readable message object
                    msg = email.message_from_bytes(response_part[1])
                    subject = msg["subject"]
                    sender = msg["from"]
                    body = get_body(msg)
                    summary = summarize(body)
                    print(f"Subject: {subject}")
                    print(f"summary: {summary}")
                    print(f"From: {sender}\n" + "-" * 20)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        mail.logout()


if __name__ == "__main__":
    read_inbox()