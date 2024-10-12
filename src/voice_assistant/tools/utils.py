import os
from pydantic import BaseModel
import openai


def get_structured_output_completion(
    prompt: str, response_format: BaseModel
) -> BaseModel:
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    completion = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format=response_format,
    )
    message = completion.choices[0].message
    if not message.parsed:
        raise ValueError(message.refusal)
    return message.parsed


def get_chat_completion(prompt: str, model: str) -> str:
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return completion.choices[0].message.content
