"""
Base Watcher for Personal AI Employee

This module provides an abstract base class for all watcher implementations,
reducing code duplication and ensuring consistent behavior across watchers.
"""

import time
import logging
from pathlib import Path
from abc import ABC, abstractmethod

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BaseWatcher(ABC):
    """
    Abstract base class for all watcher implementations.
    
    All watchers follow the same pattern:
    1. Monitor a source (Gmail, filesystem, etc.)
    2. Check for new items
    3. Create action files in Needs_Action folder
    """

    def __init__(self, vault_path: str = ".", check_interval: int = 60):
        """
        Initialize the base watcher.
        
        Args:
            vault_path: Path to the Obsidian vault
            check_interval: Seconds between checks
        """
        self.vault_path = Path(vault_path)
        self.needs_action_path = self.vault_path / "Needs_Action"
        self.check_interval = check_interval
        
        # Create directories if they don't exist
        self.needs_action_path.mkdir(exist_ok=True)
        
        # Track processed items to avoid duplicates
        self.processed_ids = set()
        
        # Keywords that indicate high priority
        self.priority_keywords = [
            'urgent', 'asap', 'help', 'emergency', 'payment',
            'invoice', 'deadline', 'important', 'critical'
        ]
        
        logger.info(f"{self.__class__.__name__} initialized")

    @abstractmethod
    def check_for_updates(self) -> list:
        """
        Check for new items from the source.
        
        Returns:
            List of new items to process
        """
        pass

    @abstractmethod
    def create_action_file(self, item: dict) -> Path:
        """
        Create a markdown action file for an item.
        
        Args:
            item: Dictionary containing item data
            
        Returns:
            Path to the created action file
        """
        pass

    def determine_priority(self, content: str) -> str:
        """
        Determine priority based on content keywords.
        
        Args:
            content: Text content to analyze
            
        Returns:
            Priority level: 'high', 'medium', or 'low'
        """
        content_lower = content.lower()
        if any(keyword in content_lower for keyword in self.priority_keywords):
            return 'high'
        return 'medium'

    def run_once(self):
        """
        Run one iteration of checking for updates.
        """
        logger.info(f"Checking for updates...")
        
        try:
            new_items = self.check_for_updates()
            
            if new_items:
                logger.info(f"Found {len(new_items)} new items")
                
                for item in new_items:
                    # Determine priority if not already set
                    if 'priority' not in item:
                        content = f"{item.get('subject', '')} {item.get('body', '')} {item.get('text', '')}"
                        item['priority'] = self.determine_priority(content)
                    
                    # Create action file
                    self.create_action_file(item)
            else:
                logger.info("No new items found")
                
        except Exception as e:
            logger.error(f"Error during check: {str(e)}")

    def run(self):
        """
        Main run loop - continuously monitor for updates.
        """
        logger.info(f"Starting {self.__class__.__name__} (checking every {self.check_interval}s)")
        
        try:
            while True:
                self.run_once()
                logger.info(f"Sleeping for {self.check_interval} seconds...")
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            logger.info(f"{self.__class__.__name__} stopped by user")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {str(e)}")
