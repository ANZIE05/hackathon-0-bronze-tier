# Silver Tier Architecture Documentation

## Personal AI Employee - Silver Tier Implementation

**Version:** 0.2.0-Silver  
**Date:** March 2026  
**Status:** Complete

---

## Table of Contents

1. [Overview](#overview)
2. [Silver Tier Requirements](#silver-tier-requirements)
3. [Architecture Diagram](#architecture-diagram)
4. [Core Components](#core-components)
5. [Module Reference](#module-reference)
6. [Data Flow](#data-flow)
7. [Configuration](#configuration)
8. [Usage Guide](#usage-guide)

---

## Overview

The Silver Tier implementation adds **reasoning and planning capabilities** on top of the Bronze Tier sensing system. It transforms the AI Employee from a reactive system into a **proactive, intelligent assistant** that can:

- **Prioritize tasks** intelligently using a Decision Engine
- **Generate plans** with AI reasoning
- **Execute complex workflows** via Skill Chains
- **Remember context** across sessions with Three-Tier Memory
- **Handle approvals** with Human-in-the-Loop workflow
- **Schedule tasks** for timed operations
- **Take external actions** via MCP servers

### Key Improvements Over Bronze Tier

| Feature | Bronze Tier | Silver Tier |
|---------|-------------|-------------|
| Task Selection | FIFO / Simple | Priority-based Decision Engine |
| Reasoning | None | Plan Generation with Context |
| Memory | None | Three-Tier (Session/Episodic/Semantic) |
| Workflows | Single skills | Skill Chains |
| Approvals | Folder structure | Full HITL Workflow |
| Scheduling | None | Cron-like Task Scheduler |
| External Actions | None | MCP Servers (Email, LinkedIn) |

---

## Silver Tier Requirements

All Silver Tier requirements from the hackathon are satisfied:

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| ✅ All Bronze requirements | Complete | Foundation maintained |
| ✅ Two+ Watcher scripts | Complete | Gmail + Filesystem + (WhatsApp optional) |
| ✅ LinkedIn auto-posting | Complete | LinkedIn MCP Server (draft mode) |
| ✅ Claude reasoning loop (Plan.md) | Complete | Plan Generator with context |
| ✅ One working MCP server | Complete | Email MCP + LinkedIn MCP |
| ✅ Human-in-the-loop approval | Complete | Approval Workflow system |
| ✅ Basic scheduling | Complete | Task Scheduler with cron-like jobs |
| ✅ All AI as Agent Skills | Complete | 13 skills defined in config |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SILVER TIER ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐            │
│  │   Gmail      │     │  Filesystem  │     │  (WhatsApp)  │            │
│  │   Watcher    │     │   Watcher    │     │   Watcher    │            │
│  └──────┬───────┘     └──────┬───────┘     └──────┬───────┘            │
│         │                    │                    │                     │
│         └────────────────────┼────────────────────┘                     │
│                              │                                          │
│                              ▼                                          │
│                    ┌─────────────────┐                                  │
│                    │   Needs_Action  │                                  │
│                    │     Folder      │                                  │
│                    └────────┬────────┘                                  │
│                             │                                           │
│                             ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      ORCHESTRATOR                                │   │
│  │  ┌──────────────────────────────────────────────────────────┐   │   │
│  │  │              DECISION ENGINE (Silver)                     │   │   │
│  │  │  - Task Selection    - Priority Scoring                   │   │   │
│  │  │  - Chain Selection   - Approval Check                     │   │   │
│  │  └──────────────────────────────────────────────────────────┘   │   │
│  │  ┌──────────────────────────────────────────────────────────┐   │   │
│  │  │              MEMORY STORE (Silver)                        │   │   │
│  │  │  - Session Memory    - Episodic Memory                    │   │   │
│  │  │  - Semantic Memory   - Context Retrieval                  │   │   │
│  │  └──────────────────────────────────────────────────────────┘   │   │
│  │  ┌──────────────────────────────────────────────────────────┐   │   │
│  │  │              PLAN GENERATOR (Silver)                      │   │   │
│  │  │  - AI Reasoning      - Context Integration                │   │   │
│  │  │  - Plan.md Creation  - Action Steps                       │   │   │
│  │  └──────────────────────────────────────────────────────────┘   │   │
│  │  ┌──────────────────────────────────────────────────────────┐   │   │
│  │  │           SKILL CHAIN EXECUTOR (Silver)                   │   │   │
│  │  │  - Chain Loading     - Variable Substitution              │   │   │
│  │  │  - Step Execution    - Error Handling                     │   │   │
│  │  └──────────────────────────────────────────────────────────┘   │   │
│  │  ┌──────────────────────────────────────────────────────────┐   │   │
│  │  │           APPROVAL WORKFLOW (Silver)                      │   │   │
│  │  │  - Threshold Check   - Request Creation                   │   │   │
│  │  │  - Approval Tracking - Execution                          │   │   │
│  │  └──────────────────────────────────────────────────────────┘   │   │
│  │  ┌──────────────────────────────────────────────────────────┐   │   │
│  │  │              TASK SCHEDULER (Silver)                      │   │   │
│  │  │  - Daily Tasks       - Weekly Tasks                       │   │   │
│  │  │  - Interval Tasks    - Cron-like Jobs                     │   │   │
│  │  └──────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                             │                                           │
│         ┌───────────────────┼───────────────────┐                      │
│         │                   │                   │                      │
│         ▼                   ▼                   ▼                      │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                  │
│  │ MCP Email   │   │ MCP LinkedIn│   │   (MCP      │                  │
│  │   Server    │   │   Server    │   │   Payment)  │                  │
│  └─────────────┘   └─────────────┘   └─────────────┘                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Decision Engine (`silver/decision_engine.py`)

**Purpose:** Intelligent task selection and prioritization

**Key Features:**
- Priority scoring using multiple factors
- Task type to skill chain mapping
- Approval requirement checking
- Statistics and monitoring

**API:**
```python
engine = DecisionEngine(vault_path)

# Select next task
task = engine.select_next_task()

# Get priority score
score = engine._calculate_task_score(task_file)

# Select skill chain
chain = engine.select_chain_for_task(task_file)

# Check approval requirement
needs_approval, reason = engine.requires_approval(task_file)
```

### 2. Memory Store (`silver/memory_store.py`)

**Purpose:** Three-tier memory system for context-aware actions

**Memory Tiers:**
- **Short-Term (Session):** Current task, recent decisions, active contexts
- **Long-Term (Episodic):** Past decisions, completed tasks, client history
- **Semantic (Facts):** Company handbook, rules, rates, reference data

**API:**
```python
memory = MemoryStore(vault_path)

# Store decision
memory.store_decision('task_001', {'action': 'sent_email'})

# Retrieve similar decisions
similar = memory.retrieve_similar_decisions({'type': 'email'})

# Get context for task
context = memory.get_context_for_task('email', sender='client@example.com')
```

### 3. Priority Matrix (`silver/priority_matrix.py`)

**Purpose:** Multi-factor priority scoring system

**Scoring Factors:**
- Explicit priority (30% weight)
- Keyword urgency (20% weight)
- Task age (15% weight)
- Source type (15% weight)
- Handbook rules (20% weight)

**Priority Levels:**
| Score | Level | Response Time |
|-------|-------|---------------|
| 90-100 | Critical | Immediate |
| 70-89 | High | < 1 hour |
| 40-69 | Medium | < 4 hours |
| 0-39 | Low | < 24 hours |

### 4. Plan Generator (`silver/plan_generator.py`)

**Purpose:** Generate structured Plan.md files with AI reasoning

**Plan Structure:**
- Task summary
- Context (from memory)
- Action plan
- Required resources
- Potential blockers
- Success criteria
- Progress tracking checkboxes

**API:**
```python
generator = PlanGenerator(vault_path)
plan_path = generator.create_plan(task_file)
```

### 5. Skill Chain Executor (`silver/skill_chain_executor.py`)

**Purpose:** Execute multi-step workflows as chains

**Chain Definition (YAML):**
```yaml
name: "email_triage_chain"
steps:
  - skill: "parse_email_frontmatter"
    output: "email_data"
  - skill: "check_company_handbook"
    input:
      topic: "email response guidelines"
    output: "guidelines"
  - skill: "create_action_item"
    input:
      email_data: "${email_data}"
      guidelines: "${guidelines}"
```

**API:**
```python
executor = SkillChainExecutor(orchestrator, chains_path)
chain = executor.load_chain('email_triage_chain')
results = executor.execute_chain(chain, initial_context)
```

### 6. Approval Workflow (`silver/approval_workflow.py`)

**Purpose:** Human-in-the-Loop approval system

**Approval Thresholds (from Company Handbook):**
- Payments under $50: Auto-approve if recurring
- Payments $50-$200: Require approval
- Payments over $200: Require human approval
- Social media posts: Always require approval

**API:**
```python
workflow = ApprovalWorkflow(vault_path)

# Check if approval needed
needs_approval, reason = workflow.requires_approval(task_file)

# Create approval request
request_path = workflow.create_approval_request(action_type, details)

# Get pending approvals
pending = workflow.get_pending_approvals()
```

### 7. Task Scheduler (`silver/scheduler.py`)

**Purpose:** Cron-like scheduling for timed operations

**Task Types:**
- **Daily Tasks:** Run at specific time each day
- **Weekly Tasks:** Run on specific day/time each week
- **Interval Tasks:** Run every N minutes

**Default Scheduled Tasks:**
| Task | Schedule | Action |
|------|----------|--------|
| Morning Briefing | Daily 8:00 AM | Generate briefing |
| Check Approvals | Daily 12:00 PM | Check expired |
| Evening Review | Daily 6:00 PM | Review completed |
| Weekly Audit | Sunday 8:00 PM | Business audit |
| Health Check | Every 60 min | System health |

### 8. MCP Servers

**Email MCP Server (`silver/mcp_servers/email_mcp_server.py`):**
- Send emails via SMTP
- Create drafts
- Manage email folders

**LinkedIn MCP Server (`silver/mcp_servers/linkedin_mcp_server.py`):**
- Create LinkedIn posts
- Generate post content
- Schedule posts
- Publish (with API credentials)

---

## Module Reference

### Directory Structure

```
vault/
├── silver/
│   ├── __init__.py
│   ├── memory_store.py          # Three-tier memory
│   ├── decision_engine.py       # Task selection
│   ├── priority_matrix.py       # Priority scoring
│   ├── plan_generator.py        # Plan.md generation
│   ├── skill_chain_executor.py  # Chain execution
│   ├── approval_workflow.py     # HITL approvals
│   ├── scheduler.py             # Task scheduling
│   │
│   ├── chains/                  # Skill chain definitions
│   │   ├── email_triage_chain.yaml
│   │   ├── invoice_request_chain.yaml
│   │   ├── social_post_chain.yaml
│   │   ├── payment_approval_chain.yaml
│   │   └── file_processing_chain.yaml
│   │
│   ├── mcp_servers/             # MCP server implementations
│   │   ├── email_mcp_server.py
│   │   └── linkedin_mcp_server.py
│   │
│   └── templates/               # Templates
│       └── plan_template.md
│
├── Memory/                      # Memory storage
│   └── Episodic/               # Time-stamped decisions
│
├── Plans/                       # Generated plans
├── Schedules/                   # Scheduled task configs
└── Posts/                       # Social media posts
    └── LinkedIn/
```

---

## Data Flow

### Task Processing Flow (Silver Tier)

```
1. Watcher creates task in Needs_Action/
         │
         ▼
2. Decision Engine selects highest priority task
         │
         ▼
3. Memory Store retrieves context (similar tasks, sender history)
         │
         ▼
4. Plan Generator creates Plan.md with reasoning
         │
         ▼
5. Approval Workflow checks if approval required
         │
    ┌────┴────┐
    │  Yes    │  No
    │   ▼     │   ▼
    │ Create  │  Select Skill Chain
    │ Approval│   │
    │ Request │   ▼
    │   │     │  Execute Chain
    │   ▼     │   │
    │ Wait    │   ▼
    │ Human   │  Move to Done
    │ Action  │
    └─────────┘
```

---

## Configuration

### Environment Variables

```bash
# Email MCP Server
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_ADDRESS=your_email@gmail.com
EMAIL_PASSWORD=your_app_password

# LinkedIn MCP Server
LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_client_secret
LINKEDIN_ACCESS_TOKEN=your_access_token
LINKEDIN_PERSON_URN=your_person_urn

# Watcher Configuration
WATCHER_CHECK_INTERVAL=30
FILESYSTEM_CHECK_INTERVAL=5
```

### Skills Configuration (`agent_skills_config.json`)

```json
{
  "name": "personal-ai-employee",
  "version": "0.2.0-silver",
  "skills": [
    {"name": "generate_plan", ...},
    {"name": "execute_skill_chain", ...},
    {"name": "send_email_via_mcp", ...},
    ...
  ],
  "chains": [
    {"name": "email_triage_chain", ...},
    ...
  ]
}
```

---

## Usage Guide

### Starting the Orchestrator (Silver Tier)

```python
from orchestrator import Orchestrator

# Initialize with Silver Tier enabled (default)
orchestrator = Orchestrator(vault_path=".", enable_silver_tier=True)

# Run with Decision Engine
orchestrator.run(
    check_interval=30,
    auto_execute_skills=False,
    use_decision_engine=True  # Use Silver Tier Decision Engine
)
```

### Using Individual Components

```python
from pathlib import Path
from silver.decision_engine import DecisionEngine
from silver.memory_store import MemoryStore
from silver.plan_generator import PlanGenerator

vault = Path(".")

# Decision Engine
engine = DecisionEngine(vault)
task = engine.select_next_task()

# Memory
memory = MemoryStore(vault)
context = memory.get_context_for_task('email')

# Plan Generator
generator = PlanGenerator(vault)
plan = generator.create_plan(task)
```

### Creating Custom Skill Chains

```yaml
# my_custom_chain.yaml
name: "my_custom_chain"
description: "Custom workflow for specific task"
version: "1.0"

steps:
  - skill: "skill_one"
    input:
      param: "value"
    output: "result_one"
  
  - skill: "skill_two"
    input:
      data: "${result_one}"
    output: "final_result"

error_handling:
  on_failure: "rollback"
  max_retries: 2
```

### Scheduling Custom Tasks

```python
from silver.scheduler import TaskScheduler

scheduler = TaskScheduler(vault, orchestrator)

# Add daily task
scheduler.add_daily_task(
    name='noon_check',
    time='12:00',
    action='check_emails',
    description='Check for urgent emails at noon'
)

# Add weekly task
scheduler.add_weekly_task(
    name='friday_report',
    day='friday',
    time='16:00',
    action='generate_weekly_report'
)

# Start scheduler
scheduler.start()
```

---

## Testing

Run the test suite:

```bash
cd vault
python3 test_silver_tier.py
```

---

## Next Steps (Gold Tier)

- Full LinkedIn API integration (requires business account)
- WhatsApp watcher integration
- Payment gateway MCP server
- Enhanced AI reasoning with Claude Code integration
- Real-time collaboration features

---

*Silver Tier Implementation Complete - Ready for Gold Tier Development*
