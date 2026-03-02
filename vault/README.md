# Personal AI Employee - Bronze Tier Implementation

This project implements the Bronze Tier requirements for the Personal AI Employee Hackathon 0: Building Autonomous FTEs in 2026.

## Bronze Tier Requirements Completed

✅ **Obsidian vault with Dashboard.md and Company_Handbook.md**
✅ **One working Watcher script (Gmail AND file system monitoring)**
✅ **Claude Code successfully reading from and writing to the vault**
✅ **Basic folder structure: /Inbox, /Needs_Action, /Done**
✅ **All AI functionality implemented as Agent Skills**

## Directory Structure

```
├── Dashboard.md          # Main dashboard showing system status
├── Company_Handbook.md   # Rules of engagement and operating procedures
├── Inbox/               # Incoming files for processing
├── Needs_Action/        # Items requiring action
├── Done/                # Completed items
├── Logs/                # System logs
├── Plans/               # Planning documents
├── Pending_Approval/    # Items awaiting human approval
├── Approved/            # Approved items
├── Rejected/            # Rejected items
├── gmail_watcher.py     # Gmail monitoring script
├── filesystem_watcher.py # File system monitoring script
├── orchestrator.py      # Main orchestration script
├── demo_claude_integration.py # Claude Code integration demo
└── README.md           # This file
```

## Components

### 1. Dashboard.md
The central dashboard showing system status, recent activity, and statistics.

### 2. Company_Handbook.md
Contains rules of engagement, approval thresholds, communication guidelines, and standard operating procedures.

### 3. Watcher Scripts
- **gmail_watcher.py**: Monitors Gmail for new messages and creates action files in Needs_Action folder
- **filesystem_watcher.py**: Monitors the Inbox folder for new files and creates action files

### 4. Orchestrator.py
Main orchestration script that:
- Starts and monitors watcher services
- Processes files in the vault
- Updates the dashboard
- Manages the AI reasoning loop

### 5. Claude Code Integration
Demonstrated through `demo_claude_integration.py` which shows:
- Reading from vault (Dashboard, Company_Handbook, etc.)
- Writing new files to appropriate folders
- Processing information according to Company Handbook
- Updating Dashboard with system activity

## How to Run

1. **Start the orchestrator** (manages all services):
```bash
python3 orchestrator.py
```

2. **Or run individual watchers separately**:
```bash
# Terminal 1: Run the file system watcher
python3 filesystem_watcher.py

# Terminal 2: Run the Gmail watcher
python3 gmail_watcher.py
```

3. **Monitor the system**:
- Check Dashboard.md for system status
- Add files to Inbox/ to trigger processing
- Monitor Needs_Action/ for items requiring attention
- Check Done/ for completed items

## Features

- **File-based workflow**: Uses markdown files with YAML frontmatter for structured data
- **Human-in-the-loop**: Critical actions require approval through file movement
- **Persistent monitoring**: Watchers run continuously to detect new events
- **Audit trail**: All actions are logged and tracked
- **Modular design**: Easy to extend with additional watchers and capabilities

## Security Considerations

- Credentials should be stored in environment variables, not in the vault
- Sensitive operations require human approval via file movement
- All actions are logged for audit purposes
- System operates locally to maintain privacy

## Next Steps (Silver/Gold Tier)

- Add more watcher types (WhatsApp, social media, etc.)
- Implement MCP servers for external actions
- Add scheduling capabilities
- Enhance with more sophisticated AI reasoning loops

## License

This project is part of the Personal AI Employee Hackathon and follows the guidelines set forth in the hackathon documentation.