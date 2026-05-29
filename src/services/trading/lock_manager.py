"""PID lock manager — prevents multiple bot instances."""

import os
import subprocess

logger = None


def _get_logger():
    global logger
    if logger is None:
        from src.utils.logging import get_logger
        logger = get_logger(__name__)
    return logger


class LockManager:
    """Manages PID-based lock file to prevent duplicate bot instances."""

    def __init__(self, lock_file: str):
        self.lock_file = lock_file

    def acquire(self, bypass: bool = False) -> None:
        """Acquire the PID lock. Raises RuntimeError if another instance is running."""
        import sys
        if bypass:
            return
        is_testing = "pytest" in sys.modules or "unittest" in sys.modules
        if is_testing:
            return

        current_pid = os.getpid()
        if os.path.exists(self.lock_file):
            try:
                with open(self.lock_file, "r") as f:
                    old_pid_str = f.read().strip()
                if old_pid_str:
                    old_pid = int(old_pid_str)
                    if old_pid == current_pid:
                        return
                    out = subprocess.check_output(
                        f'tasklist /FI "PID eq {old_pid}"', shell=True, text=True
                    )
                    if str(old_pid) in out and "No tasks are running" not in out:
                        raise RuntimeError(
                            f"Another instance of the trading bot is already running (PID: {old_pid})."
                        )
            except (ValueError, subprocess.CalledProcessError):
                pass

        try:
            with open(self.lock_file, "w") as f:
                f.write(str(current_pid))
            _get_logger().info(f"Acquired PID lock for process {current_pid}")
        except Exception as e:
            _get_logger().warning(f"Could not create PID lock file: {e}")

    def release(self) -> None:
        """Release the PID lock if owned by the current process."""
        current_pid = os.getpid()
        if os.path.exists(self.lock_file):
            try:
                with open(self.lock_file, "r") as f:
                    old_pid_str = f.read().strip()
                if old_pid_str and int(old_pid_str) == current_pid:
                    os.remove(self.lock_file)
                    _get_logger().info("Released PID lock file")
            except Exception:
                pass
