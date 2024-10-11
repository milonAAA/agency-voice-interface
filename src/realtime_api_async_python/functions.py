# src/realtime_api_async_python/functions.py
import asyncio
import os
import json
import logging
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from realtime_api_async_python.decorators import timeit_decorator
from realtime_api_async_python.models import (
    WebUrl,
    CreateFileResponse,
    FileSelectionResponse,
    FileDeleteResponse,
    ModelName,
)
from realtime_api_async_python.utils import structured_output_prompt, chat_prompt
from realtime_api_async_python.config import SCRATCH_PAD_DIR
from realtime_api_async_python.agency_functions import (
    delegate_task_to_developer,
    assign_task_to_virtual_assistant,
)


@timeit_decorator
async def get_current_time() -> dict:
    from datetime import datetime

    return {"current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


@timeit_decorator
async def get_random_number() -> dict:
    import random

    return {"random_number": random.randint(1, 100)}


@timeit_decorator
async def open_browser(prompt: str) -> dict:
    browser_urls = json.load(open(os.getenv("PERSONALIZATION_FILE")))["browser_urls"]
    browser = json.load(open(os.getenv("PERSONALIZATION_FILE")))["browser"]
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
    {prompt}
</user-prompt>
    """
    response = structured_output_prompt(prompt_structure, WebUrl)
    if response.url:
        logging.info(f"📖 open_browser() Opening URL: {response.url}")
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor() as pool:
            await loop.run_in_executor(pool, webbrowser.get(browser).open, response.url)
        return {"status": "Browser opened", "url": response.url}
    return {"status": "No URL found"}


@timeit_decorator
async def create_file(file_name: str, prompt: str) -> dict:
    import os

    file_path = os.path.join(SCRATCH_PAD_DIR, file_name)
    if os.path.exists(file_path):
        return {"status": "file already exists"}

    prompt_structure = f"""
<purpose>
    Generate content for a new file based on the user's prompt and the file name.
</purpose>

<instructions>
    <instruction>Based on the user's prompt and the file name, generate content for a new file.</instruction>
    <instruction>The file name is the name of the file that the user wants to create.</instruction>
    <instruction>The user's prompt is the prompt that the user wants to use to generate the content for the new file.</instruction>
</instructions>

<user-prompt>
    {prompt}
</user-prompt>

<file-name>
    {file_name}
</file-name>
    """
    response = structured_output_prompt(prompt_structure, CreateFileResponse)
    with open(file_path, "w") as f:
        f.write(response.file_content)
    return {"status": "file created", "file_name": response.file_name}


@timeit_decorator
async def delete_file(prompt: str, force_delete: bool = False) -> dict:
    import os

    available_files = os.listdir(SCRATCH_PAD_DIR)
    select_file_prompt = f"""
<purpose>
    Select a file from the available files to delete.
</purpose>

<instructions>
    <instruction>Based on the user's prompt and the list of available files, infer which file the user wants to delete.</instruction>
    <instruction>If no file matches, return an empty string for 'file'.</instruction>
</instructions>

<available-files>
    {", ".join(available_files)}
</available-files>

<user-prompt>
    {prompt}
</user-prompt>
    """
    file_delete_response = structured_output_prompt(
        select_file_prompt, FileDeleteResponse
    )

    if not file_delete_response.file:
        return {"status": "No matching file found"}

    file_path = os.path.join(SCRATCH_PAD_DIR, file_delete_response.file)
    if not os.path.exists(file_path):
        return {"status": "File does not exist", "file_name": file_delete_response.file}

    if not force_delete:
        return {
            "status": "Confirmation required",
            "file_name": file_delete_response.file,
            "message": f"Are you sure you want to delete '{file_delete_response.file}'? Say force delete if you want to delete.",
        }

    os.remove(file_path)
    return {"status": "File deleted", "file_name": file_delete_response.file}


@timeit_decorator
async def update_file(prompt: str) -> dict:
    import os

    available_files = os.listdir(SCRATCH_PAD_DIR)
    available_model_map = json.dumps(
        {model.value: ModelName[model] for model in ModelName}
    )

    select_file_prompt = f"""
<purpose>
    Select a file from the available files and choose the appropriate model based on the user's prompt.
</purpose>

<instructions>
    <instruction>Based on the user's prompt and the list of available files, infer which file the user wants to update.</instruction>
    <instruction>Also, select the most appropriate model from the available models mapping.</instruction>
    <instruction>If the user does not specify a model, default to 'base_model'.</instruction>
    <instruction>If no file matches, return an empty string for 'file'.</instruction>
</instructions>

<available-files>
    {", ".join(available_files)}
</available-files>

<available-model-map>
    {available_model_map}
</available-model-map>

<user-prompt>
    {prompt}
</user-prompt>
    """
    file_selection_response = structured_output_prompt(
        select_file_prompt, FileSelectionResponse
    )

    if not file_selection_response.file:
        return {"status": "No matching file found"}

    selected_file = file_selection_response.file
    selected_model = file_selection_response.model or ModelName.BASE_MODEL
    file_path = os.path.join(SCRATCH_PAD_DIR, selected_file)

    with open(file_path, "r") as f:
        file_content = f.read()

    update_file_prompt = f"""
<purpose>
    Update the content of the file based on the user's prompt.
</purpose>

<instructions>
    <instruction>Based on the user's prompt and the file content, generate the updated content for the file.</instruction>
    <instruction>The file-name is the name of the file to update.</instruction>
    <instruction>The user's prompt describes the updates to make.</instruction>
    <instruction>Respond exclusively with the updates to the file and nothing else; they will be used to overwrite the file entirely using f.write().</instruction>
    <instruction>Do not include any preamble or commentary or markdown formatting, just the raw updates.</instruction>
    <instruction>Be precise and accurate.</instruction>
</instructions>

<file-name>
    {selected_file}
</file-name>

<file-content>
    {file_content}
</file-content>

<user-prompt>
    {prompt}
</user-prompt>
    """
    file_update_response = chat_prompt(update_file_prompt, selected_model.value)

    with open(file_path, "w") as f:
        f.write(file_update_response)

    return {
        "status": "File updated",
        "file_name": selected_file,
        "model_used": selected_model,
    }


FUNCTION_MAP = {
    "get_current_time": get_current_time,
    "get_random_number": get_random_number,
    "open_browser": open_browser,
    "create_file": create_file,
    "update_file": update_file,
    "delete_file": delete_file,
    "delegate_task_to_developer": delegate_task_to_developer,
    "assign_task_to_virtual_assistant": assign_task_to_virtual_assistant,
}
