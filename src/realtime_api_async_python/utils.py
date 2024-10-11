# src/realtime_api_async_python/utils.py
import base64
import json
import logging
import os
from datetime import datetime
from pydantic import BaseModel
import openai
from realtime_api_async_python.config import RUN_TIME_TABLE_LOG_JSON


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
