#!/usr/bin/env python3
"""Run and record one simulated survey from the command line, as the operator does with the two Apps.

    python3 tools/sim_record/record_run.py --world ~/worlds/<path>/<world> --trajectory <name> \\
        --sensor harbour_fast --name my_run [--rtf 2.0] [--range-m 18.4] [--range-at 62.6:39.0 ...]

What it does, in order (details: README.md next to this file):
  1. refuses to start if a simulation or a GCS is already running, or if the installed simulator is stale;
  2. the MCS App's own launcher starts the world with the chosen Sonar model and Slow-down; the boat holds at
     the origin because the survey path is not deployed yet;
  3. the GCS App (offscreen) starts its processing pipeline, START, Record ON;
  4. the path is deployed: the boat leaves, the whole path is in the recording;
  5. at each ``--range-at`` distance along the path the GCS's "Apply range" is used;
  6. at the last waypoint (or a stall, ``--stop-after-s``, ``--max-wall-min``, Ctrl-C): Record OFF, STOP,
     ``default`` on /blueboat/input_str, the launcher's own stop;
  7. ``<out>/<name>/run.json`` + logs; the session is where the GCS wrote it (``--session-name`` renames it).

Standard library only; the two drivers run in the workspace environment (``~/ros2_ws/env.sh``).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUPER = HERE.parents[1]
WS = Path.home() / "ros2_ws"
SIM_ROOT = SUPER / "BlueBoat-SSS-Sim/blueboat_sss_sim"
GCS_CWD = SUPER / "BlueBoat-SSS/blueboat_sss"            # where the owner starts the GCS: data root = ~/ros2_ws/data
TRAJ_DIR = Path.home() / ".config/blueboat_mcs/trajectories"
BUSY = r"gz sim|sss_sim_node|master_control|sss_processor_node|blueboat_gcs\.main|gcs_driver\.py|mcs_driver\.py"
READY = {"raycast": "ray-cast renderer ready", "geometric": "scene loaded"}
GROUND_TRUTH_TOPICS = ["/side_scan_sonar/ground_truth/contacts", "/side_scan_sonar/ground_truth/sensor"]


def env_cmd(cwd: Path, *argv: str) -> list[str]:
    """``argv`` in the workspace environment, started from ``cwd``."""
    return ["bash", "-c", f"cd {shlex.quote(str(WS))} && source env.sh >/dev/null 2>&1; "
                          f"cd {shlex.quote(str(cwd))} && exec {shlex.join(argv)}"]


def running() -> list[str]:
    out = subprocess.run(["pgrep", "-af", BUSY], capture_output=True, text=True).stdout.splitlines()
    return [ln for ln in out if "pgrep" not in ln and "record_run.py" not in ln]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_sensor(name: str) -> tuple[str, str]:
    """(renderer, profile path) of ``geometric``, a profile file, or a short name such as ``harbour_fast``."""
    if name == "geometric":
        return "geometric", ""
    p = Path(name).expanduser()
    if p.is_file():
        return "raycast", str(p.resolve())
    for d in (WS / "install/blueboat_sss_sim/share/blueboat_sss_sim/config", SIM_ROOT / "config"):
        f = d / f"raycast_{name}_sonar.yaml"
        if f.is_file():
            return "raycast", str(f)
    raise SystemExit(f"--sensor {name!r}: not 'geometric', a file, or config/raycast_<name>_sonar.yaml")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--world", type=Path, required=True, help="world folder (~/worlds/<path>/<world>)")
    ap.add_argument("--trajectory", required=True, help="MCS trajectory name or file (GPS-anchored)")
    ap.add_argument("--sensor", required=True, help="geometric | harbour_fast | harbour_live | fast | live | "
                                                    "default | <profile.yaml>")
    ap.add_argument("--name", required=True, help="run name: the folder under --out")
    ap.add_argument("--out", type=Path, default=WS / "sim_runs/recorded_runs")
    ap.add_argument("--rtf", type=float, default=1.0, help="Slow-down (Gazebo real-time factor)")
    ap.add_argument("--controller", default="MPC")
    ap.add_argument("--range-m", type=float, default=0.0, help="sonar range at the start (0 = the profile's)")
    ap.add_argument("--range-at", action="append", default=[], metavar="S_M:RANGE_M",
                    help="change the range at this distance along the path (repeatable)")
    ap.add_argument("--waves", default="", help="wave preset of the MCS launch dialog (rippled, harbour_chop, "
                                                "smooth ...); default calm")
    ap.add_argument("--waves-from", type=float, default=0.0, help="compass degrees the waves come from")
    ap.add_argument("--current", default="", help="current preset (weak, moderate ...); default none")
    ap.add_argument("--current-from", type=float, default=0.0, help="compass degrees the current comes from")
    ap.add_argument("--sea-seed", type=int, default=7, help="seed of the sea state (the dialog's default)")
    ap.add_argument("--sonar-seed", type=int, default=0, help="sensor-noise seed (0 = a fresh one, logged)")
    ap.add_argument("--max-wall-min", type=float, default=120.0)
    ap.add_argument("--stop-after-s", type=float, default=0.0, help="stop this many simulated s after leaving")
    ap.add_argument("--record-from-m", type=float, default=0.0,
                    help="Record ON this far along the path (after a lead-in); 0 = before the boat leaves")
    ap.add_argument("--session-name", default="", help="rename the session folder to this")
    ap.add_argument("--private-data-root", action="store_true",
                    help="write the session under the run folder instead of the GCS's data root")
    ap.add_argument("--ground-truth-bag", action="store_true",
                    help="also record the simulator's ground truth (contacts, sensor poses) into "
                         "<run>/ground_truth_bag, with the command of Perception's launch file; "
                         "blueboat-perception-offline --world --ground-truth-bag makes the labels from it")
    ap.add_argument("--allow-stale", action="store_true", help="run although the install is not the source tree")
    ap.add_argument("--extra", nargs="*", default=[], metavar="KEY:=VALUE", help="Extra launch args")
    a = ap.parse_args()

    world = a.world.expanduser().resolve()
    traj = Path(a.trajectory).expanduser()
    traj = traj if traj.is_file() else TRAJ_DIR / f"{a.trajectory}.yaml"
    if not (world / "metadata.yaml").is_file() or not traj.is_file():
        raise SystemExit(f"world or trajectory not found: {world} / {traj}")
    renderer, profile = resolve_sensor(a.sensor)
    out = a.out.expanduser().resolve() / a.name
    if out.exists():
        raise SystemExit(f"{out} exists: choose another --name")
    busy = running()
    if busy:
        raise SystemExit("a simulation or a GCS is already running; stop it first:\n  " + "\n  ".join(busy))
    prov = subprocess.run(env_cmd(SIM_ROOT, "python3", "-m", "blueboat_sss_sim.core.provenance", "--check"),
                          capture_output=True, text=True)
    prov_line = (prov.stdout.strip().splitlines() or [prov.stderr.strip()[-200:]])[-1]
    if prov.returncode != 0 and not a.allow_stale:
        raise SystemExit(f"the installed simulator is not the source tree ({prov_line}); rebuild, or --allow-stale")
    out.mkdir(parents=True)
    t0 = time.time()

    def say(s: str) -> None:
        line = f"{time.strftime('%H:%M:%S')} {s}"
        print(line, flush=True)
        with open(out / "run.log", "a") as f:
            f.write(line + "\n")

    extra = ["headless:=true", *a.extra]
    if a.range_m > 0:
        extra.append(f"range_length_mm:={int(round(a.range_m * 1000))}")
    if a.sonar_seed:
        extra.append(f"sonar_seed:={a.sonar_seed}")
    sea = [x for k, v in (("--waves", a.waves), ("--current", a.current)) if v for x in (k, v)]
    if sea:
        sea += ["--waves-from", str(a.waves_from), "--current-from", str(a.current_from),
                "--sea-seed", str(a.sea_seed)]
    say(f"world {world}; path {traj.name}; sensor {a.sensor} ({renderer}); rtf {a.rtf}; sea {sea or 'calm'}; "
        f"extra {extra}")
    mcs = subprocess.Popen(env_cmd(HERE, "python3", str(HERE / "mcs_driver.py"), "--out", str(out),
                                   "--world", str(world), "--trajectory", str(traj), "--rtf", str(a.rtf),
                                   "--controller", a.controller, "--renderer", renderer, "--profile", profile,
                                   "--note", a.name, *sea, *extra),
                           stdout=open(out / "mcs_driver.out", "w"), stderr=subprocess.STDOUT,
                           start_new_session=True)
    gpu = {"peak": 0, "stop": False}

    def sample_gpu() -> None:
        while not gpu["stop"]:
            r = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                               capture_output=True, text=True)
            if r.returncode == 0 and r.stdout.strip():
                v = int(r.stdout.split()[0])
                gpu["peak"] = max(gpu["peak"], v)
                with open(out / "gpu_mem.csv", "a") as f:
                    f.write(f"{time.strftime('%H:%M:%S')},{v}\n")
            time.sleep(5)

    threading.Thread(target=sample_gpu, daemon=True).start()
    signal.signal(signal.SIGINT, lambda *_: (out / "ABORT").touch())
    signal.signal(signal.SIGTERM, lambda *_: (out / "ABORT").touch())

    launch_log, status, gcs_rc, bag = out / "mcs_launch.log", "launch_failed", None, None
    deadline = time.time() + 900
    while time.time() < deadline and mcs.poll() is None and not (out / "ABORT").exists():
        if launch_log.exists() and READY[renderer] in launch_log.read_text(errors="replace"):
            status = "ready"
            break
        time.sleep(2)
    if status == "ready":
        say(f"simulation ready after {time.time() - t0:.0f} s; starting the GCS")
        cwd = GCS_CWD
        if a.private_data_root:
            cwd = out / "w/x/y/z"
            cwd.mkdir(parents=True)
        args = ["--out", str(out), "--max-wall-s", str(a.max_wall_min * 60 - (time.time() - t0)),
                "--stop-after-s", str(a.stop_after_s), "--record-from-m", str(a.record_from_m)]
        for r in a.range_at:
            args += ["--range-at", r]
        if a.ground_truth_bag:                               # the command of blueboat_perception's launch file
            bag = subprocess.Popen(env_cmd(out, "ros2", "bag", "record", "-o", str(out / "ground_truth_bag"),
                                           "--use-sim-time", "--topics", *GROUND_TRUTH_TOPICS),
                                   stdout=open(out / "ground_truth_bag.out", "w"), stderr=subprocess.STDOUT,
                                   start_new_session=True)
        gcs_rc = subprocess.run(env_cmd(cwd, "python3", str(HERE / "gcs_driver.py"), *args),
                                stdout=open(out / "gcs_driver.out", "w"), stderr=subprocess.STDOUT).returncode
        if bag is not None and bag.poll() is None:           # close the bag (its own process group, SIGINT)
            os.killpg(bag.pid, signal.SIGINT)
            try:
                bag.wait(timeout=30)
            except subprocess.TimeoutExpired:
                say("the ground-truth recorder did not close in 30 s: SIGTERM to its own process group")
                os.killpg(bag.pid, signal.SIGTERM)
                bag.wait(timeout=10)
    else:
        say(f"the simulation did not become ready (mcs driver {'died' if mcs.poll() is not None else 'timed out'})")

    # safe shutdown (CM-15, simulation branch): `default`, then the station's stop
    subprocess.run(env_cmd(HERE, "timeout", "10", "ros2", "topic", "pub", "--once", "/blueboat/input_str",
                           "std_msgs/msg/String", "{data: default}"), capture_output=True)
    (out / "STOP").touch()
    try:
        mcs.wait(timeout=60)
    except subprocess.TimeoutExpired:
        say("the MCS driver did not exit in 60 s: SIGTERM to its own process group")
        os.killpg(mcs.pid, signal.SIGTERM)
        mcs.wait(timeout=20)
    gpu["stop"] = True
    time.sleep(3)

    summary = json.loads((out / "gcs_summary.json").read_text()) if (out / "gcs_summary.json").exists() else {}
    text = launch_log.read_text(errors="replace") if launch_log.exists() else ""
    session = Path(summary["session"]) if summary.get("session") else None
    if session and session.exists() and a.session_name and summary.get("status") != "aborted":
        target = session.with_name(a.session_name)
        if target.exists():
            say(f"{target} exists: the session keeps its name {session.name}")
        else:
            session.rename(target)
            session = target
    run = {
        "name": a.name, "status": summary.get("status", status), "started": time.strftime(
            "%Y-%m-%dT%H:%M:%S", time.localtime(t0)), "wall_s": round(time.time() - t0, 1),
        "world": {"dir": str(world), "scene_manifest_sha256": sha256(world / "scene_manifest.yaml")},
        "trajectory": {"file": str(traj), "sha256": sha256(traj)},
        "sensor": {"name": a.sensor, "renderer": renderer, "profile": profile,
                   "profile_sha256": sha256(Path(profile)) if profile else None},
        "real_time_factor": a.rtf, "controller": a.controller, "range_start_m": a.range_m or None,
        "range_plan": a.range_at, "record_from_m": a.record_from_m, "extra_args": extra,
        "sea": ({"waves": a.waves or "calm", "waves_from_deg": a.waves_from, "current": a.current or "none",
                 "current_from_deg": a.current_from, "seed": a.sea_seed} if sea else "calm"),
        "sonar_seed": a.sonar_seed or None,
        "provenance": prov_line,
        "session": str(session) if session else None, "gcs": summary, "gcs_driver_exit": gcs_rc,
        "gpu_peak_mib": gpu["peak"],
        "ground_truth_bag": (str(out / "ground_truth_bag") if (out / "ground_truth_bag" / "metadata.yaml").exists()
                             else None),
        "launch_log_counts": {k: len(re.findall(p, text)) for k, p in {
            "render_failed": r"render failed", "behind_sim_clock": r"behind the sim clock",
            "process_died": r"process has died"}.items()},
        "left_running": running(),
    }
    (out / "run.json").write_text(json.dumps(run, indent=1))
    if session and session.exists():
        (session / "recorder_run.json").write_text(json.dumps(run, indent=1))
    say(f"{run['status']}: {summary.get('pings', 0)} pings, {summary.get('seabed_images', 0)} images, "
        f"session {session}, wall {run['wall_s']:.0f} s, GPU peak {gpu['peak']} MiB, "
        f"log counts {run['launch_log_counts']}")
    if run["left_running"]:
        say("still running (not started by this tool, or not yet gone):\n  " + "\n  ".join(run["left_running"]))
    return 0 if run["status"] in ("completed", "stop_after") else 1


if __name__ == "__main__":
    raise SystemExit(main())
