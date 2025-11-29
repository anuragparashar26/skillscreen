"""DB model helpers for inserting and querying evaluations in Supabase."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from uuid import UUID


def insert_evaluation(supabase_client, job_title: Optional[str], job_description: str) -> str:
    """Insert an evaluation row and return its id.

    supabase_client: a Supabase client from supabase_py
    """
    data = {"job_title": job_title, "job_description": job_description}
    res = supabase_client.table("evaluations").insert(data).execute()
    # response format: {data: [...], error: None}
    try:
        inserted = res.data[0]
        return inserted["id"]
    except Exception:
        raise


def insert_evaluation_result(supabase_client, evaluation_id: str, candidate_name: str, score: int, summary: str, matching_skills: List[str], missing_skills: List[str]):
    data = {
        "evaluation_id": evaluation_id,
        "candidate_name": candidate_name,
        "score": score,
        "summary": summary,
        "matching_skills": matching_skills,
        "missing_skills": missing_skills,
    }
    supabase_client.table("evaluation_results").insert(data).execute()


def list_evaluations(supabase_client) -> List[Dict[str, Any]]:
    res = supabase_client.table("evaluations").select("*").order("created_at", desc=True).execute()
    return res.data or []


def get_evaluation_results(supabase_client, evaluation_id: str) -> List[Dict[str, Any]]:
    res = supabase_client.table("evaluation_results").select("*").eq("evaluation_id", evaluation_id).execute()
    return res.data or []


def delete_evaluation(supabase_client, evaluation_id: str) -> None:
    """Delete an evaluation and its results (cascade delete)."""
    # Results are deleted automatically via ON DELETE CASCADE
    supabase_client.table("evaluations").delete().eq("id", evaluation_id).execute()
