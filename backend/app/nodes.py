"""The four LangGraph nodes. Each node reads from the shared state and returns a partial update."""
import json
import time
from typing import Annotated, List, Optional, TypedDict
import operator

from . import prompts
from .llm import call_llm
from .schemas import (
    ClassificationResult,
    ExtractionResult,
    HiringReport,
    ReportNarrative,
    SkillAnalysis,
    StepTrace,
)


class JobState(TypedDict, total=False):
    """Shared state that is passed from node to node."""

    job_description: str
    extraction: Optional[ExtractionResult]
    classification: Optional[ClassificationResult]
    skills: Optional[SkillAnalysis]
    report: Optional[HiringReport]
    error: Optional[str]
    # operator.add -> every node appends its own trace entry
    steps: Annotated[List[StepTrace], operator.add]


def _trace(node: str, label: str, started: float) -> List[StepTrace]:
    return [StepTrace(node=node, label=label, duration_ms=int((time.perf_counter() - started) * 1000))]


# ---------------- Node 1 ----------------
def information_extraction(state: JobState) -> JobState:
    """Extract job title, company, experience and required skills."""
    t0 = time.perf_counter()
    result = call_llm(
        prompts.EXTRACTION_SYSTEM,
        f"JOB DESCRIPTION:\n\"\"\"\n{state['job_description']}\n\"\"\"",
        ExtractionResult,
    )
    update: JobState = {"extraction": result, "steps": _trace("extract", "Information Extraction", t0)}
    if not result.is_job_description:
        update["error"] = "The text you entered does not look like a job description. Please paste a real job posting."
    return update


# ---------------- Node 2 ----------------
def job_classification(state: JobState) -> JobState:
    """Classify job category, employment type and work mode."""
    t0 = time.perf_counter()
    ext = state["extraction"]
    user = (
        f"EXTRACTED DATA:\n{ext.model_dump_json(indent=2)}\n\n"
        f"JOB DESCRIPTION:\n\"\"\"\n{state['job_description']}\n\"\"\""
    )
    result = call_llm(prompts.CLASSIFICATION_SYSTEM, user, ClassificationResult)
    return {"classification": result, "steps": _trace("classify", "Job Classification", t0)}


# ---------------- Node 3 ----------------
def skill_analysis(state: JobState) -> JobState:
    """Split skills into technical / soft and rank the top 3."""
    t0 = time.perf_counter()
    ext, cls = state["extraction"], state["classification"]
    user = (
        f"JOB TITLE: {ext.job_title}\nCATEGORY: {cls.job_category}\n"
        f"REQUIRED SKILLS: {', '.join(ext.required_skills) or 'None listed'}\n\n"
        f"JOB DESCRIPTION:\n\"\"\"\n{state['job_description']}\n\"\"\""
    )
    result = call_llm(prompts.SKILL_SYSTEM, user, SkillAnalysis)

    # Safety net: guarantee the ranking always has up to 3 entries
    if len(result.top_3_skills) < 3:
        pool = [s for s in (ext.required_skills + result.technical_skills + result.soft_skills)
                if s.lower() not in {x.lower() for x in result.top_3_skills}]
        result.top_3_skills = (result.top_3_skills + pool)[:3]
    return {"skills": result, "steps": _trace("skills", "Skill Analysis", t0)}


# ---------------- Node 4 ----------------
def hiring_report(state: JobState) -> JobState:
    """Combine everything into the final structured hiring report."""
    t0 = time.perf_counter()
    ext, cls, sk = state["extraction"], state["classification"], state["skills"]

    facts = {
        "job_title": ext.job_title,
        "company": ext.company_name,
        "experience": ext.required_experience,
        "category": cls.job_category,
        "employment_type": cls.employment_type,
        "work_mode": cls.work_mode,
        "technical_skills": sk.technical_skills,
        "soft_skills": sk.soft_skills,
        "top_3_skills": sk.top_3_skills,
    }
    narrative = call_llm(prompts.REPORT_SYSTEM, json.dumps(facts, indent=2), ReportNarrative)

    report = HiringReport(
        job_title=ext.job_title,
        company=ext.company_name,
        experience=ext.required_experience,
        job_category=cls.job_category,
        employment_type=cls.employment_type,
        work_mode=cls.work_mode,
        required_skills=ext.required_skills,
        technical_skills=sk.technical_skills,
        soft_skills=sk.soft_skills,
        top_3_skills=sk.top_3_skills,
        summary=narrative.summary,
        ideal_candidate=narrative.ideal_candidate,
        interview_focus=narrative.interview_focus,
    )
    return {"report": report, "steps": _trace("report", "Hiring Report", t0)}
