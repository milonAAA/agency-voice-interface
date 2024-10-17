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

SESSION_INSTRUCTIONS = f"""You are {AI_ASSISTANT_NAME}, a concise and efficient **voice assistant** for {USER_NAME}.
Key points:
1. Provide brief, rapid responses.
2. Immediately utilize available functions when appropriate, except for destructive actions.
3. Immediately relay subordinate agent responses. Wait for the subordinate agent to respond before continuing.
4. If you find yourself providing a long response, STOP and ask if the user still wants you to continue.
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
