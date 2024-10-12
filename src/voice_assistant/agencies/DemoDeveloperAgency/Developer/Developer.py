from agency_swarm import Agent
from agency_swarm.tools import CodeInterpreter


class Developer(Agent):
    def __init__(self):
        super().__init__(
            name="Developer",
            description="Responsible for coding tasks and technical implementations.",
            instructions="./instructions.md",
            tools=[CodeInterpreter],
            temperature=0.1,
            max_prompt_tokens=25000,
        )
