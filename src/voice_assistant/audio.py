# src/voice_assistant/audio.py
import pyaudio
import asyncio
import logging
import numpy as np
from voice_assistant.config import FORMAT, CHANNELS, RATE


async def play_audio(audio_data: bytes, visual_interface):
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True)

    chunk_size = 1024  # Adjust this value as needed
    audio_array = np.frombuffer(audio_data, dtype=np.int16)

    visual_interface.set_assistant_speaking(True)

    for i in range(0, len(audio_array), chunk_size):
        chunk = audio_array[i : i + chunk_size]
        stream.write(chunk.tobytes())

        # Update energy for visualization
        energy = np.abs(chunk).mean()
        visual_interface.update_energy(energy)

        # Allow other tasks to run
        await asyncio.sleep(0)

    # Add a small delay of silence at the end
    silence_duration = 0.2  # 200ms
    silence_frames = int(RATE * silence_duration)
    silence = b"\x00" * (silence_frames * CHANNELS * 2)
    stream.write(silence)

    await asyncio.sleep(0.5)

    stream.stop_stream()
    stream.close()
    p.terminate()

    visual_interface.set_assistant_speaking(False)
    logging.debug("Audio playback completed")
