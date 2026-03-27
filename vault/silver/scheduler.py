"""
Task Scheduler for Personal AI Employee - Silver Tier

Cron-like scheduling system for timed operations.
Supports daily, weekly, and custom interval tasks.
"""

import logging
import json
import yaml
import threading
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Default scheduled tasks configuration
DEFAULT_SCHEDULED_TASKS = {
    'daily_tasks': [
        {
            'name': 'morning_briefing',
            'description': 'Generate morning briefing summary',
            'time': '08:00',  # 8 AM daily
            'action': 'generate_briefing',
            'enabled': True
        },
        {
            'name': 'evening_review',
            'description': 'Review completed tasks and update dashboard',
            'time': '18:00',  # 6 PM daily
            'action': 'evening_review',
            'enabled': True
        },
        {
            'name': 'check_pending_approvals',
            'description': 'Check for expired approval requests',
            'time': '12:00',  # Noon daily
            'action': 'check_approvals',
            'enabled': True
        }
    ],
    'weekly_tasks': [
        {
            'name': 'weekly_audit',
            'description': 'Weekly business audit and CEO briefing',
            'day': 'sunday',
            'time': '20:00',  # Sunday 8 PM
            'action': 'weekly_audit',
            'enabled': True
        },
        {
            'name': 'subscription_review',
            'description': 'Review recurring subscriptions',
            'day': 'monday',
            'time': '09:00',  # Monday 9 AM
            'action': 'subscription_review',
            'enabled': True
        }
    ],
    'interval_tasks': [
        {
            'name': 'health_check',
            'description': 'System health check',
            'interval_minutes': 60,
            'action': 'health_check',
            'enabled': True
        },
        {
            'name': 'dashboard_update',
            'description': 'Update dashboard statistics',
            'interval_minutes': 30,
            'action': 'update_dashboard',
            'enabled': True
        }
    ]
}


class TaskScheduler:
    """
    Cron-like task scheduler for the AI Employee.
    
    Usage:
        scheduler = TaskScheduler(vault_path)
        scheduler.start()
        
        # Add custom task
        scheduler.add_daily_task('noon_check', '12:00', 'check_emails')
        
        # Stop scheduler
        scheduler.stop()
    """
    
    def __init__(
        self, 
        vault_path: Path,
        orchestrator: Any = None
    ):
        """
        Initialize the task scheduler.
        
        Args:
            vault_path: Path to the Obsidian vault
            orchestrator: Reference to orchestrator for task execution
        """
        self.vault_path = Path(vault_path)
        self.orchestrator = orchestrator
        
        # Schedules path
        self.schedules_path = self.vault_path / "Schedules"
        self.schedules_path.mkdir(exist_ok=True)
        
        # Load task configurations
        self.config_file = self.schedules_path / "scheduled_tasks.yaml"
        self.tasks_config = self._load_tasks_config()
        
        # Execution log
        self.log_file = self.schedules_path / "schedule_log.jsonl"
        
        # Scheduler state
        self.running = False
        self.scheduler_thread = None
        
        # Task registry
        self.task_handlers = self._register_task_handlers()
        
        # Next execution times
        self.next_executions: Dict[str, datetime] = {}
        
        logger.info(f"TaskScheduler initialized at {vault_path}")
    
    def _load_tasks_config(self) -> dict:
        """Load tasks configuration from file or use defaults"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                logger.info(f"Loaded tasks config from {self.config_file}")
                return config or DEFAULT_SCHEDULED_TASKS
            except Exception as e:
                logger.warning(f"Failed to load tasks config: {e}")
        
        # Save default config
        self._save_tasks_config(DEFAULT_SCHEDULED_TASKS)
        return DEFAULT_SCHEDULED_TASKS
    
    def _save_tasks_config(self, config: dict):
        """Save tasks configuration to file"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    def _register_task_handlers(self) -> Dict[str, Callable]:
        """Register built-in task handlers"""
        return {
            'generate_briefing': self._generate_briefing,
            'evening_review': self._evening_review,
            'check_approvals': self._check_approvals,
            'weekly_audit': self._weekly_audit,
            'subscription_review': self._subscription_review,
            'health_check': self._health_check,
            'update_dashboard': self._update_dashboard,
        }
    
    def register_task_handler(self, name: str, handler: Callable):
        """
        Register a custom task handler.
        
        Args:
            name: Task action name
            handler: Callable to handle the task
        """
        self.task_handlers[name] = handler
        logger.info(f"Registered task handler: {name}")
    
    def start(self):
        """Start the scheduler in a background thread"""
        if self.running:
            logger.warning("Scheduler already running")
            return
        
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("Task scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        logger.info("Task scheduler stopped")
    
    def _run_scheduler(self):
        """Main scheduler loop"""
        logger.info("Scheduler loop started")
        
        # Calculate initial next execution times
        self._calculate_next_executions()
        
        while self.running:
            try:
                now = datetime.now()
                
                # Check each scheduled task
                for task_name, next_time in list(self.next_executions.items()):
                    if now >= next_time:
                        self._execute_task(task_name)
                        self._reschedule_task(task_name)
                
                # Sleep for 1 minute
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(60)
    
    def _calculate_next_executions(self):
        """Calculate next execution time for all tasks"""
        now = datetime.now()
        
        # Daily tasks
        for task in self.tasks_config.get('daily_tasks', []):
            if task.get('enabled', True):
                task_name = task['name']
                time_str = task.get('time', '09:00')
                
                next_time = self._get_next_daily_time(now, time_str)
                self.next_executions[task_name] = next_time
        
        # Weekly tasks
        for task in self.tasks_config.get('weekly_tasks', []):
            if task.get('enabled', True):
                task_name = task['name']
                day = task.get('day', 'monday')
                time_str = task.get('time', '09:00')
                
                next_time = self._get_next_weekly_time(now, day, time_str)
                self.next_executions[task_name] = next_time
        
        # Interval tasks
        for task in self.tasks_config.get('interval_tasks', []):
            if task.get('enabled', True):
                task_name = task['name']
                interval = task.get('interval_minutes', 60)
                
                next_time = now + timedelta(minutes=interval)
                self.next_executions[task_name] = next_time
        
        logger.info(f"Calculated next executions for {len(self.next_executions)} tasks")
    
    def _get_next_daily_time(self, now: datetime, time_str: str) -> datetime:
        """Get next occurrence of a daily time"""
        hour, minute = map(int, time_str.split(':'))
        
        next_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # If already passed today, schedule for tomorrow
        if next_time <= now:
            next_time += timedelta(days=1)
        
        return next_time
    
    def _get_next_weekly_time(
        self, 
        now: datetime, 
        day: str, 
        time_str: str
    ) -> datetime:
        """Get next occurrence of a weekly day/time"""
        days = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        
        target_day = days.get(day.lower(), 0)
        hour, minute = map(int, time_str.split(':'))
        
        next_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # Calculate days until target day
        days_ahead = target_day - now.weekday()
        if days_ahead < 0:
            days_ahead += 7
        
        next_time += timedelta(days=days_ahead)
        
        # If already passed today, schedule for next week
        if next_time <= now:
            next_time += timedelta(weeks=1)
        
        return next_time
    
    def _execute_task(self, task_name: str):
        """Execute a scheduled task"""
        logger.info(f"Executing scheduled task: {task_name}")
        
        # Find task config
        task_config = self._find_task_config(task_name)
        
        if not task_config:
            logger.warning(f"Task config not found: {task_name}")
            return
        
        action = task_config.get('action')
        
        if not action:
            logger.warning(f"No action defined for task: {task_name}")
            return
        
        # Execute the task
        try:
            handler = self.task_handlers.get(action)
            
            if handler:
                result = handler()
                self._log_execution(task_name, action, 'success', str(result))
                logger.info(f"Task {task_name} completed: {result}")
            elif self.orchestrator and hasattr(self.orchestrator, action):
                method = getattr(self.orchestrator, action)
                if callable(method):
                    result = method()
                    self._log_execution(task_name, action, 'success', str(result))
                    logger.info(f"Task {task_name} completed via orchestrator: {result}")
            else:
                self._log_execution(task_name, action, 'no_handler', f"No handler for {action}")
                logger.warning(f"No handler for action: {action}")
                
        except Exception as e:
            self._log_execution(task_name, action, 'error', str(e))
            logger.error(f"Task {task_name} failed: {e}")
    
    def _reschedule_task(self, task_name: str):
        """Reschedule a task for next execution"""
        now = datetime.now()
        task_config = self._find_task_config(task_name)
        
        if not task_config:
            return
        
        # Determine task type and reschedule
        if 'time' in task_config and 'day' not in task_config:
            # Daily task
            time_str = task_config.get('time', '09:00')
            self.next_executions[task_name] = self._get_next_daily_time(now, time_str)
        
        elif 'day' in task_config:
            # Weekly task
            day = task_config.get('day', 'monday')
            time_str = task_config.get('time', '09:00')
            self.next_executions[task_name] = self._get_next_weekly_time(now, day, time_str)
        
        elif 'interval_minutes' in task_config:
            # Interval task
            interval = task_config.get('interval_minutes', 60)
            self.next_executions[task_name] = now + timedelta(minutes=interval)
    
    def _find_task_config(self, task_name: str) -> Optional[dict]:
        """Find task configuration by name"""
        for task_type in ['daily_tasks', 'weekly_tasks', 'interval_tasks']:
            for task in self.tasks_config.get(task_type, []):
                if task.get('name') == task_name:
                    return task
        return None
    
    def _log_execution(
        self, 
        task_name: str, 
        action: str, 
        status: str, 
        result: str
    ):
        """Log task execution"""
        record = {
            'timestamp': datetime.now().isoformat(),
            'task_name': task_name,
            'action': action,
            'status': status,
            'result': result
        }
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record) + '\n')
        except Exception as e:
            logger.warning(f"Failed to log execution: {e}")
    
    # ==================== Built-in Task Handlers ====================
    
    def _generate_briefing(self) -> str:
        """Generate morning briefing"""
        briefing = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': 'Morning',
            'summary': 'Morning briefing generated',
            'items': []
        }
        
        # Check for pending approvals
        pending_path = self.vault_path / "Pending_Approval"
        if pending_path.exists():
            pending_count = len(list(pending_path.glob("*.md")))
            briefing['items'].append(f"{pending_count} pending approvals")
        
        # Check needs action
        needs_action_path = self.vault_path / "Needs_Action"
        if needs_action_path.exists():
            na_count = len(list(needs_action_path.glob("*.md")))
            briefing['items'].append(f"{na_count} items needing action")
        
        # Create briefing file
        briefing_content = f"""---
type: briefing
date: {briefing['date']}
period: {briefing['time']}
---

# Morning Briefing - {briefing['date']}

## Summary
{briefing['summary']}

## Items to Address

"""
        for item in briefing['items']:
            briefing_content += f"- {item}\n"
        
        briefing_content += f"""
## Schedule
Review pending items and prioritize based on urgency.

---
*Generated by AI Employee Scheduler*
"""
        
        briefing_file = self.schedules_path / f"Briefing_{datetime.now().strftime('%Y%m%d')}.md"
        briefing_file.write_text(briefing_content, encoding='utf-8')
        
        return f"Morning briefing created: {briefing_file}"
    
    def _evening_review(self) -> str:
        """Generate evening review"""
        done_path = self.vault_path / "Done"
        done_count = 0
        
        if done_path.exists():
            today = datetime.now().strftime('%Y-%m-%d')
            for f in done_path.glob("*.md"):
                if today in f.name:
                    done_count += 1
        
        review_content = f"""---
type: review
date: {datetime.now().strftime('%Y-%m-%d')}
period: Evening
---

# Evening Review - {datetime.now().strftime('%Y-%m-%d')}

## Today's Accomplishments
- Processed {done_count} items

## Status
- System operational
- All watchers running

## Tomorrow's Focus
- Review any pending items from today
- Address overnight communications

---
*Generated by AI Employee Scheduler*
"""
        
        review_file = self.schedules_path / f"Review_{datetime.now().strftime('%Y%m%d')}.md"
        review_file.write_text(review_content, encoding='utf-8')
        
        return f"Evening review created: {review_file}"
    
    def _check_approvals(self) -> str:
        """Check for expired approval requests"""
        from .approval_workflow import ApprovalWorkflow
        
        workflow = ApprovalWorkflow(self.vault_path)
        expired = workflow.check_expired_approvals()
        
        if expired:
            return f"Found {len(expired)} expired approval requests"
        
        return "No expired approval requests"
    
    def _weekly_audit(self) -> str:
        """Generate weekly business audit"""
        audit_content = f"""---
type: weekly_audit
week_ending: {datetime.now().strftime('%Y-%m-%d')}
---

# Weekly Business Audit

## Week Ending: {datetime.now().strftime('%Y-%m-%d')}

## Tasks Completed
Review Done folder for completed items this week.

## Pending Items
Check Needs_Action and Pending_Approval folders.

## Financial Summary
- Review payment logs
- Check invoice status

## Recommendations
- Address any bottlenecks
- Plan for upcoming week

---
*Generated by AI Employee Scheduler*
"""
        
        audit_file = self.schedules_path / f"Weekly_Audit_{datetime.now().strftime('%Y%m%d')}.md"
        audit_file.write_text(audit_content, encoding='utf-8')
        
        return f"Weekly audit created: {audit_file}"
    
    def _subscription_review(self) -> str:
        """Review recurring subscriptions"""
        review_content = f"""---
type: subscription_review
date: {datetime.now().strftime('%Y-%m-%d')}
---

# Subscription Review

## Date: {datetime.now().strftime('%Y-%m-%d')}

## Action Items
- Review all recurring charges from past week
- Check for unused subscriptions
- Verify expected subscriptions are active

## Notes
Check bank statements and compare against known subscriptions.

---
*Generated by AI Employee Scheduler*
"""
        
        review_file = self.schedules_path / f"Subscription_Review_{datetime.now().strftime('%Y%m%d')}.md"
        review_file.write_text(review_content, encoding='utf-8')
        
        return f"Subscription review created: {review_file}"
    
    def _health_check(self) -> str:
        """Perform system health check"""
        health = {
            'timestamp': datetime.now().isoformat(),
            'status': 'healthy',
            'checks': []
        }
        
        # Check folders exist
        required_folders = ['Inbox', 'Needs_Action', 'Done', 'Logs', 'Plans']
        for folder in required_folders:
            folder_path = self.vault_path / folder
            if folder_path.exists():
                health['checks'].append(f"✓ {folder}/ exists")
            else:
                health['checks'].append(f"✗ {folder}/ missing")
                health['status'] = 'degraded'
        
        return f"Health check: {health['status']} - {len(health['checks'])} checks"
    
    def _update_dashboard(self) -> str:
        """Update dashboard statistics"""
        if self.orchestrator and hasattr(self.orchestrator, 'update_dashboard'):
            self.orchestrator.update_dashboard()
            return "Dashboard updated"
        
        return "Dashboard update skipped - no orchestrator"
    
    # ==================== Configuration Methods ====================
    
    def add_daily_task(
        self, 
        name: str, 
        time: str, 
        action: str,
        description: str = None
    ):
        """Add a daily scheduled task"""
        task = {
            'name': name,
            'time': time,
            'action': action,
            'enabled': True
        }
        
        if description:
            task['description'] = description
        
        if 'daily_tasks' not in self.tasks_config:
            self.tasks_config['daily_tasks'] = []
        
        self.tasks_config['daily_tasks'].append(task)
        self._save_tasks_config(self.tasks_config)
        self._calculate_next_executions()
        
        logger.info(f"Added daily task: {name} at {time}")
    
    def add_weekly_task(
        self,
        name: str,
        day: str,
        time: str,
        action: str,
        description: str = None
    ):
        """Add a weekly scheduled task"""
        task = {
            'name': name,
            'day': day,
            'time': time,
            'action': action,
            'enabled': True
        }
        
        if description:
            task['description'] = description
        
        if 'weekly_tasks' not in self.tasks_config:
            self.tasks_config['weekly_tasks'] = []
        
        self.tasks_config['weekly_tasks'].append(task)
        self._save_tasks_config(self.tasks_config)
        self._calculate_next_executions()
        
        logger.info(f"Added weekly task: {name} on {day} at {time}")
    
    def enable_task(self, task_name: str):
        """Enable a scheduled task"""
        self._set_task_enabled(task_name, True)
    
    def disable_task(self, task_name: str):
        """Disable a scheduled task"""
        self._set_task_enabled(task_name, False)
    
    def _set_task_enabled(self, task_name: str, enabled: bool):
        """Set task enabled status"""
        for task_type in ['daily_tasks', 'weekly_tasks', 'interval_tasks']:
            for task in self.tasks_config.get(task_type, []):
                if task.get('name') == task_name:
                    task['enabled'] = enabled
                    self._save_tasks_config(self.tasks_config)
                    logger.info(f"Task {task_name} {'enabled' if enabled else 'disabled'}")
                    return
        
        logger.warning(f"Task not found: {task_name}")
    
    def get_schedule_status(self) -> dict:
        """Get current scheduler status"""
        return {
            'running': self.running,
            'scheduled_tasks': len(self.next_executions),
            'next_executions': {
                name: time.isoformat() 
                for name, time in self.next_executions.items()
            },
            'config_file': str(self.config_file),
            'log_file': str(self.log_file)
        }
