from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from dotenv import load_dotenv
from voice_assistant.decorators import timeit_decorator
from voice_assistant.models import CreateFileResponse
from voice_assistant.tools.utils import get_structured_output_completion
from voice_assistant.config import SCRATCH_PAD_DIR

load_dotenv()


class CreateFileTool(BaseTool):
    """
    A tool for creating a new file with generated content based on a prompt.
    """

    file_name: str = Field(..., description="The name of the file to be created.")
    prompt: str = Field(
        ..., description="The prompt to generate content for the new file."
    )

    async def run(self):
        result = await create_file(self.file_name, self.prompt)
        return str(result)


@timeit_decorator
async def create_file(file_name: str, prompt: str) -> dict:
    file_path = os.path.join(SCRATCH_PAD_DIR, file_name)

    if os.path.exists(file_path):
        return {"status": "File already exists"}

    prompt_structure = f"""
    <purpose>
        Generate content for a new file based on the user's prompt and the file name.
    </purpose>

    <instructions>
        <instruction>Based on the user's prompt and the file name, generate content for a new file.</instruction>
        <instruction>The file name is: {file_name}</instruction>
        <instruction>Use the following prompt to generate the content: {prompt}</instruction>
    </instructions>
    """

    response = get_structured_output_completion(prompt_structure, CreateFileResponse)

    with open(file_path, "w") as f:
        f.write(response.file_content)

    return {"status": "File created", "file_name": response.file_name}


if __name__ == "__main__":
    import asyncio

    tool = CreateFileTool(
        file_name="test.txt", prompt="Write a short story about a robot."
    )

    print(asyncio.run(tool.run()))
