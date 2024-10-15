from agency_swarm import Agency

from .Developer.Developer import Developer
from .VirtualAssistant.VirtualAssistant import VirtualAssistant

developer_agent = Developer()
virtual_assistant_agent = VirtualAssistant()


agency = Agency(
    agency_chart=[
        developer_agent,
        [developer_agent, virtual_assistant_agent],
    ],
    shared_instructions="agency_manifesto.md",
    temperature=0.1,
    max_prompt_tokens=25000,
)
