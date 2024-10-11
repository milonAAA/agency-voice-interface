from agency_swarm import Agency, Agent


# Define the Developer agent
class Developer(Agent):
    def __init__(self):
        super().__init__(
            name="Developer",
            description="An expert software developer capable of writing, reviewing, and debugging code.",
            instructions="You are a skilled programmer. Your task is to write clean, efficient code, review existing code for improvements, and help debug issues.",
            tools=[],  # Add any specific tools for the Developer if needed
        )


# Define the VirtualAssistant agent
class VirtualAssistant(Agent):
    def __init__(self):
        super().__init__(
            name="VirtualAssistant",
            description="A helpful virtual assistant capable of handling various tasks and queries.",
            instructions="You are a versatile virtual assistant. Your role is to assist with general queries, provide information, and help manage tasks.",
            tools=[],  # Add any specific tools for the VirtualAssistant if needed
        )


# Initialize agents
developer_agent = Developer()
virtual_assistant_agent = VirtualAssistant()

# Initialize separate agencies for each agent
developer_agency = Agency(
    [developer_agent],
    shared_instructions="agency_manifesto.md",
    temperature=0.1,
    max_prompt_tokens=25000,
)

virtual_assistant_agency = Agency(
    [virtual_assistant_agent],
    shared_instructions="agency_manifesto.md",
    temperature=0.1,
    max_prompt_tokens=25000,
)


async def delegate_task_to_developer(task_description: str):
    response = developer_agency.get_completion(message=task_description)
    return {"response": response}


async def assign_task_to_virtual_assistant(task_description: str):
    response = virtual_assistant_agency.get_completion(message=task_description)
    return {"response": response}
