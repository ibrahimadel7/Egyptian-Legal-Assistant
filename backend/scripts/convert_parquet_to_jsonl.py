import argparse
import json
from pathlib import Path
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description="Convert Parquet rows to UTF-8 JSONL.")
    parser.add_argument("source", help="Input Parquet file")
    parser.add_argument("destination", help="Output JSONL file")
    args = parser.parse_args()
    frame = pd.read_parquet(args.source)
    out = Path(args.destination)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        for record in frame.to_dict(orient="records"):
            handle.write(json.dumps(record, ensure_ascii=False) + "\\n")
    print(f"Converted {len(frame)} records to {out}")


if __name__ == "__main__":
    main()
