from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
SAMPLE_DOCS_DIR = DATA_DIR / "sample_docs"
CHROMA_DIR = ROOT_DIR / "chroma_db"

CLAUDE_MODEL = "claude-opus-5"
EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
