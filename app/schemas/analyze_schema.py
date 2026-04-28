from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    email_text: str


class AnalyzeResponse(BaseModel):
    status: str
    analysis: str