# src/realtime_api_async_python/models.py
from enum import Enum
from pydantic import BaseModel


class ModelName(str, Enum):
    STATE_OF_THE_ART_MODEL = "state_of_the_art_model"
    REASONING_MODEL = "reasoning_model"
    BASE_MODEL = "base_model"
    FAST_MODEL = "fast_model"


class WebUrl(BaseModel):
    url: str


class CreateFileResponse(BaseModel):
    file_content: str
    file_name: str


class FileSelectionResponse(BaseModel):
    file: str
    model: ModelName = ModelName.BASE_MODEL


class FileUpdateResponse(BaseModel):
    updates: str


class FileDeleteResponse(BaseModel):
    file: str
    force_delete: bool
