import asyncio
from datetime import datetime

from agency_swarm.tools import BaseTool


class GetCurrentDateTime(BaseTool):
    """A tool to get the current date and time."""

    async def run(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


if __name__ == "__main__":
    tool = GetCurrentDateTime()
    print(asyncio.run(tool.run()))
