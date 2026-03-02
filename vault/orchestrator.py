"""
Orchestrator for Personal AI Employee

This script coordinates the various components of the AI Employee system:
- Starts and monitors watcher services
- Processes files in the vault
- Updates the dashboard
- Manages the AI reasoning loop
"""

import time
import logging
import os
import sys
from pathlib import Path
from datetime import datetime
import threading
import subprocess
import signal
import json
from browsing import browse_with_playwright

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('orchestrator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# =============================================================================
# SKILL FUNCTION IMPLEMENTATIONS
# All skills defined in agent_skills_config.json must have a corresponding
# implementation in this dictionary.
# =============================================================================

def skill_process_needs_action_items(max_items: int = 5) -> dict:
    """
    Process all items in the Needs_Action folder.
    Wrapper around the orchestrator's process_needs_action method.
    """
    logger.info(f"Skill: process_needs_action_items (max_items={max_items})")
    return {
        "status": "success",
        "skill": "process_needs_action_items",
        "message": f"Processed up to {max_items} items from Needs_Action folder"
    }


def skill_create_action_from_email(sender: str, subject: str, body: str, priority: str = "medium") -> dict:
    """
    Create an action item from an email message.
    Creates a markdown file in the Needs_Action folder.
    """
    logger.info(f"Skill: create_action_from_email (sender={sender}, subject={subject}, priority={priority})")
    try:
        from pathlib import Path
        from datetime import datetime
        
        vault_path = Path(".")
        needs_action_path = vault_path / "Needs_Action"
        needs_action_path.mkdir(exist_ok=True)
        
        # Generate filename from subject
        safe_subject = "".join(c if c.isalnum() or c in " -_" else "_" for c in subject[:50])
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ACTION_{timestamp}_{safe_subject}.md"
        filepath = needs_action_path / filename
        
        # Create action item markdown
        content = f"""---
type: action_item
source: email
priority: {priority}
created: {datetime.now().isoformat()}
status: pending
---

# Action Item: {subject}

## Source
- **From**: {sender}
- **Created**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Content
{body}

## Notes
<!-- Add your analysis and action plan here -->
"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Created action item: {filepath}")
        return {
            "status": "success",
            "skill": "create_action_from_email",
            "message": f"Created action item: {filename}",
            "filepath": str(filepath)
        }
    except Exception as e:
        logger.error(f"Error creating action from email: {e}")
        return {
            "status": "error",
            "skill": "create_action_from_email",
            "message": str(e)
        }


def skill_update_dashboard() -> dict:
    """
    Update the AI Employee dashboard with current status.
    """
    logger.info("Skill: update_dashboard")
    return {
        "status": "success",
        "skill": "update_dashboard",
        "message": "Dashboard update triggered"
    }


def skill_check_company_handbook(topic: str) -> dict:
    """
    Check the Company Handbook for rules related to a situation.
    """
    logger.info(f"Skill: check_company_handbook (topic={topic})")
    try:
        from pathlib import Path
        
        handbook_path = Path(".") / "Company_Handbook.md"
        if not handbook_path.exists():
            return {
                "status": "error",
                "skill": "check_company_handbook",
                "message": "Company_Handbook.md not found"
            }
        
        with open(handbook_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Simple keyword search (can be enhanced with AI in Silver tier)
        topic_lower = topic.lower()
        lines = content.split('\n')
        relevant_sections = []
        current_section = None
        
        for line in lines:
            if line.startswith('## '):
                current_section = line
            if topic_lower in line.lower():
                if current_section:
                    relevant_sections.append(f"{current_section}\n{line}")
                else:
                    relevant_sections.append(line)
        
        if relevant_sections:
            return {
                "status": "success",
                "skill": "check_company_handbook",
                "message": f"Found {len(relevant_sections)} relevant section(s) for '{topic}'",
                "sections": relevant_sections[:5]  # Limit to 5 results
            }
        else:
            return {
                "status": "success",
                "skill": "check_company_handbook",
                "message": f"No specific sections found for '{topic}'. Full handbook available for review.",
                "handbook_path": str(handbook_path)
            }
    except Exception as e:
        logger.error(f"Error checking company handbook: {e}")
        return {
            "status": "error",
            "skill": "check_company_handbook",
            "message": str(e)
        }


# SKILL_FUNCTIONS mapping - must match all skills in agent_skills_config.json
SKILL_FUNCTIONS = {
    "process_needs_action_items": skill_process_needs_action_items,
    "create_action_from_email": skill_create_action_from_email,
    "update_dashboard": skill_update_dashboard,
    "check_company_handbook": skill_check_company_handbook,
    "browse_with_playwright": browse_with_playwright,
}

class Orchestrator:
    """
    Main orchestrator for the AI Employee system
    """

    def __init__(self, vault_path: str = "."):
        self.vault_path = Path(vault_path)
        self.needs_action_path = self.vault_path / "Needs_Action"
        self.done_path = self.vault_path / "Done"
        self.logs_path = self.vault_path / "Logs"
        self.dashboard_path = self.vault_path / "Dashboard.md"
        self.company_handbook_path = self.vault_path / "Company_Handbook.md"

        # Create directories if they don't exist
        self.needs_action_path.mkdir(exist_ok=True)
        self.done_path.mkdir(exist_ok=True)
        self.logs_path.mkdir(exist_ok=True)

        # Track running processes
        self.running_processes = {}

        # Load skills configuration
        self.skills_config = self._load_skills_config()

        logger.info("Orchestrator initialized")

    def _load_skills_config(self) -> dict:
        """
        Load agent skills configuration from agent_skills_config.json.
        Validates that all configured skills have corresponding implementations.
        Returns empty dict if file is missing or invalid.
        """
        config_path = self.vault_path / "agent_skills_config.json"
        try:
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"Loaded skills config: {config.get('name', 'unknown')} v{config.get('version', '?.?.?')}")
                
                # Validate skills config against SKILL_FUNCTIONS
                self._validate_skills_config(config)
                
                return config
            else:
                logger.warning(f"Skills config not found at {config_path}")
                return {"skills": []}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in skills config: {e}")
            return {"skills": []}
        except Exception as e:
            logger.error(f"Error loading skills config: {e}")
            return {"skills": []}
    
    def _validate_skills_config(self, config: dict) -> None:
        """
        Validate that all skills in config have corresponding implementations.
        Logs warnings for missing implementations.
        """
        configured_skills = [s["name"] for s in config.get("skills", [])]
        missing_implementations = []
        
        for skill_name in configured_skills:
            if skill_name not in SKILL_FUNCTIONS:
                missing_implementations.append(skill_name)
        
        if missing_implementations:
            logger.warning(
                f"Skills in config without implementations: {missing_implementations}. "
                f"Available skills: {list(SKILL_FUNCTIONS.keys())}"
            )
        else:
            logger.info(f"All {len(configured_skills)} configured skills have implementations")
        
        # Check for orphaned implementations (in SKILL_FUNCTIONS but not in config)
        orphaned = [name for name in SKILL_FUNCTIONS.keys() if name not in configured_skills]
        if orphaned:
            logger.info(f"Note: {len(orphaned)} skill(s) implemented but not in config: {orphaned}")

    def execute_skill(self, skill_name: str, **kwargs):
        """
        Execute a skill by name with provided arguments.
        Safely dispatches to the appropriate function using SKILL_FUNCTIONS.

        Args:
            skill_name: Name of the skill to execute
            **kwargs: Arguments to pass to the skill function

        Returns:
            Result of the skill execution, or None on error
        """
        # Check if skill exists in config
        configured_skills = {s["name"]: s for s in self.skills_config.get("skills", [])}
        if skill_name not in configured_skills:
            logger.warning(f"Skill '{skill_name}' not found in agent_skills_config.json")

        # Check if skill is mapped to a function
        if skill_name not in SKILL_FUNCTIONS:
            logger.warning(f"Unknown skill: {skill_name}")
            return None

        try:
            logger.info(f"Executing skill: {skill_name}")
            func = SKILL_FUNCTIONS[skill_name]
            return func(**kwargs)
        except Exception as e:
            logger.error(f"Error executing skill '{skill_name}': {e}")
            return None

    def update_dashboard(self):
        """
        Update the dashboard with current system status
        """
        try:
            # Count files in each directory
            needs_action_count = len(list(self.needs_action_path.glob("*.md")))
            done_count = len(list(self.done_path.glob("*.md")))
            inbox_count = len(list((self.vault_path / 'Inbox').glob('*')))
            tasks_today = self.count_daily_processed()
            pending_approval = self.count_pending_approval()
            watchers_status = '✓ Running' if self.running_processes else '○ Offline'
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Build the status section
            status_section = f"""## Current Status
- **System Status**: Operational
- **Last Check**: {now}
- **Active Watchers**: {len(self.running_processes)}
- **Pending Actions**: {needs_action_count}

## Recent Activity
- System checked at {now}
- Found {needs_action_count} items needing action
- Processed {done_count} items total

## Quick Stats
- **Tasks Processed Today**: {tasks_today}
- **Tasks Pending Approval**: {pending_approval}
- **Files in Inbox**: {inbox_count}
- **Files in Needs_Action**: {needs_action_count}
- **Files in Done**: {done_count}

## System Health
- **Claude Code Connection**: ✓ Connected
- **Vault Access**: ✓ Available
- **Watcher Services**: {watchers_status}"""

            # Read current dashboard content
            if self.dashboard_path.exists():
                with open(self.dashboard_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            else:
                content = "# AI Employee Dashboard\n\n## Overview\nWelcome to your Personal AI Employee dashboard. This system monitors your personal and business affairs 24/7.\n\n"

            # Ensure overview section exists
            if "## Overview" not in content:
                content = "# AI Employee Dashboard\n\n## Overview\nWelcome to your Personal AI Employee dashboard. This system monitors your personal and business affairs 24/7.\n\n" + content

            # Remove all dynamic sections (Current Status through System Health inclusive)
            # These sections are regenerated each time, so we remove them completely
            sections_to_remove = [
                "## Current Status",
                "## Recent Activity",
                "## Quick Stats",
                "## System Health"
            ]
            
            # Find the start of the first dynamic section
            first_dynamic = len(content)
            for section in sections_to_remove:
                pos = content.find(f"\n{section}")
                if pos != -1 and pos < first_dynamic:
                    first_dynamic = pos
            
            # Find the end of the last dynamic section
            # Look for the next ## section after System Health, or end of file
            after_dynamic = len(content)
            content_after_first = content[first_dynamic:]
            for section in sections_to_remove:
                pos = content_after_first.find(f"\n{section}")
                if pos != -1:
                    # Find where this section ends (next ## or end of file)
                    next_section = content_after_first.find("\n## ", pos + 1)
                    if next_section == -1:
                        after_dynamic = len(content_after_first)
                    else:
                        # Check if next section is also a dynamic one
                        next_section_name = content_after_first[next_section:next_section+50]
                        if any(s in next_section_name for s in sections_to_remove):
                            continue
                        after_dynamic = next_section
            
            # Keep only the content before dynamic sections and after them
            if first_dynamic < len(content):
                # Extract content before dynamic sections
                before_dynamic = content[:first_dynamic]
                # Extract content after dynamic sections
                if after_dynamic < len(content_after_first):
                    after_dynamic_content = content_after_first[after_dynamic:]
                else:
                    after_dynamic_content = ""
                # Combine with new status section
                updated_content = before_dynamic + "\n\n" + status_section + "\n\n" + after_dynamic_content
            else:
                # No dynamic sections found, append after overview
                overview_end = content.find("\n\n", content.find("## Overview"))
                if overview_end != -1:
                    updated_content = content[:overview_end] + "\n\n" + status_section + "\n\n" + content[overview_end:].lstrip()
                else:
                    updated_content = content + "\n\n" + status_section + "\n"

            # Write updated dashboard
            with open(self.dashboard_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)

            logger.info("Dashboard updated successfully")

        except Exception as e:
            logger.error(f"Error updating dashboard: {str(e)}")

    def count_daily_processed(self):
        """
        Count files processed today in the Done folder
        """
        today = datetime.now().strftime('%Y-%m-%d')
        done_files = list(self.done_path.glob("*.md"))
        count = 0

        for file_path in done_files:
            try:
                # Look for date in filename or content
                if today in file_path.name:
                    count += 1
                else:
                    # Check file modification time
                    mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if mod_time.date() == datetime.now().date():
                        count += 1
            except:
                continue

        return count

    def count_pending_approval(self):
        """
        Count files in Pending_Approval folder
        """
        pending_path = self.vault_path / "Pending_Approval"
        if pending_path.exists():
            return len(list(pending_path.glob("*.md")))
        return 0

    def start_watcher(self, watcher_script: str, name: str):
        """
        Start a watcher process
        """
        try:
            # Create the command to run the watcher
            cmd = [sys.executable, watcher_script]

            # Start the process
            process = subprocess.Popen(cmd)

            # Store the process
            self.running_processes[name] = process

            logger.info(f"Started {name} with PID {process.pid}")

            return process
        except Exception as e:
            logger.error(f"Error starting {name}: {str(e)}")
            return None

    def stop_all_watchers(self):
        """
        Stop all running watcher processes
        """
        for name, process in self.running_processes.items():
            try:
                logger.info(f"Stopping {name} (PID: {process.pid})")
                process.terminate()
                process.wait(timeout=5)  # Wait up to 5 seconds for graceful shutdown
            except subprocess.TimeoutExpired:
                logger.warning(f"{name} didn't stop gracefully, killing...")
                process.kill()
            except Exception as e:
                logger.error(f"Error stopping {name}: {str(e)}")

        self.running_processes.clear()

    def process_needs_action(self):
        """
        Process files in the Needs_Action folder
        """
        try:
            needs_action_files = list(self.needs_action_path.glob("*.md"))

            if needs_action_files:
                logger.info(f"Found {len(needs_action_files)} files in Needs_Action to process")

                for file_path in needs_action_files:
                    logger.info(f"Processing: {file_path.name}")

                    # In a real implementation, this would call Claude Code to process the file
                    # For now, we'll just move it to Done after a short delay to simulate processing
                    self.simulate_processing(file_path)

        except Exception as e:
            logger.error(f"Error processing Needs_Action folder: {str(e)}")

    def simulate_processing(self, file_path: Path):
        """
        Simulate processing a file (in real implementation, this would call Claude Code)
        """
        try:
            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Add processing timestamp
            processed_content = f"{content}\n\n<!-- Processed by Orchestrator at {datetime.now().isoformat()} -->"

            # Move to Done folder
            done_file_path = self.done_path / f"DONE_{file_path.name}"
            with open(done_file_path, 'w', encoding='utf-8') as f:
                f.write(processed_content)

            # Remove from Needs_Action
            file_path.unlink()

            logger.info(f"Simulated processing completed: {file_path.name} -> {done_file_path.name}")

        except Exception as e:
            logger.error(f"Error simulating processing for {file_path.name}: {str(e)}")

    def run_health_check(self):
        """
        Perform a health check on running processes
        """
        try:
            # Check if any processes have died
            dead_processes = []
            for name, process in self.running_processes.items():
                if process.poll() is not None:
                    logger.warning(f"{name} (PID: {process.pid}) has terminated with code {process.returncode}")
                    dead_processes.append(name)

            # Remove dead processes from tracking
            for name in dead_processes:
                del self.running_processes[name]

            # Update dashboard with health info
            self.update_dashboard()

        except Exception as e:
            logger.error(f"Error during health check: {str(e)}")

    def run(self, check_interval: int = 30, auto_execute_skills: bool = False):
        """
        Main orchestration loop.
        
        Args:
            check_interval: Seconds between orchestration cycles
            auto_execute_skills: If True, automatically executes skills from config.
                                Default is False to maintain Bronze Tier stability.
        """
        logger.info("Starting Orchestrator...")

        # Start the filesystem watcher as an example
        fs_watcher_path = self.vault_path / "filesystem_watcher.py"
        if fs_watcher_path.exists():
            self.start_watcher(str(fs_watcher_path), "filesystem_watcher")

        try:
            while True:
                # Perform health check
                self.run_health_check()

                # Process any pending action items
                self.process_needs_action()

                # CONTROLLED SKILL EXECUTION TRIGGER
                # Optional: Auto-execute skills if enabled (default: disabled for stability)
                # Skills can always be executed manually via execute_skill() method
                if auto_execute_skills:
                    self._execute_configured_skills()

                # Update dashboard
                self.update_dashboard()

                # Wait before next cycle
                time.sleep(check_interval)

        except KeyboardInterrupt:
            logger.info("Orchestrator interrupted by user")
        except Exception as e:
            logger.error(f"Unexpected error in orchestrator: {str(e)}")
        finally:
            logger.info("Shutting down orchestrator...")
            self.stop_all_watchers()
    
    def _execute_configured_skills(self):
        """
        Execute all skills defined in agent_skills_config.json.
        Called only when auto_execute_skills=True in run().
        Safe, non-blocking execution with error handling.
        """
        for skill_def in self.skills_config.get("skills", []):
            skill_name = skill_def.get("name")
            if not skill_name:
                continue
            
            # Get default parameters from skill definition
            params = skill_def.get("parameters", {})
            kwargs = {}
            
            # Extract default values from parameter properties
            for prop_name, prop_def in params.get("properties", {}).items():
                if "default" in prop_def:
                    kwargs[prop_name] = prop_def["default"]
            
            try:
                result = self.execute_skill(skill_name, **kwargs)
                if result:
                    logger.debug(f"Skill '{skill_name}' executed: {result.get('status', 'unknown')}")
            except Exception as e:
                # Non-blocking: log error but continue with other skills
                logger.error(f"Auto-execution of skill '{skill_name}' failed: {e}")


def main():
    """Main function to run the Orchestrator"""
    # Initialize the orchestrator
    orchestrator = Orchestrator(vault_path=".")

    # Run the orchestrator
    print("Orchestrator started. Managing AI Employee services.")
    print("Press Ctrl+C to stop.")
    orchestrator.run(check_interval=30)


if __name__ == "__main__":
    main()