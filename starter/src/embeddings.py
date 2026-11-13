"""Run multilingual E5 locally with the upstream ONNX weights."""
import hashlib
from pathlib import Path
from typing import Protocol

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_query(self, question: str) -> list[float]:
        ...


class E5Embedder:
    model_name = "intfloat/multilingual-e5-small"
    revision = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
    dimensions = 384
    max_tokens = 512

    def __init__(self, model_dir: Path) -> None:
        model = model_dir / "model.onnx"
        tokenizer = model_dir / "tokenizer.json"
        if not model.is_file() or not tokenizer.is_file():
            raise FileNotFoundError(f"E5 model files missing in {model_dir}. See starter/README.md.")
        expected_hashes = {
            model: "ca456c06b3a9505ddfd9131408916dd79290368331e7d76bb621f1cba6bc8665",
            tokenizer: "0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39",
        }
        for path, expected in expected_hashes.items():
            with path.open("rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
            if actual != expected:
                raise ValueError(f"{path}: SHA-256 differs from E5 revision {self.revision}")
        self.tokenizer = Tokenizer.from_file(str(tokenizer))
        self.tokenizer.no_truncation()
        self.tokenizer.enable_padding(pad_id=1, pad_token="<pad>")
        options = ort.SessionOptions()
        options.intra_op_num_threads = 4
        self.session = ort.InferenceSession(
            str(model), sess_options=options, providers=["CPUExecutionProvider"],
        )
        self.input_names = {item.name for item in self.session.get_inputs()}

    def _encode(self, texts: list[str], prefix: str) -> list[list[float]]:
        vectors = []
        for start in range(0, len(texts), 16):
            batch = self.tokenizer.encode_batch(
                [prefix + text for text in texts[start:start + 16]]
            )
            if len(batch[0].ids) > self.max_tokens:
                raise ValueError(f"E5 input in batch at position {start} exceeds {self.max_tokens} tokens")

            mask = np.asarray([row.attention_mask for row in batch], dtype=np.int64)
            inputs = {
                "input_ids": np.asarray([row.ids for row in batch], dtype=np.int64),
                "attention_mask": mask,
                "token_type_ids": np.asarray([row.type_ids for row in batch], dtype=np.int64),
            }
            hidden, = self.session.run(
                ["last_hidden_state"], {name: inputs[name] for name in self.input_names},
            )
            pooled = (hidden * mask[..., None]).sum(axis=1) / mask.sum(axis=1, keepdims=True)
            norms = np.linalg.norm(pooled, axis=1, keepdims=True)
            if not np.isfinite(pooled).all() or np.any(norms == 0):
                raise ValueError("E5 returned a non-finite or zero embedding")
            vectors.extend((pooled / norms).tolist())
        return vectors

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._encode(texts, "passage: ")

    def embed_query(self, question: str) -> list[float]:
        if not question.strip():
            raise ValueError("query must contain text")
        return self._encode([question], "query: ")[0]
