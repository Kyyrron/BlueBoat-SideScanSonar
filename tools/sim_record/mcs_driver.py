"""Run recorder, Mission Control Station side (started by ``record_run.py``; not meant to be run by hand).

Launches a personalized-world simulation exactly as the MCS App's Launch button does: the station's own
``LaunchManager.start`` with the ``LaunchParameters`` the launch dialog builds (world, controller, Sonar model,
Slow-down, sea state, Extra args), Perception companion included. Offscreen Qt; nothing is shown.

Two flag files in ``--out`` drive it:
  DEPLOY  the survey path is deployed into the world frame with the station's own ``io_yaml.deploy_mission``
          (the world's GPS anchor as the georeference). Until then ``path_generation`` holds the boat at the
          origin, so the recorder can be recording before the boat leaves. Answered with ``DEPLOYED``.
  STOP    the station's own ``LaunchManager.stop`` (SIGINT, then SIGTERM, then SIGKILL on its own process groups).
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
SUPER = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SUPER / "BlueBoat-MCS"))

import yaml                                             # noqa: E402
from PySide6.QtCore import QTimer                       # noqa: E402
from PySide6.QtWidgets import QApplication              # noqa: E402

from mcs.config.settings import AppConfig               # noqa: E402
from mcs.core.geo import GeoFit                         # noqa: E402
from mcs.core.sea import (CurrentSetting, SeaCatalog, SeaChoice, WaveSetting,   # noqa: E402
                          find_presets_file)
from mcs.core.signals import SignalBus                  # noqa: E402
from mcs.designer import io_yaml                        # noqa: E402
from mcs.ros.launch_manager import (RENDERER_GEOMETRIC, RENDERER_RAYCAST, LaunchManager,   # noqa: E402
                                    LaunchParameters, launch_target)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--world", type=Path, required=True)
    ap.add_argument("--trajectory", type=Path, required=True, help="designer file with a geo_anchor")
    ap.add_argument("--rtf", type=float, default=1.0)
    ap.add_argument("--controller", default="MPC")
    ap.add_argument("--profile", default="", help="sonar profile (absolute path); '' = geometric default")
    ap.add_argument("--renderer", default=RENDERER_RAYCAST, choices=(RENDERER_RAYCAST, RENDERER_GEOMETRIC))
    ap.add_argument("--note", default="recorded")
    ap.add_argument("--waves", default="", help="a wave preset of the launch dialog ('' = calm)")
    ap.add_argument("--waves-from", type=float, default=0.0)
    ap.add_argument("--current", default="", help="a current preset of the launch dialog ('' = none)")
    ap.add_argument("--current-from", type=float, default=0.0)
    ap.add_argument("--sea-seed", type=int, default=7)
    ap.add_argument("extra", nargs="*", help="Extra args, key:=value")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    log = open(a.out / "mcs_launch.log", "a", buffering=1)

    def say(s: str) -> None:
        log.write(f"{time.strftime('%H:%M:%S')} {s}\n")

    deployed = a.out / "deployed_path.yaml"
    for f in (deployed, a.out / "DEPLOYED"):
        f.unlink(missing_ok=True)
    anchor = yaml.safe_load((a.world / "metadata.yaml").read_text())["geo_anchor"]
    fit = GeoFit(tx=0.0, ty=0.0, lat0=float(anchor["lat0"]), lon0=float(anchor["lon0"]), rms_m=0.0, n_pairs=1)

    sea = None
    if a.waves or a.current:                             # the two cards of the dialog's sea-state page
        cat = SeaCatalog.load(find_presets_file())
        for kind, name in (("waves", a.waves), ("current", a.current)):
            if name and name not in getattr(cat, kind):
                raise SystemExit(f"--{kind} {name!r}: not one of {list(getattr(cat, kind))}")
        sea = SeaChoice(
            current=CurrentSetting(enabled=bool(a.current), from_deg=a.current_from,
                                   speed_mps=cat.number("current", a.current, "speed_mps")),
            waves=WaveSetting(enabled=bool(a.waves), level=a.waves or "calm", from_deg=a.waves_from),
            seed=a.sea_seed)
        sea.write_scenario(a.out, "sea_schedule")        # in the run folder, not the station's last_launch
        say(f"sea state: {sea.summary(cat)} (seed {a.sea_seed}) -> {sea.scenario_file}")

    app = QApplication(sys.argv[:1])
    cfg = AppConfig.load()
    bus = SignalBus()
    bus.launch_output.connect(say)
    lm = LaunchManager(cfg, bus)
    params = LaunchParameters(
        simulation=True, world_dir=str(a.world), gps_anchored_source=str(a.trajectory),
        gps_deployed_target=str(deployed), controller_type=a.controller, note=a.note,
        sonar_renderer=a.renderer, real_time_factor=a.rtf,
        sonar_profile=a.profile if a.renderer == RENDERER_RAYCAST else "", sea=sea,
        extra_args=dict(e.split(":=", 1) for e in a.extra))
    say(f"target {launch_target(cfg.launch, params)}; slowed {params.slowed()}")
    if not lm.start(params):
        say("START REFUSED")
        return 2
    st = {"stopping": None, "deployed": False}

    def tick() -> None:
        if not st["deployed"] and (a.out / "DEPLOY").exists():
            try:
                io_yaml.deploy_mission(a.trajectory, fit, deployed)
                (a.out / "DEPLOYED").touch()
                st["deployed"] = True
                say(f"path deployed -> {deployed}")
            except Exception as exc:                    # noqa: BLE001  (logged, retried on the next tick)
                say(f"deploy failed: {exc}")
        if st["stopping"] is None and (a.out / "STOP").exists():
            say("STOP requested: LaunchManager.stop()")
            st["stopping"] = time.time()
            lm.stop()
        if not lm.running:
            say(f"launch tree {'exited' if st['stopping'] else 'DIED on its own'}, state {lm.state}")
            timer.stop()
            QTimer.singleShot(3000 if st["stopping"] else 0, app.quit)

    timer = QTimer()
    timer.timeout.connect(tick)
    timer.start(500)
    app.exec()
    return 0 if st["stopping"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
