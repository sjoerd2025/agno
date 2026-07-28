from files.cookbook import sandbox_runner as cookbook_sandbox
import asyncio
from typing import Tuple

async def run_tests_in_sandbox_async(repo_dir: str, image: str = "python:3.11-slim", cmd: str = "pytest -q", timeout: int = 300) -> Tuple[int, str]:
    """Async wrapper around the cookbook sandbox runner.

    Runs the blocking sandbox runner in a thread to avoid blocking the event loop.
    """
    return await asyncio.to_thread(cookbook_sandbox.run_tests_in_sandbox, repo_dir, image, cmd, timeout)
