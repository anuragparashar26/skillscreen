# Resume Screening Agent

A single-page Streamlit app that helps recruiters evaluate and rank resumes against a Job Description (JD) using Google Gemini, LangChain, and ChromaDB.

## Features

- **Upload Job Descriptions** - Paste or type the JD for the position
- **Upload Multiple Resumes** - Support for PDF and DOCX formats (max 5MB each)
- **AI-Powered Evaluation** - Uses Google Gemini 2.0 Flash for intelligent scoring
- **Hybrid Scoring System** - Combines LLM analysis (60%) with embedding similarity (40%)
- **Skills Analysis** - Identifies matching and missing skills for each candidate
- **Match Score & Summary** - 0-100 score with detailed fit summary
- **Export to CSV** - Download evaluation results for further analysis
- **Session History** - Clickable sidebar with recent evaluations
- **Persistent Storage** - Optional Supabase integration for cross-session history
- **View & Delete Past Evaluations** - Manage your evaluation history
- **Mobile Responsive** - Works on desktop and mobile devices
- **Reset Functionality** - Clear form and start fresh

## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Frontend** | Streamlit | Interactive web UI |
| **LLM** | Google Gemini 2.0 Flash | Resume evaluation & scoring |
| **LLM Framework** | LangChain | Prompt orchestration & output parsing |
| **Embeddings** | sentence-transformers (all-MiniLM-L6-v2) | Text vectorization |
| **Vector Store** | ChromaDB | In-memory similarity search |
| **Database** | Supabase (PostgreSQL) | Optional persistent storage |
| **Document Parsing** | PyPDF2, python-docx | Resume text extraction |

## Project Structure

```
resume-screening-agent/
├── app.py                      # Streamlit entrypoint
├── requirements.txt            # Python dependencies
├── README.md                   # Documentation
├── LICENSE                     # MIT License
└── src/
    ├── __init__.py
    ├── config.py               # Environment loader & settings
    ├── ai/
    │   ├── __init__.py
    │   ├── prompts.py          # LangChain prompt templates & Pydantic models
    │   ├── evaluator.py        # Core evaluation logic (embeddings + LLM)
    │   └── embeddings.py       # ChromaDB manager & embedding functions
    ├── db/
    │   ├── __init__.py
    │   ├── supabase_client.py  # Supabase client wrapper (optional)
    │   └── models.py           # Database model helpers (CRUD operations)
    └── ui/
        ├── __init__.py
        └── components.py       # Streamlit UI components & app logic
```

## Setup

### Prerequisites

- Python 3.9+
- Google API Key ([Get one from Google AI Studio](https://aistudio.google.com/app/apikey))

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/anuragparashar26/resume-screening-agent.git
cd resume-screening-agent
```

2. **Create virtual environment and install dependencies**

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

3. **Run the application**

```bash
streamlit run app.py
```

4. **Enter your Google API Key** in the sidebar when the app opens

### Optional: Persistent Storage with Supabase

If you want evaluation history to persist across sessions, set up your own Supabase:

1. Create a `.env` file in the project root:

```env
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

## Usage Guide

1. **Enter your Google API Key** in the sidebar (required for AI evaluation)
2. **Enter a Job Description** and optional Job Title in the main form
3. **Upload resumes** - Drag and drop or browse for PDF/DOCX files (max 5MB each)
4. **Click "Evaluate Resumes"** to run AI-powered scoring
5. **View ranked results** with scores, summaries, and skill analysis
6. **Download CSV** for offline analysis or sharing
7. **Click history items** in the sidebar to view past evaluations
8. **Use "Reset"** to clear the form and start fresh

## Storage Options

| Mode | Description | Data Persistence |
|------|-------------|------------------|
| **Session (default)** | History stored in Streamlit session_state | Cleared on page refresh |
| **Supabase (optional)** | User provides their own Supabase credentials | Persists across sessions |

## How It Works

### Evaluation Pipeline

```
Resume Upload → Text Extraction → Embedding Generation → Similarity + LLM Analysis → Final Score
```

1. **Document Parsing**: PyPDF2 (PDF) and python-docx (DOCX) extract text from uploaded resumes
2. **Embedding Generation**: sentence-transformers (all-MiniLM-L6-v2) converts text to 384-dimensional vectors
3. **Similarity Computation**: ChromaDB calculates cosine similarity between job description and resumes
4. **LLM Evaluation**: Google Gemini 2.0 Flash analyzes each resume against the JD using LangChain:
   - Generates a score (0-100)
   - Writes a fit summary (3-5 sentences)
   - Identifies matching skills
   - Identifies missing skills
5. **Score Calculation**: Final score = `(0.6 × LLM Score) + (0.4 × Similarity × 100)`
6. **Ranking**: Candidates sorted by final score in descending order

### Why Hybrid Scoring?

- **Embedding similarity** captures semantic relevance at scale
- **LLM analysis** provides nuanced understanding of qualifications
- **Combined approach** balances speed with accuracy

## Limitations

- LLM responses may occasionally be inaccurate; human review recommended
- Session history clears on page refresh (use Supabase for persistence)
- Not production-hardened (no auth, rate limiting, or retry/backoff)
- Supabase RLS policies are permissive for development
- Maximum file size: 5MB per resume

## Potential Improvements

- [ ] Add authentication and role-based access
- [ ] Improve scoring model and calibrate weights
- [ ] Add batch processing for large resume sets
- [ ] Add unit tests and CI/CD pipeline
- [ ] Support more document formats (TXT, RTF)
- [ ] Implement retry logic with exponential backoff
- [ ] Add candidate comparison view
- [ ] Enable custom evaluation criteria

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
