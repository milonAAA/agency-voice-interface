import asyncio
import base64
import logging
import re
from datetime import datetime, timedelta
from typing import Optional

from agency_swarm.tools import BaseTool
from dotenv import load_dotenv
from pydantic import Field, PrivateAttr

from voice_assistant.models import ModelName
from voice_assistant.utils.gmail_utils import GmailUtils
from voice_assistant.utils.llm_utils import get_model_completion

logger = logging.getLogger(__name__)

load_dotenv()


class GetGmailSummary(BaseTool):
    """
    A tool to summarize unread Gmail messages from the last two days.
    """

    max_results: int = Field(
        default=10, description="Maximum number of emails to fetch."
    )
    _service: Optional[GmailUtils] = PrivateAttr(None)

    async def run(self):
        logger.info("Starting Gmail authentication.")
        self._service = await GmailUtils.authenticate_gmail(
            scopes=["https://www.googleapis.com/auth/gmail.readonly"]
        )
        logger.info("Fetching unread messages.")
        messages = await self.fetch_unread_messages()
        logger.info("Summarizing messages using GPT-4o-mini.")
        summary = await self.summarize_messages_with_gpt(messages)
        logger.info("Gmail summary completed.")
        return summary

    async def fetch_unread_messages(self):
        two_days_ago = (datetime.now() - timedelta(days=2)).strftime("%Y/%m/%d")
        query = f"is:unread after:{two_days_ago}"
        logger.info(f"Executing query: {query}")

        results = await asyncio.to_thread(
            lambda: self._service.users()
            .messages()
            .list(userId="me", q=query, maxResults=self.max_results)
            .execute()
        )

        messages = results.get("messages", [])
        full_messages = []
        logger.info(f"Number of messages fetched: {len(messages)}")
        for message in messages:
            msg = await asyncio.to_thread(
                lambda: self._service.users()
                .messages()
                .get(userId="me", id=message["id"], format="full")
                .execute()
            )
            msg["id"] = message["id"]  # Store the email ID
            full_messages.append(msg)
        logger.info("All messages fetched successfully.")
        return full_messages

    async def summarize_messages_with_gpt(self, messages):
        full_texts = []
        for msg in messages:
            payload = msg["payload"]
            headers = payload.get("headers", [])
            subject = next(
                (header["value"] for header in headers if header["name"] == "Subject"),
                "No Subject",
            )
            from_email = next(
                (header["value"] for header in headers if header["name"] == "From"),
                "Unknown Sender",
            )
            date = next(
                (header["value"] for header in headers if header["name"] == "Date"),
                "Unknown Date",
            )
            email_id = msg.get("id", "Unknown ID")
            body = self.extract_body(payload)
            full_texts.append(
                f"Email ID: {email_id}\nFrom: {from_email}\nDate: {date}\nSubject: {subject}\nBody: {body}\n"
            )

        summary = await get_model_completion(
            "Please provide a summary of the following emails. For each email, include the email ID, subject, sender, date, and a brief summary of the content without too many details.\n\n"
            + "\n\n".join(full_texts),
            ModelName.FAST_MODEL,
        )
        return summary

    def extract_body(self, payload):
        """
        Extracts the body from an email payload, handling various MIME types and nested parts.
        Removes any links from the body before returning.
        """

        def recursive_extract(parts):
            for part in parts:
                mime_type = part.get("mimeType", "")
                body = part.get("body", {})
                data = body.get("data", "")
                if mime_type == "text/plain" and data:
                    try:
                        decoded_body = base64.urlsafe_b64decode(data).decode("utf-8")
                        return self.remove_links(decoded_body)
                    except Exception as e:
                        logger.error(f"Error decoding text/plain part: {e}")
                elif mime_type == "text/html" and data:
                    try:
                        decoded_body = base64.urlsafe_b64decode(data).decode("utf-8")
                        return self.remove_links(decoded_body)
                    except Exception as e:
                        logger.error(f"Error decoding text/html part: {e}")
                elif "parts" in part:
                    result = recursive_extract(part["parts"])
                    if result:
                        return result
            return ""

        # Start extraction
        if "parts" in payload:
            body = recursive_extract(payload["parts"])
            if body:
                return body
        # Fallback to the main body if no parts are found
        data = payload.get("body", {}).get("data", "")
        if data:
            try:
                decoded_body = base64.urlsafe_b64decode(data).decode("utf-8")
                return self.remove_links(decoded_body)
            except Exception as e:
                logger.error(f"Error decoding main body: {e}")
        return "No body content"

    def remove_links(self, text):
        """
        Removes URLs from the given text.
        """
        # Regex pattern to identify URLs
        url_pattern = re.compile(r"http\S+|www\.\S+")
        # Substitute URLs with an empty string
        cleaned_text = url_pattern.sub("", text)
        logger.debug("Removed links from the email body.")
        return cleaned_text


if __name__ == "__main__":
    import asyncio
    import logging

    async def main():
        tool = GetGmailSummary(max_results=5)
        result = await tool.run()
        print(result)

    asyncio.run(main())
