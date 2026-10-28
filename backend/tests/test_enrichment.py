import pytest
from unittest.mock import MagicMock, patch
from app.services.enrichment_service import EnrichmentService


def test_enrichment_not_configured_when_no_api_key():
    with patch("app.core.config.settings.GROQ_API_KEY", None):
        assert not EnrichmentService.is_configured()
        summary, err = EnrichmentService.generate_summary("Some text", "doc.txt")
        assert summary is None
        assert "not configured" in err.lower()

        facts, err = EnrichmentService.extract_facts([], "doc.txt")
        assert facts == []
        assert "not configured" in err.lower()


def test_enrichment_malformed_llm_json_handled_safely():
    with patch("app.core.config.settings.GROQ_API_KEY", "dummy_key"):
        with patch.object(EnrichmentService, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_choice = MagicMock()
            # Return invalid items that don't conform to schema
            mock_choice.message.content = '{"facts": [{"fact_type": "entity"}, {"invalid_field": 123}]}'
            mock_client.chat.completions.create.return_value.choices = [mock_choice]
            mock_get_client.return_value = mock_client

            chunks = [{"chunk_index": 0, "content": "Text", "source_location": {}}]
            facts, err = EnrichmentService.extract_facts(chunks, "test.txt")
            # Should safely reject malformed items without crashing
            assert isinstance(facts, list)


def test_enrichment_rate_limit_retries_and_graceful_fallback():
    with patch("app.core.config.settings.GROQ_API_KEY", "dummy_key"):
        with patch.object(EnrichmentService, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = Exception("Rate limit exceeded 429")
            mock_get_client.return_value = mock_client

            with patch("time.sleep"):  # avoid waiting in fast tests
                summary, err = EnrichmentService.generate_summary("Some text", "doc.txt")
                assert summary is None
                assert "Rate limit exceeded" in err

