PRODUCTION & DEPLOYMENT PLAN
=============================

Purpose
-------
This document summarizes a minimal deploy approach and recommended production changes for the Produktoprettelse pipeline. It includes a concrete, low-risk "Option 1" implementation (job-id + status API) and time estimates assuming heavy AI-assisted development (pair-coding, code generation, testing help).

High-level answer (short)
-------------------------
- The scraper must run on the server/worker (not in the browser).
- For small scale you can: build one Docker container with the backend and the scraper runtime and mount persistent storage for `cache/`.
- For production/scale add a job queue + worker(s), persistent object storage (S3), auth/rate-limiting, and monitoring.

Minimal deploy (good for testing or a single-server internal tool)
-----------------------------------------------------------------
What you need:
- Docker image that bundles: Python deps, Playwright/Chromium or headless Chrome, and the backend code (FastAPI + scraper).
- Expose port 8000 and mount/attach a persistent volume for `cache/` so artifacts and thumbnails survive restarts.
- Frontend: build static assets (npm run build) and serve them from a simple static server (or keep Vite for dev only).

Pros: simple, fast to deliver. Cons: single point of failure; scaling or multi-instance sharing of cache will require additional work.

Production-grade pattern (recommended when public or >1 user)
------------------------------------------------------------
Add these components incrementally (each bullet can be staged):
- Job queue + worker(s) (Redis + RQ/Celery/Dramatiq): API enqueues jobs, worker runs scrapers in isolated containers.
- Object storage (S3) for images + JSON artifacts; serve via CDN or signed URLs.
- Auth & rate limiting (API keys / OAuth / JWT + rate limiter) to prevent abuse.
- Job status API (GET /jobs/{id}) or push notifications (SSE/WebSocket) to update frontend.
- Logging, metrics, and resource limits for workers (Kubernetes jobs or Docker with cgroup limits).

Option 1: Minimal improvement (recommended first step)
-----------------------------------------------------
Goal: make the backend return a job id for runs and expose a job-status API so the frontend can reliably track progress. This keeps the frontend unchanged logically and makes future move to queue/workers seamless.

Deliverables
- `POST /run-scraper` returns { job_id: "<uuid>", status: "queued" }
- `GET /jobs/{job_id}` returns job metadata: { job_id, status: queued|running|failed|done, started_at, finished_at, message }
- Background task updates job state (in-memory dict or small JSON file for now).
- Frontend: when user clicks Run, call POST, save job_id, poll GET /jobs/{job_id} until status==done then fetch /results and render.

AI-assisted time estimates (heavily AI-assisted)
-----------------------------------------------
Estimates assume an experienced developer using AI pair-programming (code generation, tests, PR scaffolding). The estimates show optimistic, realistic, and conservative durations and assume a working local environment and existing repo code.

Option 1 (job-id + polling) — Total: ~4–10 hours (AI-assisted)
- Backend: add job store + endpoints (2–4 hrs)
  - Implement job data structure, create UUID job ids, wire into existing background task, update on completion/failure (1.5–3 hrs).
  - Add small persistence fallback (write jobs to JSON) and basic cleanup (0.5–1 hr).
- Frontend: wire button to poll job endpoint and fetch results when done (1–2 hrs)
- Tests & QA: unit test job endpoints + manual E2E smoke test (1–2 hrs)
- Docs + README snippet + small migration notes (0.5–1 hr)

Minimal Dockerize & single-server deploy — Total: ~6–16 hours (AI-assisted)
- Dockerfile creation + test run (2–4 hrs)
- Add Playwright/Chromium system deps and verify headless scraping inside container (1–4 hrs)
- Configure persistent volume for `cache/` and test image serving (1–2 hrs)
- Build and run, smoke test, fix bugs (2–6 hrs)

Full production (queue + S3 + auth + monitoring) — Total: 2–4 weeks (AI-assisted)
- Architecting and implementing queue workers, containerized workers, secure artifact storage (S3), job metadata DB, auth, rate limiting, CI/CD, and k8s manifests (or Compose+supervisor). Heavy ops work and testing required.

Acceptance criteria (Option 1)
------------------------------
- POST /run-scraper returns job_id and immediate 200
- GET /jobs/{job_id} returns status transitions queued→running→done (or failed) and includes timestamps/messages
- Frontend triggers run, polls until done, then displays /results reliably.
- Images in `/results` are accessible under `/static/cache/...` or the configured storage
- Basic tests cover happy path and a failure path (mocked scraper error)

Risks and mitigations
---------------------
- Long scrape tasks may be killed if the container restarts — mitigate with queue+worker and persistent job state.
- OneDrive or synced filesystems may produce locking/permission errors — prefer server local disk or S3 in production.
- Scraper runtime size (Chromium) will make the Docker image large — use multi-stage builds and use Playwright's recommended base images.

Quick verification commands (dev)
---------------------------------
# Start backend
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Check basic endpoints
Invoke-RestMethod 'http://127.0.0.1:8000/'
Invoke-RestMethod 'http://127.0.0.1:8000/results' | ConvertTo-Json -Depth 5

# Trigger run (returns job id in Option 1)
Invoke-RestMethod -Method Post 'http://127.0.0.1:8000/run-scraper' | ConvertTo-Json -Depth 3

# Poll job status (replace JOB_ID with the returned id)
Invoke-RestMethod "http://127.0.0.1:8000/jobs/JOB_ID" | ConvertTo-Json -Depth 3

Next steps (I can implement now)
--------------------------------
- Implement Option 1 endpoints + frontend polling (fast, low risk). I estimate 4–10 hours as above. If you want, I can implement that change now: edit `backend/main.py`, add job store, update `run-scraper` to create a job id and update status, add `GET /jobs/{job_id}`, then modify `frontend/src/App.jsx` to poll.

Tell me: "Do Option 1" and I will implement it now and run quick smoke tests locally.

UI tweak: thumbnails
--------------------
I updated the frontend to prefer larger 150×150 thumbnails in the table view and added responsive fallbacks. This gives the images enough space to appear clearly in the UI. If you want a lightbox preview, I can add that next.

Git: committing and pushing
--------------------------
When you're ready to push these changes to GitHub, the sequence is:

1. Review and stage changes:
  git add frontend/src/App.jsx frontend/src/index.css backend/main.py PRODUCTION_PLAN.md

2. Commit:
  git commit -m "Add job-id polling, table UI and 150x150 thumbnails; update production plan"

3. Push:
  git push origin main

If you prefer I can create a feature branch and open a draft PR for you. Say "Create branch and PR" and I'll prepare it.