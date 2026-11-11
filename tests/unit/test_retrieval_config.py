"""Settings validation for retrieval/auth options."""

import pytest
from pydantic import ValidationError

from src.config import Settings


def test_defaults():
    s = Settings(_env_file=None)
    assert s.RETRIEVAL_MODE == "hybrid" and s.VECTOR_STORE == "weaviate" and s.AUTH_ENABLED is True


@pytest.mark.parametrize("field,value", [("RETRIEVAL_MODE", "fuzzy"), ("VECTOR_STORE", "pinecone"), ("EMBEDDER", "openai")])
def test_invalid_values_rejected(field, value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field: value})


def test_values_are_normalised():
    assert Settings(_env_file=None, RETRIEVAL_MODE=" Keyword ").RETRIEVAL_MODE == "keyword"
