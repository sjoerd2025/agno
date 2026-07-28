import os
import importlib
import asyncio
from typing import List, Any, Dict

from app.services.pubsub import publish_task_message
from app.services.sandbox_runner import run_tests_in_sandbox_async

try:
    # Optional DB model for approval checks (repo may define app.models.Task)
    from app.models import Task
    from sqlmodel import Session, select
    from app.db import get_engine
    DB_AVAILABLE = True
except Exception:
    DB_AVAILABLE = False


class Processor:
    """Base class for processors. Subclass and implement async process(...)."""
    async def process(self, task_uuid: str, repo_dir: str, task_name: str, result: Any, prompt: str) -> Dict:
        return {"result": result}


def _import_class(path: str):
    module_name, class_name = path.rsplit(".", 1)
    mod = importlib.import_module(module_name)
    return getattr(mod, class_name)


def load_processors() -> List[Processor]:
    """Load processors specified in PROCESSORS env var (comma-separated class paths)."""
    raw = os.getenv("PROCESSORS", "")
    if not raw:
        return []
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    inst = []
    for p in parts:
        try:
            cls = _import_class(p)
            inst.append(cls())
        except Exception as e:
            # best-effort: publish a message if pubsub is available
            try:
                asyncio.get_event_loop().create_task(publish_task_message("local", f"[processor_loader] failed to import {p}: {e}"))
            except Exception:
                pass
    return inst


async def _is_task_approved(task_uuid: str) -> bool:
    """Try to check DB Task.approved if DB available. If DB not present, default False."""
    if not DB_AVAILABLE:
        return False
    try:
        engine = get_engine()
        with Session(engine) as session:
            t = session.exec(select(Task).where(Task.task_uuid == task_uuid)).first()
            return bool(getattr(t, "approved", False))
    except Exception:
        return False


class RunTestsProcessor(Processor):
    """Processor that runs tests inside the sandbox runner.
    Respects ALLOWED_TEST_REPOS and REQUIRE_TEST_APPROVAL (per-task approval).
    """
    async def process(self, task_uuid: str, repo_dir: str, task_name: str, result: Any, prompt: str) -> Dict:
        # allowlist check
        allowed_raw = os.getenv("ALLOWED_TEST_REPOS", "")
        if allowed_raw:
            allowed = {p.strip() for p in allowed_raw.split(",") if p.strip()}
            repo_name = os.path.basename(repo_dir.rstrip("/"))
            if repo_name not in allowed and repo_dir not in allowed:
                await publish_task_message(task_uuid, f"[RunTestsProcessor] repo {repo_name} not in allowlist; skipping tests.")
                return {"result": result, "tests": {"skipped": True}}

        # approval check
        if os.getenv("REQUIRE_TEST_APPROVAL", "false").lower() in ("1", "true", "yes"):
            approved = await _is_task_approved(task_uuid)
            if not approved:
                await publish_task_message(task_uuid, "[RunTestsProcessor] task not approved for tests; skipping.")
                return {"result": result, "tests": {"skipped": True}}

        await publish_task_message(task_uuid, "[RunTestsProcessor] running tests in sandbox...")
        # run tests in sandbox (async wrapper)
        rc, output = await run_tests_in_sandbox_async(repo_dir, image=os.getenv("SANDBOX_IMAGE", "python:3.11-slim"), cmd=os.getenv("TEST_CMD", "pytest -q"), timeout=int(os.getenv("SANDBOX_TIMEOUT", "300")))
        if rc == 0:
            await publish_task_message(task_uuid, "[RunTestsProcessor] tests passed (sandbox).")
        else:
            await publish_task_message(task_uuid, f"[RunTestsProcessor] tests failed (sandbox) rc={rc}\n{output[:1000]}")
        return {"result": result, "tests": {"rc": rc, "output_snippet": output[:200]}}
