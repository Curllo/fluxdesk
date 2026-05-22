import asyncio
import gc
import logging
import time
from typing import Optional

import litellm

logger = logging.getLogger("fluxdesk")

HIBERNATE_AFTER_SECONDS = 30 * 60  # 30 minutes
CHECK_INTERVAL_SECONDS = 60


class IdleManager:
    """Tracks last request time and triggers memory cleanup after 30 minutes of inactivity."""

    def __init__(self):
        self.last_activity = time.time()
        self._is_hibernating = False
        self._monitor_task: Optional[asyncio.Task] = None

    def record_activity(self):
        """Update the last-activity timestamp and wake if hibernating."""
        self.last_activity = time.time()
        if self._is_hibernating:
            self.wake()

    def start_monitoring(self):
        """Start a background asyncio task that checks for inactivity every 60 seconds."""
        if self._monitor_task is not None:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.warning("No running event loop; idle monitoring not started.")
            return
        self._monitor_task = loop.create_task(self._monitor_loop())

    async def _monitor_loop(self):
        while True:
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)
            now = time.time()
            if now - self.last_activity > HIBERNATE_AFTER_SECONDS and not self._is_hibernating:
                self._hibernate()

    def _hibernate(self):
        """Run garbage collection, clear LiteLLM caches, and set the hibernating flag."""
        gc.collect()
        logger.info("Idle hibernate triggered, memory released")
        try:
            litellm.cache = None
        except Exception:
            pass
        self._is_hibernating = True

    def wake(self):
        """Wake from hibernation if currently hibernating."""
        if self._is_hibernating:
            logger.info("Waking from hibernate")
            self._is_hibernating = False
        self.last_activity = time.time()

    def is_hibernating(self) -> bool:
        """Return whether the system is currently hibernating."""
        return self._is_hibernating

    def stop_monitoring(self):
        """Cancel the background monitoring task."""
        if self._monitor_task is not None:
            self._monitor_task.cancel()
            self._monitor_task = None


# Module-level singleton
_idle_manager: Optional[IdleManager] = None


def get_idle_manager() -> IdleManager:
    """Return the shared IdleManager singleton."""
    global _idle_manager
    if _idle_manager is None:
        _idle_manager = IdleManager()
    return _idle_manager
