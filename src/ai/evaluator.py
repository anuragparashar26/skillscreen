"""Evaluation logic that combines embeddings similarity and LLM scoring."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables import RunnablePassthrough

from src.ai.embeddings import ChromaManager
from src.ai.prompts import EVALUATION_PROMPT, evaluation_parser
from src.config import set_google_api_key_in_env, get_settings


logger = logging.getLogger(__name__)


class Evaluator:
    """Evaluator that computes embeddings similarity, calls LLM and merges results."""

    def __init__(self, google_api_key: Optional[str] = None):
        set_google_api_key_in_env(google_api_key)
        self.chroma = ChromaManager()
        
        # Configure LangChain with Google Generative AI
        settings = get_settings()
        api_key = google_api_key or settings.google_api_key or os.environ.get("GOOGLE_API_KEY")
        
        # Initialize LangChain ChatGoogleGenerativeAI
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=api_key,
            temperature=0.3,
            convert_system_message_to_human=True
        )
        
        # Build the LangChain chain: prompt -> llm -> parser
        self.chain = EVALUATION_PROMPT | self.llm | evaluation_parser

    def _call_llm(self, job_description: str, resume_text: str, similarity: float) -> Dict[str, Any]:
        """Call Gemini via LangChain chain."""
        try:
            result = self.chain.invoke({
                "job_description": job_description,
                "resume_text": resume_text,
                "similarity": similarity,
                "format_instructions": evaluation_parser.get_format_instructions()
            })
            return result
        except Exception as e:
            logger.exception("LLM call failed")
            return {
                "score": 0,
                "summary": f"(LLM failed: {str(e)[:100]})",
                "matching_skills": [],
                "missing_skills": []
            }

    def evaluate(self, job_description: str, resumes: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Evaluate resumes.

        resumes: list of dicts with keys: id, filename, text
        returns: list of results with score, summary, matching_skills, missing_skills, similarity, llm_score
        """
        # embed job description
        jd_embedding = self.chroma.embed_texts([job_description])[0]

        results: List[Dict[str, Any]] = []
        collection_name = "resumes"

        for r in resumes:
            rid = r.get("id")
            text = r.get("text", "")
            filename = r.get("filename")

            # embed resume
            resume_embedding = self.chroma.embed_texts([text])[0]

            # store in chroma for this evaluation run
            try:
                self.chroma.add_documents(
                    collection_name, 
                    ids=[rid], 
                    documents=[text], 
                    metadatas=[{"filename": filename}], 
                    embeddings=[resume_embedding]
                )
            except Exception:
                logger.exception("Failed to add document to chroma")

            # query similarity
            try:
                sims = self.chroma.query_similarity(collection_name, jd_embedding, n_results=10)
                sim = next((x for x in sims if x.get("id") == rid), None)
                similarity_score = sim.get("similarity") if sim else 0.0
            except Exception:
                similarity_score = 0.0

            # Call LLM directly (bypassing LangChain)
            parsed = self._call_llm(job_description, text, similarity_score)

            # extract LLM score
            llm_score = float(parsed.get("score", 0))

            # final combined score (60% LLM, 40% embedding similarity)
            final_score = round(0.6 * llm_score + 0.4 * (float(similarity_score) * 100))

            results.append({
                "candidate_name": filename or rid,
                "id": rid,
                "score": int(final_score),
                "llm_score": llm_score,
                "similarity_score": float(similarity_score),
                "summary": parsed.get("summary", ""),
                "matching_skills": parsed.get("matching_skills", []),
                "missing_skills": parsed.get("missing_skills", []),
            })

        # sort descending by score
        results.sort(key=lambda r: r.get("score", 0), reverse=True)
        return results
