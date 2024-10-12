import asyncio
import base64
import os
import tempfile
from dotenv import load_dotenv

import aiohttp
from agency_swarm.tools import BaseTool
from pydantic import Field

from voice_assistant.decorators import timeit_decorator

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


class GetScreenDescriptionTool(BaseTool):
    """Analyze the user's active window via screenshot using GPT-4o-mini."""

    prompt: str = Field(..., description="Prompt to analyze the screenshot")

    async def run(self) -> str:
        """Execute the screen description tool."""
        screenshot_path = await self.take_screenshot()

        try:
            file_content = await asyncio.to_thread(self._read_file, screenshot_path)
            encoded_image = base64.b64encode(file_content).decode("utf-8")
            analysis = await self.analyze_image(encoded_image)
        finally:
            asyncio.create_task(asyncio.to_thread(os.remove, screenshot_path))

        return analysis

    @timeit_decorator
    async def take_screenshot(self) -> str:
        """Capture a screenshot of the active window."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
            screenshot_path = tmp_file.name

        bounds = await self._get_active_window_bounds()
        if not bounds:
            raise RuntimeError("Unable to retrieve the active window bounds.")

        x, y, width, height = bounds

        process = await asyncio.create_subprocess_exec(
            "screencapture",
            "-R",
            f"{x},{y},{width},{height}",
            screenshot_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"screencapture failed: {stderr.decode().strip()}")

        if not os.path.exists(screenshot_path):
            raise FileNotFoundError(f"Screenshot was not created at {screenshot_path}")

        return screenshot_path

    async def _get_active_window_bounds(self) -> tuple:
        """Retrieve the bounds of the active window."""
        script = """
        tell application "System Events"
            set frontApp to first application process whose frontmost is true
            tell frontApp
                try
                    set win to front window
                    set {x, y} to position of win
                    set {w, h} to size of win
                    return {x, y, w, h}
                on error
                    return {}
                end try
            end tell
        end tell
        """
        process = await asyncio.create_subprocess_exec(
            "osascript",
            "-e",
            script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            return None

        output = stdout.decode().strip()
        if not output:
            return None

        try:
            bounds = eval(output)
            return bounds if isinstance(bounds, tuple) and len(bounds) == 4 else None
        except Exception as e:
            print(f"Error parsing bounds: {e}")
            return None

    @timeit_decorator
    async def analyze_image(self, base64_image: str) -> str:
        """Send the encoded image and prompt to the OpenAI API for analysis."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        }

        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert at analyzing screenshots and describing their content. Your output should be a concise and informative description of the screenshot, focusing on the aspects mentioned in the user's prompt. Pay close attention to the specific questions or elements the user is asking about.",
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Analyze this screenshot, paying particular attention to the following prompt: {self.prompt}",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            },
                        },
                    ],
                },
            ],
            "max_tokens": 300,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                if response.status != 200:
                    error = await response.text()
                    raise RuntimeError(f"OpenAI API error: {error}")
                result = await response.json()
                return result["choices"][0]["message"]["content"]

    def _read_file(self, path: str) -> bytes:
        """Read and return the content of a file."""
        with open(path, "rb") as image_file:
            return image_file.read()


if __name__ == "__main__":
    import asyncio

    async def test_tool():
        tool = GetScreenDescriptionTool(
            prompt="What do you see in this screenshot? Describe the main elements."
        )
        try:
            result = await tool.run()
            print(result)
        except Exception as e:
            print(f"Error during test: {e}")

    asyncio.run(test_tool())
