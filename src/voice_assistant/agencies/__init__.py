import os
import importlib
from agency_swarm import Agency


def load_agencies():
    agencies = []
    current_dir = os.path.dirname(os.path.abspath(__file__))

    for agency_folder in os.listdir(current_dir):
        agency_path = os.path.join(current_dir, agency_folder)
        if os.path.isdir(agency_path) and agency_folder != "__pycache__":
            try:
                agency_module = importlib.import_module(
                    f"voice_assistant.agencies.{agency_folder}.agency"
                )
                agency_class = getattr(
                    agency_module, f"{agency_folder.capitalize()}Agency"
                )
                agency_instance = agency_class()
                agencies.append(agency_instance)
            except (ImportError, AttributeError) as e:
                print(f"Error loading agency {agency_folder}: {e}")

    return agencies


# Load all agencies
AGENCIES: list[Agency] = load_agencies()


async def send_message_to_agency(agency_name: str, task_description: str):
    agency = next(
        (
            a
            for a in AGENCIES
            if a.__class__.__name__.lower() == f"{agency_name.lower()}agency"
        ),
        None,
    )
    if agency:
        response = await agency.get_completion(message=task_description)
        return {"response": response}
    else:
        return {"error": f"Agency '{agency_name}' not found"}
