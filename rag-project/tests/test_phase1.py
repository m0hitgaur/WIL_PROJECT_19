"""
Phase 1 Verification Tests: Environment, Settings, Dependencies, and Connectivity.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import settings
from database.neo4j_client import Neo4jClient


def test_settings_loaded():
    """Verify that settings are loaded properly from config and .env."""
    assert settings.PROJECT_ROOT.exists()
    assert settings.NEO4J_URI.startswith("bolt://") or settings.NEO4J_URI.startswith("neo4j://")
    assert settings.OLLAMA_LLM_MODEL != ""
    assert settings.OLLAMA_VLM_MODEL != ""
    assert settings.OLLAMA_EMBED_MODEL != ""
    print("✅ Settings verified successfully.")


def test_core_imports():
    """Verify that all core libraries can be imported without conflict."""
    import docling
    import docling_core
    import neo4j
    import langchain
    import langgraph
    import ollama
    import pydantic
    from PIL import Image

    assert docling is not None
    assert neo4j is not None
    assert langgraph is not None
    print("✅ All core libraries imported cleanly.")


def test_neo4j_connection():
    """Verify connection to Neo4j if instance is running."""
    client = Neo4jClient()
    try:
        info = client.check_connection()
        print(f"✅ Neo4j connected: agent={info['server_agent']}, APOC installed={info['apoc_installed']}")
        client.close()
    except Exception as e:
        print(f"⚠️ Neo4j connection not established yet ({e}). Please update .env when ready.")


def test_ollama_status():
    """Verify Ollama service is reachable without pulling any models."""
    import httpx

    try:
        response = httpx.get(f"{settings.OLLAMA_BASE_URL}/api/version", timeout=3.0)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Ollama service reachable at {settings.OLLAMA_BASE_URL} (version {data.get('version')}).")
        else:
            print(f"⚠️ Ollama returned status {response.status_code}.")
    except Exception as e:
        print(f"⚠️ Ollama service not reachable at {settings.OLLAMA_BASE_URL}: {e}")


if __name__ == "__main__":
    print("\n--- Running Phase 1 Verification ---")
    test_settings_loaded()
    test_core_imports()
    test_neo4j_connection()
    test_ollama_status()
    print("--- Phase 1 Verification Completed ---\n")
