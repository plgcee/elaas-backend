"""Thread-safe registry of deployment_id -> subprocess.Popen for hard cancel."""
import threading
import subprocess
import logging

logger = logging.getLogger(__name__)
_lock = threading.Lock()
_registry: dict[str, subprocess.Popen] = {}


def register(deployment_id: str, process: subprocess.Popen) -> None:
    with _lock:
        _registry[deployment_id] = process
        logger.debug(f"Registered process for deployment {deployment_id}")


def unregister(deployment_id: str) -> None:
    with _lock:
        _registry.pop(deployment_id, None)
        logger.debug(f"Unregistered deployment {deployment_id}")


def get_process(deployment_id: str) -> subprocess.Popen | None:
    with _lock:
        return _registry.get(deployment_id)


def terminate(deployment_id: str, wait_seconds: float = 3.0) -> bool:
    """Terminate process for deployment_id. Returns True if process was found and terminated."""
    with _lock:
        proc = _registry.get(deployment_id)
    if proc is None:
        return False
    try:
        proc.terminate()
        try:
            proc.wait(timeout=wait_seconds)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    except Exception as e:
        logger.warning(f"Error terminating deployment {deployment_id}: {e}")
    finally:
        unregister(deployment_id)
    return True
