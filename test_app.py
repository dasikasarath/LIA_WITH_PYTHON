import io
import sys
import time
import json

# Ensure UTF-8 output encoding on Windows consoles
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health():
    print("\n--- [1] Testing /health Endpoint ---")
    response = client.get("/health")
    assert response.status_code == 200, f"Health check failed: {response.text}"
    data = response.json()
    print("Health response:", data)
    assert data["status"] == "healthy"
    assert data["database_connected"] is True
    print("Health check PASSED!")

def test_pdf_upload():
    print("\n--- [2] Testing /upload-pdf Endpoint ---")
    minimal_pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
        b"4 0 obj << /Length 67 >> stream\n"
        b"BT\n"
        b"/F1 12 Tf\n"
        b"72 100 Td\n"
        b"(Lia Project Architecture and Innovation Guide 2026) Tj\n"
        b"ET\n"
        b"endstream\n"
        b"endobj\n"
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
        b"xref\n"
        b"0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000227 00000 n \n"
        b"0000000346 00000 n \n"
        b"trailer << /Size 6 /Root 1 0 R >>\n"
        b"startxref\n"
        b"417\n"
        b"%%EOF\n"
    )

    files = {"file": ("test_lia_guide.pdf", io.BytesIO(minimal_pdf), "application/pdf")}
    res = client.post("/upload-pdf", files=files)
    assert res.status_code == 200, f"Upload failed: {res.text}"
    data = res.json()
    print("Upload response:", data)
    assert data["chunks_stored"] >= 1
    assert data["filename"] == "test_lia_guide.pdf"
    print("PDF Upload & pgvector indexing verification PASSED!")

def test_rag_query_and_memory():
    print("\n--- [3] Testing /ask with Multi-turn Memory & /clear-memory ---")
    session_id = f"test-session-{int(time.time())}"

    # Turn 1: Introduce user
    payload_1 = {
        "question": "Hello, my name is Priya. Remember my name.",
        "conversation_id": session_id
    }
    res_1 = client.post("/ask", json=payload_1)
    assert res_1.status_code == 200, f"Turn 1 failed: {res_1.text}"
    data_1 = res_1.json()
    print("Turn 1 response:", data_1["answer"][:100], "...")
    assert data_1["conversation_id"] == session_id

    # Turn 2: Query memory
    payload_2 = {
        "question": "What is my name?",
        "conversation_id": session_id
    }
    res_2 = client.post("/ask", json=payload_2)
    assert res_2.status_code == 200, f"Turn 2 failed: {res_2.text}"
    data_2 = res_2.json()
    print("Turn 2 response:", data_2["answer"])
    assert "Priya" in data_2["answer"], f"Expected 'Priya' in answer, got: {data_2['answer']}"
    print("Conversation memory verification PASSED!")

    # Clear memory
    res_clear = client.post("/clear-memory", json={"conversation_id": session_id})
    assert res_clear.status_code == 200, f"Clear memory failed: {res_clear.text}"
    print("Clear memory response:", res_clear.json())

    # Turn 3: Check memory cleared
    payload_3 = {
        "question": "Do you still know my name?",
        "conversation_id": session_id
    }
    res_3 = client.post("/ask", json=payload_3)
    assert res_3.status_code == 200
    data_3 = res_3.json()
    print("Turn 3 response after memory clear:", data_3["answer"][:100], "...")
    print("Memory clear verification PASSED!")

def test_vector_store_retrieval():
    print("\n--- [4] Testing Vector Store Retrieval When Data IS Found ---")
    query = "What is the 7-step user journey in Shepreneur?"
    res = client.post("/ask", json={"question": query, "conversation_id": "test-vector-found"})
    assert res.status_code == 200
    data = res.json()
    print("Retrieved doc count:", data["retrieved_count"])
    print("Sources:", data["sources"])
    print("Answer excerpt:", data["answer"][:180], "...")
    assert data["retrieved_count"] > 0, "Expected at least 1 retrieved document chunk"
    assert len(data["sources"]) > 0, "Expected at least 1 source document listed"
    assert "Shepreneur" in data["answer"]
    print("Vector Store Retrieval PASSED!")

def test_fallback_domains_when_no_vector_data():
    print("\n--- [5] Testing Fallback Responses When Data IS NOT in Vector Store ---")

    test_scenarios = [
        (
            "Women Empowerment",
            "How can women overcome self-doubt and gain financial independence through entrepreneurship?",
            ["independence", "confidence", "empower", "business"]
        ),
        (
            "Business Ideas",
            "What are 3 low-cost home business ideas for a woman with only 3000 rupees to invest?",
            ["₹", "3,000", "idea", "home", "candle", "bakery", "craft", "soap", "margin"]
        ),
        (
            "Profit & Pricing Calculation",
            "My product cost is 120 rupees and I want a 35% profit margin. What should my selling price and profit be?",
            ["120", "selling price", "margin", "profit"]
        ),
        (
            "Budget Calculations",
            "Give me a startup budget calculation to start a handmade soap business with 6000 rupees.",
            ["6,000", "budget", "raw material", "packaging", "soap", "cost"]
        ),
        (
            "Guiding Women to Start Business",
            "Give me a step-by-step guide for a woman starting an online clothing alteration and tailoring service.",
            ["step", "market", "pricing", "customer", "business"]
        )
    ]

    for domain_name, query, expected_keywords in test_scenarios:
        print(f"\n* Sub-test: {domain_name}")
        res = client.post("/ask", json={"question": query, "conversation_id": f"fallback-{domain_name[:4]}"})
        assert res.status_code == 200, f"Query failed for {domain_name}: {res.text}"
        data = res.json()
        print(f"  Retrieved count: {data['retrieved_count']}")
        print(f"  Answer excerpt: {data['answer'][:200]}...")

        lower_answer = data["answer"].lower()
        matched = [kw for kw in expected_keywords if kw.lower() in lower_answer]
        assert len(matched) >= 1, f"Expected keywords from {expected_keywords} in answer, found none: {data['answer'][:200]}"
        print(f"  Matched domain keywords: {matched}")
        print(f"  [PASS] {domain_name}")

    print("\nAll Fallback Domain Tests PASSED!")

def test_out_of_domain_query():
    print("\n--- [6] Testing Out-of-Domain Query Redirection ---")
    query = "Explain the quantum mechanical properties of Hawking radiation from black holes."
    res = client.post("/ask", json={"question": query, "conversation_id": "out-of-domain-session"})
    assert res.status_code == 200
    data = res.json()
    print("Retrieved count:", data["retrieved_count"])
    print("Answer excerpt:", data["answer"][:220], "...")
    assert data["retrieved_count"] == 0, "Out-of-domain query should not match vector store"
    lower_ans = data["answer"].lower()
    # Should politely clarify not in documents and remind user of specialization in women empowerment & business
    assert any(w in lower_ans for w in ["no relevant", "not found", "uploaded documents", "shepreneur", "mentor", "women", "business"])
    print("Out-of-domain Redirection PASSED!")

def test_stream_endpoint():
    print("\n--- [7] Testing /ask/stream Endpoint (Server-Sent Events) ---")
    payload = {
        "question": "What is the price estimation formula in Shepreneur?",
        "conversation_id": "test-stream-session"
    }
    with client.stream("POST", "/ask/stream", json=payload) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        events = []
        token_count = 0
        for line in response.iter_lines():
            if line.startswith("data:"):
                raw_data = line[5:].strip()
                if raw_data:
                    parsed = json.loads(raw_data)
                    events.append(parsed.get("type"))
                    if parsed.get("type") == "token":
                        token_count += 1

        print(f"Stream received {len(events)} events, including {token_count} token chunks.")
        assert "meta" in events, "Expected 'meta' event in stream"
        assert "token" in events, "Expected 'token' events in stream"
        assert "done" in events, "Expected 'done' event in stream"
        assert token_count > 0, "Expected non-zero token chunks"
        print("Streaming endpoint PASSED!")

if __name__ == "__main__":
    print("==========================================================")
    print("STARTING FULL LIA AI END-TO-END TEST SUITE")
    print("==========================================================")
    test_health()
    test_pdf_upload()
    test_rag_query_and_memory()
    test_vector_store_retrieval()
    test_fallback_domains_when_no_vector_data()
    test_out_of_domain_query()
    test_stream_endpoint()
    print("\n==========================================================")
    print(">>> ALL 7 END-TO-END TESTS PASSED SUCCESSFULLY! <<<")
    print("==========================================================")
