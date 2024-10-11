from agency_swarm.tools import BaseTool
from datetime import datetime


class GetCurrentTime(BaseTool):
    """
    A tool to get the current time.
    """

    def run(self):
        """
        Get the current time.
        """
        return {"current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


if __name__ == "__main__":
    tool = GetCurrentTime()
    print(tool.run())
