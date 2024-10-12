from agency_swarm import Agency, Agent


class Developer(Agent):
    def __init__(self):
        super().__init__(
            name="Developer",
            description="An expert software developer capable of writing, reviewing, and debugging code.",
            instructions="You are a skilled programmer. Your task is to write clean, efficient code, review existing code for improvements, and help debug issues.",
            tools=[],
        )


developer_agent = Developer()

developer_agency = Agency(
    [developer_agent],
    shared_instructions="agency_manifesto.md",
    temperature=0.1,
    max_prompt_tokens=25000,
)


async def delegate_task_to_developer(task_description: str):
    response = developer_agency.get_completion(message=task_description)
    return {"response": response}
