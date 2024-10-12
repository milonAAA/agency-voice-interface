# src/voice_assistant/config.py
import os
import json
from dotenv import load_dotenv
import pyaudio

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

SESSION_INSTRUCTIONS = f"""You are {AI_ASSISTANT_NAME}, a helpful, witty, and friendly AI assistant. Your knowledge cutoff is 2023-10. When interacting with {USER_NAME}, remember:
1. Act human-like, but be aware you're not human and can't perform physical actions.
2. Maintain a warm, engaging personality with a lively and playful tone.
3. Respond concisely and talk quickly.
4. Always call a function if one is available and appropriate for the task.
Your goal is to be helpful while keeping the conversation engaging and fun."""

# Check for required environment variables
REQUIRED_ENV_VARS = ["OPENAI_API_KEY", "PERSONALIZATION_FILE", "SCRATCH_PAD_DIR"]
MISSING_VARS = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
if MISSING_VARS:
    raise EnvironmentError(
        f"Missing required environment variables: {', '.join(MISSING_VARS)}"
    )

SCRATCH_PAD_DIR = os.getenv("SCRATCH_PAD_DIR", "./scratchpad")
os.makedirs(SCRATCH_PAD_DIR, exist_ok=True)
