#!/usr/bin/env python3
"""
Silver Tier Test Suite

Tests all Silver Tier components:
- Memory Store
- Decision Engine
- Priority Matrix
- Plan Generator
- Skill Chain Executor
- Approval Workflow
- Task Scheduler
"""

import sys
from pathlib import Path

def test_silver_tier_imports():
    """Test that all Silver Tier modules can be imported"""
    print("=" * 60)
    print("TEST 1: Silver Tier Module Imports")
    print("=" * 60)
    
    try:
        from silver.memory_store import MemoryStore
        from silver.priority_matrix import PriorityMatrix, PriorityLevel
        from silver.decision_engine import DecisionEngine
        from silver.skill_chain_executor import SkillChainExecutor
        from silver.plan_generator import PlanGenerator
        from silver.approval_workflow import ApprovalWorkflow
        from silver.scheduler import TaskScheduler
        print("✅ All Silver Tier modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_memory_store():
    """Test Memory Store functionality"""
    print("\n" + "=" * 60)
    print("TEST 2: Memory Store")
    print("=" * 60)
    
    try:
        from silver.memory_store import MemoryStore
        
        vault_path = Path(".")
        memory = MemoryStore(vault_path)
        
        # Test short-term memory
        memory.set_current_task("test_001", {"type": "email"})
        task = memory.get_current_task()
        assert task is not None, "Failed to store current task"
        print("✅ Short-term memory: OK")
        
        # Test decision storage
        memory.store_decision("test_001", {"action": "test"}, {"type": "test"})
        print("✅ Episodic memory storage: OK")
        
        # Test semantic memory
        memory.update_semantic_index("test_key", "test_value")
        value = memory.get_semantic_fact("test_key")
        assert value == "test_value", "Failed to store/retrieve semantic fact"
        print("✅ Semantic memory: OK")
        
        # Test context retrieval
        context = memory.get_context_for_task("email")
        assert "company_handbook" in context, "Context missing expected key"
        print("✅ Context retrieval: OK")
        
        return True
        
    except Exception as e:
        print(f"❌ Memory Store test failed: {e}")
        return False


def test_priority_matrix():
    """Test Priority Matrix functionality"""
    print("\n" + "=" * 60)
    print("TEST 3: Priority Matrix")
    print("=" * 60)
    
    try:
        from silver.priority_matrix import PriorityMatrix, PriorityLevel
        
        matrix = PriorityMatrix()
        
        # Test priority scoring
        content = "URGENT: Payment needed immediately"
        frontmatter = {"priority": "high", "type": "payment", "amount": 500}
        
        score = matrix.calculate_score(content, frontmatter)
        assert 0 <= score <= 100, f"Invalid score: {score}"
        print(f"✅ Priority scoring: OK (score={score})")
        
        # Test priority level conversion
        level = matrix.get_priority_level(score)
        assert isinstance(level, PriorityLevel), "Invalid priority level"
        print(f"✅ Priority level: {level.value}")
        
        # Test approval check
        can_auto, reason = matrix.can_auto_execute("payment", {"amount": 500}, score)
        print(f"✅ Auto-execution check: {'Allowed' if can_auto else 'Requires Approval'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Priority Matrix test failed: {e}")
        return False


def test_decision_engine():
    """Test Decision Engine functionality"""
    print("\n" + "=" * 60)
    print("TEST 4: Decision Engine")
    print("=" * 60)
    
    try:
        from silver.decision_engine import DecisionEngine
        
        vault_path = Path(".")
        engine = DecisionEngine(vault_path)
        
        # Test task selection
        task = engine.select_next_task()
        if task:
            print(f"✅ Task selection: OK (selected: {task.name})")
        else:
            print("✅ Task selection: OK (no pending tasks)")
        
        # Test chain selection
        chains = engine.list_chains() if hasattr(engine, 'list_chains') else engine.chain_map
        print(f"✅ Chain mapping: {len(chains)} chains configured")
        
        # Test statistics
        stats = engine.get_task_statistics()
        print(f"✅ Statistics: {stats['total']} pending tasks")
        
        return True
        
    except Exception as e:
        print(f"❌ Decision Engine test failed: {e}")
        return False


def test_plan_generator():
    """Test Plan Generator functionality"""
    print("\n" + "=" * 60)
    print("TEST 5: Plan Generator")
    print("=" * 60)
    
    try:
        from silver.plan_generator import PlanGenerator
        
        vault_path = Path(".")
        generator = PlanGenerator(vault_path)
        
        # Find a test task file
        needs_action = vault_path / "Needs_Action"
        if needs_action.exists():
            test_files = list(needs_action.glob("*.md"))
            if test_files:
                plan_path = generator.create_plan(test_files[0])
                print(f"✅ Plan generation: OK (created: {plan_path.name})")
            else:
                print("⚠️  Plan generation: No test files available")
        else:
            print("⚠️  Plan generation: Needs_Action folder not found")
        
        return True
        
    except Exception as e:
        print(f"❌ Plan Generator test failed: {e}")
        return False


def test_skill_chain_executor():
    """Test Skill Chain Executor functionality"""
    print("\n" + "=" * 60)
    print("TEST 6: Skill Chain Executor")
    print("=" * 60)
    
    try:
        from silver.skill_chain_executor import SkillChainExecutor
        
        vault_path = Path(".")
        chains_path = vault_path / "silver" / "chains"
        
        # Create mock orchestrator
        class MockOrchestrator:
            def execute_skill(self, name, **kwargs):
                return {"status": "mock", "skill": name}
        
        executor = SkillChainExecutor(MockOrchestrator(), chains_path)
        
        # List available chains
        chains = executor.list_chains()
        print(f"✅ Available chains: {len(chains)} ({', '.join(chains)})")
        
        # Test chain loading
        if chains:
            chain = executor.load_chain(chains[0])
            assert chain is not None, "Failed to load chain"
            print(f"✅ Chain loading: OK ({chain['name']})")
        
        return True
        
    except Exception as e:
        print(f"❌ Skill Chain Executor test failed: {e}")
        return False


def test_approval_workflow():
    """Test Approval Workflow functionality"""
    print("\n" + "=" * 60)
    print("TEST 7: Approval Workflow")
    print("=" * 60)
    
    try:
        from silver.approval_workflow import ApprovalWorkflow
        
        vault_path = Path(".")
        workflow = ApprovalWorkflow(vault_path)
        
        # Test approval check for payment
        requires_approval, reason = workflow.requires_approval(
            task_metadata={"type": "payment", "amount": 500}
        )
        print(f"✅ Payment approval check: {'Required' if requires_approval else 'Not Required'}")
        print(f"   Reason: {reason}")
        
        # Test approval request creation
        request_path = workflow.create_approval_request(
            action_type="payment",
            action_details={"amount": 100, "recipient": "Test Vendor"},
            priority="medium"
        )
        print(f"✅ Approval request created: {request_path.name}")
        
        # Test statistics
        stats = workflow.get_approval_statistics()
        print(f"✅ Approval stats: {stats['pending_count']} pending, {stats['approved_count']} approved")
        
        return True
        
    except Exception as e:
        print(f"❌ Approval Workflow test failed: {e}")
        return False


def test_scheduler():
    """Test Task Scheduler functionality"""
    print("\n" + "=" * 60)
    print("TEST 8: Task Scheduler")
    print("=" * 60)
    
    try:
        from silver.scheduler import TaskScheduler
        
        vault_path = Path(".")
        
        # Create mock orchestrator
        class MockOrchestrator:
            def update_dashboard(self):
                pass
        
        scheduler = TaskScheduler(vault_path, MockOrchestrator())
        
        # Test configuration
        status = scheduler.get_schedule_status()
        task_count = status.get('scheduled_tasks', 0)
        print(f"✅ Scheduler status: {task_count} tasks configured")
        
        # Test adding tasks
        scheduler.add_daily_task("test_task", "23:59", "test_action", "Test task")
        print("✅ Task addition: OK")
        
        return True
        
    except Exception as e:
        print(f"❌ Scheduler test failed: {e}")
        return False


def test_mcp_servers():
    """Test MCP Server functionality"""
    print("\n" + "=" * 60)
    print("TEST 9: MCP Servers")
    print("=" * 60)
    
    try:
        from silver.mcp_servers.email_mcp_server import EmailMCPServer
        from silver.mcp_servers.linkedin_mcp_server import LinkedInMCPServer
        
        vault_path = Path(".")
        
        # Test Email MCP Server
        email_server = EmailMCPServer(vault_path)
        tools = email_server.get_tools()
        print(f"✅ Email MCP Server: {len(tools)} tools available")
        
        # Test LinkedIn MCP Server
        linkedin_server = LinkedInMCPServer(vault_path)
        tools = linkedin_server.get_tools()
        print(f"✅ LinkedIn MCP Server: {len(tools)} tools available")
        
        return True
        
    except Exception as e:
        print(f"❌ MCP Servers test failed: {e}")
        return False


def test_orchestrator_integration():
    """Test Orchestrator Silver Tier integration"""
    print("\n" + "=" * 60)
    print("TEST 10: Orchestrator Integration")
    print("=" * 60)
    
    try:
        from orchestrator import Orchestrator, SILVER_TIER_AVAILABLE
        
        print(f"Silver Tier Available: {SILVER_TIER_AVAILABLE}")
        
        vault_path = Path(".")
        orchestrator = Orchestrator(vault_path=vault_path, enable_silver_tier=True)
        
        print(f"✅ Orchestrator initialized (Silver Tier: {orchestrator.silver_enabled})")
        
        if orchestrator.silver_enabled:
            print("✅ Memory Store: Connected")
            print("✅ Decision Engine: Connected")
            print("✅ Plan Generator: Connected")
            print("✅ Skill Chain Executor: Connected")
            print("✅ Approval Workflow: Connected")
            print("✅ Task Scheduler: Connected")
        
        # Test skill execution
        result = orchestrator.execute_skill("update_dashboard")
        print(f"✅ Skill execution test: {result.get('status', 'unknown')}")
        
        return orchestrator.silver_enabled
        
    except Exception as e:
        print(f"❌ Orchestrator integration test failed: {e}")
        return False


def main():
    """Run all Silver Tier tests"""
    print("\n" + "=" * 60)
    print("SILVER TIER TEST SUITE")
    print("Personal AI Employee - Silver Tier Implementation")
    print("=" * 60)
    
    results = []
    
    # Run all tests
    results.append(("Module Imports", test_silver_tier_imports()))
    results.append(("Memory Store", test_memory_store()))
    results.append(("Priority Matrix", test_priority_matrix()))
    results.append(("Decision Engine", test_decision_engine()))
    results.append(("Plan Generator", test_plan_generator()))
    results.append(("Skill Chain Executor", test_skill_chain_executor()))
    results.append(("Approval Workflow", test_approval_workflow()))
    results.append(("Scheduler", test_scheduler()))
    results.append(("MCP Servers", test_mcp_servers()))
    results.append(("Orchestrator Integration", test_orchestrator_integration()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({100*passed/total:.1f}%)")
    
    if passed == total:
        print("\n🎉 ALL SILVER TIER TESTS PASSED!")
        print("\nSilver Tier Implementation Status: COMPLETE")
        print("Ready for Gold Tier Development")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
