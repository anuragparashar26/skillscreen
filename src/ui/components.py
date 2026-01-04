"""Streamlit UI components and app wiring."""
from __future__ import annotations

import io
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from src.ai.evaluator import Evaluator


logger = logging.getLogger(__name__)


# ============== Session Storage (Default) ==============

def init_session_storage() -> None:
    """Initialize session-based storage for evaluations."""
    if "evaluations" not in st.session_state:
        st.session_state.evaluations = []  # List of evaluation dicts


def save_evaluation_to_session(job_title: str, job_description: str, results: List[Dict]) -> str:
    """Save evaluation to session storage. Returns evaluation ID."""
    eval_id = str(uuid.uuid4())
    evaluation = {
        "id": eval_id,
        "job_title": job_title,
        "job_description": job_description,
        "created_at": datetime.now().isoformat(),
        "results": results
    }
    st.session_state.evaluations.insert(0, evaluation)  # Most recent first
    return eval_id


def get_session_evaluations() -> List[Dict]:
    """Get all evaluations from session storage."""
    return st.session_state.get("evaluations", [])


def get_session_evaluation_by_id(eval_id: str) -> Optional[Dict]:
    """Get a specific evaluation by ID."""
    for e in st.session_state.get("evaluations", []):
        if e.get("id") == eval_id:
            return e
    return None


def delete_session_evaluation(eval_id: str) -> None:
    """Delete an evaluation from session storage."""
    st.session_state.evaluations = [
        e for e in st.session_state.get("evaluations", []) 
        if e.get("id") != eval_id
    ]


# ============== Supabase Storage (Optional) ==============

def get_supabase_client():
    """Try to create Supabase client, return None if not configured."""
    try:
        from src.db.supabase_client import create_supabase_client
        return create_supabase_client()
    except Exception:
        return None


def save_evaluation_to_supabase(client, job_title: str, job_description: str, results: List[Dict]) -> Optional[str]:
    """Save evaluation to Supabase. Returns evaluation ID or None on failure."""
    try:
        from src.db import models as db_models
        evaluation_id = db_models.insert_evaluation(client, job_title, job_description)
        for r in results:
            db_models.insert_evaluation_result(
                client,
                evaluation_id,
                r.get("candidate_name"),
                int(r.get("score") or 0),
                r.get("summary") or "",
                r.get("matching_skills") or [],
                r.get("missing_skills") or [],
            )
        return evaluation_id
    except Exception as e:
        logger.exception("Failed to save to Supabase")
        return None


# ============== UI Helpers ==============

def parse_resume(uploaded_file) -> Dict[str, str]:
    """Parse an uploaded file (PDF or DOCX) and return id/filename/text."""
    name = uploaded_file.name
    raw = uploaded_file.read()
    text = ""
    
    # Determine file type and parse accordingly
    if name.lower().endswith(".pdf"):
        try:
            import PyPDF2
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(raw))
            text = "\n".join(page.extract_text() or "" for page in pdf_reader.pages)
        except Exception as e:
            logger.warning(f"Failed to parse PDF {name}: {e}")
            text = f"[Could not parse PDF: {e}]"
    
    elif name.lower().endswith(".docx"):
        try:
            import docx
            doc = docx.Document(io.BytesIO(raw))
            text = "\n".join(para.text for para in doc.paragraphs)
        except Exception as e:
            logger.warning(f"Failed to parse DOCX {name}: {e}")
            text = f"[Could not parse DOCX: {e}]"
    
    else:
        text = f"[Unsupported file format: {name}]"
    
    return {"id": name, "filename": name, "text": text}


def format_datetime(dt_str: str) -> str:
    """Format ISO datetime string to readable format in IST."""
    if not dt_str:
        return ""
    try:
        from zoneinfo import ZoneInfo
        # Parse ISO format datetime
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        # Convert to IST (Indian Standard Time)
        ist = ZoneInfo("Asia/Kolkata")
        dt_ist = dt.astimezone(ist)
        return dt_ist.strftime("%B %d, %Y at %I:%M %p IST")
    except Exception:
        return dt_str[:10]  # Fallback to just date part


def display_session_historical_results(evaluation: Dict[str, Any]) -> None:
    """Display results from a session-stored evaluation."""
    eval_id = evaluation.get("id")
    job_title = evaluation.get("job_title") or "(no title)"
    job_description = evaluation.get("job_description") or ""
    created_at = evaluation.get("created_at", "")
    results = evaluation.get("results", [])
    
    st.subheader(job_title)
    st.caption(f"Evaluated on: {format_datetime(created_at)}")
    
    with st.expander("View Job Description", expanded=False):
        st.text(job_description[:1000] + ("..." if len(job_description) > 1000 else ""))
    
    if results:
        df = pd.DataFrame([
            {
                "Candidate": r.get("candidate_name", ""),
                "Score": r.get("score", 0),
                "Matching Skills": ", ".join(r.get("matching_skills") or []),
                "Missing Skills": ", ".join(r.get("missing_skills") or []),
                "Summary": r.get("summary", ""),
            }
            for r in results
        ])
        st.dataframe(df.sort_values("Score", ascending=False).reset_index(drop=True))
        
        # CSV download
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download CSV", 
            data=csv_bytes, 
            file_name=f"evaluation_{eval_id[:8]}.csv", 
            mime="text/csv",
            key=f"download_{eval_id}"
        )
    else:
        st.info("No candidate results found for this evaluation.")
    
    # Delete button
    st.markdown("---")
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Delete Evaluation", type="secondary", use_container_width=True):
            delete_session_evaluation(eval_id)
            st.session_state.selected_evaluation = None
            st.success("Evaluation deleted.")
            st.rerun()


def run_app() -> None:
    st.set_page_config(
        page_title="Resume Screening Agent", 
        layout="wide",
        initial_sidebar_state="auto"
    )
    
    # Add mobile-responsive CSS
    st.markdown("""
        <style>
        /* Better mobile responsiveness */
        @media (max-width: 768px) {
            .stTextInput, .stTextArea, .stFileUploader {
                width: 100% !important;
            }
            .stButton > button {
                width: 100% !important;
            }
            section[data-testid="stSidebar"] {
                width: 100% !important;
            }
        }
        /* Ensure dataframes are scrollable on mobile */
        .stDataFrame {
            overflow-x: auto !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Initialize session storage
    init_session_storage()
    
    # Get Google API key from Streamlit Cloud secrets
    # To configure: Add GOOGLE_API_KEY in Streamlit Cloud Dashboard -> App Settings -> Secrets
    # Format in secrets: GOOGLE_API_KEY = "your-api-key-here"
    default_api_key = st.secrets.get("GOOGLE_API_KEY", "")
    
    st.sidebar.title("Configuration")
    
    # Allow users to provide their own API key
    st.sidebar.markdown("### Google Gemini API Key")
    user_api_key = st.sidebar.text_input(
        "Enter your API key (optional)",
        type="password",
        help="Provide your own Google Gemini API key if the default one is exhausted. Get one at https://aistudio.google.com/app/apikey",
        placeholder="Your API key here..."
    )
    
    # Use user's key if provided, otherwise use default
    active_api_key = user_api_key.strip() if user_api_key.strip() else default_api_key
    
    if user_api_key.strip():
        st.sidebar.success("Using your custom API key")
    elif default_api_key:
        st.sidebar.success("Using default API key")
    else:
        st.sidebar.error("No API Key configured")
        st.sidebar.info("Please provide your own Google Gemini API key above, or contact the admin to configure a default key.")
    
    # Model selection
    st.sidebar.markdown("### Gemini Model")
    selected_model = st.sidebar.selectbox(
        "Choose model",
        options=[
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash-exp",
            "gemini-2.0-flash",
            "gemini-exp-1206",
            "gemini-flash-latest",
            "gemini-pro-latest"
        ],
        index=0,
        help="Try different models if you encounter quota issues. Each model has separate quotas."
    )

    # Check for optional Supabase
    supabase_client = get_supabase_client()
    supabase_available = supabase_client is not None
    
    if supabase_available:
        st.sidebar.markdown("---")
        st.sidebar.success("Supabase connected (persistent storage)")

    # Title with GitHub link inline
    st.markdown(
        """
        <div style="display: flex; align-items: center; gap: 12px;">
            <h1 style="margin: 0;">SkillScreen - Resume Screening Agent</h1>
            <a href="https://github.com/anuragparashar26/skillscreen" target="_blank" style="text-decoration: none; display: flex; align-items: center;">
                <svg height="28" viewBox="0 0 16 16" width="28" style="fill: currentColor;">
                    <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
                </svg>
            </a>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Initialize session state
    if "selected_evaluation" not in st.session_state:
        st.session_state.selected_evaluation = None
    if "form_key" not in st.session_state:
        st.session_state.form_key = 0

    # Show success message if we just saved an evaluation
    if "last_saved_eval_id" in st.session_state:
        eval_id = st.session_state.pop("last_saved_eval_id")
        supabase_saved = st.session_state.pop("supabase_available", False)
        st.session_state.selected_evaluation = eval_id  # Auto-select the new evaluation
        if supabase_saved:
            st.success("Evaluation saved! (Persistent with Supabase)")
        else:
            st.success("Evaluation saved!")
            st.caption("Note: Session history clears on page refresh. Configure Supabase in .env for persistent storage.")

    with st.form(key=f"evaluate_form_{st.session_state.form_key}"):
        job_title = st.text_input("Job Title (optional)")
        job_description = st.text_area("Job Description", height=240)
        uploaded_files = st.file_uploader(
            "Upload resumes (PDF or DOCX)", 
            accept_multiple_files=True, 
            type=["pdf", "docx"]
        )
        col1, col2 = st.columns([1, 1])
        with col1:
            submitted = st.form_submit_button("Evaluate Resumes", use_container_width=True)
        with col2:
            reset = st.form_submit_button("Reset", use_container_width=True)
    
    if reset:
        st.session_state.form_key += 1
        st.session_state.selected_evaluation = None
        st.rerun()

    # History panel (session-based)
    st.sidebar.header("History")
    session_evals = get_session_evaluations()
    
    if session_evals:
        # Clear selection button
        if st.session_state.selected_evaluation is not None:
            if st.sidebar.button("New Evaluation", use_container_width=True):
                st.session_state.selected_evaluation = None
                st.rerun()
            st.sidebar.markdown("---")
        
        # Display clickable history items
        for i, e in enumerate(session_evals[:10]):
            eval_id = e.get("id")
            title = e.get("job_title") or "(no title)"
            created = e.get("created_at", "")[:10]  # Just the date part
            
            # Highlight selected item
            is_selected = st.session_state.selected_evaluation == eval_id
            button_label = f"{'> ' if is_selected else ''}{created} - {title[:20]}"
            
            if st.sidebar.button(button_label, key=f"hist_{i}", use_container_width=True):
                st.session_state.selected_evaluation = eval_id
                st.rerun()
    else:
        st.sidebar.info("No evaluation history yet. Evaluations will appear here after you run them. Note: History clears on page refresh unless Supabase is configured.")

    # Check if viewing historical evaluation
    if st.session_state.selected_evaluation is not None:
        selected_eval = get_session_evaluation_by_id(st.session_state.selected_evaluation)
        if selected_eval:
            display_session_historical_results(selected_eval)
            return  # Don't show the form results when viewing history

    if submitted:
        # Clear any selected history when submitting new evaluation
        st.session_state.selected_evaluation = None
        
        if not job_description or not uploaded_files:
            st.error("Please provide a Job Description and at least one resume file.")
            return

        # Check file sizes (max 5MB per file)
        MAX_FILE_SIZE_MB = 5
        MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
        oversized_files = [f.name for f in uploaded_files if f.size > MAX_FILE_SIZE_BYTES]
        if oversized_files:
            st.error(f"The following files exceed the {MAX_FILE_SIZE_MB}MB limit: {', '.join(oversized_files)}")
            return

        # Check API key
        if not active_api_key:
            st.error("Google API Key not configured. Please provide your own API key in the sidebar or contact the admin.")
            return

        # parse resumes
        resumes = [parse_resume(f) for f in uploaded_files]

        with st.spinner("Evaluating resumes..."):
            # Pass the user's API key explicitly - never use environment variables
            evaluator = Evaluator(google_api_key=active_api_key, model=selected_model)
            try:
                results = evaluator.evaluate(job_description=job_description, resumes=resumes)
            except Exception as e:
                logger.exception("Evaluation failed")
                error_msg = str(e)
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    st.error(f"API quota exhausted for model '{selected_model}'")
                    st.info("Solutions:\n- Get a new API key: https://aistudio.google.com/app/apikey\n- Try a different model from the sidebar\n- Wait for quota to reset (usually resets daily)")
                else:
                    st.error(f"Evaluation failed: {error_msg}")
                return

        if not results:
            st.info("No results produced.")
            return

        # show results
        df = pd.DataFrame([
            {
                "Candidate": r["candidate_name"],
                "Score": r["score"],
                "Matching Skills": ", ".join(r.get("matching_skills") or []),
                "Missing Skills": ", ".join(r.get("missing_skills") or []),
                "Summary": r.get("summary", ""),
            }
            for r in results
        ])

        st.subheader("Results")
        st.dataframe(df.sort_values("Score", ascending=False).reset_index(drop=True))

        # CSV download
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", data=csv_bytes, file_name="evaluation_results.csv", mime="text/csv")

        # Save to session storage (always)
        eval_id = save_evaluation_to_session(job_title, job_description, results)
        
        # Also save to Supabase if available
        if supabase_available:
            save_evaluation_to_supabase(supabase_client, job_title, job_description, results)
        
        # Store a flag to show success message after rerun
        st.session_state.last_saved_eval_id = eval_id
        st.session_state.supabase_available = supabase_available
        st.rerun()
