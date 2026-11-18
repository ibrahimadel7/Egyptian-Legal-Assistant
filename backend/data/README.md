# Dataset files

- `source.parquet`: original Parquet file supplied in the conversation; preserved unchanged.
- `legal_dataset_decoded.jsonl`: UTF-8 JSONL working copy available in the project workspace. It preserves the observed fields `law_name`, `categories`, `text`, and `tokens`.
- `dataset_profile.json`: basic profile computed from the decoded JSONL.

The ingestion pipeline defaults to JSONL so it does not need to read Parquet at runtime. To regenerate JSONL from the Parquet source, install requirements (including `pyarrow`) and run:

```bash
python scripts/convert_parquet_to_jsonl.py data/source.parquet data/legal_dataset_decoded.jsonl
```

Do not treat the presence of a record as proof that its legal content is current, authoritative, complete, or applicable. The inspected schema does not expose verified provenance/currentness metadata.

## Conversion caveat

The runtime used to assemble this ZIP did not have a Parquet engine installed and had no package-network access. The JSONL file was already present in the project workspace from earlier work, so it was used as the working corpus. The original uploaded Parquet is preserved unchanged, but row-for-row parity between that Parquet and the pre-existing JSONL could not be independently verified in this build. If exact parity matters, regenerate the JSONL from `source.parquet` using the included conversion script before indexing.
