import argparse
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.logging_config import configure_logging
from app.core.config import get_settings
from app.services.ingestion import ingest

def main():
    configure_logging()
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Ingest the legal dataset into ChromaDB.")
    parser.add_argument("--source", default=settings.dataset_path, help="JSONL or Parquet source file")
    parser.add_argument("--reset", action="store_true", help="Delete and rebuild the Chroma collection")
    args = parser.parse_args()
    report = ingest(args.source, reset=args.reset)
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
