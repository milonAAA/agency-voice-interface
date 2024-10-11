# src/realtime_api_async_python/audio.py
import pyaudio
import asyncio
import logging
from realtime_api_async_python.config import FORMAT, CHANNELS, RATE


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
