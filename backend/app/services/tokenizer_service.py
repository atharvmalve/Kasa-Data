from typing import List, Dict, Any, Optional
import logging
from app.core.config import settings

logger = logging.getLogger("kasa.tokenizer")

_tokenizer_instance = None
_tokenizer_error: Optional[str] = None


class TokenizerService:
    TOKENIZER_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    TOKENIZER_VERSION = "transformers-bert-wordpiece"
    TOKENIZER_REVISION = "main"
    MODEL_MAX_LENGTH = 512
    SPECIAL_TOKENS_COUNT = 2  # [CLS] and [SEP]
    EFFECTIVE_MAX_TOKENS = 510  # 512 - 2

    @classmethod
    def get_tokenizer(cls):
        global _tokenizer_instance, _tokenizer_error
        if _tokenizer_instance is not None:
            return _tokenizer_instance

        try:
            from transformers import AutoTokenizer
            _tokenizer_instance = AutoTokenizer.from_pretrained(cls.TOKENIZER_NAME)
            # Set high model_max_length on counting instance to prevent warnings when measuring entire document lengths
            _tokenizer_instance.model_max_length = int(1e9)
            logger.info(f"Loaded tokenizer: {cls.TOKENIZER_NAME} ({_tokenizer_instance.__class__.__name__})")
            return _tokenizer_instance
        except Exception as e:
            _tokenizer_error = str(e)
            logger.warning(f"Could not load HuggingFace AutoTokenizer '{cls.TOKENIZER_NAME}': {e}. Falling back to rule-based tokenizer.")
            return None

    @classmethod
    def count_tokens(cls, text: str) -> int:
        if not text:
            return 0
        tok = cls.get_tokenizer()
        if tok is not None:
            try:
                # Fast tokenization without special tokens
                tokens = tok.tokenize(text)
                return len(tokens)
            except Exception as e:
                logger.warning(f"Tokenizer error: {e}, using fallback")
        # Rule-based fallback: WordPiece approximation ~ 1.3 tokens per word
        words = text.split()
        return max(1, int(len(words) * 1.3))

    @classmethod
    def count_sequence_tokens(cls, text: str, add_special_tokens: bool = True) -> int:
        """Returns the full sequence length including special tokens ([CLS], [SEP]) when add_special_tokens=True."""
        base_count = cls.count_tokens(text)
        return (base_count + cls.SPECIAL_TOKENS_COUNT) if add_special_tokens else base_count

    @classmethod
    def tokenize(cls, text: str) -> List[str]:
        if not text:
            return []
        tok = cls.get_tokenizer()
        if tok is not None:
            try:
                return tok.tokenize(text)
            except Exception as e:
                logger.warning(f"Tokenizer error: {e}, using fallback")
        return text.split()

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        tok = cls.get_tokenizer()
        if tok is not None:
            return {
                "tokenizer_name": cls.TOKENIZER_NAME,
                "tokenizer_class": tok.__class__.__name__,
                "tokenizer_revision": cls.TOKENIZER_REVISION,
                "vocab_size": getattr(tok, "vocab_size", 30522),
                "model_max_length": getattr(tok, "model_max_length", cls.MODEL_MAX_LENGTH),
                "special_tokens_count": cls.SPECIAL_TOKENS_COUNT,
                "effective_max_tokens": cls.EFFECTIVE_MAX_TOKENS,
                "is_fallback": False,
            }
        return {
            "tokenizer_name": "rule-based-fallback",
            "tokenizer_class": "WhitespaceWordPieceApproximation",
            "tokenizer_revision": "fallback",
            "vocab_size": None,
            "model_max_length": cls.MODEL_MAX_LENGTH,
            "special_tokens_count": cls.SPECIAL_TOKENS_COUNT,
            "effective_max_tokens": cls.EFFECTIVE_MAX_TOKENS,
            "is_fallback": True,
            "error": _tokenizer_error,
        }
