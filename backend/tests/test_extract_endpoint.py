"""/api/extract: what the page pre-fills while the student pastes. No search, no network."""
from fastapi.testclient import TestClient

import app.pipeline as pl
from app.main import app
from app.samples import SAMPLES

client = TestClient(app)


def detect(text):
    r = client.post("/api/extract", json={"offer_text": text})
    assert r.status_code == 200
    return r.json()


def test_detects_company_sender_and_role_from_the_sample_offers():
    d = detect(SAMPLES["IMPERSONATION"]["offer_text"])
    assert d == {"company": "Tata Consultancy Services", "sender_email": "hr@tcs-careers-india.in", "role": "Associate Software Engineer"}
    d = detect(SAMPLES["GENUINE_BIG_BRAND"]["offer_text"])
    assert d["company"] == "Infosys Limited" and d["sender_email"] == "campus@infosys.com"


def test_a_subject_line_and_signature_are_used():
    d = detect("Wipro | Internship Program Registration Open\nFrom: HR <hr@inspire.example>\nDear Students, registrations are open now.")
    assert d["company"] == "Wipro" and d["sender_email"] == "hr@inspire.example"


def test_short_or_empty_text_detects_nothing_and_does_not_error():
    assert detect("") == {"company": None, "sender_email": None, "role": None}
    assert detect("hello") == {"company": None, "sender_email": None, "role": None}


def test_the_text_is_redacted_first_and_the_recipients_own_address_is_not_the_sender():
    d = detect("Dear student@college.edu\nGreetings from Acme Corp. Aadhaar 1234 5678 9012. Write to hr@acme.example for details.")
    assert d["sender_email"] == "hr@acme.example"
    assert "1234" not in str(d)


def test_it_never_searches_or_makes_an_http_request(monkeypatch):
    import requests
    import serpapi

    calls = []

    def boom(*a, **k):
        calls.append(a)
        raise AssertionError("a search or HTTP request was made")

    monkeypatch.setattr(pl, "Serp", boom)  # any search would construct one
    monkeypatch.setattr(serpapi, "Client", boom)
    monkeypatch.setattr(requests.sessions.Session, "request", boom)
    assert detect(SAMPLES["SCAM_FEE"]["offer_text"])["company"] == "Nexora Global Solutions"
    assert not calls


def test_over_the_length_limit_is_rejected_like_a_check():
    assert client.post("/api/extract", json={"offer_text": "x" * 10_001}).status_code == 422
