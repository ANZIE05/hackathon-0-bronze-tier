"""
File System Watcher for Personal AI Employee

This script monitors the Inbox folder for new files and creates action files
in the Needs_Action folder when new files are detected.
"""

import time
import logging
import mimetypes
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from base_watcher import BaseWatcher

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('filesystem_watcher.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class FileDropHandler(FileSystemEventHandler):
    """
    Handler for file system events in the Inbox folder
    """

    def __init__(self, vault_path: str = "."):
        self.vault_path = Path(vault_path)
        self.needs_action_path = self.vault_path / "Needs_Action"
        self.done_path = self.vault_path / "Done"

        # Create directories if they don't exist
        self.needs_action_path.mkdir(exist_ok=True)
        self.done_path.mkdir(exist_ok=True)

        # Track processed files to avoid duplicates
        self.processed_files = set()

        logger.info("FileDropHandler initialized")

    def on_created(self, event):
        """
        Handle file creation events
        """
        if event.is_directory:
            return

        # Get the file path
        file_path = Path(event.src_path)

        # Skip temporary files
        if file_path.name.startswith('.'):
            return

        # Skip if already processed
        if file_path.name in self.processed_files:
            return

        # Add to processed files
        self.processed_files.add(file_path.name)

        # Process the new file
        self.process_new_file(file_path)

    def on_moved(self, event):
        """
        Handle file move events
        """
        if event.is_directory:
            return

        # Get the destination path
        dest_path = Path(event.dest_path)

        # Skip temporary files
        if dest_path.name.startswith('.'):
            return

        # Skip if already processed
        if dest_path.name in self.processed_files:
            return

        # Add to processed files
        self.processed_files.add(dest_path.name)

        # Process the moved file
        self.process_new_file(dest_path)

    def process_new_file(self, file_path: Path):
        """
        Process a new file by creating an action file
        """
        try:
            logger.info(f"Processing new file: {file_path}")

            # Determine file type
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type:
                file_type = mime_type.split('/')[0]  # Get main type (image, text, application, etc.)
            else:
                file_type = 'unknown'

            # Get file size
            size = file_path.stat().st_size

            # Create action file in Needs_Action folder
            action_filename = f"FILE_{file_path.name.replace('.', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            action_filepath = self.needs_action_path / action_filename

            # Create content for the action file
            action_content = f"""---
type: file_drop
original_file: {file_path.name}
full_path: {str(file_path.absolute())}
file_type: {file_type}
size_bytes: {size}
received: {datetime.now().isoformat()}
priority: medium
status: pending
---

## File Information
- **Original Name**: {file_path.name}
- **Path**: {str(file_path)}
- **Type**: {file_type}
- **Size**: {size} bytes
- **Received**: {datetime.now().isoformat()}

## File Content Preview
```
{self.get_file_preview(file_path)}
```

## Suggested Actions
- [ ] Review file content
- [ ] Determine appropriate action based on content
- [ ] Follow Company Handbook guidelines for processing
- [ ] Move to appropriate folder when processed
- [ ] Update Dashboard with status

## Processing Notes
- File was automatically detected in the monitored folder
- Please review and take appropriate action according to Company Handbook
"""

            # Write the action file
            with open(action_filepath, 'w', encoding='utf-8') as f:
                f.write(action_content)

            logger.info(f"Created action file: {action_filepath}")

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")

    def get_file_preview(self, file_path: Path, max_lines: int = 10):
        """
        Get a preview of the file content (first few lines)
        """
        try:
            if file_path.suffix.lower() in ['.txt', '.md', '.csv', '.json', '.py', '.js', '.html', '.css']:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= max_lines:
                            if i < len(open(file_path).readlines()):  # More lines exist
                                lines.append("... (truncated)")
                            break
                        lines.append(line.rstrip())
                return '\n'.join(lines)
            else:
                return f"[Binary file of type {file_path.suffix}]"
        except Exception:
            return "[Could not read file preview]"


class FileSystemWatcher(BaseWatcher):
    """
    Main file system watcher class
    """

    def __init__(self, vault_path: str = ".", inbox_folder: str = "Inbox", check_interval: int = 5):
        super().__init__(vault_path, check_interval)
        self.inbox_path = self.vault_path / inbox_folder

        # Create inbox directory if it doesn't exist
        self.inbox_path.mkdir(exist_ok=True)

        # Set up the event handler
        self.event_handler = FileDropHandler(vault_path=vault_path)

        # Set up the observer
        self.observer = Observer()
        self.observer.schedule(self.event_handler, str(self.inbox_path), recursive=False)

        logger.info(f"FileSystemWatcher initialized for: {self.inbox_path}")

    def check_for_updates(self) -> list:
        """
        This method is not used for filesystem watcher since it uses
        event-driven monitoring via watchdog. Included for BaseWatcher compatibility.
        """
        return []

    def create_action_file(self, item: dict) -> Path:
        """
        This method is not used for filesystem watcher since it creates
        action files directly in the FileDropHandler. Included for BaseWatcher compatibility.
        """
        pass

    def run(self):
        """
        Start monitoring the file system
        """
        logger.info(f"Starting file system monitoring on: {self.inbox_path}")

        try:
            self.observer.start()
            logger.info("File system watcher started successfully")

            try:
                while True:
                    time.sleep(self.check_interval)
            except KeyboardInterrupt:
                logger.info("File system watcher stopped by user")
            finally:
                self.observer.stop()
                self.observer.join()

        except Exception as e:
            logger.error(f"Error in file system watcher: {str(e)}")


def main():
    """Main function to run the File System Watcher"""
    # Initialize the watcher
    watcher = FileSystemWatcher(
        vault_path=".",
        inbox_folder="Inbox",
        check_interval=5  # Check every 5 seconds
    )

    # Run the watcher
    print("File System Watcher started. Monitoring Inbox folder for new files.")
    print("Press Ctrl+C to stop.")
    watcher.run()


if __name__ == "__main__":
    main()