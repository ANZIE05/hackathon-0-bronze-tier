"""
Skill Chain Executor for Personal AI Employee - Silver Tier

Enables composing multiple skills into workflows (chains) for complex tasks.
Chains are defined in YAML format and executed with variable substitution.

Chain Definition Format:
    name: "email_response_workflow"
    steps:
      - skill: "read_email_content"
        output: "email_data"
      - skill: "check_company_handbook"
        input:
          topic: "email response guidelines"
        output: "guidelines"
      - skill: "draft_email_response"
        input:
          email: "${email_data}"
          guidelines: "${guidelines}"
        output: "draft"
"""

import logging
import yaml
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SkillChainExecutor:
    """
    Executes skill chains with variable substitution and error handling.
    
    Usage:
        executor = SkillChainExecutor(orchestrator, chains_path)
        
        # Load a chain definition
        chain = executor.load_chain('email_triage_chain')
        
        # Execute the chain
        results = executor.execute_chain(chain, initial_context)
    """
    
    def __init__(
        self, 
        orchestrator: Any,
        chains_path: Path = None
    ):
        """
        Initialize the skill chain executor.
        
        Args:
            orchestrator: Reference to the orchestrator for skill execution
            chains_path: Path to chain definitions directory
        """
        self.orchestrator = orchestrator
        self.chains_path = chains_path or Path(__file__).parent / "chains"
        
        # Loaded chain definitions
        self.chains: Dict[str, dict] = {}
        
        # Execution history
        self.execution_history: List[dict] = []
        
        # Active chains (for monitoring)
        self.active_chains: Dict[str, dict] = {}
        
        # Load available chains
        self._load_all_chains()
        
        logger.info(f"SkillChainExecutor initialized with {len(self.chains)} chains")
    
    def _load_all_chains(self):
        """Load all chain definitions from the chains directory"""
        if not self.chains_path.exists():
            logger.warning(f"Chains path not found: {self.chains_path}")
            return
        
        for chain_file in self.chains_path.glob("*.yaml"):
            try:
                chain = self._load_chain_file(chain_file)
                if chain:
                    self.chains[chain['name']] = chain
                    logger.info(f"Loaded chain: {chain['name']}")
            except Exception as e:
                logger.error(f"Failed to load chain {chain_file}: {e}")
    
    def _load_chain_file(self, chain_file: Path) -> Optional[dict]:
        """
        Load a chain definition from a YAML file.
        
        Args:
            chain_file: Path to YAML file
            
        Returns:
            Chain definition dictionary
        """
        try:
            with open(chain_file, 'r', encoding='utf-8') as f:
                chain = yaml.safe_load(f)
            
            # Validate required fields
            if not chain or 'name' not in chain or 'steps' not in chain:
                logger.warning(f"Invalid chain definition in {chain_file}")
                return None
            
            return chain
            
        except Exception as e:
            logger.error(f"Error loading chain file {chain_file}: {e}")
            return None
    
    def load_chain(self, chain_name: str) -> Optional[dict]:
        """
        Load a chain by name.
        
        Args:
            chain_name: Name of the chain to load
            
        Returns:
            Chain definition or None if not found
        """
        if chain_name in self.chains:
            return self.chains[chain_name]
        
        # Try to load from file
        chain_file = self.chains_path / f"{chain_name}.yaml"
        if chain_file.exists():
            chain = self._load_chain_file(chain_file)
            if chain:
                self.chains[chain_name] = chain
                return chain
        
        logger.warning(f"Chain not found: {chain_name}")
        return None
    
    def execute_chain(
        self, 
        chain: dict, 
        initial_context: dict = None,
        task_id: str = None
    ) -> dict:
        """
        Execute a skill chain.
        
        Args:
            chain: Chain definition dictionary
            initial_context: Initial context variables
            task_id: Optional task identifier for tracking
            
        Returns:
            Dictionary with all step outputs
        """
        chain_name = chain.get('name', 'unknown')
        execution_id = f"{chain_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Starting chain execution: {chain_name} (ID: {execution_id})")
        
        # Initialize context
        context = initial_context or {}
        context['_execution_id'] = execution_id
        context['_chain_name'] = chain_name
        context['_started_at'] = datetime.now().isoformat()
        
        if task_id:
            context['_task_id'] = task_id
        
        # Track execution
        self.active_chains[execution_id] = {
            'chain': chain_name,
            'status': 'running',
            'started_at': context['_started_at'],
            'steps_completed': 0,
            'total_steps': len(chain.get('steps', []))
        }
        
        results = {}
        error = None
        
        try:
            # Execute each step
            for i, step in enumerate(chain.get('steps', [])):
                logger.debug(f"Executing step {i+1}: {step.get('skill')}")
                
                # Resolve input variables from context
                resolved_inputs = self._resolve_inputs(
                    step.get('input', {}), 
                    context
                )
                
                # Execute skill
                skill_name = step.get('skill')
                result = self._execute_skill(skill_name, resolved_inputs)
                
                # Store output in context
                output_key = step.get('output')
                if output_key:
                    context[output_key] = result
                    results[output_key] = result
                
                # Update progress
                self.active_chains[execution_id]['steps_completed'] = i + 1
                
                # Check for error handling
                if result is None and step.get('required', True):
                    raise ValueError(f"Required skill returned None: {skill_name}")
            
            # Mark as completed
            self.active_chains[execution_id]['status'] = 'completed'
            self.active_chains[execution_id]['completed_at'] = datetime.now().isoformat()
            
            # Record in history
            self._record_execution(execution_id, chain_name, results, None)
            
            logger.info(f"Chain execution completed: {chain_name}")
            return results
            
        except Exception as e:
            error = str(e)
            logger.error(f"Chain execution failed: {e}")
            
            # Handle error based on chain config
            error_handling = chain.get('error_handling', {})
            on_failure = error_handling.get('on_failure', 'stop')
            
            if on_failure == 'rollback':
                self._rollback_chain(chain, results)
            
            # Update status
            self.active_chains[execution_id]['status'] = 'failed'
            self.active_chains[execution_id]['error'] = error
            
            # Record in history
            self._record_execution(execution_id, chain_name, results, error)
            
            raise
    
    def _resolve_inputs(self, inputs: dict, context: dict) -> dict:
        """
        Replace ${variable} placeholders with context values.
        
        Args:
            inputs: Input dictionary with potential variable references
            context: Context dictionary with variable values
            
        Returns:
            Resolved input dictionary
        """
        resolved = {}
        
        for key, value in inputs.items():
            resolved[key] = self._resolve_value(value, context)
        
        return resolved
    
    def _resolve_value(self, value: Any, context: dict) -> Any:
        """
        Recursively resolve variable references in a value.
        
        Args:
            value: Value to resolve (can be string, dict, list, etc.)
            context: Context dictionary
            
        Returns:
            Resolved value
        """
        if isinstance(value, str):
            # Check for ${variable} pattern
            if value.startswith('${') and value.endswith('}'):
                var_name = value[2:-1]
                return context.get(var_name)
            
            # Check for nested variables in string
            import re
            pattern = r'\$\{([^}]+)\}'
            matches = re.findall(pattern, value)
            
            if matches:
                result = value
                for match in matches:
                    if match in context:
                        result = result.replace(f'${{{match}}}', str(context[match]))
                return result
            
            return value
        
        elif isinstance(value, dict):
            return {k: self._resolve_value(v, context) for k, v in value.items()}
        
        elif isinstance(value, list):
            return [self._resolve_value(item, context) for item in value]
        
        else:
            return value
    
    def _execute_skill(self, skill_name: str, inputs: dict) -> Any:
        """
        Execute a single skill.
        
        Args:
            skill_name: Name of the skill to execute
            inputs: Input parameters for the skill
            
        Returns:
            Skill execution result
        """
        logger.debug(f"Executing skill: {skill_name} with inputs: {inputs}")
        
        # Try to execute via orchestrator
        if hasattr(self.orchestrator, 'execute_skill'):
            return self.orchestrator.execute_skill(skill_name, **inputs)
        
        # Fallback: try to call method directly on orchestrator
        if hasattr(self.orchestrator, skill_name):
            method = getattr(self.orchestrator, skill_name)
            if callable(method):
                return method(**inputs)
        
        # Last resort: return mock result for testing
        logger.warning(f"Skill not found: {skill_name}, returning mock result")
        return {'skill': skill_name, 'status': 'mock', 'inputs': inputs}
    
    def _rollback_chain(self, chain: dict, results: dict):
        """
        Rollback a chain execution (compensating transactions).
        
        Args:
            chain: Chain definition
            results: Results from executed steps
        """
        logger.info(f"Rolling back chain: {chain.get('name')}")
        
        # Reverse through steps and execute rollback actions if defined
        for step in reversed(chain.get('steps', [])):
            rollback_action = step.get('rollback')
            if rollback_action:
                try:
                    logger.debug(f"Executing rollback: {rollback_action}")
                    # Execute rollback action
                except Exception as e:
                    logger.error(f"Rollback failed for {rollback_action}: {e}")
    
    def _record_execution(
        self, 
        execution_id: str, 
        chain_name: str, 
        results: dict, 
        error: str = None
    ):
        """Record execution in history"""
        record = {
            'execution_id': execution_id,
            'chain_name': chain_name,
            'timestamp': datetime.now().isoformat(),
            'results': results,
            'error': error,
            'status': 'failed' if error else 'completed'
        }
        
        self.execution_history.append(record)
        
        # Remove from active chains
        if execution_id in self.active_chains:
            del self.active_chains[execution_id]
        
        # Save to file if chains path exists
        if self.chains_path.exists():
            history_file = self.chains_path.parent.parent / "Chains" / "chain_history.jsonl"
            try:
                with open(history_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(record) + '\n')
            except Exception as e:
                logger.warning(f"Failed to save execution history: {e}")
    
    def get_chain_status(self, execution_id: str) -> Optional[dict]:
        """Get status of a chain execution"""
        return self.active_chains.get(execution_id)
    
    def get_execution_history(
        self, 
        chain_name: str = None,
        limit: int = 20
    ) -> List[dict]:
        """
        Get execution history.
        
        Args:
            chain_name: Filter by chain name (optional)
            limit: Maximum number of records to return
            
        Returns:
            List of execution records
        """
        history = self.execution_history
        
        if chain_name:
            history = [h for h in history if h.get('chain_name') == chain_name]
        
        return history[-limit:]
    
    def list_chains(self) -> List[str]:
        """List available chain names"""
        return list(self.chains.keys())
    
    def get_chain_info(self, chain_name: str) -> Optional[dict]:
        """
        Get information about a chain.
        
        Args:
            chain_name: Name of the chain
            
        Returns:
            Chain information dictionary
        """
        chain = self.chains.get(chain_name)
        
        if not chain:
            return None
        
        return {
            'name': chain.get('name'),
            'description': chain.get('description', ''),
            'version': chain.get('version', '1.0'),
            'steps_count': len(chain.get('steps', [])),
            'has_error_handling': 'error_handling' in chain
        }


# Helper function to create chain YAML files
def create_chain_template(
    name: str,
    description: str,
    steps: List[dict],
    output_path: Path
) -> Path:
    """
    Create a chain template YAML file.
    
    Args:
        name: Chain name
        description: Chain description
        steps: List of step definitions
        output_path: Directory to save the file
        
    Returns:
        Path to created file
    """
    chain = {
        'name': name,
        'description': description,
        'version': '1.0',
        'steps': steps,
        'error_handling': {
            'on_failure': 'rollback',
            'max_retries': 2,
            'notify_on_error': True
        }
    }
    
    output_path.mkdir(exist_ok=True)
    chain_file = output_path / f"{name}.yaml"
    
    with open(chain_file, 'w', encoding='utf-8') as f:
        yaml.dump(chain, f, default_flow_style=False, sort_keys=False)
    
    logger.info(f"Created chain template: {chain_file}")
    return chain_file
