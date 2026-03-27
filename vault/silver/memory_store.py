"""
Memory Store for Personal AI Employee - Silver Tier

Three-tier memory system for context-aware AI actions:
1. Short-Term (Session): Current task, active contexts, recent decisions
2. Long-Term (Episodic): Past decisions, completed tasks, client history
3. Semantic (Facts): Company handbook, rules, rates, reference data
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import deque

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MemoryStore:
    """
    Three-tier memory system for context-aware AI actions.
    
    Usage:
        memory = MemoryStore(vault_path)
        
        # Store a decision
        memory.store_decision('task_001', {'action': 'sent_email', 'result': 'success'})
        
        # Retrieve similar past decisions
        similar = memory.retrieve_similar_decisions({'type': 'email', 'priority': 'high'})
        
        # Get context for task
        context = memory.get_context_for_task('email', sender='client@example.com')
    """
    
    def __init__(self, vault_path: Path):
        """
        Initialize the memory store.
        
        Args:
            vault_path: Path to the Obsidian vault
        """
        self.vault_path = Path(vault_path)
        self.memory_path = self.vault_path / "Memory"
        self.memory_path.mkdir(exist_ok=True)
        
        # Short-term memory (in-memory, session-based)
        self.session_memory = {
            'current_task': None,
            'recent_decisions': deque(maxlen=50),  # Last 50 decisions
            'active_contexts': {},
            'session_start': datetime.now()
        }
        
        # Long-term memory (file-based, episodic)
        self.episodic_path = self.memory_path / "Episodic"
        self.episodic_path.mkdir(exist_ok=True)
        
        # Semantic memory (indexed facts)
        self.semantic_index_path = self.memory_path / "semantic_index.json"
        self.semantic_index = self._load_semantic_index()
        
        logger.info(f"MemoryStore initialized at {self.memory_path}")
    
    # ==================== SHORT-TERM MEMORY ====================
    
    def set_current_task(self, task_id: str, task_data: dict):
        """Set the current task being processed"""
        self.session_memory['current_task'] = {
            'id': task_id,
            'data': task_data,
            'started_at': datetime.now()
        }
    
    def get_current_task(self) -> Optional[dict]:
        """Get the current task"""
        return self.session_memory.get('current_task')
    
    def add_recent_decision(self, decision: dict):
        """Add a decision to short-term memory"""
        decision_record = {
            'timestamp': datetime.now().isoformat(),
            'decision': decision
        }
        self.session_memory['recent_decisions'].append(decision_record)
    
    def get_recent_decisions(self, limit: int = 10) -> List[dict]:
        """Get recent decisions from short-term memory"""
        decisions = list(self.session_memory['recent_decisions'])
        return decisions[-limit:]
    
    def set_active_context(self, context_name: str, context_data: dict):
        """Set an active context (e.g., current client, project)"""
        self.session_memory['active_contexts'][context_name] = {
            'data': context_data,
            'set_at': datetime.now()
        }
    
    def get_active_context(self, context_name: str) -> Optional[dict]:
        """Get an active context by name"""
        ctx = self.session_memory['active_contexts'].get(context_name)
        return ctx['data'] if ctx else None
    
    def clear_session(self):
        """Clear short-term memory (called on session end)"""
        self.session_memory = {
            'current_task': None,
            'recent_decisions': deque(maxlen=50),
            'active_contexts': {},
            'session_start': datetime.now()
        }
    
    # ==================== LONG-TERM MEMORY (EPISODIC) ====================
    
    def store_decision(self, task_id: str, decision: dict, metadata: dict = None):
        """
        Store a decision in episodic memory.
        
        Args:
            task_id: Unique identifier for the task
            decision: Decision details to store
            metadata: Optional metadata (sender, type, outcome, etc.)
        """
        record = {
            'timestamp': datetime.now().isoformat(),
            'task_id': task_id,
            'decision': decision,
            'metadata': metadata or {},
            'context': {
                'current_task': self.session_memory.get('current_task'),
                'active_contexts': self.session_memory.get('active_contexts', {})
            }
        }
        
        # Write to dated file (JSONL format)
        date_str = datetime.now().strftime('%Y-%m-%d')
        filepath = self.episodic_path / f"{date_str}.jsonl"
        
        try:
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
            logger.debug(f"Stored decision for task {task_id} in episodic memory")
        except Exception as e:
            logger.error(f"Failed to store decision in episodic memory: {e}")
    
    def retrieve_similar_decisions(
        self, 
        query: dict, 
        limit: int = 5,
        days_back: int = 30
    ) -> List[dict]:
        """
        Retrieve similar past decisions for context-aware reasoning.
        
        Args:
            query: Query parameters (type, priority, sender, etc.)
            limit: Maximum number of results to return
            days_back: How many days to search back
            
        Returns:
            List of similar decision records
        """
        similar = []
        
        for days_ago in range(min(days_back, 90)):  # Max 90 days
            date = datetime.now() - timedelta(days=days_ago)
            filepath = self.episodic_path / f"{date.strftime('%Y-%m-%d')}.jsonl"
            
            if not filepath.exists():
                continue
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        record = json.loads(line)
                        similarity = self._calculate_similarity(query, record)
                        
                        if similarity > 0.3:  # Threshold for relevance
                            similar.append((similarity, record))
            except Exception as e:
                logger.warning(f"Error reading episodic memory file {filepath}: {e}")
        
        # Sort by similarity and return top matches
        similar.sort(key=lambda x: x[0], reverse=True)
        return [record for _, record in similar[:limit]]
    
    def get_sender_history(
        self, 
        sender: str, 
        limit: int = 10
    ) -> List[dict]:
        """
        Get history of interactions with a specific sender.
        
        Args:
            sender: Email address or identifier
            limit: Maximum number of records to return
            
        Returns:
            List of past interactions with this sender
        """
        history = []
        
        for days_ago in range(60):  # Search back 60 days
            date = datetime.now() - timedelta(days=days_ago)
            filepath = self.episodic_path / f"{date.strftime('%Y-%m-%d')}.jsonl"
            
            if not filepath.exists():
                continue
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        record = json.loads(line)
                        metadata = record.get('metadata', {})
                        
                        if metadata.get('sender') == sender:
                            history.append(record)
                            
                        if len(history) >= limit:
                            return history
            except Exception as e:
                logger.warning(f"Error reading sender history from {filepath}: {e}")
        
        return history
    
    def get_task_type_history(
        self, 
        task_type: str, 
        limit: int = 20
    ) -> List[dict]:
        """
        Get history of tasks of a specific type.
        
        Args:
            task_type: Type of task (email, payment, invoice, etc.)
            limit: Maximum number of records to return
            
        Returns:
            List of past tasks of this type
        """
        history = []
        
        for days_ago in range(60):
            date = datetime.now() - timedelta(days=days_ago)
            filepath = self.episodic_path / f"{date.strftime('%Y-%m-%d')}.jsonl"
            
            if not filepath.exists():
                continue
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        record = json.loads(line)
                        metadata = record.get('metadata', {})
                        
                        if metadata.get('type') == task_type:
                            history.append(record)
                            
                        if len(history) >= limit:
                            return history
            except Exception as e:
                logger.warning(f"Error reading task history from {filepath}: {e}")
        
        return history
    
    # ==================== SEMANTIC MEMORY ====================
    
    def _load_semantic_index(self) -> dict:
        """Load semantic index from file"""
        if self.semantic_index_path.exists():
            try:
                with open(self.semantic_index_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load semantic index: {e}")
        
        # Default semantic index
        return {
            'company_handbook_summary': '',
            'rules': {},
            'rates': {},
            'clients': {},
            'subscriptions': {},
            'last_updated': None
        }
    
    def update_semantic_index(self, key: str, value: Any):
        """
        Update a value in the semantic index.
        
        Args:
            key: Index key (e.g., 'clients', 'rates', 'rules')
            value: New value to store
        """
        self.semantic_index[key] = value
        self.semantic_index['last_updated'] = datetime.now().isoformat()
        
        try:
            with open(self.semantic_index_path, 'w', encoding='utf-8') as f:
                json.dump(self.semantic_index, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save semantic index: {e}")
    
    def get_semantic_fact(self, key: str, default: Any = None) -> Any:
        """Get a fact from semantic memory"""
        return self.semantic_index.get(key, default)
    
    def index_company_handbook(self, handbook_path: Path):
        """
        Index the Company Handbook for quick reference.
        
        Args:
            handbook_path: Path to Company_Handbook.md
        """
        if not handbook_path.exists():
            logger.warning(f"Company Handbook not found at {handbook_path}")
            return
        
        content = handbook_path.read_text(encoding='utf-8')
        
        # Extract key sections
        rules = self._extract_handbook_rules(content)
        rates = self._extract_handbook_rates(content)
        
        self.update_semantic_index('company_handbook_summary', content[:2000])
        self.update_semantic_index('rules', rules)
        self.update_semantic_index('rates', rates)
        
        logger.info("Company Handbook indexed successfully")
    
    def _extract_handbook_rules(self, content: str) -> dict:
        """Extract rules from handbook content"""
        rules = {}
        
        # Extract approval thresholds
        if 'Approval Thresholds' in content:
            rules['approval_thresholds'] = {
                'auto_approve_under': 50,
                'require_approval_over': 50,
                'require_human_over': 200
            }
        
        # Extract communication guidelines
        if 'Communication Guidelines' in content:
            rules['communication'] = {
                'response_time_hours': 2,
                'business_hours': '9 AM - 6 PM',
                'tone': 'polite and professional'
            }
        
        return rules
    
    def _extract_handbook_rates(self, content: str) -> dict:
        """Extract rates/pricing from handbook content"""
        # This would parse actual rates if defined in handbook
        return {}
    
    # ==================== UTILITY METHODS ====================
    
    def _calculate_similarity(self, query: dict, record: dict) -> float:
        """
        Calculate similarity between query and record.
        
        Uses simple keyword matching and metadata comparison.
        """
        score = 0.0
        matches = 0
        
        # Check metadata match
        record_metadata = record.get('metadata', {})
        
        for key in ['type', 'priority', 'sender']:
            if key in query and key in record_metadata:
                if query[key] == record_metadata[key]:
                    score += 0.3
                    matches += 1
        
        # Check decision content match
        decision = record.get('decision', {})
        query_str = json.dumps(query).lower()
        decision_str = json.dumps(decision).lower()
        
        # Simple keyword overlap
        query_words = set(query_str.split())
        decision_words = set(decision_str.split())
        
        if query_words and decision_words:
            overlap = len(query_words & decision_words) / len(query_words)
            score += overlap * 0.4
        
        # Recency boost (more recent = higher score)
        try:
            record_time = datetime.fromisoformat(record['timestamp'])
            days_old = (datetime.now() - record_time).days
            recency_boost = max(0, 1 - (days_old / 30))  # Boost for last 30 days
            score += recency_boost * 0.3
        except:
            pass
        
        return min(1.0, score)
    
    def get_context_for_task(
        self, 
        task_type: str, 
        sender: str = None
    ) -> dict:
        """
        Build comprehensive context package for AI reasoning.
        
        Args:
            task_type: Type of task (email, payment, invoice, etc.)
            sender: Optional sender identifier
            
        Returns:
            Dictionary with all relevant context
        """
        context = {
            'company_handbook': self.semantic_index.get('company_handbook_summary', ''),
            'rules': self.semantic_index.get('rules', {}),
            'rates': self.semantic_index.get('rates', {}),
            'recent_similar_tasks': self.retrieve_similar_decisions(
                {'type': task_type},
                limit=5
            ),
            'sender_history': self.get_sender_history(sender) if sender else [],
            'task_type_history': self.get_task_type_history(task_type, limit=10),
            'recent_decisions': self.get_recent_decisions(limit=5),
            'active_contexts': self.session_memory.get('active_contexts', {})
        }
        
        return context
    
    def export_memory_summary(self) -> dict:
        """
        Export a summary of memory contents for debugging/reporting.
        
        Returns:
            Dictionary with memory statistics
        """
        # Count episodic records
        total_records = 0
        date_range = {'earliest': None, 'latest': None}
        
        for filepath in self.episodic_path.glob("*.jsonl"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    total_records += len(lines)
                    
                    date_str = filepath.stem
                    if date_range['earliest'] is None or date_str < date_range['earliest']:
                        date_range['earliest'] = date_str
                    if date_range['latest'] is None or date_str > date_range['latest']:
                        date_range['latest'] = date_str
            except:
                continue
        
        return {
            'short_term': {
                'current_task': self.session_memory['current_task'] is not None,
                'recent_decisions_count': len(self.session_memory['recent_decisions']),
                'active_contexts_count': len(self.session_memory['active_contexts']),
                'session_start': self.session_memory['session_start'].isoformat()
            },
            'long_term': {
                'total_records': total_records,
                'date_range': date_range,
                'storage_path': str(self.episodic_path)
            },
            'semantic': {
                'keys': list(self.semantic_index.keys()),
                'last_updated': self.semantic_index.get('last_updated')
            }
        }
