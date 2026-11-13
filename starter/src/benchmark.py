"""Run controlled Pro Git retrieval experiments in separate dev and test phases."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
from statistics import median
from time import perf_counter

from .chunking import by_paragraph, fixed_size
from .embeddings import E5Embedder
from .evaluation import evaluate_query, summarize
from .ingestion import load_jsonl, normalize_text
from .run import DEFAULT_CORPUS, STARTER
from .store import QdrantStore

ROOT = STARTER.parent
QUESTIONS = ROOT / "benchmark" / "questions.jsonl"
STRATEGIES = {
    "A": {"index": "fixed", "size": 500, "overlap": 50, "filter": False,
          "hypothesis": "Overlap giữ lại bằng chứng gần ranh giới cửa sổ."},
    "B": {"index": "paragraph", "size": 500, "overlap": 0, "filter": False,
          "hypothesis": "Ranh giới theo tiêu đề và đoạn giúp giữ bằng chứng cùng ngữ cảnh."},
    "C": {"index": "paragraph", "size": 500, "overlap": 0, "filter": True,
          "hypothesis": "Lọc theo chương giảm kết quả ngoài phạm vi khi người hỏi chỉ định."},
}
SELECTION_RULE = ["Evidence Hit@3 (descending)", "Hit@1 (descending)",
                  "ingest_seconds (ascending)", "A, B, C"]


def write_json(path: Path, data: dict) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def build_indexes(store: QdrantStore, embedder: E5Embedder, model_id: str) -> dict:
    pages = load_jsonl(DEFAULT_CORPUS)
    indexes = {}
    for strategy in ("A", "B"):
        config = STRATEGIES[strategy]
        started = perf_counter()
        if strategy == "A":
            chunks = [chunk for page in pages for chunk in fixed_size(page, config["size"], config["overlap"])]
        else:
            chunks = [chunk for page in pages for chunk in by_paragraph(page, config["size"])]
        vectors = embedder.embed_documents([chunk.text for chunk in chunks])
        count = store.replace(config["index"], chunks, vectors, model_id)
        lengths = [len(chunk.text) for chunk in chunks]
        indexes[config["index"]] = {
            "chunks": count,
            "characters": {"min": min(lengths), "median": median(lengths),
                           "max": max(lengths), "total": sum(lengths)},
            "ingest_seconds": round(perf_counter() - started, 3),
        }
    return indexes


def run_split(store: QdrantStore, embedder: E5Embedder, model_id: str, split: str) -> tuple[list, dict]:
    questions = [
        row for row in map(json.loads, QUESTIONS.read_text(encoding="utf-8").splitlines())
        if row["split"] == split
    ]
    if len(questions) < {"dev": 15, "test": 5}[split]:
        raise ValueError(f"too few {split} questions")
    vectors = [embedder.embed_query(normalize_text(row["question"])) for row in questions]
    traces = []
    metrics = {}
    for strategy, config in STRATEGIES.items():
        rows = []
        for question, vector in zip(questions, vectors, strict=True):
            filters = question.get("filter") if config["filter"] else None
            hits = store.search(config["index"], vector, model_id, top_k=3, filters=filters)
            rows.append({"strategy": strategy, "applied_filter": filters, **evaluate_query(question, hits)})
        traces.extend(rows)
        metrics[strategy] = summarize(rows)
    return traces, metrics


def write_experiment_log(dev: dict, test: dict, lock: dict) -> None:
    path = ROOT / "artifacts" / "experiment_log.csv"
    fields = ("strategy", "chunking", "chunk_size", "overlap", "metadata", "filter",
              "vectorizer", "hypothesis", "dev_hit1", "dev_hit3", "test_hit1", "test_hit3", "notes")
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(fields)
        for strategy, config in STRATEGIES.items():
            index = lock["indexes"][config["index"]]
            scores = [
                f"{phase[strategy][metric]}/{phase[strategy]['questions']}"
                for phase in (dev, test) for metric in ("hit_at_1", "evidence_hit_at_3")
            ]
            notes = f"{index['chunks']} chunks, {index['ingest_seconds']} s ingest, 0 USD API"
            if strategy == "C":
                notes += ", shared index with B"
            if strategy == lock["selected"]:
                notes += ", selected on dev"
            writer.writerow([
                strategy, config["index"], config["size"], config["overlap"],
                "document_id/source/page/section/title/char_start/char_end",
                "exact section when specified" if config["filter"] else "off",
                lock["inputs"]["model"], config["hypothesis"], *scores, notes,
            ])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("split", choices=("dev", "test"))
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results")
    args = parser.parse_args()
    args.results_dir.mkdir(parents=True, exist_ok=True)
    lock_path = args.results_dir / "selection.json"
    traces_path = args.results_dir / f"{args.split}_traces.jsonl"
    metrics_path = args.results_dir / f"{args.split}_metrics.json"
    if args.split == "dev" and lock_path.exists():
        parser.error("selection already recorded; choose a fresh results directory for a new run")
    if args.split == "test" and not lock_path.is_file():
        parser.error("run dev and record selection.json before running test")

    embedder = E5Embedder(STARTER / ".models")
    model_id = f"{embedder.model_name}@{embedder.revision}"
    inputs = {
        "model": model_id,
        "dimensions": embedder.dimensions,
        "store": f"Qdrant local {version('qdrant-client')}",
        "runtime": f"ONNX Runtime {version('onnxruntime')}",
        "metric": "cosine exact",
        "top_k": 3,
        "corpus_sha256": hashlib.sha256(DEFAULT_CORPUS.read_bytes()).hexdigest(),
        "benchmark_sha256": hashlib.sha256(QUESTIONS.read_bytes()).hexdigest(),
        "strategies": STRATEGIES,
        "api_cost_usd": 0,
    }
    store_path = STARTER / ".qdrant" / hashlib.sha256(str(args.results_dir.resolve()).encode()).hexdigest()[:16]
    with QdrantStore.open(store_path, embedder.dimensions) as store:
        if args.split == "dev":
            indexes = build_indexes(store, embedder, model_id)
        else:
            lock = json.loads(lock_path.read_text(encoding="utf-8"))
            aliases = {alias.alias_name: alias.collection_name for alias in store.client.get_aliases().aliases}
            if lock["inputs"] != inputs or lock["aliases"] != aliases:
                raise ValueError("benchmark inputs or indexes differ from the dev selection")

        traces, metrics = run_split(store, embedder, model_id, args.split)
        traces_path.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in traces), encoding="utf-8",
        )
        write_json(metrics_path, metrics)
        if args.split == "dev":
            selected = min(STRATEGIES, key=lambda strategy: (
                -metrics[strategy]["evidence_hit_at_3"], -metrics[strategy]["hit_at_1"],
                indexes[STRATEGIES[strategy]["index"]]["ingest_seconds"], strategy,
            ))
            lock = {
                "selected": selected,
                "selected_at": datetime.now(timezone.utc).isoformat(),
                "selection_rule": SELECTION_RULE,
                "inputs": inputs,
                "indexes": indexes,
                "aliases": {alias.alias_name: alias.collection_name for alias in store.client.get_aliases().aliases},
                "dev_metrics": metrics,
            }
            write_json(lock_path, lock)
        elif args.results_dir.resolve() == ROOT / "results":
            write_experiment_log(lock["dev_metrics"], metrics, lock)

    print(json.dumps({"split": args.split, "selected_on_dev": lock["selected"], "metrics": metrics}, indent=2))


if __name__ == "__main__":
    main()
