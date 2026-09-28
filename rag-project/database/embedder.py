"""
Embedding Generator using Ollama.
Generates dense vector embeddings using the configured model (e.g. qwen3-embedding:4b).
"""

from typing import List, Optional
import logging
import ollama
from config import settings

logger = logging.getLogger(__name__)


class OllamaEmbedder:
    """Computes dense vector representations via Ollama API."""

    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        batch_size: int = 16,
    ):
        self.model = model or settings.OLLAMA_EMBED_MODEL
        self.client = ollama.Client(host=base_url or settings.OLLAMA_BASE_URL)
        self.batch_size = batch_size

    def embed_text(self, text: str) -> List[float]:
        """Generate vector embedding for a single text string."""
        cleaned_text = text.strip()
        if not cleaned_text:
            cleaned_text = "empty"
        
        response = self.client.embeddings(model=self.model, prompt=cleaned_text)
        return response["embedding"]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate vector embeddings for a list of text strings."""
        embeddings: List[List[float]] = []
        total = len(texts)
        for i in range(0, total, self.batch_size):
            batch = texts[i : i + self.batch_size]
            for text in batch:
                embeddings.append(self.embed_text(text))
        return embeddings


# Singleton instance
embedder = OllamaEmbedder()
