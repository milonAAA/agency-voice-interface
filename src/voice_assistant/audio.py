# src/voice_assistant/audio.py
import pyaudio
import asyncio
import logging
import numpy as np
from voice_assistant.config import FORMAT, CHANNELS, RATE


class AudioPlayer:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=FORMAT, channels=CHANNELS, rate=RATE, output=True, start=False
        )
        self.is_playing = False

    async def play_audio_chunk(self, audio_chunk: bytes, visual_interface):
        if not self.is_playing:
            self.stream.start_stream()
            self.is_playing = True
            visual_interface.set_assistant_speaking(True)

        self.stream.write(audio_chunk)

        # Update energy for visualization
        audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
        energy = np.abs(audio_array).mean()
        visual_interface.update_energy(energy)

        # Allow other tasks to run
        await asyncio.sleep(0)

    async def stop_playback(self, visual_interface):
        if self.is_playing:
            # Add a small delay of silence at the end
            silence_duration = 0.2  # 200ms
            silence_frames = int(RATE * silence_duration)
            silence = b"\x00" * (silence_frames * CHANNELS * 2)
            self.stream.write(silence)

            await asyncio.sleep(0.5)

            self.stream.stop_stream()
            self.is_playing = False
            visual_interface.set_assistant_speaking(False)
            logging.debug("Audio playback completed")

    def close(self):
        self.stream.close()
        self.p.terminate()


audio_player = AudioPlayer()
