# Resume Screening Agent

A single-page Streamlit app that helps recruiters evaluate and rank resumes against a Job Description (JD) using Google Gemini, LangChain, and ChromaDB.

## Features

- Upload a Job Description (JD)
- Upload multiple resumes (PDF or DOCX, max 5MB each)
- AI-powered evaluation & ranking by fit with the JD
- Display match score, summary, matching & missing skills
- Export results to CSV
- Session-based history with clickable sidebar
- Optional persistent storage via Supabase (user configures their own)
- View and delete past evaluations
- Reset form to start fresh
- GitHub repository link in header

## Tech Stack

- Python 3.x
- Streamlit (UI)
- Google Gemini via LangChain (LLM orchestration)
- ChromaDB with sentence-transformers (embeddings & similarity)
- Supabase (Postgres) - optional, user-provided

## Project Structure

```
resume-screening-agent/
├── app.py                  # Streamlit entrypoint
├── requirements.txt
├── README.md
└── src/
    ├── config.py           # env loader and helpers
    ├── ai/
    │   ├── prompts.py      # LangChain prompt templates
    │   ├── evaluator.py    # evaluation logic using LangChain + Gemini
    │   └── embeddings.py   # ChromaDB + embeddings setup
    ├── db/
    │   ├── supabase_client.py  # Supabase client wrapper (optional)
    │   └── models.py       # DB model helpers
    └── ui/
        └── components.py   # Streamlit UI components
```

## Setup

1. Clone the repo

```bash
git clone https://github.com/anuragparashar26/resume-screening-agent.git
cd resume-screening-agent
```

2. Create a virtualenv and install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Run the app

```bash
streamlit run app.py
```

4. Enter your **Google API Key** in the sidebar (get one from [Google AI Studio](https://aistudio.google.com/app/apikey))

### Optional: Persistent Storage with Supabase

If you want evaluation history to persist across sessions, set up your own Supabase:

1. Create a `.env` file:

```env
GOOGLE_API_KEY=your-google-api-key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
```

2. Run this SQL in your Supabase SQL editor:

```sql
-- Create tables
CREATE TABLE IF NOT EXISTS evaluations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_title TEXT,
  job_description TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS evaluation_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  evaluation_id UUID REFERENCES evaluations(id) ON DELETE CASCADE,
  candidate_name TEXT,
  score NUMERIC,
  summary TEXT,
  matching_skills JSONB,
  missing_skills JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE evaluations ENABLE ROW LEVEL SECURITY;
ALTER TABLE evaluation_results ENABLE ROW LEVEL SECURITY;

-- Create policies for anonymous access
CREATE POLICY "Allow anonymous insert on evaluations" ON evaluations
  FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "Allow anonymous select on evaluations" ON evaluations
  FOR SELECT TO anon USING (true);
CREATE POLICY "Allow anonymous delete on evaluations" ON evaluations
  FOR DELETE TO anon USING (true);

CREATE POLICY "Allow anonymous insert on evaluation_results" ON evaluation_results
  FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "Allow anonymous select on evaluation_results" ON evaluation_results
  FOR SELECT TO anon USING (true);
CREATE POLICY "Allow anonymous delete on evaluation_results" ON evaluation_results
  FOR DELETE TO anon USING (true);
```

## How to use

1. Enter your **Google API Key** in the sidebar
2. Enter a Job Description and optional Job Title
3. Upload one or more resumes (PDF or DOCX, max 5MB each)
4. Click **Evaluate Resumes** to run AI-powered scoring
5. View ranked results table with scores and skill analysis
6. Download results as CSV
7. Click on history items in sidebar to view past evaluations
8. Use **Reset** to clear the form and start fresh

## Storage Options

| Mode                    | How it works                                           | Persistence              |
| ----------------------- | ------------------------------------------------------ | ------------------------ |
| **Session (default)**   | History stored in Streamlit session                    | Cleared on page refresh  |
| **Supabase (optional)** | User provides their own Supabase credentials in `.env` | Persists across sessions |

## How it works

1. **Embeddings**: Resumes and job descriptions are embedded using sentence-transformers (all-MiniLM-L6-v2) via ChromaDB
2. **Similarity**: Cosine similarity is computed between job description and each resume
3. **LLM Evaluation**: Google Gemini analyzes each resume against the JD and provides:
   - Score (0-100)
   - Summary of candidate fit
   - Matching skills
   - Missing skills
4. **Final Score**: Combines LLM score (60%) and embedding similarity (40%)

## Limitations

- LLM responses may occasionally be inaccurate; outputs should be reviewed by a human
- Session history clears on page refresh (use Supabase for persistence)
- Not production-hardened (no auth, rate limiting, or retry/backoff)
- Supabase RLS policies are permissive for development

## Potential Improvements

- Add authentication and role-based access
- Improve scoring model and calibrate weights
- Add batch processing for large resume sets
- Add unit tests and CI
- Support more document formats
