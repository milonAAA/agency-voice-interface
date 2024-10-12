import os
from pydantic import BaseModel
import openai

from voice_assistant.models import ModelName


def get_structured_output_completion(
    prompt: str, response_format: BaseModel
) -> BaseModel:
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    completion = client.beta.chat.completions.parse(
        model=ModelName.STATE_OF_THE_ART_MODEL.value,
        messages=[{"role": "user", "content": prompt}],
        response_format=response_format,
    )
    message = completion.choices[0].message
    if not message.parsed:
        raise ValueError(message.refusal)
    return message.parsed


def get_chat_completion(prompt: str, model: ModelName) -> str:
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    completion = client.beta.chat.completions.parse(
        model=model.value,
        messages=[{"role": "user", "content": prompt}],
    )
    return completion.choices[0].message.content
