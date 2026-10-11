# Bulk Certificate Generator

A small backend API for generating certificates in bulk. You send a course name and a list of people, and it makes a PDF certificate for each valid person using one fixed template. You can check progress and download the PDFs afterwards.

Built with FastAPI, SQLAlchemy (SQLite) and ReportLab.

## Getting started

You need Python 3.10 or newer. I developed this on 3.14.

```bash
git clone https://github.com/Vasudha-kasu/certificate-generator.git
cd certificate-generator
python -m venv venv
```

Activate the virtual environment:

- Windows: `venv\Scripts\activate`
- Mac/Linux: `source venv/bin/activate`

Then install the packages and start the server:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs to try every endpoint from the browser. The database file (`certificates.db`) is created on the first run, and PDFs are saved in `generated/<job-id>/`.

## Running the tests

```bash
pytest -v
```

Every test gets its own temporary database and folder, so tests never touch real data.

## Using the API

There are three endpoints:

| Method | Path | What it does |
|---|---|---|
| POST | `/api/jobs/` | Start a bulk generation job |
| GET | `/api/jobs/{job_id}/` | Check progress and see results per person |
| GET | `/api/jobs/{job_id}/certificates/{certificate_id}/` | Download one PDF |

### 1. Submit a job

`POST /api/jobs/`

```json
{
  "course_name": "Python Backend Workshop",
  "recipients": [
    {"name": "Asha", "email": "asha@example.com"},
    {"name": "Ravi Kumar", "email": "not-an-email"}
  ]
}
```

You get back `202 Accepted` right away:

```json
{
  "id": "73f093c8-20a9-4d35-a419-cb9624d55288",
  "status": "PENDING",
  "total": 2,
  "succeeded": 0,
  "failed": 1,
  "created_at": "2026-10-11T06:41:09.221432"
}
```

Bad recipients (like the invalid email above) are already counted as failed. The valid ones are generated in the background.

### 2. Check progress

`GET /api/jobs/{job_id}/`

```json
{
  "id": "73f093c8-20a9-4d35-a419-cb9624d55288",
  "status": "COMPLETED",
  "total": 2,
  "succeeded": 1,
  "failed": 1,
  "created_at": "2026-10-11T06:41:09.221432",
  "certificates": [
    {
      "id": "3f785381-7600-45a2-80d2-349b919cb425",
      "recipient_name": "Asha Rao",
      "recipient_email": "asha@example.com",
      "status": "SUCCESS",
      "error_message": null
    },
    {
      "id": "7281b188-a72f-4f8f-a8af-29b1b75e2f60",
      "recipient_name": "Ravi Kumar",
      "recipient_email": "not-an-email",
      "status": "FAILED",
      "error_message": "email: value is not a valid email address: An email address must have an @-sign."
    }
  ]
}
```

A job is `PENDING`, `PROCESSING` or `COMPLETED`. Each certificate is `PENDING`, `SUCCESS` or `FAILED`. Keep calling this endpoint to watch the numbers change.

### 3. Download a certificate

`GET /api/jobs/{job_id}/certificates/{certificate_id}/` returns the PDF. You get a `404` if the certificate doesn't exist, belongs to another job, or failed to generate.

## How the code is organised

```
app/
  main.py               starts the app and registers the routes
  database.py           database connection and session
  models.py             Job and Certificate tables
  schemas.py            request and response shapes
  routers/jobs.py       the three endpoints
  services/
    processor.py        creates jobs, validates people, generates certificates
    pdf_generator.py    draws one certificate (knows nothing about the database)
tests/
  conftest.py           test database and test client setup
  test_jobs.py          tests for the main behaviours
```

## Why I built it this way

**Background processing.** One request could have hundreds of people, and making all those PDFs inside the request would leave the client waiting. So the API saves the job, replies immediately, and does the generation in a FastAPI background task. The client checks progress by calling the status endpoint. I thought about using Celery with Redis, which is sturdier, but it felt like too much setup for this size of project.

**Checking each recipient separately.** If I had declared the recipients as a validated list, one bad email would make FastAPI reject the whole request. That goes against the idea that one failure shouldn't stop the others. So the request only checks the basics (course name present, list not empty, at most 1000 people), and each recipient is validated one by one. Bad ones are saved as `FAILED` with a readable reason.

**Validate first, generate later.** Bad data is caught during the request, so the failed count is correct in the very first response. Only the slow part, drawing the PDFs, happens in the background.

**One failure doesn't stop the rest.** Each certificate is generated inside its own `try/except`. If one crashes, the error is saved on that certificate and the loop carries on. Progress is saved after every certificate, so the status stays accurate while the job runs.

**The background task opens its own database session.** The session used by the request is closed as soon as the response is sent, so the background task can't reuse it. I ran into this while planning the design.

**SQLite.** It's a real relational database with no setup. Switching to PostgreSQL later would mostly mean changing the connection URL.

**File safety.** PDFs are named after the certificate's random ID, never the person's name, so odd characters or a malicious name can't affect file paths. The API never shows server file paths. Downloads check both the certificate ID and the job ID, so you can't fetch a certificate through a different job's URL.

**The PDF code is separate.** `pdf_generator.py` only draws a PDF and knows nothing about jobs or databases. That made it easy to test on its own, and to fake a failure for one person in the tests. Very long names shrink to fit the page.

## What I learned

- Background tasks run after the response, so they need their own database session. Reusing the request's session is an easy bug to introduce.
- Validating a whole list at once is simpler, but it fights the requirement that one bad item shouldn't block the rest. Validating each item separately fixed that.
- Pytest's `monkeypatch` is useful for forcing a failure on purpose. That's how I tested that one broken certificate doesn't stop the others.

## Known limits and what I'd do next

- If the server stops in the middle of a job, that job stays `PROCESSING` forever. A task queue with retries, or a check on startup for stuck jobs, would fix this.
- The built-in PDF font only supports basic Latin characters, so names in scripts like Telugu or Hindi won't display correctly. A Unicode font such as Noto Sans would fix that.
- A "download everything as a zip" endpoint for a job.
- Pagination for the certificates list in large jobs.
- For production: authentication, rate limiting, PostgreSQL, database migrations (Alembic), and clearing out old generated files.
- A more flexible template (logo, signature, configurable text).