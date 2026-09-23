"""Usage (from backend/, with the same env the API runs with -- needs
DATABASE_URL and LIVEBLOCKS_API_KEY):

    infisical run --env=dev -- python -m app.kg_samples
"""
import logging

from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

from ..db import init_db  # noqa: E402
from .seed import seed_samples  # noqa: E402

init_db()
created = seed_samples()
print("Created: " + ", ".join(created) if created else "Nothing to do -- every sample board already exists.")
