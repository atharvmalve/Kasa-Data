import pytest
from unittest.mock import MagicMock, patch
from app.services.embedding_service import EmbeddingService
from app.core.config import settings


def test_embedding_dimension_validation():
    # Test that embed_texts returns 384 dimensions when mock model is used
    dummy_vec = [0.1] * settings.EMBEDDING_DIMENSION
    with patch.object(EmbeddingService, "get_model") as mock_get_model:
        mock_model = MagicMock()
        import numpy as np
        mock_model.encode.return_value = np.array([dummy_vec])
        mock_get_model.return_value = mock_model

        res = EmbeddingService.embed_texts(["Valid chunk text"])
        assert len(res) == 1
        assert len(res[0]) == 384


def test_embedding_dimension_mismatch_raises_error():
    # If the vector dimension does not match 384, an exception must be raised
    wrong_vec = [0.1] * 128
    with patch.object(EmbeddingService, "get_model") as mock_get_model:
        mock_model = MagicMock()
        import numpy as np
        mock_model.encode.return_value = np.array([wrong_vec])
        mock_get_model.return_value = mock_model

        with pytest.raises(ValueError, match="Expected embedding dimension 384"):
            EmbeddingService.embed_texts(["Valid chunk text"])


def test_embedding_empty_texts_handled():
    res = EmbeddingService.embed_texts([])
    assert res == []

