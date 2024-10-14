import os
import importlib
from agency_swarm import Agency


def load_agencies() -> dict[str, Agency]:
    agencies = {}
    current_dir = os.path.dirname(os.path.abspath(__file__))

    for agency_folder in os.listdir(current_dir):
        agency_path = os.path.join(current_dir, agency_folder)
        if os.path.isdir(agency_path) and agency_folder != "__pycache__":
            try:
                agency_module = importlib.import_module(
                    f"voice_assistant.agencies.{agency_folder}.agency"
                )
                agencies[agency_folder] = getattr(agency_module, "agency")
            except (ImportError, AttributeError) as e:
                print(f"Error loading agency {agency_folder}: {e}")

    return agencies


# Load all agencies
AGENCIES: dict[str, Agency] = load_agencies()
