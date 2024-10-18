import asyncio
import logging
from datetime import UTC, datetime

from agency_swarm.tools import BaseTool
from dotenv import load_dotenv
from pydantic import Field

from voice_assistant.utils.calendar_utils import CalendarUtils

load_dotenv()

logger = logging.getLogger(__name__)


class GetMeetingAgenda(BaseTool):
    """
    A tool to fetch and prioritize the CEO's daily meeting agenda.
    """

    date: str = Field(
        default_factory=lambda: datetime.now(UTC).strftime("%Y-%m-%d"),
        description="The date for which to fetch the meeting agenda. Defaults to today if not provided.",
    )

    async def run(self):
        try:
            meetings = await self.fetch_meetings(self.date)
            formatted_meetings = self.format_meetings(meetings)
            return formatted_meetings
        except Exception as e:
            logger.error(f"Error in GetMeetingAgenda: {str(e)}")
            return f"An error occurred while fetching the meeting agenda: {str(e)}"

    async def fetch_meetings(self, date):
        service = await CalendarUtils.authenticate_calendar()
        events_result = await asyncio.to_thread(
            service.events()
            .list(
                calendarId="primary",
                timeMin=f"{date}T00:00:00Z",
                timeMax=f"{date}T23:59:59Z",
                singleEvents=True,
                orderBy="startTime",
            )
            .execute
        )
        return events_result.get("items", [])

    def format_meetings(self, meetings):
        formatted = []
        for meeting in meetings:
            start_time = datetime.fromisoformat(
                meeting["start"].get("dateTime", meeting["start"].get("date"))
            )
            end_time = datetime.fromisoformat(
                meeting["end"].get("dateTime", meeting["end"].get("date"))
            )

            formatted_meeting = f"{start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}: {meeting.get('summary', 'Untitled Event')}"

            if meeting.get("location"):
                formatted_meeting += f" | Location: {meeting['location']}"

            if meeting.get("description"):
                description = meeting["description"].split("\n")[0]
                formatted_meeting += f" | Description: {description}"

            formatted.append(formatted_meeting)

        if not formatted:
            return "No meetings scheduled for today."

        return "Today's Agenda:\n" + "\n".join(formatted)


if __name__ == "__main__":
    import asyncio

    tool = GetMeetingAgenda()
    result = asyncio.run(tool.run())
    print(result)
