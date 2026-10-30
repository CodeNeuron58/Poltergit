from typing import Literal

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    id: str
    kind: Literal["commit", "pull_request", "issue", "comment"] = "commit"
    title: str
    body: str
    sha: str = ""
    date: str = ""
    url: str = ""
    path: str = ""
    patch: str = ""


class LineHistory(BaseModel):
    repo: str
    revision: str
    path: str
    line: int
    code: str
    context: list[dict] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class Claim(BaseModel):
    text: str = Field(min_length=1, max_length=1500)
    source_id: str
    quote: str = Field(min_length=1, max_length=1200)


class ModelAnswer(BaseModel):
    claims: list[Claim] = Field(default_factory=list, max_length=6)
    silent: bool = False


class Answer(BaseModel):
    history: LineHistory
    text: str
    claims: list[Claim]
    mode: Literal["ollama", "record"]
    model: str = ""
    silent: bool = False
    warnings: list[str] = Field(default_factory=list)
    trace_id: str = ""
    spans: list[dict] = Field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    inference_cost_usd: float = 0


class Memorial(BaseModel):
    name: str
    path: str
    kind: Literal["file", "function"]
    born: str = ""
    departed: str
    days: int | None = None
    removal_sha: str
    removal_url: str = ""
    reason: str
    epitaph: str

