"""Prompt templates for evaluator LLM calls."""
from __future__ import annotations

from typing import List

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field


class EvaluationResult(BaseModel):
    """Structured output for resume evaluation."""
    score: int = Field(description="Score from 0-100 indicating how well the candidate matches the job")
    summary: str = Field(description="3-5 sentence summary of the candidate's fit for the role")
    matching_skills: List[str] = Field(description="List of skills from the resume that match the job requirements")
    missing_skills: List[str] = Field(description="List of required skills missing from the resume")


# JSON output parser for structured responses
evaluation_parser = JsonOutputParser(pydantic_object=EvaluationResult)


EVALUATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert recruiter assistant. Your task is to evaluate candidate resumes against job descriptions and provide structured assessments.

Always respond with valid JSON matching the specified format. Use the similarity score to inform your judgement but rely primarily on the resume and job description content."""),
    ("human", """Evaluate the following candidate resume against the job description.

Job Description:
{job_description}

Candidate Resume:
{resume_text}

Embedding Similarity Score: {similarity}

{format_instructions}

Provide your evaluation as JSON:""")
])
