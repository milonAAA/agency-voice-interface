import asyncio
import logging
import os

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()

logger = logging.getLogger(__name__)


class GmailUtils:
    """
    Utility class for Gmail authentication and service creation.
    """

    SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.compose",
    ]

    @staticmethod
    async def authenticate_gmail(scopes=None):
        """
        Authenticates the user and returns a Gmail service object.
        """
        if scopes is None:
            scopes = GmailUtils.SCOPES

        def authenticate():
            creds = None
            token_path = "token.json"
            credentials_path = "credentials.json"

            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, scopes)
                logger.info("Loaded credentials from token.json.")

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    logger.info("Refreshing expired credentials.")
                    creds.refresh(Request())
                else:
                    logger.info("Initiating new authentication flow.")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_path, scopes
                    )
                    creds = flow.run_local_server(port=8080)  # Fixed port
                with open(token_path, "w") as token:
                    token.write(creds.to_json())
                    logger.info("Saved new credentials to token.json.")

            return build("gmail", "v1", credentials=creds)

        try:
            service = await asyncio.to_thread(authenticate)
            logger.info("Gmail service authenticated successfully.")
            return service
        except Exception as e:
            logger.error(f"Failed to authenticate Gmail service: {e}")
            raise e
