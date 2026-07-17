"""Mission library I/O.

Two files per mission, in ``designer.trajectories_dir``:

* ``<name>.yaml`` — the **runtime** trajectory: only what execution needs
  (format tag, speed, loop, time-stamped ``[t, x, y, yaw]`` samples plus
  informative length/duration). Consumed by
  ``integration/yaml_trajectory.py`` on the robot side; documented in
  ``docs/08_trajectory_format.md``.
* ``<name>.meta.yaml`` — **editor** metadata: the full designer model
  (groups, locks, segment interpolation settings, comments). The runtime
  never reads it; without it a runtime file can still be re-imported as
  plain waypoints (decimated), so nothing is ever lost beyond styling.
"""

from __future__ import annotations

import datetime
import re
from pathlib import Path

import numpy as np
import yaml

from mcs.designer.model import MissionModel
from mcs.designer.sampling import SampledMission

FORMAT = "blueboat_trajectory/1"
_NAME_RE = re.compile(r"^[A-Za-z0-9_\-]+$")


def valid_name(name: str) -> bool:
    return bool(_NAME_RE.match(name))


def runtime_path(directory: Path, name: str) -> Path:
    return directory / f"{name}.yaml"


def meta_path(directory: Path, name: str) -> Path:
    return directory / f"{name}.meta.yaml"


def list_missions(directory: Path) -> list[str]:
    if not directory.exists():
        return []
    return sorted(p.stem for p in directory.glob("*.yaml")
                  if not p.name.endswith(".meta.yaml"))


def save_mission(directory: Path, name: str, model: MissionModel,
                 samples: SampledMission) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    points = [[round(float(t), 3), round(float(x), 4), round(float(y), 4),
               round(float(psi), 5)]
              for t, (x, y), psi in zip(samples.t, samples.xy, samples.yaw)]
    runtime = {
        "format": FORMAT,
        "name": name,
        "generator": "mission-pattern-designer/1.0",
        "created": datetime.datetime.now().isoformat(timespec="seconds"),
        "frame": "world",
        "speed": float(model.speed),
        "loop": bool(model.loop),
        "length_m": round(samples.length_m, 3),
        "duration_s": round(samples.duration_s, 3),
        "points": points,
    }
    path = runtime_path(directory, name)
    path.write_text(yaml.safe_dump(runtime, sort_keys=False,
                                   default_flow_style=None))
    meta = {"format": "blueboat_trajectory_meta/1", "model": model.to_dict()}
    meta_path(directory, name).write_text(yaml.safe_dump(meta, sort_keys=False))
    return path


def load_mission(directory: Path, name: str, model: MissionModel) -> None:
    """Load into *model*: from metadata when present, otherwise re-import the
    runtime samples as plain straight-line waypoints (decimated)."""
    mp = meta_path(directory, name)
    if mp.exists():
        meta = yaml.safe_load(mp.read_text()) or {}
        model.from_dict(meta.get("model", {}))
        model.name = name
        return
    rp = runtime_path(directory, name)
    data = yaml.safe_load(rp.read_text()) or {}
    pts = np.asarray(data.get("points", []), dtype=float)
    model.from_dict({"name": name, "speed": data.get("speed", 0.5),
                     "loop": data.get("loop", False), "items": []})
    if len(pts):
        keep = _decimate(pts[:, 1:3], min_step=5.0)
        for i in keep:
            model.add_waypoint(float(pts[i, 1]), float(pts[i, 2]))
    model.name = name


def _decimate(xy: np.ndarray, min_step: float) -> list[int]:
    keep = [0]
    for i in range(1, len(xy)):
        if np.hypot(*(xy[i] - xy[keep[-1]])) >= min_step or i == len(xy) - 1:
            keep.append(i)
    return keep


def delete_mission(directory: Path, name: str) -> None:
    for p in (runtime_path(directory, name), meta_path(directory, name)):
        p.unlink(missing_ok=True)


def rename_mission(directory: Path, old: str, new: str) -> None:
    for old_p, new_p in ((runtime_path(directory, old), runtime_path(directory, new)),
                         (meta_path(directory, old), meta_path(directory, new))):
        if old_p.exists():
            old_p.rename(new_p)


def duplicate_mission(directory: Path, src: str, dst: str) -> None:
    for src_p, dst_p in ((runtime_path(directory, src), runtime_path(directory, dst)),
                         (meta_path(directory, src), meta_path(directory, dst))):
        if src_p.exists():
            dst_p.write_bytes(src_p.read_bytes())
