"""Direct retrieval verification test script."""

import sys
from pathlib import Path

project_dir = Path(__file__).resolve().parents[2]
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

from backend.app.rag.retriever import retrieve_documents


def test_retrieval():
    print("=== DIRECT RETRIEVAL TEST ===")
    query = "What is the total sales of the company?"
    results = retrieve_documents(query, limit=2)
    print(f"Query: {query}")
    print(f"Results count: {len(results)}")
    for idx, res in enumerate(results, start=1):
        print(f"\n--- Match {idx} ---")
        print(f"Source   : {res.get('metadata', {}).get('source')}")
        print(f"Distance : {res.get('distance')}")
        print(f"Text snippet: {res.get('text', '')[:200]}...")


if __name__ == "__main__":
    test_retrieval()
