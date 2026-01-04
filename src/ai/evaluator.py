"""Evaluation logic that combines embeddings similarity and LLM scoring."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from langchain_google_genai import ChatGoogleGenerativeAI

from src.ai.embeddings import ChromaManager
from src.ai.prompts import EVALUATION_PROMPT, evaluation_parser


logger = logging.getLogger(__name__)


class Evaluator:
    """Evaluator that computes embeddings similarity, calls LLM and merges results."""

    def __init__(self, google_api_key: str, model: str = "gemini-2.5-flash"):
        """Initialize evaluator with explicit API key.
        
        Args:
            google_api_key: Required Google API key for Gemini. Must be provided explicitly.
            model: Gemini model to use. Default: gemini-2.5-flash
        """
        if not google_api_key:
            raise ValueError("Google API key is required")
        
        self.chroma = ChromaManager()
        self.model = model
        
        # Initialize LangChain ChatGoogleGenerativeAI with explicit key (no env fallback)
        self.llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=google_api_key,
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
            error_msg = str(e)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                return {
                    "score": 0,
                    "summary": f"API quota exhausted for model '{self.model}'. Please get a new API key from https://aistudio.google.com/app/apikey or try a different model.",
                    "matching_skills": [],
                    "missing_skills": []
                }
            return {
                "score": 0,
                "summary": f"(LLM failed: {error_msg[:150]})",
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
