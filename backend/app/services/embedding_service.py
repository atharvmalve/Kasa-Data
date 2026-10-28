import time
import math
import json
from typing import List, Optional, Dict, Any, Tuple
import logging
from app.core.config import settings
from app.utils.hashing import compute_text_hash
from app.services.tokenizer_service import TokenizerService

logger = logging.getLogger("kasa.embedding")

_model_instance = None
_model_failed = False
_model_error_message: Optional[str] = None


class EmbeddingOutput:
    def __init__(
        self,
        vector: List[float],
        dimension: int,
        l2_norm: float,
        is_normalized: bool,
        input_hash: str,
        serialized_bytes: int,
        datatype: str = "float32",
        token_count: Optional[int] = None,
        effective_limit: int = TokenizerService.EFFECTIVE_MAX_TOKENS
    ):
        self.vector = vector
        self.dimension = dimension
        self.l2_norm = l2_norm
        self.is_normalized = is_normalized
        self.input_hash = input_hash
        self.serialized_bytes = serialized_bytes
        self.datatype = datatype
        self.token_count = token_count
        self.effective_limit = effective_limit


class EmbeddingService:
    @classmethod
    def get_model(cls):
        global _model_instance, _model_failed, _model_error_message
        if _model_instance is not None:
            return _model_instance
        if _model_failed:
            raise RuntimeError(f"Embedding model initialization previously failed: {_model_error_message}")

        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
            _model_instance = SentenceTransformer(settings.EMBEDDING_MODEL)
            # Configure maximum sequence length to the model's architectural capability (512)
            _model_instance.max_seq_length = TokenizerService.MODEL_MAX_LENGTH
            logger.info(f"Embedding model loaded successfully (max_seq_length={_model_instance.max_seq_length}).")
            return _model_instance
        except Exception as e:
            _model_failed = True
            _model_error_message = str(e)
            logger.error(f"Failed to initialize embedding model '{settings.EMBEDDING_MODEL}': {e}")
            raise RuntimeError(f"Could not load embedding model: {e}")

    @classmethod
    def embed_texts_with_metadata(
        cls, texts: List[str], batch_size: int = 32
    ) -> Tuple[List[Optional[EmbeddingOutput]], int]:
        """
        Generates 384-dimensional embeddings and calculates rich deterministic metadata.
        Fails safely if any input exceeds the effective sequence length limit of 510 tokens.
        Returns (list_of_outputs, total_latency_ms).
        """
        if not texts:
            return [], 0

        valid_indices = [i for i, t in enumerate(texts) if t and t.strip()]
        outputs: List[Optional[EmbeddingOutput]] = [None for _ in texts]
        if not valid_indices:
            return outputs, 0

        # Validate sequence lengths prior to passing to the model
        token_counts: Dict[int, int] = {}
        for orig_idx in valid_indices:
            t = texts[orig_idx]
            tok_count = TokenizerService.count_tokens(t)
            token_counts[orig_idx] = tok_count
            if tok_count > TokenizerService.EFFECTIVE_MAX_TOKENS:
                raise ValueError(
                    f"Chunk at index {orig_idx} has {tok_count} WordPiece tokens, which exceeds the effective safe "
                    f"embedding limit of {TokenizerService.EFFECTIVE_MAX_TOKENS} tokens "
                    f"(model max_seq_length {TokenizerService.MODEL_MAX_LENGTH} minus {TokenizerService.SPECIAL_TOKENS_COUNT} "
                    f"special tokens [CLS] and [SEP]). Oversized chunks must be split prior to embedding."
                )

        model = cls.get_model()
        valid_texts = [texts[i] for i in valid_indices]

        t0 = time.time()
        try:
            embeddings_matrix = model.encode(
                valid_texts,
                batch_size=batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise RuntimeError(f"Embedding inference failed: {e}")
        total_latency_ms = int((time.time() - t0) * 1000)

        for idx, orig_idx in enumerate(valid_indices):
            raw_vec = embeddings_matrix[idx]
            vec = [round(float(val), 6) for val in raw_vec]
            dim = len(vec)
            if dim != settings.EMBEDDING_DIMENSION:
                raise ValueError(
                    f"Expected embedding dimension {settings.EMBEDDING_DIMENSION}, got {dim}"
                )

            # Calculate L2 norm: sqrt(sum(x^2))
            l2_norm = math.sqrt(sum(x * x for x in vec))
            # Model normalized: norm should be ~ 1.0
            is_norm = abs(l2_norm - 1.0) < 0.05

            input_text = texts[orig_idx]
            input_hash = compute_text_hash(input_text)
            # Serialized size in JSONB array format
            serialized_json_bytes = len(json.dumps(vec).encode("utf-8"))

            outputs[orig_idx] = EmbeddingOutput(
                vector=vec,
                dimension=dim,
                l2_norm=round(l2_norm, 4),
                is_normalized=is_norm,
                input_hash=input_hash,
                serialized_bytes=serialized_json_bytes,
                datatype="float32",
                token_count=token_counts.get(orig_idx, 0),
                effective_limit=TokenizerService.EFFECTIVE_MAX_TOKENS
            )

        return outputs, total_latency_ms

        return outputs, total_latency_ms

    @classmethod
    def embed_texts(cls, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Legacy helper returning bare vectors for test compatibility."""
        outputs, _ = cls.embed_texts_with_metadata(texts, batch_size=batch_size)
        return [o.vector if o else [] for o in outputs]
