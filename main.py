import imaplib
import email
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup
# from docsumm_ai import summarize
# from transformers import pipeline # not working

from mlx_lm import load, generate

# Load the model
model, tokenizer = load("mlx-community/Llama-3.2-3B-Instruct-4bit")


# --- Configuration ---
load_dotenv()
EMAIL = os.getenv("GMAIL_ACCOUNT")
APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
IMAP_SERVER = os.getenv("IMAP_SERVER")


def get_body_with_signals(msg):
    """
    EXTRACTS body text + HTML signals (like ALT tags) to help 
    the AI identify banners and promotions.
    """
    body = ""
    signals = []
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            
            # 1. Capture Plain Text
            if content_type == "text/plain":
                text = part.get_payload(decode=True).decode(errors='ignore')
                body += text
            
            # 2. Scrape HTML for "Hidden" Context
            elif content_type == "text/html":
                html_content = part.get_payload(decode=True).decode(errors='ignore')
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Get 'alt' text from images (Crucial for banners like Kforce)
                alt_texts = [img.get('alt') for img in soup.find_all('img') if img.get('alt')]
                if alt_texts:
                    signals.append(f"[Images Detected: {', '.join(alt_texts)}]")
                
                # Check for "Unsubscribe" links
                if soup.find(string=lambda t: "unsubscribe" in t.lower()):
                    signals.append("[Automated Content: Yes]")
                
                if not body:
                    body += soup.get_text(separator=' ')
    else:
        body = msg.get_payload(decode=True).decode(errors='ignore')

    # Combine signals and body
    full_context = "\n".join(signals) + "\n" + body
    return full_context[:2500] # Limit to 2500 chars for RAM efficiency



def summarize_with_triage(subject, sender, context):
    """
    THE TRIAGE ENGINE:
    Receives Subject, Sender, and Context to produce the final summary.
    """
    # Industry Standard: Few-shot prompting with the context clues
    prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
                You are an AI Email Filter. Your goal is to determine if an email is "Useful" or "Noise."

                DECISION RULES:
                1. USEFUL: Personal messages, meeting invites, bills, or educational content. 
                -> TASK: Provide a 2-bullet point summary of the value/action.
                2. NOISE: Generic promotions, banner ads, or automated alerts. 
                -> TASK: Provide a 1-sentence description of what it is.

                ### EXAMPLES
                Input: Subject: Invoice #123 | Body: Your monthly bill is ready for $50.
                Output: [USEFUL] Monthly bill for $50 is due. Check the attachment for details.

                Input: Subject: Career Update | Body: [Visual Context: Kforce Logo] Let's Connect.
                Output: [NOISE] This is a promotional recruitment banner from Kforce.

                ### YOUR TASK
                Input: Subject: {subject} | Sender: {sender} | Body: {context[:2000]}
                Output: <|eot_id|><|start_header_id|>assistant<|end_header_id|>"""

    summary = generate(model, tokenizer, prompt=prompt, max_tokens=500, verbose=False)
    return summary.strip()


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
    search_query, message_ids = 'is:unread', []
    if status == 'OK':
        status, message_ids = mail.search( None, 'X-GM-RAW', f'"{search_query}"')
        print(f"Successfully selected {message_ids}")
    else:
        print(f"""search a folder: {folder_name} that wasn't selected, 
              or your search syntax: {search_query} was wrong""")
        exit()

    try:
        # id_string = ",".join([id.decode() if isinstance(id, bytes) else str(id) for id in message_ids[0].split()])
        # status, response = mail.store(id_string, '+X-GM-LABELS', '\\Trash')

        # print(status, response)



        # messages[0] contains a space-separated list of mail IDs
        for num in message_ids[0].split():
            # Fetch the mail body (RFC822) for the given ID
            status, data = mail.fetch(num, '(RFC822)')
            # print(data, len(data), sep = '\n')
            for response_part in data:
                if isinstance(response_part, tuple):
                    # Parse the raw bytes into a readable message object
                    msg = email.message_from_bytes(response_part[1])
                    subject = msg.get("subject", "No Subject")
                    sender = msg.get("from", "Unknown")
                    context = get_body_with_signals(msg)
                    print(f"From: {sender}\n" + "-" * 20)
                    print(f"Subject: {subject}")
                    # print(f"Body:\n {body}")
                    summary = summarize_with_triage(subject, sender, context)
                    print(f"Summary:\n {summary}")
                    

    except Exception as e:
        print(f"Error: {e}")
    finally:
        mail.logout()


if __name__ == "__main__":
    read_inbox()