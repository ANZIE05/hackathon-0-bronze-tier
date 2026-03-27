"""
Decision Engine for Personal AI Employee - Silver Tier

The Decision Engine is the "brain" that determines:
- What task to work on next
- In what order to process tasks
- Which skill chain to execute
- Whether approval is required

Architecture:
    Task Collector → Priority Scorer → Selector → Next Task
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .memory_store import MemoryStore
from .priority_matrix import PriorityMatrix, PriorityLevel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DecisionEngine:
    """
    Decision engine for intelligent task selection and prioritization.
    
    Usage:
        engine = DecisionEngine(vault_path)
        
        # Select next task to work on
        next_task = engine.select_next_task()
        
        # Get task with highest priority
        task, score = engine.get_highest_priority_task()
        
        # Select appropriate skill chain for task
        chain = engine.select_chain_for_task(task_file)
    """
    
    # Minimum priority score to process automatically
    MIN_PRIORITY_THRESHOLD = 20
    
    # Task type to chain mapping
    DEFAULT_CHAIN_MAP = {
        'email': 'email_triage_chain',
        'invoice': 'invoice_request_chain',
        'payment': 'payment_approval_chain',
        'social_post': 'social_post_chain',
        'linkedin': 'social_post_chain',
        'file_drop': 'file_processing_chain',
    }
    
    def __init__(self, vault_path: Path):
        """
        Initialize the decision engine.
        
        Args:
            vault_path: Path to the Obsidian vault
        """
        self.vault_path = Path(vault_path)
        
        # Folder paths
        self.needs_action_path = self.vault_path / "Needs_Action"
        self.pending_approval_path = self.vault_path / "Pending_Approval"
        self.approved_path = self.vault_path / "Approved"
        self.done_path = self.vault_path / "Done"
        
        # Ensure folders exist
        for path in [self.needs_action_path, self.pending_approval_path, 
                     self.approved_path, self.done_path]:
            path.mkdir(exist_ok=True)
        
        # Initialize components
        self.memory_store = MemoryStore(vault_path)
        self.priority_matrix = PriorityMatrix()
        
        # Index company handbook for rules
        handbook_path = self.vault_path / "Company_Handbook.md"
        if handbook_path.exists():
            self.memory_store.index_company_handbook(handbook_path)
        
        # Chain configuration
        self.chain_map = self.DEFAULT_CHAIN_MAP.copy()
        
        logger.info(f"DecisionEngine initialized at {vault_path}")
    
    # ==================== TASK SELECTION ====================
    
    def select_next_task(self) -> Optional[Path]:
        """
        Select the highest-priority task to work on next.
        
        Decision flow:
        1. Check Approved folder (approved actions ready to execute)
        2. Check Pending_Approval folder (blocked tasks)
        3. Check Needs_Action folder (active tasks)
        4. Score all candidates
        5. Return highest score above threshold
        
        Returns:
            Path to selected task file, or None if no tasks
        """
        # Step 1: Check for approved actions ready to execute
        approved = list(self.approved_path.glob("*.md"))
        if approved:
            logger.info(f"Found {len(approved)} approved actions ready to execute")
            return approved[0]  # Execute approvals first
        
        # Step 2: Score all pending tasks in Needs_Action
        pending = list(self.needs_action_path.glob("*.md"))
        if not pending:
            logger.debug("No pending tasks in Needs_Action")
            return None
        
        # Step 3: Score and sort
        scored_tasks = self._score_all_tasks(pending)
        
        if not scored_tasks:
            return None
        
        # Step 4: Return highest if above threshold
        best_task, best_score = scored_tasks[0]
        
        if best_score >= self.MIN_PRIORITY_THRESHOLD:
            logger.info(f"Selected task: {best_task.name} (score: {best_score})")
            return best_task
        else:
            logger.debug(f"All tasks below threshold (best: {best_score})")
            return None
    
    def _score_all_tasks(
        self, 
        tasks: List[Path]
    ) -> List[Tuple[Path, int]]:
        """
        Score all tasks and return sorted by priority.
        
        Args:
            tasks: List of task file paths
            
        Returns:
            List of (task_path, score) tuples, sorted descending
        """
        scored = []
        
        for task_file in tasks:
            score = self._calculate_task_score(task_file)
            scored.append((task_file, score))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return scored
    
    def _calculate_task_score(self, task_file: Path) -> int:
        """
        Calculate priority score for a single task.
        
        Args:
            task_file: Path to task file
            
        Returns:
            Priority score 0-100
        """
        try:
            content = task_file.read_text(encoding='utf-8')
            frontmatter = self._parse_frontmatter(content)
            
            # Calculate task age
            age_hours = self._calculate_task_age(task_file)
            
            # Build metadata
            metadata = {
                'age_hours': age_hours,
                'source': frontmatter.get('type', 'manual'),
                'is_known_sender': self._is_known_sender(frontmatter.get('from')),
                'is_overdue': self._is_overdue(frontmatter),
                'is_due_today': self._is_due_today(frontmatter),
                'amount': float(frontmatter.get('amount', 0)),
            }
            
            # Calculate score using priority matrix
            score = self.priority_matrix.calculate_score(
                content=content,
                frontmatter=frontmatter,
                metadata=metadata
            )
            
            return score
            
        except Exception as e:
            logger.warning(f"Error scoring task {task_file}: {e}")
            return 50  # Default medium priority
    
    def get_highest_priority_task(self) -> Optional[Tuple[Path, int, str]]:
        """
        Get the highest priority task with score and level.
        
        Returns:
            Tuple of (task_path, score, priority_level) or None
        """
        task = self.select_next_task()
        
        if task:
            score = self._calculate_task_score(task)
            level = self.priority_matrix.get_priority_level(score).value
            return task, score, level
        
        return None
    
    # ==================== CHAIN SELECTION ====================
    
    def select_chain_for_task(self, task_file: Path) -> Optional[str]:
        """
        Select the appropriate skill chain for a task.
        
        Args:
            task_file: Path to task file
            
        Returns:
            Chain name or None if no matching chain
        """
        try:
            content = task_file.read_text(encoding='utf-8')
            frontmatter = self._parse_frontmatter(content)
            
            task_type = frontmatter.get('type', 'unknown')
            
            # Look up chain in map
            chain_name = self.chain_map.get(task_type)
            
            if chain_name:
                logger.info(f"Selected chain '{chain_name}' for task type '{task_type}'")
                return chain_name
            
            # Try to infer chain from content
            inferred_chain = self._infer_chain_from_content(content, frontmatter)
            if inferred_chain:
                logger.info(f"Inferred chain '{inferred_chain}' from content")
                return inferred_chain
            
            logger.debug(f"No matching chain for task type '{task_type}'")
            return None
            
        except Exception as e:
            logger.error(f"Error selecting chain for {task_file}: {e}")
            return None
    
    def _infer_chain_from_content(
        self, 
        content: str, 
        frontmatter: dict
    ) -> Optional[str]:
        """
        Infer appropriate chain from task content.
        
        Args:
            content: Task content
            frontmatter: Task frontmatter
            
        Returns:
            Inferred chain name or None
        """
        content_lower = content.lower()
        
        # Check for invoice-related content
        if any(kw in content_lower for kw in ['invoice', 'billing', 'payment request']):
            return 'invoice_request_chain'
        
        # Check for email-related content
        if frontmatter.get('type') == 'email':
            return 'email_triage_chain'
        
        # Check for social media content
        if any(kw in content_lower for kw in ['linkedin', 'post', 'social', 'tweet']):
            return 'social_post_chain'
        
        # Check for payment content
        if any(kw in content_lower for kw in ['payment', 'transfer', 'pay']):
            return 'payment_approval_chain'
        
        return None
    
    def register_chain(self, task_type: str, chain_name: str):
        """
        Register a chain for a task type.
        
        Args:
            task_type: Type of task
            chain_name: Name of chain to execute
        """
        self.chain_map[task_type] = chain_name
        logger.info(f"Registered chain '{chain_name}' for task type '{task_type}'")
    
    # ==================== APPROVAL DECISIONS ====================
    
    def requires_approval(self, task_file: Path) -> Tuple[bool, str]:
        """
        Determine if a task requires human approval.
        
        Args:
            task_file: Path to task file
            
        Returns:
            Tuple of (requires_approval: bool, reason: str)
        """
        try:
            content = task_file.read_text(encoding='utf-8')
            frontmatter = self._parse_frontmatter(content)
            
            task_type = frontmatter.get('type', 'unknown')
            score = self._calculate_task_score(task_file)
            
            # Build metadata
            metadata = {
                'amount': float(frontmatter.get('amount', 0)),
                'is_known_sender': self._is_known_sender(frontmatter.get('from')),
            }
            
            # Check with priority matrix
            can_auto, reason = self.priority_matrix.can_auto_execute(
                task_type=task_type,
                metadata=metadata,
                score=score
            )
            
            if not can_auto:
                logger.info(f"Task {task_file.name} requires approval: {reason}")
            
            return not can_auto, reason
            
        except Exception as e:
            logger.error(f"Error checking approval requirement: {e}")
            return True, "Error evaluating task - manual review required"
    
    # ==================== UTILITY METHODS ====================
    
    def _parse_frontmatter(self, content: str) -> dict:
        """Parse YAML frontmatter from markdown content"""
        import re
        
        frontmatter = {}
        
        # Look for YAML frontmatter between --- markers
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        
        if match:
            yaml_content = match.group(1)
            
            # Simple YAML parsing (key: value format)
            for line in yaml_content.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    # Try to convert to appropriate type
                    if value.lower() == 'true':
                        value = True
                    elif value.lower() == 'false':
                        value = False
                    else:
                        try:
                            value = float(value)
                            if value == int(value):
                                value = int(value)
                        except ValueError:
                            pass
                    
                    frontmatter[key] = value
        
        return frontmatter
    
    def _calculate_task_age(self, task_file: Path) -> float:
        """Calculate task age in hours"""
        try:
            # Try to get age from frontmatter first
            content = task_file.read_text(encoding='utf-8')
            frontmatter = self._parse_frontmatter(content)
            
            if 'received' in frontmatter:
                received = frontmatter['received']
                if isinstance(received, str):
                    try:
                        received_time = datetime.fromisoformat(received)
                        age = datetime.now() - received_time
                        return age.total_seconds() / 3600
                    except:
                        pass
            
            # Fall back to file modification time
            mtime = datetime.fromtimestamp(task_file.stat().st_mtime)
            age = datetime.now() - mtime
            return age.total_seconds() / 3600
            
        except Exception as e:
            logger.warning(f"Error calculating task age: {e}")
            return 0
    
    def _is_known_sender(self, sender: str) -> bool:
        """Check if sender is in known contacts"""
        if not sender:
            return False
        
        # Check semantic memory for known senders
        known_clients = self.memory_store.get_semantic_fact('clients', {})
        
        if isinstance(known_clients, dict):
            return sender in known_clients
        
        # Simple heuristic: if we have history with this sender, they're known
        history = self.memory_store.get_sender_history(sender, limit=1)
        return len(history) > 0
    
    def _is_overdue(self, frontmatter: dict) -> bool:
        """Check if task is overdue"""
        due_date = frontmatter.get('due_date')
        if not due_date:
            return False
        
        try:
            if isinstance(due_date, str):
                due = datetime.fromisoformat(due_date)
                return datetime.now() > due
        except:
            pass
        
        return False
    
    def _is_due_today(self, frontmatter: dict) -> bool:
        """Check if task is due today"""
        due_date = frontmatter.get('due_date')
        if not due_date:
            return False
        
        try:
            if isinstance(due_date, str):
                due = datetime.fromisoformat(due_date)
                return due.date() == datetime.now().date()
        except:
            pass
        
        return False
    
    def get_task_statistics(self) -> dict:
        """
        Get statistics about pending tasks.
        
        Returns:
            Dictionary with task statistics
        """
        pending = list(self.needs_action_path.glob("*.md"))
        
        if not pending:
            return {
                'total': 0,
                'by_priority': {},
                'average_score': 0,
                'oldest_task': None
            }
        
        scored = self._score_all_tasks(pending)
        
        # Group by priority level
        by_priority = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        total_score = 0
        oldest_age = 0
        oldest_task = None
        
        for task_file, score in scored:
            total_score += score
            level = self.priority_matrix.get_priority_level(score).value
            by_priority[level] = by_priority.get(level, 0) + 1
            
            age = self._calculate_task_age(task_file)
            if age > oldest_age:
                oldest_age = age
                oldest_task = task_file.name
        
        return {
            'total': len(pending),
            'by_priority': by_priority,
            'average_score': total_score / len(pending) if pending else 0,
            'oldest_task': oldest_task,
            'oldest_age_hours': oldest_age
        }
    
    def get_decision_summary(self) -> dict:
        """
        Get a summary of decision engine state.
        
        Returns:
            Dictionary with decision engine status
        """
        return {
            'pending_tasks': len(list(self.needs_action_path.glob("*.md"))),
            'approved_actions': len(list(self.approved_path.glob("*.md"))),
            'pending_approval': len(list(self.pending_approval_path.glob("*.md"))),
            'registered_chains': len(self.chain_map),
            'chain_map': self.chain_map,
            'priority_config': self.priority_matrix.to_dict(),
            'memory_summary': self.memory_store.export_memory_summary()
        }
