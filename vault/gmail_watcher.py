"""
Gmail Watcher for Personal AI Employee

This script monitors Gmail for new messages and creates action files
in the Needs_Action folder when certain criteria are met.
"""

import os
import logging
from pathlib import Path
from datetime import datetime

from base_watcher import BaseWatcher

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gmail_watcher.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class GmailWatcher(BaseWatcher):
    """
    Gmail watcher that monitors for new emails.
    
    For production use, configure Gmail API credentials via environment variables:
    - GMAIL_CREDENTIALS_PATH: Path to OAuth2 credentials JSON
    - GMAIL_TOKEN_PATH: Path to saved token file
    """

    def __init__(self, vault_path: str = ".", check_interval: int = 60):
        super().__init__(vault_path, check_interval)
        self.inbox_path = self.vault_path / "Inbox"
        self.inbox_path.mkdir(exist_ok=True)
        
        # Gmail API configuration (for production use)
        self.credentials_path = os.environ.get('GMAIL_CREDENTIALS_PATH')
        self.token_path = os.environ.get('GMAIL_TOKEN_PATH', 'token.json')
        self.service = None
        
        # Simulated email counter for demo
        self._sim_email_counter = 0

    def _connect_gmail_api(self):
        """
        Connect to Gmail API using OAuth2 credentials.
        For production use - requires credentials setup.
        """
        if not self.credentials_path:
            logger.warning("GMAIL_CREDENTIALS_PATH not set, using simulation mode")
            return None

        try:
            from gmail_auth import authenticate_gmail
            
            self.service = authenticate_gmail(
                credentials_path=self.credentials_path,
                token_path=self.token_path
            )
            
            if self.service:
                logger.info("Connected to Gmail API")
            return self.service

        except Exception as e:
            logger.error(f"Failed to connect to Gmail API: {str(e)}")
            return None

    def check_for_updates(self) -> list:
        """
        Check for new emails from Gmail.
        Uses simulation mode if Gmail API credentials are not configured.
        """
        # Try real Gmail API first
        if self.service is None and self.credentials_path:
            self._connect_gmail_api()
        
        if self.service:
            return self._check_gmail_real()
        else:
            return self._check_gmail_simulated()

    def _check_gmail_real(self) -> list:
        """
        Check Gmail using real API connection.
        """
        try:
            results = self.service.users().messages().list(
                userId='me', q='is:unread', maxResults=10
            ).execute()
            
            messages = results.get('messages', [])
            new_emails = []
            
            for msg in messages:
                if msg['id'] not in self.processed_ids:
                    full_msg = self.service.users().messages().get(
                        userId='me', id=msg['id'], format='metadata',
                        metadataHeaders=['From', 'Subject', 'Date']
                    ).execute()
                    
                    headers = {h['name']: h['value'] for h in full_msg['payload']['headers']}
                    
                    new_emails.append({
                        'id': msg['id'],
                        'from': headers.get('From', 'Unknown'),
                        'subject': headers.get('Subject', 'No Subject'),
                        'body': full_msg.get('snippet', ''),
                        'timestamp': headers.get('Date', datetime.now().isoformat()),
                        'priority': 'medium'
                    })
                    self.processed_ids.add(msg['id'])
            
            return new_emails
            
        except Exception as e:
            logger.error(f"Error checking Gmail: {str(e)}")
            return []

    def _check_gmail_simulated(self) -> list:
        """
        Simulate checking for new emails (demo mode).
        """
        # For demo purposes, we'll simulate finding emails periodically
        simulated_emails = [
            {
                'id': f'sim_email_{self._sim_email_counter:03d}',
                'from': 'client@example.com',
                'subject': 'Urgent: Invoice Needed',
                'body': 'Hi, can you please send the invoice for the January project?',
                'timestamp': datetime.now().isoformat(),
            },
            {
                'id': f'sim_email_{self._sim_email_counter + 1:03d}',
                'from': 'supplier@business.com',
                'subject': 'Payment Reminder',
                'body': 'This is a reminder about the outstanding payment of $500.',
                'timestamp': datetime.now().isoformat(),
            }
        ]
        
        self._sim_email_counter += 2

        # Return only emails that haven't been processed yet
        new_emails = []
        for email in simulated_emails:
            if email['id'] not in self.processed_ids:
                new_emails.append(email)
                self.processed_ids.add(email['id'])

        return new_emails

    def create_action_file(self, email_data: dict) -> Path:
        """
        Create a markdown file in the Needs_Action folder for the email.
        """
        # Determine filename based on email ID and timestamp
        filename = f"GMAIL_{email_data['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = self.needs_action_path / filename

        # Create frontmatter for the action file
        frontmatter = f"""---
type: email
from: {email_data['from']}
subject: {email_data['subject']}
received: {email_data['timestamp']}
priority: {email_data.get('priority', 'medium')}
status: pending
---

## Email Content
From: {email_data['from']}
Subject: {email_data['subject']}
Date: {email_data['timestamp']}

{email_data['body']}

## Suggested Actions
- [ ] Review content and determine appropriate response
- [ ] Check Company Handbook for response guidelines
- [ ] Draft response or escalate as needed
- [ ] Update Dashboard with status
"""

        # Write the action file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(frontmatter)

        logger.info(f"Created action file: {filepath}")
        return filepath


def main():
    """Main function to run the Gmail Watcher"""
    # Check if credentials path is set
    credentials_path = os.environ.get('GMAIL_CREDENTIALS_PATH')
    
    if not credentials_path:
        # Default to credentials.json in vault directory
        credentials_path = str(Path("vault/credentials.json").resolve())
        if not Path(credentials_path).exists():
            credentials_path = None
    
    # Initialize the watcher
    watcher = GmailWatcher(
        vault_path=".",
        check_interval=30
    )
    watcher.credentials_path = credentials_path
    
    # Run once for initial setup, or continuously
    print("Gmail Watcher started. Press Ctrl+C to stop.")
    if credentials_path:
        print(f"Using credentials: {credentials_path}")
        print("First run will open browser for OAuth authentication.")
    else:
        print("Running in simulation mode.")
        print("Set GMAIL_CREDENTIALS_PATH or place credentials.json in vault/ for real Gmail API.")
    
    watcher.run()


if __name__ == "__main__":
    main()