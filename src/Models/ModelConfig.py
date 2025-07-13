
from dataclasses import dataclass

@dataclass
class ModelConfig:
    modelId: str
    contextWindow: int
    maxCompletionTokens: int