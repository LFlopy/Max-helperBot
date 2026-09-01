from dataclasses import dataclass
from typing import Literal


type AIMessageRole = Literal["system", "user", "assistant"]


@dataclass(frozen=True, slots=True)
class AIMessage:
    role: AIMessageRole
    content: str
