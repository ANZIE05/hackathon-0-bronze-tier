"""
MCP LinkedIn Server for Personal AI Employee - Silver Tier

Model Context Protocol (MCP) server for LinkedIn operations.
Provides LinkedIn posting capabilities for the AI Employee.

Note: LinkedIn API requires business account and API access approval.
This implementation uses a draft-first approach with manual posting
as a fallback when API access is not available.

Usage:
    python linkedin_mcp_server.py
    
Or integrate with Claude Code via MCP configuration.
"""

import logging
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LinkedInMCPServer:
    """
    MCP Server for LinkedIn operations.
    
    Provides tools for:
    - Creating LinkedIn posts
    - Scheduling posts
    - Managing post drafts
    - Generating post content
    """
    
    def __init__(self, vault_path: Path = None):
        """
        Initialize the LinkedIn MCP server.
        
        Args:
            vault_path: Path to the Obsidian vault
        """
        self.vault_path = vault_path or Path(".")
        
        # LinkedIn API configuration (optional)
        self.linkedin_client_id = os.environ.get('LINKEDIN_CLIENT_ID', '')
        self.linkedin_client_secret = os.environ.get('LINKEDIN_CLIENT_SECRET', '')
        self.linkedin_access_token = os.environ.get('LINKEDIN_ACCESS_TOKEN', '')
        
        # LinkedIn API endpoints
        self.base_url = 'https://api.linkedin.com/v2'
        
        # Posts folder
        self.posts_path = self.vault_path / "Posts" / "LinkedIn"
        self.posts_path.mkdir(parents=True, exist_ok=True)
        
        # Scheduled posts
        self.scheduled_path = self.posts_path / "Scheduled"
        self.scheduled_path.mkdir(exist_ok=True)
        
        # Published posts log
        self.published_path = self.posts_path / "Published"
        self.published_path.mkdir(exist_ok=True)
        
        logger.info(f"LinkedInMCPServer initialized")
        
        if not self.linkedin_access_token:
            logger.warning("LinkedIn API not configured - using draft mode")
    
    # ==================== MCP Tool Definitions ====================
    
    def get_tools(self) -> List[dict]:
        """Get list of available MCP tools"""
        return [
            {
                'name': 'create_linkedin_post',
                'description': 'Create a LinkedIn post (draft or publish)',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'content': {
                            'type': 'string',
                            'description': 'Post content (max 3000 characters)'
                        },
                        'schedule_time': {
                            'type': 'string',
                            'description': 'ISO format datetime for scheduled posting'
                        },
                        'publish': {
                            'type': 'boolean',
                            'description': 'Whether to publish immediately or save as draft'
                        }
                    },
                    'required': ['content']
                }
            },
            {
                'name': 'generate_linkedin_content',
                'description': 'Generate LinkedIn post content based on topic',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'topic': {
                            'type': 'string',
                            'description': 'Topic for the post'
                        },
                        'tone': {
                            'type': 'string',
                            'enum': ['professional', 'casual', 'enthusiastic', 'informative'],
                            'description': 'Tone of the post'
                        },
                        'include_hashtags': {
                            'type': 'boolean',
                            'description': 'Whether to include hashtags'
                        }
                    },
                    'required': ['topic']
                }
            },
            {
                'name': 'schedule_linkedin_post',
                'description': 'Schedule a LinkedIn post for later',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'post_file': {
                            'type': 'string',
                            'description': 'Path to draft post file'
                        },
                        'schedule_time': {
                            'type': 'string',
                            'description': 'ISO format datetime for posting'
                        }
                    },
                    'required': ['post_file', 'schedule_time']
                }
            },
            {
                'name': 'list_linkedin_drafts',
                'description': 'List all LinkedIn post drafts',
                'inputSchema': {
                    'type': 'object',
                    'properties': {}
                }
            },
            {
                'name': 'publish_linkedin_post',
                'description': 'Publish a LinkedIn post draft',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'post_file': {
                            'type': 'string',
                            'description': 'Path to draft post file'
                        }
                    },
                    'required': ['post_file']
                }
            },
            {
                'name': 'get_linkedin_post_analytics',
                'description': 'Get analytics for a published post',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'post_id': {
                            'type': 'string',
                            'description': 'LinkedIn post ID'
                        }
                    },
                    'required': ['post_id']
                }
            }
        ]
    
    # ==================== Tool Implementations ====================
    
    def create_linkedin_post(
        self,
        content: str,
        schedule_time: str = None,
        publish: bool = False
    ) -> dict:
        """
        Create a LinkedIn post.
        
        Args:
            content: Post content (max 3000 characters)
            schedule_time: Optional ISO format datetime for scheduling
            publish: Whether to publish immediately
            
        Returns:
            Result dictionary with post details
        """
        logger.info(f"Creating LinkedIn post (publish={publish})")
        
        # Validate content length
        if len(content) > 3000:
            return {
                'success': False,
                'error': 'Content exceeds 3000 character limit',
                'current_length': len(content)
            }
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Determine status and folder
        if publish and self.linkedin_access_token:
            status = 'published'
            folder = self.published_path
        elif schedule_time:
            status = 'scheduled'
            folder = self.scheduled_path
        else:
            status = 'draft'
            folder = self.posts_path
        
        # Generate filename
        filename = f"LinkedIn_{status}_{timestamp}.md"
        filepath = folder / filename
        
        # Create post content
        post_content = f"""---
type: linkedin_post
status: {status}
created: {datetime.now().isoformat()}
scheduled_time: {schedule_time}
character_count: {len(content)}
---

# LinkedIn Post

## Content

{content}

---
*Created by AI Employee - {status.title()}*
"""
        
        filepath.write_text(post_content, encoding='utf-8')
        
        # If publish requested and API available, publish now
        if publish and self.linkedin_access_token:
            publish_result = self._publish_to_linkedin(content)
            
            if publish_result.get('success'):
                # Update status
                post_content = f"""---
type: linkedin_post
status: published
created: {datetime.now().isoformat()}
published_at: {datetime.now().isoformat()}
post_id: {publish_result.get('post_id')}
---

# LinkedIn Post

## Content

{content}

---
*Published to LinkedIn*
"""
                filepath.write_text(post_content, encoding='utf-8')
                
                return {
                    'success': True,
                    'status': 'published',
                    'post_file': str(filepath),
                    'post_id': publish_result.get('post_id'),
                    'message': 'Post published to LinkedIn'
                }
        
        return {
            'success': True,
            'status': status,
            'post_file': str(filepath),
            'message': f'Post {status} created: {filename}'
        }
    
    def generate_linkedin_content(
        self,
        topic: str,
        tone: str = 'professional',
        include_hashtags: bool = True
    ) -> dict:
        """
        Generate LinkedIn post content based on topic.
        
        Args:
            topic: Topic for the post
            tone: Tone of the post
            include_hashtags: Whether to include hashtags
            
        Returns:
            Generated content dictionary
        """
        logger.info(f"Generating LinkedIn content for: {topic}")
        
        # Tone-specific introductions
        introductions = {
            'professional': "I'm excited to share some insights on",
            'casual': "Hey everyone! Been thinking about",
            'enthusiastic': "🚀 Amazing discoveries in",
            'informative': "Key takeaways about"
        }
        
        # Generate content structure
        intro = introductions.get(tone, introductions['professional'])
        
        content = f"""{intro} {topic}.

Here are my key thoughts:

1. **Understanding the Basics**: {topic} is becoming increasingly important in today's landscape.

2. **Key Insights**: Through my experience, I've found that success in this area requires dedication and continuous learning.

3. **Moving Forward**: I encourage everyone to explore this topic further and share your experiences.

What are your thoughts on {topic}? I'd love to hear from you in the comments!
"""
        
        # Add hashtags if requested
        if include_hashtags:
            hashtags = self._generate_hashtags(topic)
            content += f"\n\n{hashtags}"
        
        return {
            'success': True,
            'content': content,
            'topic': topic,
            'tone': tone,
            'character_count': len(content),
            'hashtags_included': include_hashtags
        }
    
    def schedule_linkedin_post(
        self,
        post_file: str,
        schedule_time: str
    ) -> dict:
        """
        Schedule a LinkedIn post for later.
        
        Args:
            post_file: Path to draft post file
            schedule_time: ISO format datetime for posting
            
        Returns:
            Result dictionary
        """
        try:
            path = Path(post_file)
            
            if not path.exists():
                return {
                    'success': False,
                    'error': f'Post file not found: {post_file}'
                }
            
            content = path.read_text(encoding='utf-8')
            
            # Update frontmatter with schedule time
            content = content.replace(
                'status: draft',
                f'status: scheduled\nscheduled_time: {schedule_time}'
            )
            
            # Move to scheduled folder
            new_filename = f"Scheduled_{path.name}"
            new_path = self.scheduled_path / new_filename
            new_path.write_text(content, encoding='utf-8')
            
            # Remove original
            path.unlink()
            
            return {
                'success': True,
                'scheduled_file': str(new_path),
                'schedule_time': schedule_time,
                'message': f'Post scheduled for {schedule_time}'
            }
            
        except Exception as e:
            logger.error(f"Failed to schedule post: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_linkedin_drafts(self) -> dict:
        """
        List all LinkedIn post drafts.
        
        Returns:
            List of draft files
        """
        drafts = list(self.posts_path.glob("*.md"))
        drafts = [d for d in drafts if 'draft' in d.name.lower() or 'status: draft' in d.read_text() if d.exists()]
        
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
    
    def publish_linkedin_post(self, post_file: str) -> dict:
        """
        Publish a LinkedIn post draft.
        
        Args:
            post_file: Path to draft post file
            
        Returns:
            Result dictionary
        """
        try:
            path = Path(post_file)
            
            if not path.exists():
                return {
                    'success': False,
                    'error': f'Post file not found: {post_file}'
                }
            
            content = path.read_text(encoding='utf-8')
            
            # Extract post body (after frontmatter)
            parts = content.split('---', 2)
            if len(parts) < 3:
                return {
                    'success': False,
                    'error': 'Invalid post format'
                }
            
            frontmatter = parts[1]
            body = parts[2].strip()
            
            # Remove markdown headers from body
            body = body.replace('# LinkedIn Post\n\n', '').replace('## Content\n\n', '')
            
            # Check if API is available
            if self.linkedin_access_token:
                # Publish via API
                result = self._publish_to_linkedin(body)
                
                if result.get('success'):
                    # Update file status
                    updated_content = f"""---
type: linkedin_post
status: published
published_at: {datetime.now().isoformat()}
post_id: {result.get('post_id')}
---

# LinkedIn Post

## Content

{body}

---
*Published to LinkedIn*
"""
                    # Move to published folder
                    new_filename = f"Published_{path.name}"
                    new_path = self.published_path / new_filename
                    new_path.write_text(updated_content, encoding='utf-8')
                    path.unlink()
                    
                    return {
                        'success': True,
                        'post_id': result.get('post_id'),
                        'message': 'Post published to LinkedIn'
                    }
            else:
                # No API - create approval request
                return {
                    'success': True,
                    'status': 'draft',
                    'message': 'LinkedIn API not configured. Post saved as draft for manual publishing.',
                    'post_file': str(path),
                    'action_required': 'Please publish manually via LinkedIn.com'
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to publish post: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_linkedin_post_analytics(self, post_id: str) -> dict:
        """
        Get analytics for a published post.
        
        Args:
            post_id: LinkedIn post ID
            
        Returns:
            Analytics dictionary
        """
        if not self.linkedin_access_token:
            return {
                'success': False,
                'error': 'LinkedIn API not configured'
            }
        
        try:
            # In a real implementation, this would call the LinkedIn API
            # For now, return mock data
            return {
                'success': True,
                'post_id': post_id,
                'analytics': {
                    'impressions': 0,
                    'likes': 0,
                    'comments': 0,
                    'shares': 0,
                    'clicks': 0
                },
                'message': 'Analytics would be retrieved from LinkedIn API'
            }
            
        except Exception as e:
            logger.error(f"Failed to get analytics: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # ==================== Internal Methods ====================
    
    def _publish_to_linkedin(self, content: str) -> dict:
        """
        Publish content to LinkedIn via API.
        
        Args:
            content: Post content
            
        Returns:
            Result with post ID
        """
        try:
            import requests
            
            # LinkedIn Person URN (required for posting)
            person_urn = os.environ.get('LINKEDIN_PERSON_URN', '')
            
            if not person_urn:
                # Try to get user info
                user_response = requests.get(
                    f'{self.base_url}/me',
                    headers={'Authorization': f'Bearer {self.linkedin_access_token}'}
                )
                
                if user_response.status_code == 200:
                    person_urn = user_response.json().get('id')
            
            if not person_urn:
                return {
                    'success': False,
                    'error': 'Could not determine LinkedIn user URN'
                }
            
            # Create share post
            post_data = {
                'author': f'urn:li:person:{person_urn}',
                'lifecycleState': 'PUBLISHED',
                'specificContent': {
                    'com.linkedin.ugc.ShareContent': {
                        'shareCommentary': {
                            'text': content
                        },
                        'shareMediaCategory': 'NONE'
                    }
                },
                'visibility': {
                    'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC'
                }
            }
            
            response = requests.post(
                f'{self.base_url}/ugcPosts',
                headers={
                    'Authorization': f'Bearer {self.linkedin_access_token}',
                    'Content-Type': 'application/json',
                    'X-Restli-Protocol-Version': '2.0.0'
                },
                json=post_data
            )
            
            if response.status_code in [200, 201]:
                post_id = response.json().get('id', 'unknown')
                return {
                    'success': True,
                    'post_id': post_id,
                    'message': 'Post published successfully'
                }
            else:
                return {
                    'success': False,
                    'error': f'API error: {response.status_code}',
                    'response': response.text
                }
                
        except ImportError:
            return {
                'success': False,
                'error': 'requests library not available'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_hashtags(self, topic: str) -> str:
        """Generate relevant hashtags for a topic"""
        # Simple hashtag generation
        words = topic.lower().split()
        hashtags = ['#' + word.replace('.', '').replace(',', '') for word in words[:5]]
        
        # Add common professional hashtags
        common = ['#ProfessionalDevelopment', '#CareerGrowth', '#Networking']
        
        return ' '.join(hashtags + common)
    
    # ==================== MCP Protocol Handlers ====================
    
    def handle_request(self, request: dict) -> dict:
        """Handle MCP protocol request"""
        method = request.get('method', '')
        params = request.get('params', {})
        
        if method == 'tools/list':
            return {'result': {'tools': self.get_tools()}}
        
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
            'create_linkedin_post': self.create_linkedin_post,
            'generate_linkedin_content': self.generate_linkedin_content,
            'schedule_linkedin_post': self.schedule_linkedin_post,
            'list_linkedin_drafts': self.list_linkedin_drafts,
            'publish_linkedin_post': self.publish_linkedin_post,
            'get_linkedin_post_analytics': self.get_linkedin_post_analytics
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
            return {'result': result}
        except Exception as e:
            return {
                'error': {
                    'code': -32000,
                    'message': str(e)
                }
            }


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='LinkedIn MCP Server')
    parser.add_argument('--vault', type=str, default='.', help='Path to vault')
    parser.add_argument('--stdio', action='store_true', help='Use stdio transport')
    
    args = parser.parse_args()
    
    server = LinkedInMCPServer(vault_path=Path(args.vault))
    
    if args.stdio:
        logger.info("Running in stdio mode")
        for line in __import__('sys').stdin:
            try:
                request = json.loads(line)
                response = server.handle_request(request)
                print(json.dumps(response), flush=True)
            except:
                continue
    else:
        logger.info("LinkedIn MCP Server running in interactive mode")
        logger.info("Available tools:")
        for tool in server.get_tools():
            logger.info(f"  - {tool['name']}: {tool['description']}")


if __name__ == '__main__':
    main()
