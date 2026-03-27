"""
MCP Email Server for Personal AI Employee - Silver Tier

Model Context Protocol (MCP) server for email operations.
Provides email send/receive capabilities for the AI Employee.

Usage:
    python email_mcp_server.py
    
Or integrate with Claude Code via MCP configuration.
"""

import logging
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmailMCPServer:
    """
    MCP Server for email operations.
    
    Provides tools for:
    - Sending emails
    - Reading emails
    - Drafting email responses
    - Managing email folders
    """
    
    def __init__(self, vault_path: Path = None):
        """
        Initialize the email MCP server.
        
        Args:
            vault_path: Path to the Obsidian vault
        """
        self.vault_path = vault_path or Path(".")
        
        # Email configuration
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        self.email_address = os.environ.get('EMAIL_ADDRESS', '')
        self.email_password = os.environ.get('EMAIL_PASSWORD', '')
        
        # Sent emails log
        self.sent_emails_path = self.vault_path / "Logs" / "sent_emails"
        self.sent_emails_path.mkdir(exist_ok=True)
        
        # Drafts folder
        self.drafts_path = self.vault_path / "Drafts"
        self.drafts_path.mkdir(exist_ok=True)
        
        logger.info(f"EmailMCPServer initialized")
        logger.info(f"SMTP Server: {self.smtp_server}:{self.smtp_port}")
    
    # ==================== MCP Tool Definitions ====================
    
    def get_tools(self) -> List[dict]:
        """Get list of available MCP tools"""
        return [
            {
                'name': 'send_email',
                'description': 'Send an email to a recipient',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'to': {
                            'type': 'string',
                            'description': 'Recipient email address'
                        },
                        'subject': {
                            'type': 'string',
                            'description': 'Email subject'
                        },
                        'body': {
                            'type': 'string',
                            'description': 'Email body content'
                        },
                        'cc': {
                            'type': 'string',
                            'description': 'CC recipients (comma-separated)'
                        },
                        'attachments': {
                            'type': 'array',
                            'items': {'type': 'string'},
                            'description': 'Paths to attachment files'
                        }
                    },
                    'required': ['to', 'subject', 'body']
                }
            },
            {
                'name': 'draft_email',
                'description': 'Create an email draft for review',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'to': {'type': 'string'},
                        'subject': {'type': 'string'},
                        'body': {'type': 'string'},
                        'reference_task': {'type': 'string'}
                    },
                    'required': ['to', 'subject', 'body']
                }
            },
            {
                'name': 'read_email',
                'description': 'Read email content from a file',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'email_file': {
                            'type': 'string',
                            'description': 'Path to email file'
                        }
                    },
                    'required': ['email_file']
                }
            },
            {
                'name': 'list_drafts',
                'description': 'List all email drafts',
                'inputSchema': {
                    'type': 'object',
                    'properties': {}
                }
            },
            {
                'name': 'send_draft',
                'description': 'Send a draft email',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'draft_file': {'type': 'string'}
                    },
                    'required': ['draft_file']
                }
            }
        ]
    
    # ==================== Tool Implementations ====================
    
    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: str = None,
        attachments: List[str] = None
    ) -> dict:
        """
        Send an email.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body content
            cc: CC recipients
            attachments: List of attachment file paths
            
        Returns:
            Result dictionary with status and message
        """
        logger.info(f"Sending email to {to}: {subject}")
        
        # Check if credentials are configured
        if not self.email_address or not self.email_password:
            logger.warning("Email credentials not configured, creating draft instead")
            return self.draft_email(to, subject, body)
        
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email_address
            msg['To'] = to
            msg['Subject'] = subject
            
            if cc:
                msg['Cc'] = cc
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Add attachments
            if attachments:
                from email.mime.base import MIMEBase
                from email import encoders
                
                for attachment_path in attachments:
                    attachment = Path(attachment_path)
                    if attachment.exists():
                        with open(attachment, 'rb') as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename="{attachment.name}"'
                            )
                            msg.attach(part)
            
            # Send email
            recipients = [to]
            if cc:
                recipients.extend(cc.split(','))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_address, self.email_password)
            server.send_message(msg, to_addrs=recipients)
            server.quit()
            
            # Log sent email
            self._log_sent_email(to, subject, body)
            
            return {
                'success': True,
                'message': f'Email sent to {to}',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to send email'
            }
    
    def draft_email(
        self,
        to: str,
        subject: str,
        body: str,
        reference_task: str = None
    ) -> dict:
        """
        Create an email draft.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body content
            reference_task: Optional reference to task file
            
        Returns:
            Result dictionary with draft file path
        """
        logger.info(f"Creating email draft to {to}: {subject}")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        draft_filename = f"DRAFT_{timestamp}_{subject[:30].replace(' ', '_')}.md"
        draft_path = self.drafts_path / draft_filename
        
        draft_content = f"""---
type: email_draft
to: {to}
subject: {subject}
created: {datetime.now().isoformat()}
status: draft
---

# Email Draft

## To: {to}
## Subject: {subject}

{body}

---
*Draft created by AI Employee - Review before sending*
"""
        
        if reference_task:
            draft_content += f"\n\n**Reference Task:** {reference_task}\n"
        
        draft_path.write_text(draft_content, encoding='utf-8')
        
        return {
            'success': True,
            'draft_file': str(draft_path),
            'message': f'Draft created: {draft_filename}'
        }
    
    def read_email(self, email_file: str) -> dict:
        """
        Read email content from a file.
        
        Args:
            email_file: Path to email file
            
        Returns:
            Email content dictionary
        """
        try:
            path = Path(email_file)
            
            if not path.exists():
                return {
                    'success': False,
                    'error': f'File not found: {email_file}'
                }
            
            content = path.read_text(encoding='utf-8')
            
            # Parse frontmatter
            frontmatter = self._parse_frontmatter(content)
            
            # Get body
            body_match = content.split('---', 2)
            body = body_match[2].strip() if len(body_match) > 2 else content
            
            return {
                'success': True,
                'file': email_file,
                'frontmatter': frontmatter,
                'body': body
            }
            
        except Exception as e:
            logger.error(f"Failed to read email: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_drafts(self) -> dict:
        """
        List all email drafts.
        
        Returns:
            List of draft files
        """
        drafts = list(self.drafts_path.glob("*.md"))
        
        return {
            'success': True,
            'drafts': [
                {
                    'file': str(d),
                    'name': d.name
                }
                for d in drafts
            ],
            'count': len(drafts)
        }
    
    def send_draft(self, draft_file: str) -> dict:
        """
        Send a draft email.
        
        Args:
            draft_file: Path to draft file
            
        Returns:
            Result dictionary
        """
        try:
            path = Path(draft_file)
            
            if not path.exists():
                return {
                    'success': False,
                    'error': f'Draft not found: {draft_file}'
                }
            
            content = path.read_text(encoding='utf-8')
            frontmatter = self._parse_frontmatter(content)
            
            to = frontmatter.get('to', '')
            subject = frontmatter.get('subject', '')
            
            # Get body (after frontmatter)
            body_match = content.split('---', 2)
            body = body_match[2].strip() if len(body_match) > 2 else ''
            
            if not to or not subject:
                return {
                    'success': False,
                    'error': 'Draft missing required fields (to, subject)'
                }
            
            # Send the email
            result = self.send_email(to, subject, body)
            
            if result.get('success'):
                # Move draft to sent
                sent_path = self.sent_emails_path / path.name
                path.rename(sent_path)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to send draft: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # ==================== Helper Methods ====================
    
    def _parse_frontmatter(self, content: str) -> dict:
        """Parse YAML frontmatter from content"""
        import re
        
        frontmatter = {}
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        
        if match:
            yaml_content = match.group(1)
            
            for line in yaml_content.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    
                    frontmatter[key] = value
        
        return frontmatter
    
    def _log_sent_email(self, to: str, subject: str, body: str):
        """Log sent email"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'to': to,
            'subject': subject,
            'body_preview': body[:200]
        }
        
        log_file = self.sent_emails_path / f"sent_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    # ==================== MCP Protocol Handlers ====================
    
    def handle_request(self, request: dict) -> dict:
        """
        Handle an MCP protocol request.
        
        Args:
            request: MCP request dictionary
            
        Returns:
            MCP response dictionary
        """
        method = request.get('method', '')
        params = request.get('params', {})
        
        if method == 'tools/list':
            return {
                'result': {
                    'tools': self.get_tools()
                }
            }
        
        elif method == 'tools/call':
            tool_name = params.get('name')
            arguments = params.get('arguments', {})
            
            return self._call_tool(tool_name, arguments)
        
        else:
            return {
                'error': {
                    'code': -32601,
                    'message': f'Method not found: {method}'
                }
            }
    
    def _call_tool(self, tool_name: str, arguments: dict) -> dict:
        """Call a tool by name"""
        tools = {
            'send_email': self.send_email,
            'draft_email': self.draft_email,
            'read_email': self.read_email,
            'list_drafts': self.list_drafts,
            'send_draft': self.send_draft
        }
        
        tool = tools.get(tool_name)
        
        if not tool:
            return {
                'error': {
                    'code': -32602,
                    'message': f'Tool not found: {tool_name}'
                }
            }
        
        try:
            result = tool(**arguments)
            return {
                'result': result
            }
        except Exception as e:
            return {
                'error': {
                    'code': -32000,
                    'message': str(e)
                }
            }


def main():
    """Main entry point for MCP server"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Email MCP Server')
    parser.add_argument('--vault', type=str, default='.', help='Path to vault')
    parser.add_argument('--stdio', action='store_true', help='Use stdio transport')
    
    args = parser.parse_args()
    
    server = EmailMCPServer(vault_path=Path(args.vault))
    
    if args.stdio:
        # Run in stdio mode for MCP
        logger.info("Running in stdio mode")
        
        for line in sys.stdin:
            try:
                request = json.loads(line)
                response = server.handle_request(request)
                print(json.dumps(response), flush=True)
            except json.JSONDecodeError:
                continue
            except Exception as e:
                logger.error(f"Error processing request: {e}")
    else:
        # Interactive mode
        logger.info("Email MCP Server running in interactive mode")
        logger.info("Available tools:")
        for tool in server.get_tools():
            logger.info(f"  - {tool['name']}: {tool['description']}")


if __name__ == '__main__':
    main()
