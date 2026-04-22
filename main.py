import imaplib
import email
import os
from dotenv import load_dotenv
# from docsumm_ai import summarize
from transformers import pipeline

# --- Configuration ---
load_dotenv()
EMAIL = os.getenv("GMAIL_ACCOUNT")
APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
IMAP_SERVER = os.getenv("IMAP_SERVER")


def get_body(msg):
    """NEW: Extracts the plain text body from an mail message object."""
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

# This downloads a small, specialized summarization model (first time only)
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
#installed torch to use above model in the pipeline

def summarize_email(email_body):
    # Max_length controls the summary size
    summary = summarizer(email_body, max_length=50, min_length=20, do_sample=False)
    return summary[0]['summary_text']

def read_inbox():
    try:

        # Connect to Gmail's IMAP server
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL, APP_PASSWORD)
    except Exception as e:
        print(f"Runtime Exception: {e}")
    
    #mail.list() to see the list of folders in your mail server

    # 1. Use the correct Gmail-specific folder name
    folder_name = '"[Gmail]/All Mail"' 
    list = mail.list()
    status, _ = mail.select(folder_name)
    search_query, message_ids = 'category:Updates is:unread', []
    if status == 'OK':
        status, message_ids = mail.search( None, 'X-GM-RAW', f'"{search_query}"')
        print(f"Successfully selected {message_ids}")
    else:
        print(f"""search a folder: {folder_name} that wasn't selected, 
              or your search syntax: {search_query} was wrong""")
        exit()

    try:
        id_string = ",".join([id.decode() if isinstance(id, bytes) else str(id) for id in message_ids[0].split()])
        status, response = mail.store(id_string, '+X-GM-LABELS', '\\Trash')

        # print(status, response)



        # messages[0] contains a space-separated list of mail IDs
        # for num in messages[0].split():
            # Fetch the mail body (RFC822) for the given ID
            # status, data = mail.fetch(num, '(RFC822)')

            # for response_part in data:
            #     if isinstance(response_part, tuple):
            #         # Parse the raw bytes into a readable message object
            #         msg = mail.message_from_bytes(response_part[1])
            #         subject = msg["subject"]
            #         sender = msg["from"]
            #         body = get_body(msg)
            #         # summary = summarize(body)
            #         summary = summarize_email(body)
            #         print(f"Subject: {subject}")
            #         print(f"summary: {summary}")
                    # print(f"From: {sender}\n" + "-" * 20)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        mail.logout()


if __name__ == "__main__":
    read_inbox()