"""Acquisition pipeline lifecycle (bottom-toolbar START/STOP).

What START does (in order):
  1. spawn ``pipeline.launch_command`` — by default
     ``ros2 launch blueboat_sss SSS_processing_launch.py`` which starts
     *only* the processing pipeline (sss_processor_node). The application
     never launches sss_node.py: that node runs on the robot and this GUI
     only subscribes to the pipeline's outputs;
  2. after ``start_delay_s`` (processor node bring-up), publish ``true``
     on the ping-enable and svlog-enable topics if configured.

What STOP does:
  1. publish ``false`` on ping/svlog enable (stop firing immediately);
  2. SIGINT the launch process group (the signal ``ros2 launch`` expects
     for a clean child shutdown), escalate to SIGKILL after a grace
     period.

The subprocess is started in its own session so the whole launch tree is
signalled as a group. State is polled with a QTimer and broadcast on
``pipeline_state`` ("stopped" | "starting" | "running" | "error").
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
from typing import Optional

from PySide6.QtCore import QObject, QTimer

from ..config.settings import PipelineConfig
from ..core.signals import AppSignals
from .ros_manager import RosManager


class PipelineLauncher(QObject):
    """Owns the `ros2 launch` subprocess for the SSS processing pipeline."""

    def __init__(self, config: PipelineConfig, ros: RosManager,
                 signals: AppSignals) -> None:
        super().__init__()
        self._config = config
        self._ros = ros
        self._signals = signals
        self._proc: Optional[subprocess.Popen] = None
        self._stop_deadline: Optional[float] = None

        self._poll = QTimer(self)
        self._poll.setInterval(500)
        self._poll.timeout.connect(self._on_poll)

    # ---- API -----------------------------------------------------------------
    @property
    def running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self) -> None:
        if self.running:
            return
        cmd = list(self._config.launch_command)
        exe = cmd[0] if cmd else ""
        if shutil.which(exe) is None:
            msg = (f"[pipeline] '{exe}' not on PATH — is your ROS 2 environment "
                f"sourced in the shell that launched this app?")
            print(msg, file=sys.stderr, flush=True)
            self._signals.pipeline_state.emit("error")
            self._signals.status_message.emit(msg)
            return

        print(f"[pipeline] launching: {' '.join(cmd)}", file=sys.stderr, flush=True)
        self._signals.pipeline_state.emit("starting")
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=None,
                stderr=None,
                start_new_session=True,  # own process group for group SIGINT
            )
        except (OSError, FileNotFoundError) as exc:
            print(f"[pipeline] spawn failed: {exc!r}", file=sys.stderr, flush=True)
            self._signals.pipeline_state.emit("error")
            self._signals.status_message.emit(
                f"Failed to launch pipeline ({' '.join(cmd)}): {exc}")
            self._proc = None
            return
        self._poll.start()
        # Give the processor node time to come up before enabling pinging.
        self._enable_deadline = time.monotonic() + max(self._config.start_delay_s, 10.0)
        self._enable_timer = QTimer(self)
        self._enable_timer.setInterval(200)
        self._enable_timer.timeout.connect(self._try_enable)
        self._enable_timer.start()

    def _try_enable(self) -> None:
        if not self.running:
            self._enable_timer.stop()
            return
        ready = self._ros.svlog_enable_ready()   # sss_node has subscribed
        if ready or time.monotonic() > self._enable_deadline:
            self._enable_timer.stop()
            if not ready:
                print("[pipeline] svlog subscriber not seen before timeout — "
                    "enabling anyway", file=sys.stderr, flush=True)
            self._enable_acquisition()

    def _enable_acquisition(self) -> None:
        if not self.running:
            return
        if self._config.publish_ping_enable:
            self._ros.publish_ping_enable(True)
        if self._config.enable_svlog_on_start:
            self._ros.publish_svlog_enable(True)
        self._signals.pipeline_state.emit("running")
        self._signals.status_message.emit("Acquisition running.")

    def stop(self) -> None:
        if self._config.publish_ping_enable:
            self._ros.publish_ping_enable(False)
        if self._config.enable_svlog_on_start:
            self._ros.publish_svlog_enable(False)
        if not self.running:
            self._signals.pipeline_state.emit("stopped")
            return
        try:
            os.killpg(os.getpgid(self._proc.pid), signal.SIGINT)
        except (ProcessLookupError, PermissionError):
            pass
        self._stop_deadline = time.monotonic() + self._config.stop_grace_s

    # ---- polling ---------------------------------------------------------------
    def _on_poll(self) -> None:
        if self._proc is None:
            self._poll.stop()
            return
        code = self._proc.poll()
        if code is not None:
            was_stopping = self._stop_deadline is not None
            self._proc = None
            self._stop_deadline = None
            self._poll.stop()
            self._signals.pipeline_state.emit(
                "stopped" if (was_stopping or code == 0) else "error")
            if not was_stopping and code != 0:
                self._signals.status_message.emit(
                    f"Pipeline exited unexpectedly (code {code}).")
            return
        if (self._stop_deadline is not None
                and time.monotonic() > self._stop_deadline):
            try:  # graceful shutdown timed out — escalate
                os.killpg(os.getpgid(self._proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            self._stop_deadline = None
