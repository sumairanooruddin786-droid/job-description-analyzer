"""Pydantic models: LLM outputs for each node, the final report and API payloads."""
from typing import List

from pydantic import BaseModel, Field, field_validator


def _clean_list(values: List[str]) -> List[str]:
    """Strip, drop empties and remove case-insensitive duplicates (keeps order)."""
    seen, out = set(), []
    for v in values or []:
        item = str(v).strip()
        if item and item.lower() not in seen:
            seen.add(item.lower())
            out.append(item)
    return out


# ---------- Node outputs ----------
class ExtractionResult(BaseModel):
    is_job_description: bool = True
    job_title: str = "Not specified"
    company_name: str = "Not specified"
    required_experience: str = "Not specified"
    required_skills: List[str] = Field(default_factory=list)

    @field_validator("required_skills", mode="before")
    @classmethod
    def _skills(cls, v):
        return _clean_list(v)

    @field_validator("job_title", "company_name", "required_experience", mode="before")
    @classmethod
    def _default_text(cls, v):
        v = str(v).strip() if v is not None else ""
        return v or "Not specified"


class ClassificationResult(BaseModel):
    job_category: str = "Other"
    employment_type: str = "Not specified"  # Full-time / Part-time / Internship / Contract
    work_mode: str = "Not specified"  # Remote / Hybrid / On-site


class SkillAnalysis(BaseModel):
    technical_skills: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)
    top_3_skills: List[str] = Field(default_factory=list)

    @field_validator("technical_skills", "soft_skills", mode="before")
    @classmethod
    def _lists(cls, v):
        return _clean_list(v)

    @field_validator("top_3_skills", mode="before")
    @classmethod
    def _top3(cls, v):
        return _clean_list(v)[:3]


class ReportNarrative(BaseModel):
    summary: str = ""
    ideal_candidate: str = ""
    interview_focus: List[str] = Field(default_factory=list)

    @field_validator("interview_focus", mode="before")
    @classmethod
    def _focus(cls, v):
        return _clean_list(v)[:5]


# ---------- Final report ----------
class HiringReport(BaseModel):
    job_title: str
    company: str
    experience: str
    job_category: str
    employment_type: str
    work_mode: str
    required_skills: List[str]
    technical_skills: List[str]
    soft_skills: List[str]
    top_3_skills: List[str]
    summary: str
    ideal_candidate: str
    interview_focus: List[str]


class StepTrace(BaseModel):
    node: str
    label: str
    duration_ms: int


# ---------- API ----------
class AnalyzeRequest(BaseModel):
    job_description: str = ""


class AnalyzeResponse(BaseModel):
    report: HiringReport
    steps: List[StepTrace]
    model: str
    total_ms: int
