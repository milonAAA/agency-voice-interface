import pygame
import asyncio
import numpy as np
from collections import deque
import os


class VisualInterface:
    def __init__(self, width=400, height=400):
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Assistant Voice Activity")

        # Set the app icon
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        icon = pygame.image.load(icon_path)
        pygame.display.set_icon(icon)

        self.clock = pygame.time.Clock()
        self.is_active = False
        self.is_assistant_speaking = False
        self.active_color = (50, 139, 246)  # Sky Blue
        self.inactive_color = (100, 100, 100)  # Gray
        self.current_color = self.inactive_color
        self.base_radius = 100
        self.current_radius = self.base_radius
        self.energy_queue = deque(maxlen=50)  # Store last 50 energy values
        self.update_interval = 0.05  # Update every 50ms
        self.max_energy = 1.0  # Initial max energy value

    async def update(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return False

        self.screen.fill((0, 0, 0))  # Black background

        # Smooth transition for radius
        target_radius = self.base_radius
        if self.energy_queue:
            normalized_energy = np.mean(self.energy_queue) / (
                self.max_energy or 1.0
            )  # Avoid division by zero
            target_radius += int(normalized_energy * self.base_radius)

        self.current_radius += (target_radius - self.current_radius) * 0.2
        self.current_radius = min(
            max(self.current_radius, self.base_radius), self.width // 2
        )

        # Smooth transition for color
        target_color = (
            self.active_color
            if self.is_active or self.is_assistant_speaking
            else self.inactive_color
        )
        self.current_color = tuple(
            int(self.current_color[i] + (target_color[i] - self.current_color[i]) * 0.1)
            for i in range(3)
        )

        pygame.draw.circle(
            self.screen,
            self.current_color,
            (self.width // 2, self.height // 2),
            int(self.current_radius),
        )

        pygame.display.flip()
        self.clock.tick(60)
        await asyncio.sleep(self.update_interval)
        return True

    def set_active(self, is_active):
        self.is_active = is_active

    def set_assistant_speaking(self, is_speaking):
        self.is_assistant_speaking = is_speaking

    def update_energy(self, energy):
        if isinstance(energy, np.ndarray):
            energy = np.mean(np.abs(energy))
        self.energy_queue.append(energy)

        # Update max_energy dynamically
        current_max = max(self.energy_queue)
        if current_max > self.max_energy:
            self.max_energy = current_max
        elif len(self.energy_queue) == self.energy_queue.maxlen:
            self.max_energy = max(self.energy_queue)


async def run_visual_interface(interface):
    while True:
        if not await interface.update():
            break
