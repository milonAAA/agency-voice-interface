from agency_swarm import Agent


class VirtualAssistant(Agent):
    def __init__(self):
        super().__init__(
            name="Virtual Assistant",
            description="Responsible for general assistance and support tasks.",
            instructions="./instructions.md",
            tools=[],
            temperature=0.3,
            max_prompt_tokens=25000,
        )
