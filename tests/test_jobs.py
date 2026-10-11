from app.services import processor
from app.services.pdf_generator import generate_certificate

VALID_1 = {"name": "Asha Rao", "email": "asha@example.com"}
VALID_2 = {"name": "Ravi Kumar", "email": "ravi@example.com"}


def make_payload(recipients=None):
    return {
        "course_name": "Python Backend Workshop",
        "recipients": [VALID_1, VALID_2] if recipients is None else recipients,
    }


def submit(client, payload):
    response = client.post("/api/jobs/", json=payload)
    assert response.status_code == 202, response.text
    return response.json()


def fetch(client, job_id):
    response = client.get(f"/api/jobs/{job_id}/")
    assert response.status_code == 200, response.text
    return response.json()


# ---------- 1. Creating a generation job ----------

def test_create_job_returns_202_with_id_and_total(client):
    job = submit(client, make_payload())

    assert job["id"]
    assert job["total"] == 2
    assert job["failed"] == 0


# ---------- 2. Input validation ----------

def test_rejects_empty_recipient_list(client):
    response = client.post("/api/jobs/", json=make_payload(recipients=[]))
    assert response.status_code == 422


def test_rejects_missing_course_name(client):
    response = client.post("/api/jobs/", json={"recipients": [VALID_1]})
    assert response.status_code == 422


def test_invalid_recipients_are_marked_failed_not_rejected(client):
    payload = make_payload([
        VALID_1,
        {"name": "Bad Email", "email": "not-an-email"},
        {"name": "", "email": "empty@example.com"},
        {"name": "No Email"},
    ])
    job = submit(client, payload)
    detail = fetch(client, job["id"])

    assert detail["total"] == 4
    assert detail["succeeded"] == 1
    assert detail["failed"] == 3

    failed = [c for c in detail["certificates"] if c["status"] == "FAILED"]
    assert len(failed) == 3
    assert all(c["error_message"] for c in failed)


def test_job_with_only_invalid_recipients_completes_immediately(client):
    job = submit(client, make_payload([{"name": "X", "email": "bad"}]))

    assert job["status"] == "COMPLETED"
    assert job["failed"] == 1


# ---------- 3. Certificate generation ----------

def test_valid_recipient_gets_a_real_pdf(client):
    job = submit(client, make_payload())
    cert = fetch(client, job["id"])["certificates"][0]

    assert cert["status"] == "SUCCESS"
    assert "file_path" not in cert  # server paths must not leak

    response = client.get(f"/api/jobs/{job['id']}/certificates/{cert['id']}/")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_pdf_generator_handles_very_long_name_and_creates_folders(tmp_path):
    output = tmp_path / "nested" / "long.pdf"

    generate_certificate("A" * 100, "Some Course", "11 October 2026", str(output))

    assert output.exists()
    assert output.stat().st_size > 0


# ---------- 4. Job status / progress ----------

def test_job_status_and_counts_add_up(client):
    payload = make_payload([VALID_1, VALID_2, {"name": "Bad", "email": "nope"}])
    job = submit(client, payload)
    detail = fetch(client, job["id"])

    assert detail["status"] == "COMPLETED"
    assert detail["total"] == 3
    assert detail["succeeded"] == 2
    assert detail["failed"] == 1
    assert detail["succeeded"] + detail["failed"] == detail["total"]


def test_unknown_job_returns_404(client):
    response = client.get("/api/jobs/does-not-exist/")
    assert response.status_code == 404


# ---------- 5. One certificate failing must not stop the others ----------

def test_one_generation_failure_does_not_block_others(client, monkeypatch):
    real_generate = processor.generate_certificate

    def flaky_generate(name, course, issue_date, path):
        if name == "Broken Person":
            raise RuntimeError("simulated disk error")
        return real_generate(name, course, issue_date, path)

    monkeypatch.setattr(processor, "generate_certificate", flaky_generate)

    payload = make_payload([
        VALID_1,
        {"name": "Broken Person", "email": "broken@example.com"},
        VALID_2,
    ])
    job = submit(client, payload)
    detail = fetch(client, job["id"])
    by_name = {c["recipient_name"]: c for c in detail["certificates"]}

    assert detail["status"] == "COMPLETED"
    assert detail["succeeded"] == 2
    assert detail["failed"] == 1
    assert by_name["Broken Person"]["status"] == "FAILED"
    assert "simulated disk error" in by_name["Broken Person"]["error_message"]
    assert by_name["Asha Rao"]["status"] == "SUCCESS"
    assert by_name["Ravi Kumar"]["status"] == "SUCCESS"


# ---------- 6. Retrieving generated certificates ----------

def test_cannot_download_a_failed_certificate(client):
    job = submit(client, make_payload([VALID_1, {"name": "Bad", "email": "nope"}]))
    detail = fetch(client, job["id"])
    failed = next(c for c in detail["certificates"] if c["status"] == "FAILED")

    response = client.get(f"/api/jobs/{job['id']}/certificates/{failed['id']}/")
    assert response.status_code == 404


def test_unknown_certificate_returns_404(client):
    job = submit(client, make_payload())

    response = client.get(f"/api/jobs/{job['id']}/certificates/does-not-exist/")
    assert response.status_code == 404


def test_certificate_is_not_reachable_through_a_different_job(client):
    job_a = submit(client, make_payload())
    job_b = submit(client, make_payload())
    cert_a = fetch(client, job_a["id"])["certificates"][0]

    response = client.get(f"/api/jobs/{job_b['id']}/certificates/{cert_a['id']}/")
    assert response.status_code == 404