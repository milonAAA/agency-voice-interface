import asyncio
import base64
import os
import tempfile
from dotenv import load_dotenv

import aiohttp
from agency_swarm.tools import BaseTool
from pydantic import Field

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


class ScreenshotAnalysisTool(BaseTool):
    """
    Analyze what's currently on the user's screen by examining a screenshot of the active window.
    """

    prompt: str = Field(..., description="Prompt to analyze the screenshot")

    async def run(self):
        # Take screenshot of active window
        screenshot_path = await self.take_screenshot()

        try:
            # Encode screenshot to base64
            file_content = await asyncio.to_thread(self.read_file, screenshot_path)
            encoded_image = base64.b64encode(file_content).decode("utf-8")

            # Analyze screenshot with GPT-4 Vision
            analysis = await self.analyze_image(encoded_image)
        finally:
            # Clean up the temporary screenshot file
            asyncio.create_task(asyncio.to_thread(os.remove, screenshot_path))

        return analysis

    def read_file(self, path):
        with open(path, "rb") as image_file:
            return image_file.read()

    async def take_screenshot(self):
        # Create a temporary file for the screenshot
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
            screenshot_path = tmp_file.name

        # Get the active window bounds
        bounds = await self.get_active_window_bounds()
        if not bounds:
            raise RuntimeError("Unable to retrieve the active window bounds.")

        x, y, width, height = bounds

        # Capture the screenshot of the active window using bounds
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

    async def get_active_window_bounds(self):
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
            # Parse the output {x, y, w, h}
            bounds = eval(output)
            if isinstance(bounds, tuple) and len(bounds) == 4:
                return bounds
            else:
                return None
        except Exception as e:
            print(f"Error parsing bounds: {e}")
            return None

    async def analyze_image(self, base64_image):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        }

        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            },
                        },
                    ],
                }
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

    async def read_file_async(self, path):
        return await asyncio.to_thread(self.read_file, path)


if __name__ == "__main__":
    import asyncio

    async def test_tool():
        tool = ScreenshotAnalysisTool(
            prompt="What do you see in this screenshot? Describe the main elements."
        )
        try:
            result = await tool.run()
            print(result)
        except Exception as e:
            print(f"Error during test: {e}")

    asyncio.run(test_tool())
