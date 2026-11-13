"""Run recorder, GCS side (started by ``record_run.py``; not meant to be run by hand).

The BlueBoat GCS App assembled exactly as ``python -m blueboat_gcs.main`` does in ROS mode (RosManager,
PipelineLauncher with the Sonar selector on Simulation, the five listeners, MainWindow), offscreen, then operated
through the signals its own buttons emit:

  pipeline running -> START -> pings flowing -> Record ON -> (flag DEPLOY: the boat leaves)
     [--record-from-m S: the boat leaves first and Record ON comes S metres along the path, after a lead-in]
  -> along the path, "Apply range" at each --range-at distance
  -> end of the path (or --stop-after-s, a stall, the wall limit, flag ABORT) -> Record OFF -> STOP.

The session is written by the GCS itself, where the GCS writes it: ``<cwd>/../../../../data/SSS_data/sessions``
(its ``data_root``), so the working directory chooses the data root. The boat is followed on ``/blueboat/odom``
(a subscription on the GCS's own node; the App is not modified). Writes ``<out>/gcs_summary.json``.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
SUPER = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SUPER / "BlueBoat-SSS/blueboat_sss"))

import yaml                                                        # noqa: E402
from PySide6.QtCore import QTimer                                  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox            # noqa: E402

END_RADIUS_M = 2.5          # the last waypoint counts as reached inside this radius ...
END_SETTLE_S = 3.0          # ... after this much more simulated time
STALL_S, STALL_M = 90.0, 1.0   # simulated seconds without this much progress = a stall
SEARCH_AHEAD_M = 15.0       # progress is searched this far ahead of the last position (the path may cross itself)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--range-at", action="append", default=[], metavar="S_M:RANGE_M")
    ap.add_argument("--max-wall-s", type=float, default=7200.0)
    ap.add_argument("--stop-after-s", type=float, default=0.0, help="simulated seconds after the boat leaves")
    ap.add_argument("--record-from-m", type=float, default=0.0, help="Record ON this far along the path")
    a = ap.parse_args()
    out = a.out
    out.mkdir(parents=True, exist_ok=True)
    plan = sorted((float(s), float(r)) for s, r in (x.split(":") for x in a.range_at))
    log = open(out / "gcs_driver.log", "a", buffering=1)

    def say(s: str) -> None:
        log.write(f"{time.strftime('%H:%M:%S')} {s}\n")

    for name in ("information", "warning", "critical", "question"):     # no modal dialog may block offscreen
        setattr(QMessageBox, name, staticmethod(lambda *_a, **_k: QMessageBox.StandardButton.Ok))
    from blueboat_gcs.config.settings import load_config
    from blueboat_gcs.core import logging_bus
    from blueboat_gcs.core.mosaic_service import MosaicService
    from blueboat_gcs.core.signals import AppSignals
    from blueboat_gcs.gui.main_window import MainWindow
    from blueboat_gcs.ros import sonar_source as ss
    from blueboat_gcs.ros.detections_listener import DetectionsListener
    from blueboat_gcs.ros.path_listener import PathListener
    from blueboat_gcs.ros.pinger_listener import PingerListener
    from blueboat_gcs.ros.pipeline_launcher import PipelineLauncher
    from blueboat_gcs.ros.ros_manager import RosManager
    from blueboat_gcs.ros.sonar_listener import SonarListener
    from blueboat_gcs.ros.telemetry_listener import TelemetryListener

    config = load_config(None)
    app = QApplication(sys.argv[:1])
    signals = AppSignals()
    logging_bus.install(signals)
    signals.log_line.connect(lambda lvl, msg: log.write(f"[gcs {lvl}] {msg}\n"))
    signals.status_message.connect(lambda msg: log.write(f"[gcs status] {msg}\n"))
    mosaic = MosaicService(config)
    ros = RosManager(config, signals)
    acq = PipelineLauncher(config.pipeline, ros, signals, acquisition=config.acquisition,
                           sonar_source=ss.SIMULATION)
    if not (ros.start() and ros.node is not None):
        say("RosManager did not start")
        return 2
    node = ros.node
    ros.sonar_listener = SonarListener(
        node, signals, config.topics.processed_ping, queue_depth=config.sonar_stream.queue_depth,
        warn_on_ping_gap=config.sonar_stream.warn_on_ping_gap,
        profile_topics=(config.topics.port_profile, config.topics.starboard_profile),
        profile_queue_depth=config.sonar_stream.profile_queue_depth,
        profile_cache_per_side=config.sonar_stream.profile_cache_per_side,
        profile_wait_ms=config.sonar_stream.profile_wait_ms,
        nadir_blank_m=(config.depth.nadir_blank_m if config.depth.blank_nadir else 0.0))
    TelemetryListener(node, signals, config.topics, gps_fallback=config.alignment.gps_fallback)
    DetectionsListener(node, signals, config.topics.detections)
    PingerListener(node, signals, config.topics.pinger)
    ros.path_listener = PathListener(node, signals, config.topics.planned_path, config.planned_path)
    window = MainWindow(config, signals, mosaic, acq)
    window.show()

    # the boat, on the GCS's own node (best effort matches a reliable or a best-effort publisher)
    from nav_msgs.msg import Odometry
    from rclpy.qos import qos_profile_sensor_data
    boat = {"n": 0}

    def on_odom(m) -> None:
        boat.update(x=m.pose.pose.position.x, y=m.pose.pose.position.y,
                    t=m.header.stamp.sec + 1e-9 * m.header.stamp.nanosec, n=boat["n"] + 1)

    node.create_subscription(Odometry, config.topics.odom, on_odom, qos_profile_sensor_data)

    pings = {"n": 0}
    signals.sonar_ping.connect(lambda _p: pings.update(n=pings["n"] + 1))
    acq.start()
    say(f"pipeline start requested; data_root {Path(config.data_root).expanduser().resolve()}; range plan {plan}")
    st = dict(phase="wait_pipeline", t0=time.time(), t=time.time(), status="", session=None, idx=0,
              t_leave=None, t_end=None, track=[], ranges=[], prog_t=None, prog_s=0.0, p_at_record=0,
              recording=False, t_record=None)
    path = {}

    def load_path() -> None:
        pts = np.array(yaml.safe_load((out / "deployed_path.yaml").read_text())["points"], float)[:, 1:3]
        path.update(xy=pts, s=np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]))

    def progress() -> tuple[float, float]:
        """(distance along the path, cross-track distance) of the boat; the index only moves forward."""
        xy, s, i = path["xy"], path["s"], st["idx"]
        j = int(np.searchsorted(s, s[i] + SEARCH_AHEAD_M))
        d = np.hypot(xy[i:j + 1, 0] - boat["x"], xy[i:j + 1, 1] - boat["y"])
        k = int(np.argmin(d))
        st["idx"] = i + k
        return float(s[i + k]), float(d[k])

    def record_on() -> None:
        say(f"Record ON ({pings['n']} pings so far)")
        window.toolbar.record_toggled.emit(True)
        st.update(recording=True, p_at_record=pings["n"])

    def finish(status: str) -> None:
        if st["recording"]:
            say(f"Record OFF ({status}): {pings['n']} pings")
            window.toolbar.record_toggled.emit(False)
            st.update(phase="adopt", t=time.time(), status=status, recording=False)
        else:
            if st["phase"] != "wait_pipeline":           # pinging is on, nothing is being recorded
                window.toolbar.stop_clicked.emit()
            st.update(phase="stopping", t=time.time(), status=status)

    def tick() -> None:
        now, ph = time.time(), st["phase"]
        if ph not in ("adopt", "stopping", "quit"):
            if (out / "ABORT").exists():
                return finish("aborted")
            if now - st["t0"] > a.max_wall_s:
                return finish("wall_limit")
        if ph == "wait_pipeline":
            if acq.state.value == "running":
                say("pipeline running -> START")
                window.toolbar.start_clicked.emit()
                st.update(phase="started", t=now)
            elif now - st["t0"] > 180:
                say(f"pipeline never ran (state {acq.state.value})")
                finish("no_pipeline")
        elif ph == "started":
            if pings["n"] >= 10:
                if a.record_from_m > 0:                  # leave first, record from the real path's start
                    say("DEPLOY")
                    (out / "DEPLOY").touch()
                    st.update(phase="wait_deploy", t=now)
                else:
                    record_on()
                    st.update(phase="recording", t=now)
            elif now - st["t"] > 300:
                say("no pings 300 s after START")
                finish("no_pings")
        elif ph == "recording":
            if now - st["t"] > 3.0 and pings["n"] >= st["p_at_record"] + 5 and window.recording.session_dir:
                say("DEPLOY")
                (out / "DEPLOY").touch()
                st.update(phase="wait_deploy", t=now)
        elif ph == "wait_deploy":
            if (out / "DEPLOYED").exists() and boat["n"]:
                load_path()
                st.update(phase="running", t_leave=boat["t"], prog_t=boat["t"], prog_s=0.0)
                say(f"path deployed ({path['s'][-1]:.1f} m); the boat leaves at sim t {boat['t']:.1f} s")
            elif now - st["t"] > 60:
                say("path not deployed after 60 s")
                finish("no_deploy")
        elif ph == "running":
            s, xt = progress()
            t, L = boat["t"], float(path["s"][-1])
            if not st["recording"] and st["t_record"] is None and s >= a.record_from_m:
                record_on()
                st["t_record"] = t
            if st["recording"] and st["session"] is None and window.recording.session_dir:
                st["session"] = str(Path(window.recording.session_dir).resolve())
                say(f"session {st['session']}")
            st["track"].append((round(t - st["t_leave"], 2), round(boat["x"], 2), round(boat["y"], 2),
                                round(s, 2), round(xt, 2), int(st["recording"])))
            for k, (s_at, r_m) in enumerate(plan):
                if k == len(st["ranges"]) and s >= s_at and not getattr(acq, "_range_pending", False):
                    say(f"Apply range {r_m} m at {s:.1f} m along the path (sim t {t - st['t_leave']:.1f} s)")
                    window.right_panel.range_apply_requested.emit(float(r_m))
                    st["ranges"].append({"at_m": round(s, 1), "range_m": r_m, "sim_t_s": round(t - st["t_leave"], 1)})
            if s > st["prog_s"] + STALL_M:
                st.update(prog_s=s, prog_t=t)
            last = float(np.hypot(*(path["xy"][-1] - (boat["x"], boat["y"]))))
            if st["t_end"] is None and s >= 0.8 * L and last <= END_RADIUS_M:
                st["t_end"] = t
                say(f"last waypoint reached at sim t {t - st['t_leave']:.1f} s")
            if st["t_end"] is not None and t - st["t_end"] >= END_SETTLE_S:
                finish("completed")
            elif a.stop_after_s and t - st["t_leave"] >= a.stop_after_s:
                finish("stop_after")
            elif t - st["prog_t"] > STALL_S:
                say(f"no progress for {STALL_S:.0f} simulated s at {s:.1f} / {L:.1f} m")
                finish("stall")
            elif int(now) % 60 == 0 and now - st["t"] >= 1.0:
                st["t"] = now
                say(f"{s:.0f} / {L:.0f} m, cross-track {xt:.2f} m, {pings['n']} pings, sim t {t - st['t_leave']:.0f} s")
        elif ph == "adopt" and now - st["t"] > config.recording.adopt_delay_s + 5:
            say("STOP")
            window.toolbar.stop_clicked.emit()
            st.update(phase="stopping", t=now)
        elif ph == "stopping" and now - st["t"] > 5:
            st["phase"] = "quit"
        if st["phase"] == "quit":
            timer.stop()
            sd = Path(st["session"]) if st["session"] else None
            files = (sorted(str(p.relative_to(sd)) for p in sd.rglob("*") if p.is_file())
                     if sd and sd.exists() else [])
            tr = np.array(st["track"], float) if st["track"] else np.zeros((0, 6))
            rec = tr[tr[:, 5] > 0] if len(tr) else tr
            per_m = ([rec[np.floor(rec[:, 3]) == k, 4].mean() for k in np.unique(np.floor(rec[:, 3]))]
                     if len(rec) else [])
            summary = {
                "status": st["status"], "session": st["session"], "pings": pings["n"],
                "svlogs": [f for f in files if f.endswith(".svlog")],
                "seabed_images": sum(f.startswith("seabed_images/seabed_") and f.endswith(".png") for f in files),
                "files": len(files), "range_changes": st["ranges"],
                "path_length_m": round(float(path["s"][-1]), 1) if path else None,
                "path_covered_m": round(float(tr[:, 3].max()), 1) if len(tr) else 0.0,
                "recorded_from_m": round(float(rec[0, 3]), 1) if len(rec) else None,
                "sim_time_on_path_s": round(float(tr[-1, 0]), 1) if len(tr) else 0.0,
                "sim_time_recorded_s": round(float(rec[-1, 0] - rec[0, 0]), 1) if len(rec) else 0.0,
                # per metre of path, not per sample: the samples are taken in wall time and pile up
                # wherever the simulation runs slowly
                "cross_track_recorded_m": ({"p50": round(float(np.percentile(per_m, 50)), 2),
                                            "p90": round(float(np.percentile(per_m, 90)), 2),
                                            "max": round(float(rec[:, 4].max()), 2)} if len(rec) else None),
                "wall_s": round(time.time() - st["t0"], 1)}
            (out / "gcs_summary.json").write_text(json.dumps(summary, indent=1))
            if len(tr):
                np.savetxt(out / "boat_track.csv", tr, fmt="%.2f", delimiter=",",
                           header="sim_t_s,x,y,along_path_m,cross_track_m,recording", comments="")
            say(f"summary written: {summary['status']}, {summary['pings']} pings, {summary['seabed_images']} images")
            window.close()
            QTimer.singleShot(2000, app.quit)

    timer = QTimer()
    timer.timeout.connect(tick)
    timer.start(500)
    app.exec()
    ros.shutdown()
    logging_bus.uninstall()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
