from agency_swarm.tools import BaseTool
from pydantic import Field
import json
import os
import webbrowser
import asyncio
from concurrent.futures import ThreadPoolExecutor
from voice_assistant.decorators import timeit_decorator
from voice_assistant.tools.utils import get_structured_output_completion
from voice_assistant.models import WebUrl
import logging


class OpenBrowser(BaseTool):
    """
    A tool to open a browser with a URL based on the user's prompt.
    """

    prompt: str = Field(
        ..., description="The user's prompt to determine which URL to open."
    )

    @timeit_decorator
    async def run(self):
        """
        Open a browser with the best-fitting URL based on the user's prompt.
        """
        with open(os.getenv("PERSONALIZATION_FILE")) as f:
            personalization = json.load(f)
        browser_urls = personalization["browser_urls"]
        browser = personalization["browser"]

        prompt_structure = f"""
<purpose>
    Select a browser URL from the list of browser URLs based on the user's prompt.
</purpose>

<instructions>
    <instruction>Infer the browser URL that the user wants to open from the user-prompt and the list of browser URLs.</instruction>
    <instruction>If the user-prompt is not related to the browser URLs, return an empty string.</instruction>
</instructions>

<browser-urls>
    {", ".join(browser_urls)}
</browser-urls>

<user-prompt>
    {self.prompt}
</user-prompt>
        """
        response = get_structured_output_completion(prompt_structure, WebUrl)

        if response.url:
            logging.info(f"📖 open_browser() Opening URL: {response.url}")
            loop = asyncio.get_running_loop()
            with ThreadPoolExecutor() as pool:
                await loop.run_in_executor(
                    pool, webbrowser.get(browser).open, response.url
                )
            return {"status": "Browser opened", "url": response.url}
        return {"status": "No URL found"}


if __name__ == "__main__":
    tool = OpenBrowser(prompt="Open my favorite website")
    asyncio.run(tool.run())
