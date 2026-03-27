"""
Priority Matrix for Personal AI Employee - Silver Tier

Defines priority rules and scoring weights for task prioritization.
Rules are based on Company Handbook guidelines and urgency indicators.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Callable, Any, Optional
from enum import Enum


class PriorityLevel(Enum):
    """Priority levels for tasks"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SourceType(Enum):
    """Source types for tasks"""
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    FILESYSTEM = "filesystem"
    LINKEDIN = "linkedin"
    SCHEDULED = "scheduled"
    MANUAL = "manual"


@dataclass
class PriorityRule:
    """
    A rule for determining task priority.
    
    Attributes:
        name: Human-readable name for the rule
        condition: Function that takes task metadata and returns bool
        priority: Priority level to assign if condition matches
        weight: Importance weight for this rule (0-1)
    """
    name: str
    condition: Callable[[dict], bool]
    priority: PriorityLevel
    weight: float = 1.0


@dataclass
class PriorityConfig:
    """Configuration for priority scoring"""
    
    # Scoring weights (must sum to 100)
    WEIGHTS: Dict[str, int] = field(default_factory=lambda: {
        'explicit_priority': 30,    # From YAML frontmatter
        'keyword_urgency': 20,       # From content analysis
        'task_age': 15,              # Older = higher priority
        'source_type': 15,           # Email > File > Social
        'handbook_rules': 20,        # Company policy overrides
    })
    
    # Priority level numeric values
    PRIORITY_VALUES: Dict[str, int] = field(default_factory=lambda: {
        'critical': 100,
        'high': 80,
        'medium': 50,
        'low': 20
    })
    
    # Keywords indicating urgency
    URGENT_KEYWORDS: List[str] = field(default_factory=lambda: [
        'urgent', 'asap', 'emergency', 'critical', 'immediately',
        'deadline', 'payment', 'invoice', 'legal', 'complaint',
        'error', 'failed', 'broken', 'down', 'help'
    ])
    
    # High-value keywords
    HIGH_VALUE_KEYWORDS: List[str] = field(default_factory=lambda: [
        'contract', 'proposal', 'client', 'revenue', 'sale',
        'partnership', 'investment', 'opportunity'
    ])


class PriorityMatrix:
    """
    Priority matrix for task scoring and classification.
    
    Usage:
        matrix = PriorityMatrix()
        
        # Get priority score (0-100)
        score = matrix.calculate_score(task_file, content, frontmatter)
        
        # Get priority level
        level = matrix.get_priority_level(score)
        
        # Check if auto-execution is allowed
        can_auto = matrix.can_auto_execute(task_metadata)
    """
    
    def __init__(self, config: PriorityConfig = None):
        """
        Initialize the priority matrix.
        
        Args:
            config: Optional custom configuration
        """
        self.config = config or PriorityConfig()
        self.rules = self._build_default_rules()
    
    def _build_default_rules(self) -> List[PriorityRule]:
        """Build default priority rules based on Company Handbook"""
        rules = [
            # Payment-related rules
            PriorityRule(
                name="Large payment required",
                condition=lambda m: m.get('type') == 'payment' and m.get('amount', 0) > 200,
                priority=PriorityLevel.CRITICAL,
                weight=1.0
            ),
            PriorityRule(
                name="Medium payment required",
                condition=lambda m: m.get('type') == 'payment' and 50 <= m.get('amount', 0) <= 200,
                priority=PriorityLevel.HIGH,
                weight=1.0
            ),
            PriorityRule(
                name="Small payment required",
                condition=lambda m: m.get('type') == 'payment' and m.get('amount', 0) < 50,
                priority=PriorityLevel.MEDIUM,
                weight=0.8
            ),
            
            # Invoice rules
            PriorityRule(
                name="Invoice request",
                condition=lambda m: m.get('type') == 'email' and 'invoice' in m.get('subject', '').lower(),
                priority=PriorityLevel.HIGH,
                weight=0.9
            ),
            
            # Urgent keyword rules
            PriorityRule(
                name="Emergency keyword",
                condition=lambda m: any(
                    kw in (m.get('subject', '') + m.get('body', '')).lower()
                    for kw in ['emergency', 'critical', 'asap']
                ),
                priority=PriorityLevel.CRITICAL,
                weight=1.0
            ),
            PriorityRule(
                name="Urgent keyword",
                condition=lambda m: 'urgent' in (m.get('subject', '') + m.get('body', '')).lower(),
                priority=PriorityLevel.HIGH,
                weight=0.9
            ),
            
            # Source type rules
            PriorityRule(
                name="WhatsApp urgent message",
                condition=lambda m: m.get('source') == 'whatsapp' and m.get('priority') == 'high',
                priority=PriorityLevel.HIGH,
                weight=0.95
            ),
            PriorityRule(
                name="Email from known client",
                condition=lambda m: m.get('source') == 'email' and m.get('is_known_sender', False),
                priority=PriorityLevel.MEDIUM,
                weight=0.7
            ),
            
            # Deadline rules
            PriorityRule(
                name="Overdue task",
                condition=lambda m: m.get('is_overdue', False),
                priority=PriorityLevel.HIGH,
                weight=1.0
            ),
            PriorityRule(
                name="Due today",
                condition=lambda m: m.get('is_due_today', False),
                priority=PriorityLevel.HIGH,
                weight=0.9
            ),
        ]
        
        return rules
    
    def add_rule(self, rule: PriorityRule):
        """Add a custom priority rule"""
        self.rules.append(rule)
    
    def remove_rule(self, name: str):
        """Remove a rule by name"""
        self.rules = [r for r in self.rules if r.name != name]
    
    def calculate_score(
        self, 
        content: str, 
        frontmatter: dict,
        metadata: dict = None
    ) -> int:
        """
        Calculate composite priority score (0-100).
        
        Args:
            content: Task content text
            frontmatter: YAML frontmatter data
            metadata: Additional metadata (age, source, etc.)
            
        Returns:
            Priority score 0-100
        """
        metadata = metadata or {}
        scores = {}
        
        # 1. Explicit priority from frontmatter
        scores['explicit_priority'] = self._score_explicit_priority(frontmatter)
        
        # 2. Keyword urgency from content
        scores['keyword_urgency'] = self._score_keywords(content)
        
        # 3. Task age score
        scores['task_age'] = self._score_age(metadata)
        
        # 4. Source type score
        scores['source_type'] = self._score_source_type(metadata)
        
        # 5. Handbook rules score
        scores['handbook_rules'] = self._score_handbook_rules(frontmatter, metadata)
        
        # Calculate weighted sum
        total = 0
        for key, weight in self.config.WEIGHTS.items():
            score = scores.get(key, 0)
            total += (score / 100) * weight
        
        return min(100, max(0, int(total)))
    
    def _score_explicit_priority(self, frontmatter: dict) -> int:
        """Score based on explicit priority in frontmatter"""
        priority = frontmatter.get('priority', 'medium').lower()
        return self.config.PRIORITY_VALUES.get(priority, 50)
    
    def _score_keywords(self, content: str) -> int:
        """Score based on urgency keywords in content"""
        content_lower = content.lower()
        
        urgent_count = sum(
            1 for kw in self.config.URGENT_KEYWORDS
            if kw in content_lower
        )
        
        high_value_count = sum(
            1 for kw in self.config.HIGH_VALUE_KEYWORDS
            if kw in content_lower
        )
        
        # Urgent keywords have higher impact
        score = min(100, urgent_count * 15 + high_value_count * 8)
        return score
    
    def _score_age(self, metadata: dict) -> int:
        """Score based on task age (older = higher priority)"""
        age_hours = metadata.get('age_hours', 0)
        
        if age_hours >= 48:
            return 100  # Over 48 hours = critical
        elif age_hours >= 24:
            return 80   # Over 24 hours = high
        elif age_hours >= 4:
            return 60   # Over 4 hours = medium-high
        elif age_hours >= 1:
            return 40   # Over 1 hour = medium
        else:
            return 20   # Fresh = low-medium
    
    def _score_source_type(self, metadata: dict) -> int:
        """Score based on source type"""
        source = metadata.get('source', 'manual').lower()
        
        source_scores = {
            'email': 70,
            'whatsapp': 75,
            'filesystem': 50,
            'linkedin': 60,
            'scheduled': 40,
            'manual': 30
        }
        
        return source_scores.get(source, 50)
    
    def _score_handbook_rules(
        self, 
        frontmatter: dict, 
        metadata: dict
    ) -> int:
        """Score based on Company Handbook rules"""
        score = 50  # Base score
        
        # Check matching rules
        for rule in self.rules:
            combined = {**frontmatter, **metadata}
            if rule.condition(combined):
                if rule.priority == PriorityLevel.CRITICAL:
                    score += 40 * rule.weight
                elif rule.priority == PriorityLevel.HIGH:
                    score += 25 * rule.weight
                elif rule.priority == PriorityLevel.MEDIUM:
                    score += 10 * rule.weight
        
        return min(100, score)
    
    def get_priority_level(self, score: int) -> PriorityLevel:
        """
        Convert numeric score to priority level.
        
        Args:
            score: Priority score 0-100
            
        Returns:
            PriorityLevel enum value
        """
        if score >= 90:
            return PriorityLevel.CRITICAL
        elif score >= 70:
            return PriorityLevel.HIGH
        elif score >= 40:
            return PriorityLevel.MEDIUM
        else:
            return PriorityLevel.LOW
    
    def get_response_time(self, level: PriorityLevel) -> str:
        """
        Get expected response time for priority level.
        
        Args:
            level: Priority level
            
        Returns:
            Human-readable response time
        """
        times = {
            PriorityLevel.CRITICAL: "Immediate (< 15 minutes)",
            PriorityLevel.HIGH: "Within 1 hour",
            PriorityLevel.MEDIUM: "Within 4 hours",
            PriorityLevel.LOW: "Within 24 hours"
        }
        return times.get(level, "Within 24 hours")
    
    def can_auto_execute(
        self, 
        task_type: str, 
        metadata: dict,
        score: int
    ) -> tuple:
        """
        Determine if task can be auto-executed or requires approval.
        
        Args:
            task_type: Type of task
            metadata: Task metadata
            score: Priority score
            
        Returns:
            Tuple of (can_auto: bool, reason: str)
        """
        # Critical tasks always require approval
        if score >= 90:
            return False, "Critical priority requires human approval"
        
        # Payment tasks have threshold-based rules
        if task_type == 'payment':
            amount = metadata.get('amount', 0)
            if amount > 50:
                return False, f"Payment ${amount} exceeds auto-approve threshold ($50)"
        
        # Email sending requires approval for unknown senders
        if task_type == 'email' and not metadata.get('is_known_sender', True):
            return False, "Email to unknown sender requires approval"
        
        # High priority tasks need approval
        level = self.get_priority_level(score)
        if level == PriorityLevel.CRITICAL:
            return False, "Critical tasks require human approval"
        
        return True, "Auto-execution allowed"
    
    def get_applicable_rules(self, metadata: dict) -> List[dict]:
        """
        Get all rules that apply to a task.
        
        Args:
            metadata: Task metadata
            
        Returns:
            List of applicable rule descriptions
        """
        applicable = []
        
        for rule in self.rules:
            if rule.condition(metadata):
                applicable.append({
                    'name': rule.name,
                    'priority': rule.priority.value,
                    'weight': rule.weight
                })
        
        return applicable
    
    def to_dict(self) -> dict:
        """Export priority matrix configuration as dictionary"""
        return {
            'weights': self.config.WEIGHTS,
            'priority_values': self.config.PRIORITY_VALUES,
            'urgent_keywords': self.config.URGENT_KEYWORDS,
            'high_value_keywords': self.config.HIGH_VALUE_KEYWORDS,
            'rules_count': len(self.rules)
        }
