# server_setup: install the files that live outside git on a new machine

The repositories travel by `git clone`. Everything else the project needs outside git travels as
one or two zips made on the source machine: worlds, MCS trajectories, the calibration tree, the field
corpus kept on disk, world-rebuild inputs, gitignored hooks and fixtures, and, optionally, the thesis
evidence. Each zip carries a `MANIFEST.json` with every file's SHA-256, its class, whether it holds
absolute paths, the commit of every repository, and the simulator identity.

| Zip | Content |
|---|---|
| `blueboat_transfer_<date>.zip` | REQUIRED (a run needs it) + NEEDED (tests, world rebuilds) + the freeze core records |
| `blueboat_evidence_<date>.zip` | EVIDENCE (acceptance evidence, review provenance, simulated run records). Optional |

Members are paths relative to `$HOME`, so `worlds/...` installs at `~/worlds/...`. `repos/<path>`
entries are gitignored files of this superproject and its submodules (hooks, the interface baseline,
the MCS lint config, test fixtures); they go into this checkout.

## Use

On the new machine, clone the superproject with its submodules at the recorded commits. Clone the
four workspace repositories into `~/ros2_ws/src` as well (`auv_control`, `pose_to_tf`,
`thruster_manager`, `urdf_parser_py`; the script prints the clone commands if any is missing). Then:

```bash
cd ~/ros2_ws/src/BlueBoat-SideScanSonar
python3 tools/server_setup/install_transfer.py --dry-run ~/blueboat_transfer_<date>.zip ~/blueboat_evidence_<date>.zip
python3 tools/server_setup/install_transfer.py ~/blueboat_transfer_<date>.zip ~/blueboat_evidence_<date>.zip
```

Python 3.8+, standard library only. The log is `~/server_transfer/install_<stamp>.log`. The record of
every installed file and every rewrite is `~/server_transfer/install_<stamp>.json`.

| Option | Effect |
|---|---|
| `--dry-run` | Check commits, plan every file, print the counts (per-file actions go to the log); write nothing but the log |
| `--overwrite` | Replace existing files whose content differs (default: stop and list them) |
| `--ignore-commits` | Go on when a repository is missing or at another commit (default: stop and print the fix) |

Exit codes: 0 done, 2 repository commits differ, 3 existing files differ, 4 bad package, 5 a
verification failed.

## What it does

1. **Commits.** It runs `git rev-parse HEAD` in the superproject, each submodule and the four
   workspace repositories, and compares each with the manifest.
2. **Plan.** Nothing is written until every target is checked:
   - an existing file with the expected SHA-256 is skipped;
   - an existing file with any other content stops the install;
   - member names that are absolute or contain `..` are refused.
3. **Install.** Each member is checked against the manifest SHA-256, written to `<file>.part`, then
   renamed into place, with its file mode kept. Symlinks are recreated and empty folders made.
4. **Path rewrite.** In every file the manifest flags (`rewrite: true`: text containing the source
   home), the old home (`source_home`, e.g. `/home/kyyrron`) becomes this `$HOME`. The rule is
   `<old home>(?![A-Za-z0-9_.-])`. Absolute symlink targets get the same rewrite. Binary files that
   contain the old home are flagged (`abs_paths: true`, `binary: true`) but left as they are.
   The rewrite changes `metadata.yaml`, so the content digest of a world with a rewritten
   `source_path.file` no longer equals the one recorded in it (`core/provenance.content_digest`
   neutralises only the world folder's own path). The JSON record lists every rewritten file.
5. **Verify.** Every installed file is hashed again: plain files against the manifest, rewritten
   files against the hash computed during the install.
6. **Next steps** are printed at the end: the venv, acados, warp-lang in the system Python, the
   `colcon build`, `provenance --check` with the expected code digest, and the smoke test.

## Not in the package

- `~/ros2_ws/.venv`: rebuild it (`python3 -m venv .venv`, then `pip install -r requirements.txt`).
- acados: build it by hand (`BlueBoat-Control/README.md`, pinned commit `db1c3caa`).
- `warp-lang==1.19.0` in `/usr/bin/python3`.
- `colcon` build output.
- Caches: map tiles, the Gauss-Legendre cache, the acados solver cache.
- Data that was not on the source machine: the beach and pool recordings on the external drive,
  and the BlueBoat-SSS test corpus under `/media/...`.
- The manifest's `absent_not_packed` lists each of these with the reason.
