from agency_swarm import Agency, Agent


class VirtualAssistant(Agent):
    def __init__(self):
        super().__init__(
            name="VirtualAssistant",
            description="A helpful virtual assistant capable of handling various tasks and queries.",
            instructions="You are a versatile virtual assistant. Your role is to assist with general queries, provide information, and help manage tasks.",
            tools=[],
        )


virtual_assistant_agent = VirtualAssistant()

virtual_assistant_agency = Agency(
    [virtual_assistant_agent],
    shared_instructions="agency_manifesto.md",
    temperature=0.1,
    max_prompt_tokens=25000,
)


async def assign_task_to_virtual_assistant(task_description: str):
    response = virtual_assistant_agency.get_completion(message=task_description)
    return {"response": response}
