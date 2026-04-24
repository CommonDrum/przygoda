"""In-process locks guarding against concurrent generation requests for the
same project or page. Single-process uvicorn → in-memory dict is enough.

Pattern:
    async with project_busy(project_id):
        ...  # heavy work

If another request enters while the lock is held, `project_busy` raises
`ProjectBusyError` immediately (non-blocking) — the router converts it to HTTP
409. This prevents double-clicks from firing two parallel LLM/image pipelines.
"""

import asyncio
from contextlib import asynccontextmanager


class ProjectBusyError(RuntimeError):
    """Raised when a second caller tries to enter a project/page that is
    already being processed."""


# --- Per-project ---

_project_locks: dict[int, asyncio.Lock] = {}
_project_busy: set[int] = set()


def _get_project_lock(project_id: int) -> asyncio.Lock:
    lock = _project_locks.get(project_id)
    if lock is None:
        lock = asyncio.Lock()
        _project_locks[project_id] = lock
    return lock


def is_project_busy(project_id: int) -> bool:
    return project_id in _project_busy


@asynccontextmanager
async def project_busy(project_id: int):
    lock = _get_project_lock(project_id)
    if lock.locked() or project_id in _project_busy:
        raise ProjectBusyError(f"project {project_id} already busy")
    async with lock:
        _project_busy.add(project_id)
        try:
            yield
        finally:
            _project_busy.discard(project_id)


# --- Per-page (for single-image regen) ---

_page_locks: dict[int, asyncio.Lock] = {}
_page_busy: set[int] = set()


def _get_page_lock(page_id: int) -> asyncio.Lock:
    lock = _page_locks.get(page_id)
    if lock is None:
        lock = asyncio.Lock()
        _page_locks[page_id] = lock
    return lock


@asynccontextmanager
async def page_busy(page_id: int):
    lock = _get_page_lock(page_id)
    if lock.locked() or page_id in _page_busy:
        raise ProjectBusyError(f"page {page_id} already busy")
    async with lock:
        _page_busy.add(page_id)
        try:
            yield
        finally:
            _page_busy.discard(page_id)
