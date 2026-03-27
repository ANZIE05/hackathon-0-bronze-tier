"""
Orchestrator for AI Employee Email System.

Watches the Needs_Action folder for new emails and processes them
using the EmailAgent to generate replies.
"""

import asyncio
import logging
import time
import os
from pathlib import Path
from datetime import datetime
from typing import Set

from agents.email_agent import EmailAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("orchestrator.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class EmailOrchestrator:
    """
    Orchestrates email processing workflow.
    
    - Watches Needs_Action folder for new markdown files
    - Processes each email through the AI agent
    - Saves replies to Outbox folder
    - Tracks processed files to avoid duplicates
    """
    
    def __init__(
        self,
        needs_action_dir: str = "Needs_Action",
        outbox_dir: str = "Outbox",
        processed_log: str = ".processed_emails.log",
        poll_interval: float = 5.0
    ):
        """
        Initialize the orchestrator.
        
        Args:
            needs_action_dir: Directory to watch for new emails
            outbox_dir: Directory to save generated replies
            processed_log: File to track processed emails
            poll_interval: Seconds between folder checks
        """
        self.base_dir = Path(__file__).parent
        self.needs_action_dir = self.base_dir / needs_action_dir
        self.outbox_dir = self.base_dir / outbox_dir
        self.processed_log = self.base_dir / processed_log
        self.poll_interval = poll_interval
        
        self._processed_files: Set[str] = set()
        self._agent: EmailAgent = None
        
        self._ensure_directories()
        self._load_processed_log()
    
    def _ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        self.needs_action_dir.mkdir(parents=True, exist_ok=True)
        self.outbox_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Watching: {self.needs_action_dir}")
        logger.info(f"Saving to: {self.outbox_dir}")
    
    def _load_processed_log(self) -> None:
        """Load list of already processed files."""
        if self.processed_log.exists():
            with open(self.processed_log, "r") as f:
                self._processed_files = set(line.strip() for line in f if line.strip())
            logger.info(f"Loaded {len(self._processed_files)} processed files from log")
        else:
            self._processed_files = set()
            logger.info("No previous processed files found")
    
    def _mark_as_processed(self, filename: str) -> None:
        """Mark a file as processed and update the log."""
        self._processed_files.add(filename)
        with open(self.processed_log, "a") as f:
            f.write(f"{filename}\n")
    
    def _is_processed(self, filename: str) -> bool:
        """Check if a file has already been processed."""
        return filename in self._processed_files
    
    @property
    def agent(self) -> EmailAgent:
        """Lazy-load the email agent."""
        if self._agent is None:
            self._agent = EmailAgent()
        return self._agent
    
    def _get_email_files(self) -> list[Path]:
        """Get all markdown files in Needs_Action directory."""
        if not self.needs_action_dir.exists():
            return []
        return list(self.needs_action_dir.glob("*.md"))
    
    def _read_email(self, filepath: Path) -> str:
        """Read email content from markdown file."""
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    
    def _save_reply(
        self,
        original_file: str,
        summary: str,
        draft_reply: str
    ) -> Path:
        """Save the generated reply to Outbox."""
        # Extract base filename (e.g., GMAIL_123 from GMAIL_123.md)
        base_name = Path(original_file).stem
        
        # Create output filename
        output_filename = f"reply_{base_name}.md"
        output_path = self.outbox_dir / output_filename
        
        # Format timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Write the reply file
        content = f"""---
type: reply
original_email: {original_file}
generated_at: {timestamp}
---

## Summary
{summary}

## Draft Reply
{draft_reply}
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.info(f"Saved reply to: {output_path}")
        return output_path
    
    def process_email(self, filepath: Path) -> bool:
        """
        Process a single email file.
        
        Args:
            filepath: Path to the email markdown file
            
        Returns:
            True if successful, False otherwise
        """
        filename = filepath.name
        
        if self._is_processed(filename):
            logger.debug(f"Skipping already processed: {filename}")
            return False
        
        logger.info(f"Processing: {filename}")
        
        try:
            # Read email content
            email_content = self._read_email(filepath)
            
            # Generate reply using AI agent
            response = self.agent.generate_reply(email_content)
            
            # Save the reply
            self._save_reply(filename, response.summary, response.draft_reply)
            
            # Mark as processed
            self._mark_as_processed(filename)
            
            logger.info(f"Successfully processed: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to process {filename}: {e}")
            return False
    
    def process_existing(self) -> int:
        """
        Process all existing unprocessed emails.
        
        Returns:
            Number of emails processed
        """
        count = 0
        email_files = self._get_email_files()
        
        logger.info(f"Found {len(email_files)} email files")
        
        for filepath in email_files:
            if self.process_email(filepath):
                count += 1
        
        return count
    
    def start_watching(self) -> None:
        """
        Start watching the Needs_Action folder for new emails.
        
        Blocks indefinitely until interrupted (Ctrl+C).
        """
        logger.info(f"Starting email watcher (poll interval: {self.poll_interval}s)")
        logger.info("Press Ctrl+C to stop")
        
        try:
            while True:
                email_files = self._get_email_files()
                
                for filepath in email_files:
                    self.process_email(filepath)
                
                time.sleep(self.poll_interval)
                
        except KeyboardInterrupt:
            logger.info("Watcher stopped by user")
    
    def run_once(self) -> int:
        """
        Process all current emails once without continuous watching.
        
        Returns:
            Number of emails processed
        """
        logger.info("Running single pass processing")
        return self.process_existing()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="AI Employee Email Orchestrator")
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Continuously watch for new emails"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Poll interval in seconds (default: 5.0)"
    )
    parser.add_argument(
        "--linkedin",
        type=str,
        metavar="TOPIC",
        help="Generate and post to LinkedIn with the given topic"
    )

    args = parser.parse_args()

    orchestrator = EmailOrchestrator(poll_interval=args.interval)

    if args.linkedin:
        # LinkedIn posting mode
        from agents.linkedin_agent import generate_linkedin_post
        from linkedin.linkedin_bot import post_to_linkedin

        print("🔗 LinkedIn Auto-Poster")
        print("=" * 50)
        
        content = generate_linkedin_post(args.linkedin)
        print("📄 Generated content:")
        print(content)
        print("=" * 50)
        
        success = asyncio.run(post_to_linkedin(content, headless=False))
        
        if success:
            print("🎉 LinkedIn post completed!")
        else:
            print("⚠️ LinkedIn posting encountered issues")
    elif args.watch:
        orchestrator.start_watching()
    else:
        count = orchestrator.run_once()
        logger.info(f"Processed {count} email(s)")


if __name__ == "__main__":
    main()
