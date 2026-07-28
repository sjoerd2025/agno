# Cookbook: sandbox runner & processors

This directory contains small examples and guidance for adding processors and running tests in an isolated sandbox.

Files included:
- sandbox_runner.py — Docker-based sandbox runner (no network by default).
- sample_processor.py — Example processor class.

Quickstart
1. Configure environment:
   - REPOS_DIR=/repos
   - PROCESSORS=files.cookbook.sample_processor.SampleProcessor
   - ALLOWED_TEST_REPOS=owner/repo1,repo2
   - SANDBOX_IMAGE=python:3.11-slim
   - TEST_CMD=pytest -q

2. Start services (local dev):
   docker-compose up --build

3. Create a task:
   curl -X POST "http://localhost:8080/tasks" -H "Content-Type: application/json" -d '{"repo":"/repos/myrepo","task_name":"test","prompt":"run tests"}'

Security notes
- The sandbox runner launches Docker containers on the host. For production deployments prefer orchestrator jobs (Kubernetes) with resource limits and NetworkPolicies.
- Use ALLOWED_TEST_REPOS plus per-task approval to reduce risk.
- Set REQUIRE_TEST_APPROVAL=true and provide ADMIN_TOKEN env var to enforce per-task approval gate.
- Set ALLOWED_TEST_REPOS to a comma-separated list to restrict which repos can run tests (e.g., owner/repo1,repo2).

Environment variables
- ALLOWED_TEST_REPOS — comma-separated list of allowed repos (owner/repo or repo name).
- REQUIRE_TEST_APPROVAL — "true" to enforce per-task approval; requires ADMIN_TOKEN env var.
- ADMIN_TOKEN — secret token for POST /tasks/{task_uuid}/approve endpoint.
- SANDBOX_IMAGE — Docker image for sandbox (default: python:3.11-slim).
- TEST_CMD — command to run in sandbox (default: pytest -q).
- SANDBOX_TIMEOUT — timeout in seconds (default: 300).
