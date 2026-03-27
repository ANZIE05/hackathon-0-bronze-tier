"""
Email Agent for AI Employee System.

Handles email summarization and reply generation using local LLM.
"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class EmailResponse:
    """Container for email analysis results."""
    summary: str
    draft_reply: str


class EmailAgent:
    """
    AI Agent that processes emails and generates replies.
    
    Uses local LLM for privacy and offline operation.
    """
    
    def __init__(self, model_name: str = "llama3.2"):
        """
        Initialize the email agent.
        
        Args:
            model_name: Name of the Ollama model to use
        """
        self.model_name = model_name
        self._client = None
    
    @property
    def client(self):
        """Lazy-load Ollama client."""
        if self._client is None:
            try:
                from ollama import Client
                self._client = Client()
                logger.info(f"Connected to Ollama with model: {self.model_name}")
            except ImportError:
                logger.error("Ollama package not installed. Run: pip install ollama")
                raise
            except Exception as e:
                logger.error(f"Failed to connect to Ollama: {e}")
                raise
        return self._client
    
    def generate_reply(self, email_text: str) -> EmailResponse:
        """
        Process an email and generate summary + reply draft.
        
        Args:
            email_text: Raw email content as markdown string
            
        Returns:
            EmailResponse with summary and draft_reply
        """
        logger.info(f"Processing email ({len(email_text)} chars)")
        
        prompt = self._build_prompt(email_text)
        
        try:
            response = self.client.generate(
                model=self.model_name,
                prompt=prompt,
                stream=False
            )
            
            result = response.get("response", "")
            summary, draft_reply = self._parse_response(result)
            
            logger.info("Successfully generated email response")
            return EmailResponse(summary=summary, draft_reply=draft_reply)
            
        except Exception as e:
            logger.error(f"Failed to generate reply: {e}")
            raise
    
    def _build_prompt(self, email_text: str) -> str:
        """Build the prompt for the LLM."""
        return f"""You are a professional AI assistant helping to process business emails.

Analyze the following email and provide:
1. A concise summary (2-3 sentences)
2. A professional reply draft

EMAIL CONTENT:
{email_text}

Respond in this exact format:
=== SUMMARY ===
[Your 2-3 sentence summary here]

=== REPLY DRAFT ===
[Your professional reply draft here]

Keep the tone professional, helpful, and concise."""
    
    def _parse_response(self, llm_response: str) -> tuple[str, str]:
        """Parse LLM response into summary and draft."""
        summary = ""
        draft_reply = ""
        
        if "=== SUMMARY ===" in llm_response and "=== REPLY DRAFT ===" in llm_response:
            parts = llm_response.split("=== REPLY DRAFT ===")
            summary_part = parts[0].replace("=== SUMMARY ===", "").strip()
            draft_reply = parts[1].strip() if len(parts) > 1 else ""
            summary = summary_part
        else:
            # Fallback: use entire response as draft
            logger.warning("Could not parse LLM response format, using fallback")
            summary = llm_response[:200] + "..." if len(llm_response) > 200 else llm_response
            draft_reply = llm_response
        
        return summary.strip(), draft_reply.strip()
