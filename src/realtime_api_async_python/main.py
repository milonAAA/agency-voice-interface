import asyncio
import functools
import json
import logging
import os
import sys
import time
import webbrowser
import base64
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from enum import Enum
from typing import Optional

import openai
import pyaudio
import queue
import websockets
from dotenv import load_dotenv
from pydantic import BaseModel
from websockets.exceptions import ConnectionClosedError

# Constants
PREFIX_PADDING_MS = 300
SILENCE_THRESHOLD = 0.5
SILENCE_DURATION_MS = 400
RUN_TIME_TABLE_LOG_JSON = "runtime_time_table.jsonl"
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 24000

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)

# Load personalization settings
PERSONALIZATION_FILE = os.getenv("PERSONALIZATION_FILE", "./personalization.json")
with open(PERSONALIZATION_FILE, "r") as f:
    personalization = json.load(f)

AI_ASSISTANT_NAME = personalization.get("ai_assistant_name", "Assistant")
HUMAN_NAME = personalization.get("human_name", "User")

SESSION_INSTRUCTIONS = f"You are {AI_ASSISTANT_NAME}, a helpful assistant. Respond concisely to {HUMAN_NAME}."

# Check for required environment variables
REQUIRED_ENV_VARS = ["OPENAI_API_KEY", "PERSONALIZATION_FILE", "SCRATCH_PAD_DIR"]
MISSING_VARS = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
if MISSING_VARS:
    logging.error(f"Missing required environment variables: {', '.join(MISSING_VARS)}")
    logging.error("Please set these variables in your .env file.")
    sys.exit(1)

SCRATCH_PAD_DIR = os.getenv("SCRATCH_PAD_DIR", "./scratchpad")
os.makedirs(SCRATCH_PAD_DIR, exist_ok=True)


class ModelName(str, Enum):
    STATE_OF_THE_ART_MODEL = "state_of_the_art_model"
    REASONING_MODEL = "reasoning_model"
    BASE_MODEL = "base_model"
    FAST_MODEL = "fast_model"


MODEL_NAME_TO_ID = {
    ModelName.STATE_OF_THE_ART_MODEL: "o1-preview",
    ModelName.REASONING_MODEL: "o1-mini",
    ModelName.BASE_MODEL: "gpt-4o-2024-08-06",
    ModelName.FAST_MODEL: "gpt-4o-mini",
}


def timeit_decorator(func):
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = await func(*args, **kwargs)
        duration = round(time.perf_counter() - start_time, 4)
        log_runtime(func.__name__, duration)
        return result

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        duration = round(time.perf_counter() - start_time, 4)
        log_runtime(func.__name__, duration)
        return result

    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


@timeit_decorator
async def get_current_time() -> dict:
    return {"current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


@timeit_decorator
async def get_random_number() -> dict:
    return {"random_number": random.randint(1, 100)}


class WebUrl(BaseModel):
    url: str


class CreateFileResponse(BaseModel):
    file_content: str
    file_name: str


class FileSelectionResponse(BaseModel):
    file: str
    model: ModelName = ModelName.BASE_MODEL


class FileUpdateResponse(BaseModel):
    updates: str


class FileDeleteResponse(BaseModel):
    file: str
    force_delete: bool


@timeit_decorator
async def open_browser(prompt: str) -> dict:
    browser_urls = personalization.get("browser_urls", [])
    browser = personalization.get("browser", "chrome")
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
async def update_file(prompt: str, model: ModelName = ModelName.BASE_MODEL) -> dict:
    available_files = os.listdir(SCRATCH_PAD_DIR)
    available_model_map = json.dumps(
        {model.value: MODEL_NAME_TO_ID[model] for model in ModelName}
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
    selected_model = MODEL_NAME_TO_ID.get(
        file_selection_response.model, MODEL_NAME_TO_ID[ModelName.BASE_MODEL]
    )
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
    file_update_response = chat_prompt(update_file_prompt, selected_model)

    with open(file_path, "w") as f:
        f.write(file_update_response)

    return {
        "status": "File updated",
        "file_name": selected_file,
        "model_used": file_selection_response.model,
    }


FUNCTION_MAP = {
    "get_current_time": get_current_time,
    "get_random_number": get_random_number,
    "open_browser": open_browser,
    "create_file": create_file,
    "update_file": update_file,
    "delete_file": delete_file,
}


def log_ws_event(direction: str, event: dict):
    event_type = event.get("type", "Unknown")
    event_emojis = {
        "session.update": "🛠️",
        "session.created": "🔌",
        "session.updated": "🔄",
        "input_audio_buffer.append": "🎤",
        "input_audio_buffer.commit": "✅",
        "input_audio_buffer.speech_started": "🗣️",
        "input_audio_buffer.speech_stopped": "🤫",
        "input_audio_buffer.cleared": "🧹",
        "input_audio_buffer.committed": "📨",
        "conversation.item.create": "📥",
        "conversation.item.delete": "🗑️",
        "conversation.item.truncate": "✂️",
        "conversation.item.created": "📤",
        "conversation.item.deleted": "🗑️",
        "conversation.item.truncated": "✂️",
        "response.create": "➡️",
        "response.created": "📝",
        "response.output_item.added": "➕",
        "response.output_item.done": "✅",
        "response.text.delta": "✍️",
        "response.text.done": "📝",
        "response.audio.delta": "🔊",
        "response.audio.done": "🔇",
        "response.done": "✔️",
        "response.cancel": "⛔",
        "response.function_call_arguments.delta": "📥",
        "response.function_call_arguments.done": "📥",
        "rate_limits.updated": "⏳",
        "error": "❌",
        "conversation.item.input_audio_transcription.completed": "📝",
        "conversation.item.input_audio_transcription.failed": "⚠️",
    }
    emoji = event_emojis.get(event_type, "❓")
    icon = "⬆️ - Out" if direction.lower() == "outgoing" else "⬇️ - In"
    logging.info(f"{emoji} {icon} {event_type}")


def structured_output_prompt(prompt: str, response_format: BaseModel) -> BaseModel:
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[{"role": "user", "content": prompt}],
        response_format=response_format,
    )
    message = completion.choices[0].message
    if not message.parsed:
        raise ValueError(message.refusal)
    return message.parsed


def chat_prompt(prompt: str, model: str) -> str:
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return completion.choices[0].message.content


class AsyncMicrophone:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            stream_callback=self.callback,
        )
        self.queue = queue.Queue()
        self.is_recording = False
        self.is_receiving = False
        logging.info("AsyncMicrophone initialized")

    def callback(self, in_data, frame_count, time_info, status):
        if self.is_recording and not self.is_receiving:
            self.queue.put(in_data)
        return (None, pyaudio.paContinue)

    def start_recording(self):
        self.is_recording = True
        logging.info("Started recording")

    def stop_recording(self):
        self.is_recording = False
        logging.info("Stopped recording")

    def start_receiving(self):
        self.is_receiving = True
        self.is_recording = False
        logging.info("Started receiving assistant response")

    def stop_receiving(self):
        self.is_receiving = False
        logging.info("Stopped receiving assistant response")

    def get_audio_data(self) -> Optional[bytes]:
        data = b""
        while not self.queue.empty():
            data += self.queue.get()
        return data if data else None

    def close(self):
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()
        logging.info("AsyncMicrophone closed")


def base64_encode_audio(audio_bytes: bytes) -> str:
    return base64.b64encode(audio_bytes).decode("utf-8")


def log_runtime(function_or_name: str, duration: float):
    time_record = {
        "timestamp": datetime.now().isoformat(),
        "function": function_or_name,
        "duration": f"{duration:.4f}",
    }
    with open(RUN_TIME_TABLE_LOG_JSON, "a") as file:
        json.dump(time_record, file)
        file.write("\n")

    logging.info(f"⏰ {function_or_name}() took {duration:.4f} seconds")


async def realtime_api():
    while True:
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logging.error("Please set the OPENAI_API_KEY in your .env file.")
                return

            exit_event = asyncio.Event()

            url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "OpenAI-Beta": "realtime=v1",
            }

            mic = AsyncMicrophone()

            async with websockets.connect(url, extra_headers=headers) as websocket:
                logging.info("Connected to the server.")

                # Initialize the session with voice capabilities and tool
                session_update = {
                    "type": "session.update",
                    "session": {
                        "modalities": ["text", "audio"],
                        "instructions": SESSION_INSTRUCTIONS,
                        "voice": "alloy",
                        "input_audio_format": "pcm16",
                        "output_audio_format": "pcm16",
                        "turn_detection": {
                            "type": "server_vad",
                            "threshold": SILENCE_THRESHOLD,
                            "prefix_padding_ms": PREFIX_PADDING_MS,
                            "silence_duration_ms": SILENCE_DURATION_MS,
                        },
                        "tools": [
                            {
                                "type": "function",
                                "name": "get_current_time",
                                "description": "Returns the current time.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {},
                                    "required": [],
                                },
                            },
                            {
                                "type": "function",
                                "name": "get_random_number",
                                "description": "Returns a random number between 1 and 100.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {},
                                    "required": [],
                                },
                            },
                            {
                                "type": "function",
                                "name": "open_browser",
                                "description": "Opens a browser tab with the best-fitting URL based on the user's prompt.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "prompt": {
                                            "type": "string",
                                            "description": "The user's prompt to determine which URL to open.",
                                        },
                                    },
                                    "required": ["prompt"],
                                },
                            },
                            {
                                "type": "function",
                                "name": "create_file",
                                "description": "Generates content for a new file based on the user's prompt and file name.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "file_name": {
                                            "type": "string",
                                            "description": "The name of the file to create.",
                                        },
                                        "prompt": {
                                            "type": "string",
                                            "description": "The user's prompt to generate the file content.",
                                        },
                                    },
                                    "required": ["file_name", "prompt"],
                                },
                            },
                            {
                                "type": "function",
                                "name": "update_file",
                                "description": "Updates a file based on the user's prompt.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "prompt": {
                                            "type": "string",
                                            "description": "The user's prompt describing the updates to the file.",
                                        },
                                        "model": {
                                            "type": "string",
                                            "enum": [
                                                "state_of_the_art_model",
                                                "reasoning_model",
                                                "base_model",
                                                "fast_model",
                                            ],
                                            "description": "The model to use for generating the updates. Default to 'base_model' if not specified.",
                                        },
                                    },
                                    "required": ["prompt"],  # 'model' is optional
                                },
                            },
                            {
                                "type": "function",
                                "name": "delete_file",
                                "description": "Deletes a file based on the user's prompt.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "prompt": {
                                            "type": "string",
                                            "description": "The user's prompt describing the file to delete.",
                                        },
                                        "force_delete": {
                                            "type": "boolean",
                                            "description": "Whether to force delete the file without confirmation. Default to 'false' if not specified.",
                                        },
                                    },
                                    "required": ["prompt"],
                                },
                            },
                        ],
                    },
                }
                log_ws_event("outgoing", session_update)
                await websocket.send(json.dumps(session_update))

                async def process_ws_messages():
                    assistant_reply = ""
                    audio_chunks = []
                    function_call = None
                    function_call_args = ""
                    response_start_time = None

                    while True:
                        try:
                            message = await websocket.recv()
                            event = json.loads(message)
                            log_ws_event("incoming", event)

                            event_type = event.get("type")

                            if event_type == "response.created":
                                mic.start_receiving()
                            elif event_type == "response.output_item.added":
                                item = event.get("item", {})
                                if item.get("type") == "function_call":
                                    function_call = item
                                    function_call_args = ""
                            elif event_type == "response.function_call_arguments.delta":
                                function_call_args += event.get("delta", "")
                            elif event_type == "response.function_call_arguments.done":
                                if function_call:
                                    function_name = function_call.get("name")
                                    call_id = function_call.get("call_id")
                                    try:
                                        args = (
                                            json.loads(function_call_args)
                                            if function_call_args
                                            else {}
                                        )
                                    except json.JSONDecodeError:
                                        args = {}
                                    if function_name in FUNCTION_MAP:
                                        logging.info(
                                            f"🛠️ Calling function: {function_name} with args: {args}"
                                        )
                                        result = await FUNCTION_MAP[function_name](
                                            **args
                                        )
                                        logging.info(
                                            f"🛠️ Function call result: {result}"
                                        )
                                    else:
                                        result = {
                                            "error": f"Function '{function_name}' not found."
                                        }
                                    function_call_output = {
                                        "type": "conversation.item.create",
                                        "item": {
                                            "type": "function_call_output",
                                            "call_id": call_id,
                                            "output": json.dumps(result),
                                        },
                                    }
                                    log_ws_event("outgoing", function_call_output)
                                    await websocket.send(
                                        json.dumps(function_call_output)
                                    )
                                    await websocket.send(
                                        json.dumps({"type": "response.create"})
                                    )
                                    function_call = None
                                    function_call_args = ""
                            elif event_type == "response.text.delta":
                                assistant_reply += event.get("delta", "")
                                print(
                                    f"Assistant: {event.get('delta', '')}",
                                    end="",
                                    flush=True,
                                )
                            elif event_type == "response.audio.delta":
                                audio_chunks.append(base64.b64decode(event["delta"]))
                            elif event_type == "response.done":
                                if response_start_time is not None:
                                    response_duration = (
                                        time.perf_counter() - response_start_time
                                    )
                                    log_runtime(
                                        "realtime_api_response", response_duration
                                    )
                                    response_start_time = None

                                logging.info("Assistant response complete.")
                                if audio_chunks:
                                    audio_data = b"".join(audio_chunks)
                                    logging.info(
                                        f"Sending {len(audio_data)} bytes of audio data to play_audio()"
                                    )
                                    await play_audio(audio_data)
                                    logging.info("Finished play_audio()")
                                assistant_reply = ""
                                audio_chunks = []
                                logging.info("Calling stop_receiving()")
                                mic.stop_receiving()
                            elif event_type == "rate_limits.updated":
                                mic.is_recording = True
                                logging.info(
                                    "Resumed recording after rate_limits.updated"
                                )
                            elif event_type == "error":
                                error_message = event.get("error", {}).get(
                                    "message", ""
                                )
                                logging.error(f"Error: {error_message}")
                                if "buffer is empty" in error_message:
                                    logging.info(
                                        "Received 'buffer is empty' error, no audio data sent."
                                    )
                                    continue
                                elif (
                                    "Conversation already has an active response"
                                    in error_message
                                ):
                                    logging.info(
                                        "Received 'active response' error, adjusting response flow."
                                    )
                                    continue
                                else:
                                    logging.error(f"Unhandled error: {error_message}")
                                    break
                            elif event_type == "input_audio_buffer.speech_started":
                                logging.info("Speech detected, listening...")
                            elif event_type == "input_audio_buffer.speech_stopped":
                                mic.stop_recording()
                                logging.info("Speech ended, processing...")

                                # start the response timer, on send
                                response_start_time = time.perf_counter()
                                await websocket.send(
                                    json.dumps({"type": "input_audio_buffer.commit"})
                                )

                        except websockets.ConnectionClosed:
                            logging.warning("WebSocket connection closed")
                            break

                ws_task = asyncio.create_task(process_ws_messages())

                logging.info(
                    "Conversation started. Speak freely, and the assistant will respond."
                )
                mic.start_recording()
                logging.info("Recording started. Listening for speech...")

                try:
                    while not exit_event.is_set():
                        await asyncio.sleep(
                            0.1
                        )  # Small delay to accumulate some audio data
                        if not mic.is_receiving:
                            audio_data = mic.get_audio_data()
                            if audio_data:
                                base64_audio = base64_encode_audio(audio_data)
                                if base64_audio:
                                    audio_event = {
                                        "type": "input_audio_buffer.append",
                                        "audio": base64_audio,
                                    }
                                    log_ws_event("outgoing", audio_event)
                                    await websocket.send(json.dumps(audio_event))
                                else:
                                    logging.debug("No audio data to send")
                except KeyboardInterrupt:
                    logging.info("Keyboard interrupt received. Closing the connection.")
                finally:
                    exit_event.set()
                    mic.stop_recording()
                    mic.close()
                    await websocket.close()

                # Wait for the WebSocket processing task to complete
                await ws_task

            # If execution reaches here without exceptions, exit the loop
            break
        except ConnectionClosedError as e:
            if "keepalive ping timeout" in str(e):
                logging.warning(
                    "WebSocket connection lost due to keepalive ping timeout. Reconnecting..."
                )
                await asyncio.sleep(1)  # Wait before reconnecting
                continue  # Retry the connection
            logging.exception("WebSocket connection closed unexpectedly.")
            break  # Exit the loop on other connection errors
        except Exception as e:
            logging.exception(f"An unexpected error occurred: {e}")
            break  # Exit the loop on unexpected exceptions
        finally:
            if "mic" in locals():
                mic.stop_recording()
                mic.close()
            if "websocket" in locals():
                await websocket.close()


async def play_audio(audio_data: bytes):
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True)
    stream.write(audio_data)

    # Add a small delay (e.g., 200ms) of silence at the end to prevent popping and abrupt cuts
    silence_duration = 0.2  # 200ms
    silence_frames = int(RATE * silence_duration)
    silence = b"\x00" * (
        silence_frames * CHANNELS * 2
    )  # 2 bytes per sample for 16-bit audio
    stream.write(silence)

    # Add a small pause before closing the stream to ensure audio is fully played
    await asyncio.sleep(0.5)

    stream.stop_stream()
    stream.close()
    p.terminate()
    logging.debug("Audio playback completed")


def main():
    try:
        asyncio.run(realtime_api())
    except KeyboardInterrupt:
        logging.info("Program terminated by user")
    except Exception as e:
        logging.exception(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    print("Press Ctrl+C to exit the program.")
    main()
