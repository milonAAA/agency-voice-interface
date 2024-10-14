# src/voice_assistant/main.py
import asyncio
import json
import logging
import os
import websockets
from websockets.exceptions import ConnectionClosedError
import pygame
import numpy as np

from voice_assistant.config import (
    SESSION_INSTRUCTIONS,
    SILENCE_THRESHOLD,
    PREFIX_PADDING_MS,
    SILENCE_DURATION_MS,
)
from voice_assistant.microphone import AsyncMicrophone
from voice_assistant.utils import (
    log_ws_event,
    base64_encode_audio,
)
from voice_assistant.websocket_handler import TOOLS, process_ws_messages
from voice_assistant.visual_interface import (
    VisualInterface,
    run_visual_interface,
)


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)


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
            visual_interface = VisualInterface()

            # Initialize tools separately
            initialized_tools = []
            for tool in TOOLS:
                tool_schema = {
                    k: v for k, v in tool.openai_schema.items() if k != "strict"
                }
                tool_type = "function" if not hasattr(tool, "type") else tool.type
                initialized_tools.append({**tool_schema, "type": tool_type})

            async with websockets.connect(url, extra_headers=headers) as websocket:
                logging.info("Connected to the server.")
                # Initialize the session with voice capabilities and tools
                session_update = {
                    "type": "session.update",
                    "session": {
                        "modalities": ["text", "audio"],
                        "instructions": SESSION_INSTRUCTIONS,
                        "voice": "shimmer",
                        "input_audio_format": "pcm16",
                        "output_audio_format": "pcm16",
                        "turn_detection": {
                            "type": "server_vad",
                            "threshold": SILENCE_THRESHOLD,
                            "prefix_padding_ms": PREFIX_PADDING_MS,
                            "silence_duration_ms": SILENCE_DURATION_MS,
                        },
                        "tools": initialized_tools,
                    },
                }
                log_ws_event("outgoing", session_update)
                await websocket.send(json.dumps(session_update))

                ws_task = asyncio.create_task(
                    process_ws_messages(websocket, mic, visual_interface)
                )
                visual_task = asyncio.create_task(
                    run_visual_interface(visual_interface)
                )

                logging.info(
                    "Conversation started. Speak freely, and the assistant will respond."
                )
                mic.start_recording()
                logging.info("Recording started. Listening for speech...")

                try:
                    while not exit_event.is_set():
                        await asyncio.sleep(0.01)  # Small delay to reduce CPU usage
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
                                    # Update energy for visualization
                                    audio_frame = np.frombuffer(
                                        audio_data, dtype=np.int16
                                    )
                                    energy = np.abs(audio_frame).mean()
                                    visual_interface.update_energy(energy)
                                else:
                                    logging.debug("No audio data to send")
                except KeyboardInterrupt:
                    logging.info("Keyboard interrupt received. Closing the connection.")
                except Exception as e:
                    logging.exception(
                        f"An unexpected error occurred in the main loop: {e}"
                    )
                finally:
                    exit_event.set()
                    mic.stop_recording()
                    mic.close()
                    await websocket.close()
                    visual_interface.set_active(False)

                # Wait for the WebSocket processing task to complete
                try:
                    await ws_task
                    await visual_task
                except Exception as e:
                    logging.exception(f"Error in WebSocket processing task: {e}")

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
            pygame.quit()


async def main_async():
    await realtime_api()


def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logging.info("Program terminated by user")
    except Exception as e:
        logging.exception(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    print("Press Ctrl+C to exit the program.")
    main()
