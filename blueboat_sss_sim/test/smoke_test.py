"""Offline end-to-end smoke test (no ROS required).

Exercises the full ROS-free pipeline exactly as the ROS nodes drive it:

    mission YAML -> world bundle -> lawnmower trajectory -> per-ping
    render -> noise -> byte-exact encode -> decode round-trip ->
    waterfall tiles -> auto labels -> YOLO dataset export

Run with:  python3 -m test.smoke_test   (from the package root)
Artifacts land in /tmp/blueboat_sss_smoke for visual inspection.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import numpy as np

PKG_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG_ROOT))

from blueboat_sss.core.types import Pose3D, Side  # noqa: E402
from blueboat_sss.dataset.exporter import ExportConfig, YoloDatasetWriter  # noqa: E402
from blueboat_sss.dataset.labeler import LabelConfig, TileLabeler  # noqa: E402
from blueboat_sss.dataset.waterfall import (WaterfallBuilder,  # noqa: E402
                                            WaterfallTileConfig)
from blueboat_sss.mission.generate import generate_mission  # noqa: E402
from blueboat_sss.mission.patterns import WaypointTrajectory  # noqa: E402
from blueboat_sss.sonar.config import SonarConfig  # noqa: E402
from blueboat_sss.sonar.encoder import PingEncoder, parse_frame  # noqa: E402
from blueboat_sss.sonar.noise import GainDrift, apply_ping_noise  # noqa: E402
from blueboat_sss.sonar.renderer import GeometricRenderer  # noqa: E402
from blueboat_sss.worldgen.scene import SceneModel  # noqa: E402

OUT = Path("/tmp/blueboat_sss_smoke")


def check(name: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {name}" + (f" -- {detail}" if detail else ""))
    if not cond:
        raise SystemExit(f"smoke test failed at: {name}")


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    # ---- 1. Mission bundle -------------------------------------------------
    print("[1] mission bundle generation")
    bundle = generate_mission(PKG_ROOT / "config" / "default_mission.yaml",
                              OUT / "mission", seed=7)
    for f in ("world.sdf", "seabed.stl", "scene.npz", "scene_manifest.yaml",
              "trajectory.yaml", "sonar.yaml", "mission_snapshot.yaml"):
        check(f"bundle contains {f}", (bundle / f).exists())

    scene = SceneModel.load(bundle)
    check("scene has objects", len(scene.objects) > 0,
          f"{len(scene.objects)} objects")
    sdf = (bundle / "world.sdf").read_text()
    check("world.sdf has physics plugin", "physics" in sdf)
    check("world.sdf has buoyancy plugin", "buoyancy" in sdf)
    check("world.sdf references seabed mesh", "seabed.stl" in sdf)

    # ---- 2. Sonar simulation along the trajectory ----------------------------
    print("[2] sonar rendering along lawnmower pass")
    cfg = SonarConfig.from_yaml(bundle / "sonar.yaml")
    acq, model = cfg.acquisition, cfg.model
    traj = WaypointTrajectory.load_yaml(bundle / "trajectory.yaml")
    renderer = GeometricRenderer(scene, acq, model)
    rng = np.random.default_rng(1)

    builders = {s: WaterfallBuilder(acq.num_results,
                                    WaterfallTileConfig(tile_pings=400,
                                                        overlap_pings=50))
                for s in Side}
    labelers = {s: TileLabeler(acq.num_results, acq.bin_size_m,
                               LabelConfig()) for s in Side}
    encoders = {s: PingEncoder(s, acq, model) for s in Side}
    drifts = {s: GainDrift(model, rng) for s in Side}

    period = acq.ping_period_s()
    n_pings = min(int(traj.duration / period), 2600)
    contact_pings = 0
    roundtrip_checked = False
    altitudes = []

    for k in range(n_pings):
        t = k * period
        x, y, yaw = traj.pose_at(t)
        # small synthetic surface motion so attitude coupling is exercised
        pose = Pose3D(x, y, 0.0,
                      roll=np.radians(2.0) * np.sin(2 * np.pi * t / 3.1),
                      pitch=np.radians(1.0) * np.sin(2 * np.pi * t / 4.7),
                      yaw=yaw)
        for side in Side:
            r = renderer.render(side, pose, t)
            altitudes.append(r.ping.altitude_m)
            wc_mask = (acq.range_start_mm / 1000.0
                       + (np.arange(acq.num_results) + 0.5) * acq.bin_size_m
                       ) < r.ping.altitude_m
            r.ping.power = apply_ping_noise(r.ping.power, wc_mask,
                                            drifts[side].value(t), model, rng)
            enc = encoders[side].encode(r.ping)

            if not roundtrip_checked:
                # parse_frame raises on bad magic/id/checksum, so reaching
                # the next line proves the frame is byte-valid Ping Protocol.
                dec = parse_frame(enc.raw_frame)
                check("raw frame magic/id/checksum valid", dec is not None)
                corrupted = bytearray(enc.raw_frame)
                corrupted[10] ^= 0xFF
                try:
                    parse_frame(bytes(corrupted))
                    check("checksum detects corruption", False)
                except ValueError:
                    check("checksum detects corruption", True)
                check("num_results round-trip",
                      dec["num_results"] == acq.num_results)
                check("pwr_results round-trip",
                      np.array_equal(dec["pwr_results"], enc.pwr_results))
                check("frame length matches real capture layout",
                      len(enc.raw_frame) == 8 + 52 + 2 * acq.num_results + 2,
                      f"{len(enc.raw_frame)} bytes")
                roundtrip_checked = True

            if r.contacts:
                contact_pings += 1
            builders[side].add_ping(enc.pwr_results, r.contacts)

    alt = np.array(altitudes)
    check("altitude in shallow regime", bool((alt > 1.0).all() and
                                             (alt < 8.0).all()),
          f"min {alt.min():.2f} m, max {alt.max():.2f} m")
    check("contacts observed on the pass", contact_pings > 0,
          f"{contact_pings} pings with ground-truth contacts")

    # ---- 3. Waterfall + labels + export ----------------------------------------
    print("[3] waterfall tiles, labels, YOLO export")
    writer = YoloDatasetWriter(OUT / "dataset", ExportConfig())
    n_boxes = 0
    tile_shapes = []
    for side, b in builders.items():
        for i, (img, rows) in enumerate(b.ready_tiles(flush=True)):
            boxes = labelers[side].label_tile(rows)
            n_boxes += len(boxes)
            tile_shapes.append(img.shape)
            writer.add_tile(img, boxes, f"smoke_{side.value}_{i:04d}")
    check("tiles produced", writer.tile_count > 0,
          f"{writer.tile_count} tiles {tile_shapes[0]}")
    check("YOLO boxes produced", n_boxes > 0, f"{n_boxes} boxes")
    classes = []
    for lab in labelers.values():
        for n in lab.class_names:
            if n not in classes:
                classes.append(n)
    yaml_path = writer.finalize(classes)
    check("dataset.yaml written", yaml_path.exists(),
          f"classes: {classes}")

    # normalized box sanity
    from blueboat_sss.dataset.labeler import YoloBox  # noqa: F401
    bad = 0
    for lbl in (OUT / "dataset" / "labels").rglob("*.txt"):
        for line in lbl.read_text().splitlines():
            vals = [float(v) for v in line.split()[1:]]
            if not all(0.0 <= v <= 1.0 for v in vals):
                bad += 1
    check("all YOLO coords normalized", bad == 0)

    # ---- 4. Visual artifact ------------------------------------------------------
    print("[4] visual artifact")
    from PIL import Image
    imgs = sorted((OUT / "dataset" / "images").rglob("*.png"))
    montage_src = [np.array(Image.open(p)) for p in imgs[:2]]
    if len(montage_src) == 2 and montage_src[0].shape == montage_src[1].shape:
        # port mirrored | starboard, classic waterfall presentation
        m = np.hstack([np.fliplr(montage_src[0]), montage_src[1]])
        Image.fromarray(m).save(OUT / "waterfall_preview.png")
        print(f"  preview: {OUT/'waterfall_preview.png'} {m.shape}")

    stats = montage_src[0].astype(float)
    check("waterfall has dynamic range", stats.std() > 10.0,
          f"std {stats.std():.1f}, mean {stats.mean():.1f}")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
