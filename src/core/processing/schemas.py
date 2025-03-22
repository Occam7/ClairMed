from pydantic import BaseModel

class ProcessedChunk(BaseModel):
    content: str
    metadata: dict
    vector: list[float] = None
