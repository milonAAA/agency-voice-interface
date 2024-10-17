# src/voice_assistant/config.py
import json
import os

import pyaudio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
PREFIX_PADDING_MS = 300
SILENCE_THRESHOLD = 0.5
SILENCE_DURATION_MS = 400
RUN_TIME_TABLE_LOG_JSON = "runtime_time_table.jsonl"
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 24000

# Load personalization settings
PERSONALIZATION_FILE = os.getenv("PERSONALIZATION_FILE", "./personalization.json")
with open(PERSONALIZATION_FILE, "r") as f:
    personalization = json.load(f)

AI_ASSISTANT_NAME = personalization.get("ai_assistant_name", "Assistant")
USER_NAME = personalization.get("user_name", "User")

SESSION_INSTRUCTIONS = f"""You are {AI_ASSISTANT_NAME}, a concise and efficient voice assistant for {USER_NAME}.
Key points:
1. Provide brief, rapid responses.
2. Utilize available functions when appropriate.
3. Immediately relay subordinate agent responses.
4. Adapt tone to user's context and needs.
5. Prioritize clarity and relevance in all interactions.
"""

# Check for required environment variables
REQUIRED_ENV_VARS = ["OPENAI_API_KEY", "PERSONALIZATION_FILE", "SCRATCH_PAD_DIR"]
MISSING_VARS = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
if MISSING_VARS:
    raise EnvironmentError(
        f"Missing required environment variables: {', '.join(MISSING_VARS)}"
    )

SCRATCH_PAD_DIR = os.getenv("SCRATCH_PAD_DIR", "./scratchpad")
os.makedirs(SCRATCH_PAD_DIR, exist_ok=True)
