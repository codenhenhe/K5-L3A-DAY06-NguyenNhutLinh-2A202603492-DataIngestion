"""Persistent cosine retrieval using Qdrant local mode."""
from collections.abc import Iterator
from contextlib import contextmanager
import logging
import math
from pathlib import Path
from uuid import uuid4

from qdrant_client import QdrantClient, models

from .models import Chunk

logger = logging.getLogger(__name__)


class QdrantStore:
    def __init__(self, client: QdrantClient, dimensions: int) -> None:
        self.client = client
        self.dimensions = dimensions

    @classmethod
    @contextmanager
    def open(cls, path: Path, dimensions: int) -> Iterator["QdrantStore"]:
        client = QdrantClient(path=str(path))
        try:
            yield cls(client, dimensions)
        finally:
            client.close()

    def _validate_vector(self, vector: list[float]) -> None:
        if (len(vector) != self.dimensions or not all(map(math.isfinite, vector))
                or not any(vector)):
            raise ValueError(f"expected a finite nonzero vector of size {self.dimensions}")

    def replace(
        self, strategy: str, chunks: list[Chunk], vectors: list[list[float]], model_id: str,
    ) -> int:
        """Publish a full corpus snapshot only after all new points are stored."""
        if not chunks or len(chunks) != len(vectors):
            raise ValueError("expected one embedding per chunk and a nonempty corpus")
        if len({chunk.chunk_id for chunk in chunks}) != len(chunks):
            raise ValueError("duplicate chunk IDs")
        for vector in vectors:
            self._validate_vector(vector)

        alias = f"day06_{strategy}"
        previous = next(
            (item.collection_name for item in self.client.get_aliases().aliases
             if item.alias_name == alias),
            None,
        )
        collection = f"{alias}_{uuid4().hex}"
        self.client.create_collection(
            collection,
            vectors_config=models.VectorParams(size=self.dimensions, distance=models.Distance.COSINE),
            metadata={"model_id": model_id},
        )
        try:
            for start in range(0, len(chunks), 128):
                points = [
                    models.PointStruct(
                        id=chunk.chunk_id,
                        vector=vector,
                        payload={
                            **chunk.metadata, "document_id": chunk.document_id,
                            "source": chunk.source, "page": chunk.page, "text": chunk.text,
                        },
                    )
                    for chunk, vector in zip(chunks[start:start + 128], vectors[start:start + 128], strict=True)
                ]
                self.client.upsert(collection, points=points, wait=True)
            count = self.client.count(collection, exact=True).count
            if count != len(chunks):
                raise RuntimeError(f"stored {count} of {len(chunks)} chunks")
        except Exception:
            try:
                self.client.delete_collection(collection)
            except Exception:
                logger.exception("could not remove incomplete collection %s", collection)
            raise

        aliases = []
        if previous:
            aliases.append(models.DeleteAliasOperation(delete_alias=models.DeleteAlias(alias_name=alias)))
        aliases.append(models.CreateAliasOperation(create_alias=models.CreateAlias(
            collection_name=collection, alias_name=alias,
        )))
        if not self.client.update_collection_aliases(aliases):
            raise RuntimeError(f"could not publish collection {collection}")
        if previous:
            try:
                self.client.delete_collection(previous)
            except Exception:
                logger.exception("published %s but could not remove previous collection %s", alias, previous)
        return count

    def search(
        self, strategy: str, query_vector: list[float], model_id: str, top_k: int = 3,
        filters: dict[str, str] | None = None,
    ) -> list[dict]:
        self._validate_vector(query_vector)
        if top_k < 1:
            raise ValueError("top_k must be positive")
        collection = f"day06_{strategy}"
        if not self.client.collection_exists(collection):
            raise ValueError(f"index {collection} is missing. Run ingest first.")
        info = self.client.get_collection(collection)
        if (info.config.metadata or {}).get("model_id") != model_id:
            raise ValueError(f"index {collection} uses another embedding model. Run ingest again.")

        condition = None
        if filters:
            if set(filters) != {"section"} or not isinstance(filters["section"], str) or not filters["section"].strip():
                raise ValueError("the only supported filter is a nonempty section")
            condition = models.Filter(must=[
                models.FieldCondition(key="section", match=models.MatchValue(value=filters["section"])),
            ])
        result = self.client.query_points(
            collection, query=query_vector, query_filter=condition, limit=top_k,
            with_payload=True,
        )
        hits = []
        for point in result.points:
            metadata = dict(point.payload or {})
            hits.append({
                "chunk_id": str(point.id), "text": metadata.pop("text"),
                "score": point.score, "metadata": metadata,
            })
        return hits
