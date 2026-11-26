#!/usr/bin/env python3
"""Install a BlueBoat server-transfer package (the files the project needs outside git).

    python3 tools/server_setup/install_transfer.py <zip> [<zip> ...] [--dry-run] [--overwrite] [--ignore-commits]

Each zip carries MANIFEST.json (format ``blueboat_server_transfer/1``). Members are paths relative
to $HOME, except ``repos/<path>``, which goes into this superproject checkout (found from this
script's own location). Standard library only. What it does, in order:

1. checks that every repository (superproject, its submodules, the workspace repositories beside
   it in ``ros2_ws/src``) is checked out at the commit the manifest records (exit 2 otherwise,
   unless ``--ignore-commits``);
2. plans every file before writing anything: an existing file whose SHA-256 matches is skipped; any
   other existing file stops the install (exit 3) unless ``--overwrite``;
3. unpacks, checking each member against the manifest SHA-256. In the files the manifest flags
   (``rewrite: true``), it replaces the old home (``source_home``) with this machine's $HOME and
   records each change;
4. re-hashes every installed file (rewritten files against the hash computed in step 3, which is
   stored in ``$HOME/server_transfer/install_<date>.json``; exit 5 on a mismatch);
5. prints the next steps (build, provenance check with the expected digest, smoke test).

``--dry-run`` prints what it would do and writes only the log ``$HOME/server_transfer/install_<date>.log``.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath

FORMAT = "blueboat_server_transfer/1"
SUPERPROJECT = Path(__file__).resolve().parents[2]
HOME = Path.home()
STAMP = dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")
LOGDIR = HOME / "server_transfer"
CHUNK = 1 << 22

EXIT_OK, EXIT_COMMITS, EXIT_CONFLICT, EXIT_PACKAGE, EXIT_VERIFY = 0, 2, 3, 4, 5


class Log:
    def __init__(self, path: Path):
        self.path = path
        self.lines: list[str] = []

    def __call__(self, msg: str = "") -> None:
        print(msg, flush=True)
        self.lines.append(msg)

    def quiet(self, msg: str) -> None:
        """Into the log file only."""
        self.lines.append(msg)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write("\n".join(self.lines) + "\n")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def safe_rel(name: str) -> PurePosixPath:
    p = PurePosixPath(name)
    if p.is_absolute() or ".." in p.parts or not p.parts or "\\" in name:
        raise ValueError(f"unsafe member name: {name!r}")
    return p


def target_of(name: str) -> Path:
    rel = safe_rel(name)
    if rel.parts[0] == "repos":
        if len(rel.parts) < 2:
            raise ValueError(f"bad repos/ entry: {name!r}")
        return SUPERPROJECT.joinpath(*rel.parts[1:])
    return HOME.joinpath(*rel.parts)


# ------------------------------------------------------------------ manifests
def load_package(zips: list[Path], log: Log):
    """Merge the manifests of all zips: {path: (zip, entry)}, links, dirs, common header."""
    files: dict[str, tuple[Path, dict]] = {}
    links: dict[str, dict] = {}
    dirs: set[str] = set()
    common = None
    for z in zips:
        with zipfile.ZipFile(z) as zf:
            try:
                man = json.loads(zf.read("MANIFEST.json"))
            except KeyError:
                raise SystemExit(f"{z}: no MANIFEST.json")
        if man.get("format") != FORMAT:
            raise SystemExit(f"{z}: unknown manifest format {man.get('format')!r}")
        if common is None:
            common = man
        else:
            for key in ("source_home", "repositories"):
                if man[key] != common[key]:
                    raise SystemExit(f"{z}: '{key}' differs from the first zip's; not one package")
        for e in man["files"]:
            prev = files.get(e["path"])
            if prev and prev[1]["sha256"] != e["sha256"]:
                raise SystemExit(f"{e['path']}: different content in {prev[0].name} and {z.name}")
            if not prev:
                files[e["path"]] = (z, e)
        for e in man["links"]:
            links[e["path"]] = e
        for e in man["empty_dirs"]:
            dirs.add(e["path"])
        log(f"package {z.name}: part={man['zip_part']} files={len(man['files'])} links={len(man['links'])} "
            f"empty_dirs={len(man['empty_dirs'])} created={man['created']}")
    return files, links, dirs, common


# ------------------------------------------------------------------ commits
def git_head(path: Path) -> str | None:
    if not path.is_dir():
        return None
    r = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def repo_path(repo: dict) -> Path:
    if repo["location"] == "superproject":
        return SUPERPROJECT
    return (SUPERPROJECT / repo["path"]).resolve()


def check_commits(common: dict, log: Log) -> list[dict]:
    log("\n== repositories (recorded commit vs checkout)")
    diffs = []
    for repo in common["repositories"]:
        path = repo_path(repo)
        head = git_head(path)
        ok = head == repo["commit"]
        state = "ok" if ok else ("MISSING" if head is None else "DIFFERS")
        log(f"  {state:8} {repo['location']:12} {repo['name']:24} want {repo['commit'][:12]} "
            f"have {head[:12] if head else '-':12} {path}")
        if not ok:
            diffs.append({**repo, "have": head, "local_path": str(path)})
    want_sp = HOME / common["superproject_rel_home"]
    if SUPERPROJECT != want_sp.resolve():
        log(f"  WARNING: the superproject is at {SUPERPROJECT}, the recorded layout puts it at {want_sp}; "
            "paths rewritten to $HOME/... will point at the recorded layout")
    return diffs


def print_commit_fix(diffs: list[dict], log: Log) -> None:
    log("\nTo fix, check out the recorded commits:")
    for d in diffs:
        p = d["local_path"]
        if d["have"] is None and d["location"] == "workspace":
            log(f"  git clone {d['remote']} {p} && git -C {p} checkout {d['commit']}")
        elif d["have"] is None:
            log(f"  git -C {SUPERPROJECT} submodule update --init {d['path']}")
        else:
            log(f"  git -C {p} fetch && git -C {p} checkout {d['commit']}")


# ------------------------------------------------------------------ rewrite
def make_rewriter(old: str, new: str):
    rx = re.compile(re.escape(old.encode()) + rb"(?![A-Za-z0-9_.-])")
    newb = new.encode()

    def rewrite(data: bytes) -> tuple[bytes, int]:
        return rx.subn(lambda _m: newb, data)
    return rewrite


def read_member(zips: dict[Path, zipfile.ZipFile], z: Path, name: str) -> bytes:
    return zips[z].read(name)


# ------------------------------------------------------------------ plan
def plan(files, links, dirs, zips, rewrite, log: Log):
    """Return (actions, conflicts, problems). An action: dict(kind, path, target, ...)."""
    actions, conflicts, problems = [], [], []
    for name in sorted(files):
        z, e = files[name]
        try:
            tgt = target_of(name)
        except ValueError as exc:
            problems.append(str(exc))
            continue
        expected, nrep, data = e["sha256"], 0, None
        if e.get("rewrite"):
            data = read_member(zips, z, name)
            if sha256_bytes(data) != e["sha256"]:
                problems.append(f"{name}: zip member does not match the manifest SHA-256")
                continue
            new, nrep = rewrite(data)
            expected = sha256_bytes(new)
        act = {"kind": "file", "path": name, "target": tgt, "zip": z, "entry": e, "expected": expected,
               "replacements": nrep}
        if tgt.is_symlink() or tgt.exists():
            if tgt.is_symlink() or not tgt.is_file():
                conflicts.append(f"{tgt}: exists and is not a regular file")
                act["action"] = "overwrite"
            else:
                have = sha256_file(tgt)
                if have == expected:
                    act["action"] = "skip"
                elif have == e["sha256"] and e.get("rewrite"):
                    act["action"] = "skip"
                    act["note"] = "identical to the original, paths not rewritten (use --overwrite to rewrite)"
                else:
                    conflicts.append(f"{tgt}: exists with different content")
                    act["action"] = "overwrite"
        else:
            act["action"] = "write"
        actions.append(act)
    for name in sorted(links):
        e = links[name]
        tgt = target_of(name)
        new_target, nrep = rewrite(e["target"].encode())
        new_target = new_target.decode()
        act = {"kind": "link", "path": name, "target": tgt, "link_to": new_target, "replacements": nrep}
        if tgt.is_symlink():
            act["action"] = "skip" if os.readlink(tgt) == new_target else "overwrite"
            if act["action"] == "overwrite":
                conflicts.append(f"{tgt}: symlink to {os.readlink(tgt)}, expected {new_target}")
        elif tgt.exists():
            act["action"] = "overwrite"
            conflicts.append(f"{tgt}: exists and is not a symlink")
        else:
            act["action"] = "write"
        actions.append(act)
    for name in sorted(dirs):
        tgt = target_of(name)
        actions.append({"kind": "dir", "path": name, "target": tgt,
                        "action": "skip" if tgt.is_dir() else "write"})
        if tgt.exists() and not tgt.is_dir():
            conflicts.append(f"{tgt}: exists and is not a directory")
    return actions, conflicts, problems


# ------------------------------------------------------------------ install
def install_file(act, zips, rewrite) -> dict:
    tgt: Path = act["target"]
    e = act["entry"]
    tgt.parent.mkdir(parents=True, exist_ok=True)
    part = tgt.with_name(tgt.name + ".part")
    rec = {"path": act["path"], "target": str(tgt), "sha256_manifest": e["sha256"]}
    zf = zips[act["zip"]]
    if e.get("rewrite"):
        data = zf.read(act["path"])
        if sha256_bytes(data) != e["sha256"]:
            raise RuntimeError(f"{act['path']}: zip member does not match the manifest SHA-256")
        data, nrep = rewrite(data)
        with open(part, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        rec.update(rewritten=True, replacements=nrep, sha256_installed=sha256_bytes(data))
    else:
        h = hashlib.sha256()
        with zf.open(act["path"]) as src, open(part, "wb") as f:
            for block in iter(lambda: src.read(CHUNK), b""):
                h.update(block)
                f.write(block)
            f.flush()
            os.fsync(f.fileno())
        if h.hexdigest() != e["sha256"]:
            part.unlink()
            raise RuntimeError(f"{act['path']}: zip member does not match the manifest SHA-256")
        rec.update(rewritten=False, sha256_installed=e["sha256"])
    try:
        os.chmod(part, int(e.get("mode", "0o644"), 8) & 0o7777)
    except (ValueError, OSError):
        pass
    if tgt.is_symlink() or (tgt.exists() and not tgt.is_file()):
        raise RuntimeError(f"{tgt}: refusing to replace a non-regular file")
    os.replace(part, tgt)
    return rec


def next_steps(common: dict, log: Log) -> None:
    exp = common.get("provenance", {}).get("expected", {})
    code = exp.get("code_digest_v1_1", "?")
    ws = HOME / "ros2_ws"
    sim = SUPERPROJECT / "BlueBoat-SSS-Sim" / "blueboat_sss_sim"
    log(f"""
== next steps
 0. Not in the package (see tools/server_setup/README.md): the venv
      cd {ws} && python3 -m venv .venv && source .venv/bin/activate
      pip install -r {SUPERPROJECT}/requirements.txt
    acados (C library built by hand in .venv/src/acados-template, BlueBoat-Control/README.md), then in ~/.bashrc:
      export ACADOS_SOURCE_DIR=$HOME/ros2_ws/.venv/src/acados-template
      export LD_LIBRARY_PATH=$ACADOS_SOURCE_DIR/lib:$LD_LIBRARY_PATH
    warp-lang for the simulated sonar node (system Python):
      /usr/bin/python3 -m pip install --user --break-system-packages warp-lang==1.19.0
 1. Build, from a fresh shell with only ROS sourced (not env.sh):
      cd {ws} && source /opt/ros/jazzy/setup.bash
      colcon build --packages-select blueboat_interfaces
      colcon build
 2. Simulator identity:
      cd {sim} && source {ws}/install/setup.bash
      python3 -m blueboat_sss_sim.core.provenance --check
    expected: code digest {code}... (v1.1; v1.0 would be {exp.get('code_digest_v1_0', '?')}...)
 3. Offline smoke test (system python, ~260 s):
      cd {sim} && python3 -m test.smoke_test
""")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("zips", nargs="+", type=Path)
    ap.add_argument("--dry-run", action="store_true", help="print what would be done; write only the log")
    ap.add_argument("--overwrite", action="store_true", help="replace existing files whose content differs")
    ap.add_argument("--ignore-commits", action="store_true", help="install even if a repository is at another commit")
    args = ap.parse_args(argv)

    log = Log(LOGDIR / f"install_{STAMP}.log")
    log(f"install_transfer {STAMP}  HOME={HOME}  superproject={SUPERPROJECT}  dry_run={args.dry_run}")
    try:
        return run(args, log)
    finally:
        log.save()
        print(f"log: {log.path}")


def run(args, log: Log) -> int:
    for z in args.zips:
        if not z.is_file():
            log(f"no such zip: {z}")
            return EXIT_PACKAGE
    zips_paths = [z.resolve() for z in args.zips]
    files, links, dirs, common = load_package(zips_paths, log)
    old_home = common["source_home"]
    log(f"source home {old_home} -> this home {HOME}")

    diffs = check_commits(common, log)
    if diffs:
        print_commit_fix(diffs, log)
        if not args.ignore_commits:
            log(f"\nSTOP: {len(diffs)} repositories differ from the recorded commits (use --ignore-commits to go on)")
            return EXIT_COMMITS
        log("--ignore-commits: going on")

    rewrite = make_rewriter(old_home, str(HOME))
    zips = {z: zipfile.ZipFile(z) for z in zips_paths}
    try:
        actions, conflicts, problems = plan(files, links, dirs, zips, rewrite, log)
        if problems:
            log("\nSTOP: package problems:")
            for p in problems:
                log("  " + p)
            return EXIT_PACKAGE
        counts: dict[str, int] = {}
        for a in actions:
            counts[f"{a['kind']}:{a['action']}"] = counts.get(f"{a['kind']}:{a['action']}", 0) + 1
        n_rw = sum(1 for a in actions if a["kind"] == "file" and a["entry"].get("rewrite"))
        log(f"\n== plan: {dict(sorted(counts.items()))}; files with paths to rewrite: {n_rw}")
        notes = [a for a in actions if a.get("note")]
        if notes:
            log(f"  {len(notes)} existing files equal the original but keep the old paths, e.g. {notes[0]['target']}")
        if conflicts:
            log(f"\n{len(conflicts)} existing files differ from the package:")
            for c in conflicts[:200]:
                log("  " + c)
            if len(conflicts) > 200:
                log(f"  ... and {len(conflicts) - 200} more")
            if not args.overwrite:
                log("STOP: nothing was written (use --overwrite to replace them)")
                return EXIT_CONFLICT
            log("--overwrite: they will be replaced")

        if args.dry_run:
            for a in actions:
                if a["action"] == "skip":
                    continue
                extra = f" (rewrite {a['replacements']} paths)" if a.get("replacements") else ""
                what = f" -> {a['link_to']}" if a["kind"] == "link" else ""
                log.quiet(f"  would {a['action']:9} {a['kind']:4} {a['target']}{what}{extra}")
            todo = sum(1 for a in actions if a["action"] != "skip")
            log(f"\ndry run: nothing written ({todo} actions listed in the log)")
            next_steps(common, log)
            return EXIT_OK

        records, written = [], 0
        for a in actions:
            if a["action"] == "skip":
                if a["kind"] == "file":
                    have = a["entry"]["sha256"] if a.get("note") else a["expected"]
                    records.append({"path": a["path"], "target": str(a["target"]), "skipped": True,
                                    "sha256_manifest": a["entry"]["sha256"], "sha256_installed": have})
                continue
            if a["kind"] == "dir":
                a["target"].mkdir(parents=True, exist_ok=True)
            elif a["kind"] == "link":
                a["target"].parent.mkdir(parents=True, exist_ok=True)
                if a["target"].is_symlink():
                    a["target"].unlink()
                os.symlink(a["link_to"], a["target"])
                records.append({"path": a["path"], "target": str(a["target"]), "link_to": a["link_to"]})
            else:
                rec = install_file(a, zips, rewrite)
                records.append(rec)
                if rec.get("rewritten") and rec["replacements"]:
                    log.quiet(f"  rewrote {rec['replacements']:4d} paths  {a['target']}")
            written += 1
            if written % 1000 == 0:
                log(f"  ... {written} written")
        log(f"\n== written {written} entries")
    finally:
        for zf in zips.values():
            zf.close()

    # verify
    bad = []
    for r in records:
        tgt = Path(r["target"])
        if "link_to" in r:
            if not tgt.is_symlink() or os.readlink(tgt) != r["link_to"]:
                bad.append(f"{tgt}: symlink wrong")
            continue
        if not tgt.is_file() or sha256_file(tgt) != r["sha256_installed"]:
            bad.append(f"{tgt}: SHA-256 differs from the expected {r['sha256_installed'][:12]}")
    for a in actions:
        if a["kind"] == "dir" and not a["target"].is_dir():
            bad.append(f"{a['target']}: directory missing")
    rec_path = LOGDIR / f"install_{STAMP}.json"
    LOGDIR.mkdir(parents=True, exist_ok=True)
    rec_path.write_text(json.dumps({"stamp": STAMP, "home": str(HOME), "source_home": old_home,
                                    "superproject": str(SUPERPROJECT), "zips": [str(z) for z in zips_paths],
                                    "records": records, "verify_problems": bad}, indent=1))
    n_rw = sum(1 for r in records if r.get("rewritten") and r.get("replacements"))
    log(f"== verify: {len(records)} entries checked, {len(bad)} problems; {n_rw} files rewritten "
        f"(record: {rec_path})")
    for b in bad[:100]:
        log("  " + b)
    if bad:
        return EXIT_VERIFY
    next_steps(common, log)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
