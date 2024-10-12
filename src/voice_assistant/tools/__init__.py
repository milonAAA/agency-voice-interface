import os
import importlib
from agency_swarm.tools import BaseTool


def load_tools():
    tools = []
    current_dir = os.path.dirname(os.path.abspath(__file__))
    for filename in os.listdir(current_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = filename[:-3]
            module = importlib.import_module(f"voice_assistant.tools.{module_name}")
            for name, obj in module.__dict__.items():
                if (
                    isinstance(obj, type)
                    and issubclass(obj, BaseTool)
                    and obj != BaseTool
                ):
                    tools.append(obj)
    return tools
