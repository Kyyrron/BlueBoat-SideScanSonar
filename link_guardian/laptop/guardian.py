#!/usr/bin/env python3
"""
Laptop side of the BlueBoat connection-loss guardian (see ../README.md).

The guardian itself is a Lua script on the autopilot (../autopilot/link_guardian.lua);
it is the only part that can act once the WiFi link is gone. This tool prepares and
supervises it while the link is up, through the MAVROS node of a running BlueBoat
launch. The Mission Control Station starts `watch` with every real-robot session and
drives everything else from its GUARDIAN box; the subcommands also work from a terminal.

    guardian.py check [--json]  read-only: installed, configured, ready?
    guardian.py setup           write the recommended ArduPilot failsafe parameters
    guardian.py on | off        set the session flag LGRD_ON on the autopilot
    guardian.py reclaim         after a guardian return: give control back to our stack
    guardian.py watch           session companion (started by MCS): keeps the guardian ON,
                                moves HOME to each run start, reports on
                                /link_guardian/status, obeys /link_guardian/command

Arming is not done here: robot_interface arms the autopilot when a session connects
(before going to override), and the script arms it itself if it has to take over.

Run it from a terminal with the workspace sourced:
    source ~/ros2_ws/install/setup.bash
    python3 link_guardian/laptop/guardian.py check
"""

import argparse
import json
import queue
import sys
import threading
import time
from collections import deque

import rclpy
from mavros_msgs.msg import HomePosition, State, StatusText
from mavros_msgs.srv import CommandHome, ParamPull, SetMode
from rcl_interfaces.msg import Parameter, ParameterType, ParameterValue
from rcl_interfaces.srv import GetParameters, SetParameters
from rclpy.executors import ExternalShutdownException, SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String
from std_srvs.srv import Trigger

STATUS_TOPIC = "/link_guardian/status"
COMMAND_TOPIC = "/link_guardian/command"

# --- What the guardian needs on the autopilot ------------------------------------
# (name, recommended value, level when different, why). Applied by `setup`, verified
# by `check`. Level 'fail' blocks READY; 'warn' is shown but does not.
RECOMMENDED = [
    ("SCR_ENABLE", 1, "fail", "Lua scripting on (restart the autopilot after changing it)"),
    ("FS_GCS_ENABLE", 1, "warn", "ArduPilot's own GCS failsafe as a backstop"),
    ("FS_ACTION", 1, "warn", "failsafe action = RTL (same destination as the guardian)"),
    ("FS_GCS_TIMEOUT", 10, "warn", "backstop fires after the guardian (LGRD_TIMEOUT 5 s)"),
    ("FS_THR_ENABLE", 0, "warn", ("no RC receiver on the boat: the radio failsafe would "
                                  "fire while armed (set 1 only with a hand transmitter)")),
]
OPTIONAL_PARAMS = {"FS_GCS_TIMEOUT"}     # absent on older firmware
# Verified by `check` only, never written by `setup` (a bitmask the owner may have tuned).
ARMING_CHECK_WHY = ("0 disables Rover's pre-arm motor check, which is what refuses arming on "
                    "passthrough and before the thrusters' output range is set (README §9)")
# Created by the script itself on its first run.
GUARDIAN_PARAMS = ["LGRD_ENABLE", "LGRD_ON", "LGRD_TIMEOUT", "LGRD_STAGE1",
                   "LGRD_SYSID", "LGRD_COMPID", "LGRD_DETECT", "LGRD_NEUTRAL"]

# Thruster mapping, identical to blueboat_control's param_set.py.
RCIN1_PASSTHROUGH, RCIN3_PASSTHROUGH = 51, 53     # 'override' (our stack drives)
THROTTLE_RIGHT, THROTTLE_LEFT = 74, 73            # 'default' (autopilot drives)

# Modes the guardian or ArduPilot's failsafe put the boat in.
AUTONOMOUS_MODES = {"RTL", "SMART_RTL", "GUIDED", "LOITER", "HOLD"}
# Boat messages worth showing the operator.
MESSAGE_PREFIXES = ("LinkGuard", "PreArm", "Arm:", "Arming", "Failsafe", "GCS Failsafe")


class Guardian(Node):
    """One node, spun by a background executor thread. Every blocking helper below
    waits on futures from the calling thread, so it works from the CLI main thread and
    from the `watch` worker alike - never from inside a callback."""

    def __init__(self):
        super().__init__("link_guardian")
        self.state = None            # mavros_msgs/State
        self.home = None             # mavros_msgs/HomePosition
        self.run_state = None        # dict from /blueboat/run_state
        self.param_mode = None       # '' / 'override' / 'default' from param_set
        self.messages = deque(maxlen=8)
        self.on_text = None          # hook used by `watch`
        self.on_command = None       # hook used by `watch`

        self.create_subscription(State, "/mavros/state", self._on_state, 10)
        self.create_subscription(HomePosition, "/mavros/home_position/home", self._on_home,
                                 QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT,
                                            history=HistoryPolicy.KEEP_LAST))
        self.create_subscription(StatusText, "/mavros/statustext/recv", self._on_text, 50)
        self.create_subscription(String, "/blueboat/run_state", self._on_run_state, 10)
        self.create_subscription(String, "/blueboat/param_mode", self._on_param_mode, 10)
        self.create_subscription(String, COMMAND_TOPIC, self._on_command, 10)

        self.pull_cli = self.create_client(ParamPull, "/mavros/param/pull")
        self.get_cli = self.create_client(GetParameters, "/mavros/param/get_parameters")
        self.set_cli = self.create_client(SetParameters, "/mavros/param/set_parameters")
        self.mode_cli = self.create_client(SetMode, "/mavros/set_mode")
        self.home_cli = self.create_client(CommandHome, "/mavros/cmd/set_home")
        self.home_req_cli = self.create_client(Trigger, "/mavros/home_position/req_update")
        self.mavros_get_cli = self.create_client(GetParameters, "/mavros/get_parameters")
        self.status_pub = self.create_publisher(String, STATUS_TOPIC, 10)

        self._executor = SingleThreadedExecutor()
        self._executor.add_node(self)
        self._spin_thread = threading.Thread(target=self._spin, daemon=True)
        self._spin_thread.start()

    def _spin(self):
        try:
            self._executor.spin()
        except (ExternalShutdownException, KeyboardInterrupt):
            pass             # SIGINT / launch teardown: a clean exit

    def shutdown(self):
        # Stop the executor and let its thread leave rcl before the node goes away:
        # destroying a node under a waiting executor aborts the process.
        self._executor.shutdown(timeout_sec=2.0)
        self._spin_thread.join(timeout=3.0)
        self.destroy_node()

    # ---------------- subscriptions (executor thread; never block here) ----------------
    def _on_state(self, msg):
        self.state = msg

    def _on_home(self, msg):
        self.home = msg

    def _on_text(self, msg):
        if msg.text.startswith(MESSAGE_PREFIXES):
            self.messages.append({"t": time.time(), "severity": int(msg.severity),
                                  "text": msg.text})
            if self.on_text:
                self.on_text(msg.text)

    def _on_run_state(self, msg):
        try:
            self.run_state = json.loads(msg.data)
        except ValueError:
            pass

    def _on_param_mode(self, msg):
        self.param_mode = msg.data

    def _on_command(self, msg):
        if self.on_command is None:
            return
        try:
            cmd = json.loads(msg.data)
        except ValueError:
            return
        if isinstance(cmd, dict) and isinstance(cmd.get("cmd"), str):
            self.on_command(cmd)

    # ---------------- state helpers ----------------
    @property
    def connected(self):
        return self.state is not None and self.state.connected

    @property
    def run_running(self):
        return bool(self.run_state and self.run_state.get("state") == "running")

    # ---------------- blocking helpers (main or worker thread) ----------------
    def call(self, client, request, timeout=10.0):
        if not client.wait_for_service(timeout_sec=min(timeout, 5.0)):
            raise RuntimeError(f"service {client.srv_name} not available - is the BlueBoat launch running?")
        future = client.call_async(request)
        end = time.monotonic() + timeout
        while not future.done():
            if time.monotonic() > end:
                future.cancel()
                raise RuntimeError(f"{client.srv_name} did not answer within {timeout:.0f} s")
            time.sleep(0.02)
        return future.result()

    def wait_connected(self, timeout=15.0):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if self.connected:
                return True
            time.sleep(0.1)
        return False

    def pull_params(self, force=False):
        req = ParamPull.Request()
        req.force_pull = force
        res = self.call(self.pull_cli, req, timeout=60.0)
        if not res.success:
            raise RuntimeError("parameter pull from the autopilot failed")

    def get_params(self, names):
        """{name: value or None (missing)} - values as int or float (mavros cache)."""
        req = GetParameters.Request()
        req.names = list(names)
        res = self.call(self.get_cli, req)
        out = {}
        for name, v in zip(names, res.values):
            if v.type == ParameterType.PARAMETER_INTEGER:
                out[name] = v.integer_value
            elif v.type == ParameterType.PARAMETER_DOUBLE:
                out[name] = v.double_value
            else:
                out[name] = None
        return out

    def set_param(self, name, value):
        """Set one autopilot parameter, keeping its existing type. MAVROS only reports
        success once the autopilot has echoed the value. Returns the read-back."""
        current = self.get_params([name])[name]
        if current is None:
            raise RuntimeError(f"{name} does not exist on this autopilot")
        pv = ParameterValue()
        if isinstance(current, int):
            pv.type = ParameterType.PARAMETER_INTEGER
            pv.integer_value = int(value)
        else:
            pv.type = ParameterType.PARAMETER_DOUBLE
            pv.double_value = float(value)
        p = Parameter()
        p.name = name
        p.value = pv
        req = SetParameters.Request()
        req.parameters = [p]
        res = self.call(self.set_cli, req, timeout=15.0)
        if not res.results[0].successful:
            raise RuntimeError(f"autopilot refused {name}={value}: {res.results[0].reason}")
        return self.get_params([name])[name]

    def set_mode(self, mode):
        req = SetMode.Request()
        req.base_mode = 0
        req.custom_mode = mode
        if not self.call(self.mode_cli, req).mode_sent:
            raise RuntimeError(f"mode {mode} not sent")
        end = time.monotonic() + 5.0
        while time.monotonic() < end:
            if self.state is not None and self.state.mode == mode:
                return
            time.sleep(0.1)
        raise RuntimeError(f"autopilot did not enter {mode} (still {self.state.mode if self.state else '?'})")

    def mavros_identity(self):
        """(system_id, component_id) MAVROS sends its heartbeat with, or None."""
        req = GetParameters.Request()
        req.names = ["system_id", "component_id"]
        res = self.call(self.mavros_get_cli, req, timeout=3.0)
        vals = [v.integer_value for v in res.values if v.type == ParameterType.PARAMETER_INTEGER]
        return tuple(vals) if len(vals) == 2 else None


def _fmt(v):
    return "MISSING" if v is None else (f"{v:g}" if isinstance(v, float) else str(v))


# ======================================================================
#  Operations (shared by the CLI and `watch`); each returns (ok, detail)
# ======================================================================

def op_check(node, pull=True):
    """Readiness report: {ready, items[{name, level, text}], script, guardian_on,
    servo1, armed, mode}. Raises only when MAVROS itself is unreachable."""
    if pull:
        node.pull_params()
    names = ([n for n, *_ in RECOMMENDED] + GUARDIAN_PARAMS
             + ["ARMING_CHECK", "SERVO1_FUNCTION", "SERVO3_FUNCTION"])
    v = node.get_params(names)
    items = []

    def item(name, level, text):
        items.append({"name": name, "level": level, "text": text})

    script = v["LGRD_ENABLE"] is not None
    if script:
        item("Script", "ok" if v["LGRD_ENABLE"] >= 1 else "fail",
             "installed and running" if v["LGRD_ENABLE"] >= 1
             else "installed but LGRD_ENABLE = 0 (switched off)")
    else:
        item("Script", "fail", "LGRD_* parameters not found: script not uploaded, "
             "SCR_ENABLE = 0, or the autopilot was not restarted")

    for name, want, level, why in RECOMMENDED:
        have = v[name]
        if have is None and name in OPTIONAL_PARAMS:
            item(name, "ok", "not on this firmware (older ArduPilot)")
            continue
        good = have is not None and float(have) == float(want)
        item(name, "ok" if good else level,
             f"{_fmt(have)}" + ("" if good else f" (recommended {want}: {why})"))

    have = v["ARMING_CHECK"]
    item("ARMING_CHECK", "ok" if have not in (None, 0) else "warn",
         _fmt(have) + ("" if have not in (None, 0) else f" (keep it non-zero: {ARMING_CHECK_WHY})"))

    # Thrusters go neutral before the takeover, never after it.
    if script and v["LGRD_NEUTRAL"] is None:
        item("Script version", "warn", "older script (no LGRD_NEUTRAL): upload the current "
             "link_guardian.lua and restart the autopilot")
    elif v["LGRD_NEUTRAL"] is not None and v["LGRD_TIMEOUT"] is not None:
        neutral, timeout = v["LGRD_NEUTRAL"], v["LGRD_TIMEOUT"]
        good = neutral == 0 or neutral < timeout
        item("Neutral hold", "ok" if good else "warn",
             f"LGRD_NEUTRAL {_fmt(neutral)} s, LGRD_TIMEOUT {_fmt(timeout)} s"
             + ("" if good else " - LGRD_NEUTRAL must be below LGRD_TIMEOUT or it never acts"))

    # The heartbeat identity the script listens for must be MAVROS's.
    try:
        ident = node.mavros_identity()
    except RuntimeError:
        ident = None
    if script:
        want = (int(v["LGRD_SYSID"]), int(v["LGRD_COMPID"]))
        if ident is None:
            item("Laptop identity", "warn",
                 f"could not read MAVROS system_id/component_id; script expects "
                 f"sys {want[0]} comp {want[1]} (MAVROS 2 default: 1 / 191)")
        else:
            match = ident[0] == want[0] and want[1] in (0, ident[1])
            item("Laptop identity", "ok" if match else "fail",
                 f"MAVROS sys {ident[0]} comp {ident[1]}"
                 + ("" if match else f" - script expects sys {want[0]} comp {want[1]}: "
                                     f"set LGRD_SYSID / LGRD_COMPID"))

    ready = all(i["level"] != "fail" for i in items)
    return {"ready": ready, "items": items, "script": script,
            "guardian_on": (v["LGRD_ON"] >= 1) if v["LGRD_ON"] is not None else None,
            "servo1": v["SERVO1_FUNCTION"], "servo3": v["SERVO3_FUNCTION"],
            "armed": bool(node.state and node.state.armed),
            "mode": node.state.mode if node.state else None, "t": time.time()}


def op_setup(node):
    if node.run_running:
        return False, "a run is active - stop it first"
    node.pull_params()
    done, failed = [], []
    for name, want, _level, _why in RECOMMENDED:
        try:
            got = node.set_param(name, want)
            done.append(f"{name}={_fmt(got)}")
        except RuntimeError as e:
            if name in OPTIONAL_PARAMS:
                continue
            failed.append(f"{name}: {e}")
    detail = "set " + ", ".join(done)
    if failed:
        detail += "; FAILED " + "; ".join(failed)
    return not failed, detail + ". If SCR_ENABLE was 0, restart the autopilot."


def op_flag(node, on):
    got = node.set_param("LGRD_ON", 1 if on else 0)
    ok = (got >= 1) == on
    return ok, f"LGRD_ON = {_fmt(got)}"


def op_reclaim(node, force=False):
    if node.run_running and not force:
        return False, ("a run is still active - press Stop Run first, otherwise the boat "
                       "resumes the run the instant control is back")
    mode = node.param_mode if node.param_mode in ("override", "default") else "override"
    servo = ((RCIN1_PASSTHROUGH, RCIN3_PASSTHROUGH) if mode == "override"
             else (THROTTLE_RIGHT, THROTTLE_LEFT))
    node.set_mode("HOLD")
    node.pull_params()
    for name, val in (("SERVO1_FUNCTION", servo[0]), ("SERVO3_FUNCTION", servo[1])):
        got = node.set_param(name, val)
        if int(got) != val:
            return False, f"{name} reads {got}, expected {val}; the boat stays in HOLD"
    node.set_mode("MANUAL")
    return True, (f"control back with the station: HOLD -> SERVO1/3 {servo[0]}/{servo[1]} "
                  f"('{mode}') -> MANUAL")


# ======================================================================
#  CLI commands
# ======================================================================

def _need_connection(node, quiet=False):
    if not node.wait_connected():
        if not quiet:
            print("✗ MAVROS is not connected to the autopilot. Start the BlueBoat launch first.")
        return False
    return True


def cmd_check(node, args):
    if not _need_connection(node, quiet=args.json):
        if args.json:
            print(json.dumps({"ready": False, "error": "not connected"}))
        return 1
    rep = op_check(node)
    if args.json:
        print(json.dumps(rep))
        return 0 if rep["ready"] else 1
    marks = {"ok": "✓", "warn": "!", "fail": "✗"}
    print(f"autopilot: {'ARMED' if rep['armed'] else 'disarmed'}, mode {rep['mode']}, "
          f"guardian flag LGRD_ON = {rep['guardian_on']}")
    for it in rep["items"]:
        print(f"  {marks[it['level']]} {it['name']:16s} {it['text']}")
    print("\nRESULT:", "READY" if rep["ready"] else "NOT READY - see ✗ above")
    return 0 if rep["ready"] else 1


def cmd_simple(op):
    def run(node, args):
        if not _need_connection(node):
            return 1
        ok, detail = op(node, args)
        print(("✓ " if ok else "✗ ") + detail)
        return 0 if ok else 1
    return run


# ======================================================================
#  watch: the session companion started by MCS
# ======================================================================

class Watch:
    ENSURE_PERIOD_S = 5.0

    def __init__(self, node):
        self.node = node
        self.log = node.get_logger()
        self.want_on = True            # the guardian is ON by default in every session
        self.guardian_on = None        # last value the autopilot confirmed
        self.check = None              # last op_check report
        self.busy = None               # operator command being executed
        self.running_job = None        # any job being executed (ensure included)
        self.ack = None
        self.session_home = None
        self.home_source = None
        self.was_armed = False
        self.was_running = False
        self.was_connected = False
        self.last_mode = None
        self.next_ensure = 0.0
        self.pending_home_req = None
        self.jobs = queue.Queue()
        node.on_command = self._on_command
        node.on_text = self._on_text

    # -- inputs from the executor thread --
    def _on_command(self, cmd):
        self.jobs.put(cmd)

    def _on_text(self, text):
        self.log.warning(f"[boat] {text}")
        if text.startswith("LinkGuard: loaded"):
            # The autopilot (re)booted: the script reset LGRD_ON - set it again now.
            self.next_ensure = 0.0

    # -- worker: one job at a time --
    def worker(self):
        while True:
            job = self.jobs.get()
            name = job.get("cmd")
            self.running_job = name
            self.busy = name if name != "ensure" else None
            try:
                ok, detail = self._run(job)
            except Exception as e:  # noqa: BLE001 - any failure is reported to the station
                ok, detail = False, str(e)
            if name == "ensure":
                # Internal keep-alive: never overwrites the answer to an
                # operator command, and only failures are worth a log line.
                if not ok:
                    self.log.warning(f"keeping the guardian {'ON' if self.want_on else 'OFF'}: {detail}",
                                  throttle_duration_sec=30.0)
            else:
                self.ack = {"seq": job.get("seq"), "cmd": name, "ok": ok, "detail": detail,
                            "t": time.time()}
                (self.log.info if ok else self.log.error)(f"{name}: {detail}")
            self.busy = None
            self.running_job = None

    def _run(self, job):
        n = self.node
        name = job["cmd"]
        if name in ("ensure", "check", "setup", "on", "off", "reclaim") and not n.connected:
            return False, "autopilot not connected"
        if name == "ensure":
            return self._ensure()
        if name == "check":
            self.check = op_check(n)
            return self.check["ready"], "READY" if self.check["ready"] else "NOT READY"
        if name == "setup":
            ok, detail = op_setup(n)
            self.check = op_check(n, pull=False)
            return ok, detail
        if name in ("on", "off"):
            self.want_on = name == "on"
            ok, detail = op_flag(n, self.want_on)
            self.guardian_on = self.want_on if ok else self.guardian_on
            return ok, detail
        if name == "reclaim":
            return op_reclaim(n, force=bool(job.get("force")))
        return False, f"unknown command '{name}'"

    def _ensure(self):
        """Keep the autopilot's session flag equal to what the operator wants."""
        if self.check is None:
            self.check = op_check(self.node)
        if not self.check["script"]:
            self.guardian_on = None
            return False, "script not installed"
        ok, detail = op_flag(self.node, self.want_on)
        if ok:
            if self.guardian_on != self.want_on:
                self.log.info(f"guardian {'ON' if self.want_on else 'OFF'} ({detail})")
            self.guardian_on = self.want_on
        return ok, detail

    # -- main loop --
    def run(self):
        threading.Thread(target=self.worker, daemon=True).start()
        self.log.info("Guardian companion running (guardian ON by default).")
        last_status = 0.0
        while rclpy.ok():
            self.tick()
            if time.monotonic() - last_status >= 1.0:
                last_status = time.monotonic()
                self.publish_status()
            time.sleep(0.2)

    def tick(self):
        n, log, now = self.node, self.log, time.monotonic()
        st = n.state
        if st is None:
            return

        if st.connected and not self.was_connected:
            log.info("Autopilot connected: checking the guardian and switching it ON.")
            self.check = None
            self.next_ensure = 0.0
        if not st.connected and self.was_connected:
            log.error("LINK TO THE BOAT LOST. If the guardian is ON, the boat returns HOME "
                      "after LGRD_TIMEOUT s on its own.")
        self.was_connected = st.connected

        # Keep the flag set (cheap, idempotent; also covers an autopilot reboot).
        if (st.connected and now >= self.next_ensure and self.running_job is None
                and self.jobs.empty()):
            self.next_ensure = now + self.ENSURE_PERIOD_S
            self.jobs.put({"cmd": "ensure"})

        # Arming = session start: ArduPilot sets HOME there.
        if st.armed and not self.was_armed:
            log.info("Autopilot armed: HOME = session start.")
            self.session_home = None
            self.home_source = "session start"
            self.pending_home_req = now + 2.0
        if not st.armed and self.was_armed:
            log.warning("Autopilot disarmed (E-STOP?). The guardian stays ON and arms the "
                     "boat itself if the link is lost.")
        self.was_armed = st.armed

        if self.pending_home_req and now >= self.pending_home_req and st.connected:
            self.pending_home_req = None
            if n.home_req_cli.service_is_ready():
                n.home_req_cli.call_async(Trigger.Request())

        if (st.armed and self.session_home is None and n.home is not None
                and self.home_source == "session start"):
            g = n.home.geo
            self.session_home = (g.latitude, g.longitude, g.altitude)
            log.info(f"Session-start HOME: {g.latitude:.7f}, {g.longitude:.7f}")

        # Run start / run end move HOME.
        running = n.run_running
        if running and not self.was_running and st.connected and n.home_cli.service_is_ready():
            n.home_cli.call_async(_home_req(True))
            self.home_source = "run start"
            self.pending_home_req = now + 1.5
            log.info("Run started: HOME moved to the run start.")
        if (not running and self.was_running and st.connected and self.session_home
                and n.home_cli.service_is_ready()):
            n.home_cli.call_async(_home_req(False, *self.session_home))
            self.home_source = "session start"
            self.pending_home_req = now + 1.5
            log.info("Run ended: HOME back to the session start.")
        self.was_running = running

        if st.mode != self.last_mode:
            if st.mode in AUTONOMOUS_MODES and st.connected and self.busy != "reclaim":
                log.error(f"Boat is in {st.mode}: the guardian (or an ArduPilot failsafe) "
                          "is in control. Stop the run, then Take back control.")
            self.last_mode = st.mode

    def publish_status(self):
        n, st = self.node, self.node.state
        home = None
        if n.home is not None:
            home = {"lat": n.home.geo.latitude, "lon": n.home.geo.longitude,
                    "source": self.home_source}
        msg = String()
        msg.data = json.dumps({
            "connected": bool(st and st.connected),
            "armed": bool(st and st.armed),
            "mode": st.mode if st else None,
            "want_on": self.want_on,
            "guardian_on": self.guardian_on,
            "check": self.check,
            "home": home,
            "run_running": n.run_running,
            "messages": list(n.messages),
            "busy": self.busy,
            "ack": self.ack,
        })
        n.status_pub.publish(msg)


def _home_req(current, lat=0.0, lon=0.0, alt=0.0):
    req = CommandHome.Request()
    req.current_gps = current
    req.yaw = 0.0
    req.latitude, req.longitude, req.altitude = float(lat), float(lon), float(alt)
    return req


def cmd_watch(node, args):
    Watch(node).run()
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("check", help="read-only readiness check")
    p.add_argument("--json", action="store_true", help="one JSON object on stdout")
    sub.add_parser("setup", help="write the recommended failsafe parameters")
    sub.add_parser("on", help="guardian ON (LGRD_ON = 1)")
    sub.add_parser("off", help="guardian OFF (LGRD_ON = 0)")
    p = sub.add_parser("reclaim", help="take control back after a guardian return")
    p.add_argument("--force", action="store_true", help="even if a run is still active")
    sub.add_parser("watch", help="session companion (started by MCS)")
    args = ap.parse_args()

    commands = {
        "check": cmd_check,
        "setup": cmd_simple(lambda n, a: op_setup(n)),
        "on": cmd_simple(lambda n, a: op_flag(n, True)),
        "off": cmd_simple(lambda n, a: op_flag(n, False)),
        "reclaim": cmd_simple(lambda n, a: op_reclaim(n, force=a.force)),
        "watch": cmd_watch,
    }
    rclpy.init()
    node = Guardian()
    try:
        rc = commands[args.cmd](node, args)
    except KeyboardInterrupt:
        rc = 0
    except RuntimeError as e:
        print(f"✗ {e}")
        rc = 1
    finally:
        node.shutdown()
        if rclpy.ok():
            rclpy.shutdown()
    sys.exit(rc)


if __name__ == "__main__":
    main()
