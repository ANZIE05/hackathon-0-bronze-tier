"""
Gmail OAuth2 Authentication for WSL

This module handles Gmail API authentication with proper WSL support.
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Gmail API scopes
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


def authenticate_gmail(credentials_path: str, token_path: str = "token.json"):
    """
    Authenticate with Gmail API using OAuth2.
    
    WSL-compatible: Opens auth URL for manual browser access,
    then captures the callback on localhost.
    
    Args:
        credentials_path: Path to credentials.json from Google Cloud Console
        token_path: Path where token.json will be saved/loaded
        
    Returns:
        Authorized Gmail API service object, or None if authentication fails
    """
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    import pickle
    
    creds = None
    token_file = Path(token_path)
    
    # Load existing token if available
    if token_file.exists():
        try:
            with open(token_file, 'rb') as f:
                creds = pickle.load(f)
            logger.info(f"Loaded existing token from {token_path}")
        except Exception as e:
            logger.warning(f"Failed to load token: {e}")
            creds = None
    
    # Refresh or obtain new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired token...")
            try:
                creds.refresh(Request())
                logger.info("Token refreshed successfully")
            except Exception as e:
                logger.warning(f"Token refresh failed: {e}")
                creds = None
        
        if not creds:
            logger.info("Starting OAuth2 flow (first time setup)...")
            creds = _run_oauth_flow(credentials_path, token_path)
    
    if not creds or not creds.valid:
        logger.error("Authentication failed - no valid credentials")
        return None
    
    # Build and return Gmail API service
    try:
        service = build('gmail', 'v1', credentials=creds)
        logger.info("Gmail API service created successfully")
        return service
    except Exception as e:
        logger.error(f"Failed to build Gmail API service: {e}")
        return None


def _run_oauth_flow(credentials_path: str, token_path: str):
    """
    Run the OAuth2 flow for first-time authentication.
    
    WSL Strategy:
    - Start local server on localhost (not 127.0.0.1)
    - Print the auth URL for user to open in Windows browser
    - Server listens for callback and captures the token
    """
    from google_auth_oauthlib.flow import InstalledAppFlow
    import webbrowser
    import socket
    
    credentials_file = Path(credentials_path)
    if not credentials_file.exists():
        logger.error(f"Credentials file not found: {credentials_path}")
        return None
    
    try:
        # Create the OAuth flow
        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_file),
            scopes=GMAIL_SCOPES
        )
        
        # WSL-compatible: Use run_local_server with localhost binding
        # This works because Windows can resolve 'localhost' to WSL
        logger.info("=" * 60)
        logger.info("GMAIL API AUTHENTICATION")
        logger.info("=" * 60)
        logger.info("Opening browser for authentication...")
        logger.info("If browser doesn't open automatically:")
        logger.info("1. Copy the URL shown below")
        logger.info("2. Paste it into your Windows browser (Chrome/Edge/Firefox)")
        logger.info("3. Complete authentication")
        logger.info("4. You'll be redirected - just wait for the page to load")
        logger.info("=" * 60)
        
        # run_local_server is the modern replacement for run_console()
        # bind_addr="localhost" ensures WSL<->Windows compatibility
        creds = flow.run_local_server(
            host='localhost',
            port=8080,
            bind_addr="localhost",  # Critical for WSL
            open_browser=False,     # We'll handle browser opening manually
        )
        
        # Save the token for future use
        token_file = Path(token_path)
        with open(token_file, 'wb') as f:
            import pickle
            pickle.dump(creds, f)
        logger.info(f"Token saved to {token_path}")
        
        return creds
        
    except Exception as e:
        logger.error(f"OAuth flow failed: {e}")
        return None


def test_gmail_connection(service):
    """Test the Gmail API connection by fetching profile info."""
    if service is None:
        return False
    
    try:
        profile = service.users().getProfile().execute()
        logger.info(f"Connected to Gmail account: {profile.get('emailAddress')}")
        return True
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False
