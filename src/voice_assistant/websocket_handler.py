# src/voice_assistant/websocket_handler.py
import json
import logging
import base64
import time
import websockets

from voice_assistant.tools import TOOLS
from voice_assistant.utils import log_ws_event, log_runtime
from voice_assistant.audio import audio_player


async def process_ws_messages(websocket, mic, visual_interface):
    assistant_reply = ""
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
                visual_interface.set_active(True)
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
                            json.loads(function_call_args) if function_call_args else {}
                        )
                    except json.JSONDecodeError:
                        logging.error(
                            f"Failed to parse function arguments: {function_call_args}"
                        )
                        args = {}

                    tool = next(
                        (
                            t
                            for t in TOOLS
                            if t.__name__.lower() == function_name.lower()
                        ),
                        None,
                    )
                    if tool:
                        logging.info(
                            f"🛠️ Calling function: {function_name} with args: {args}"
                        )
                        try:
                            tool_instance = tool(**args)
                            result = await tool_instance.run()
                            logging.info(f"🛠️ Function call result: {result}")
                        except Exception as e:
                            logging.error(
                                f"Error calling function {function_name}: {str(e)}"
                            )
                            result = {
                                "error": f"Function '{function_name}' failed: {str(e)}"
                            }
                    else:
                        logging.warning(
                            f"Function '{function_name}' not found in TOOLS"
                        )
                        result = {"error": f"Function '{function_name}' not found."}

                    function_call_output = {
                        "type": "conversation.item.create",
                        "item": {
                            "type": "function_call_output",
                            "call_id": call_id,
                            "output": json.dumps(result),
                        },
                    }
                    log_ws_event("outgoing", function_call_output)
                    await websocket.send(json.dumps(function_call_output))
                    await websocket.send(json.dumps({"type": "response.create"}))
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
                audio_chunk = base64.b64decode(event["delta"])
                await audio_player.play_audio_chunk(audio_chunk, visual_interface)
            elif event_type == "response.done":
                if response_start_time is not None:
                    response_duration = time.perf_counter() - response_start_time
                    log_runtime("realtime_api_response", response_duration)
                    response_start_time = None

                logging.info("Assistant response complete.")
                await audio_player.stop_playback(visual_interface)
                assistant_reply = ""
                logging.info("Calling stop_receiving()")
                mic.stop_receiving()
                visual_interface.set_active(False)
                mic.start_recording()
                logging.info("Started recording for next user input")
            elif event_type == "rate_limits.updated":
                mic.start_recording()
                logging.info("Resumed recording after rate_limits.updated")
            elif event_type == "error":
                error_message = event.get("error", {}).get("message", "")
                if "buffer is empty" in error_message:
                    logging.info(
                        "Received 'buffer is empty' error, no audio data sent."
                    )
                    continue
                elif "Conversation already has an active response" in error_message:
                    logging.info(
                        "Received 'active response' error, adjusting response flow."
                    )
                    continue
                else:
                    logging.error(f"Unhandled error: {error_message}")
                    break
            elif event_type == "input_audio_buffer.speech_started":
                logging.info("Speech detected, listening...")
                visual_interface.set_active(True)
            elif event_type == "input_audio_buffer.speech_stopped":
                mic.stop_recording()
                logging.info("Speech ended, processing...")
                visual_interface.set_active(False)

                response_start_time = time.perf_counter()
                await websocket.send(json.dumps({"type": "input_audio_buffer.commit"}))
        except websockets.ConnectionClosed:
            logging.warning("WebSocket connection closed")
            break

    audio_player.close()
