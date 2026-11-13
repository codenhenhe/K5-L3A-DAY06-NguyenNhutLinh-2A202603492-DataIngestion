"""Ingest the Pro Git corpus and query the persisted index."""
import argparse
from importlib.metadata import version
import json
import logging
from pathlib import Path
from statistics import median
from time import perf_counter

from .chunking import by_paragraph, fixed_size
from .embeddings import E5Embedder
from .ingestion import load_jsonl, normalize_text
from .store import QdrantStore

STARTER = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = STARTER.parent / "data" / "progit-v2-en.jsonl"
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, default=STARTER / ".models")
    parser.add_argument("--store-dir", type=Path, default=STARTER / ".qdrant")
    parser.add_argument("--log-file", type=Path, default=STARTER / "results" / "pipeline.log")
    commands = parser.add_subparsers(dest="command", required=True)

    ingest = commands.add_parser("ingest", help="replace an index with the complete corpus")
    ingest.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    ingest.add_argument("--chunking", choices=("fixed", "paragraph"), default="fixed")
    ingest.add_argument("--size", type=int, default=500)
    ingest.add_argument("--overlap", type=int, default=50, help="used by fixed chunking")

    query = commands.add_parser("query", help="retrieve matching chunks")
    query.add_argument("text")
    query.add_argument("--chunking", choices=("fixed", "paragraph"), default="fixed")
    query.add_argument("--section", help="match the section metadata exactly")
    query.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()

    try:
        args.log_file.parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
            handlers=[logging.StreamHandler(), logging.FileHandler(args.log_file, encoding="utf-8")],
        )
        started = perf_counter()
        if args.command == "ingest":
            pages = load_jsonl(args.corpus)
            chunks = []
            for page in pages:
                if args.chunking == "fixed":
                    chunks.extend(fixed_size(page, args.size, args.overlap))
                else:
                    chunks.extend(by_paragraph(page, args.size))

        embedder = E5Embedder(args.model_dir)
        model_id = f"{embedder.model_name}@{embedder.revision}"
        if args.command == "ingest":
            vectors = embedder.embed_documents([chunk.text for chunk in chunks])
            with QdrantStore.open(args.store_dir, embedder.dimensions) as store:
                count = store.replace(args.chunking, chunks, vectors, model_id)
            lengths = [len(chunk.text) for chunk in chunks]
            result = {
                "corpus": str(args.corpus),
                "source_units": len(pages),
                "chunking": args.chunking,
                "size_chars": args.size,
                "overlap_chars": args.overlap if args.chunking == "fixed" else 0,
                "chunk_count": count,
                "chunk_chars": {
                    "min": min(lengths), "median": median(lengths),
                    "max": max(lengths), "total": sum(lengths),
                },
                "model": model_id,
                "dimensions": embedder.dimensions,
                "store": f"Qdrant local {version('qdrant-client')}",
                "metric": "cosine",
                "elapsed_seconds": round(perf_counter() - started, 3),
                "api_cost_usd": 0,
            }
            logger.info("ingest completed: %s", json.dumps(result, ensure_ascii=False))
        else:
            vector = embedder.embed_query(normalize_text(args.text))
            filters = {"section": args.section} if args.section is not None else None
            with QdrantStore.open(args.store_dir, embedder.dimensions) as store:
                result = store.search(args.chunking, vector, model_id, args.top_k, filters)

        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception:
        logger.exception("%s failed", args.command)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
