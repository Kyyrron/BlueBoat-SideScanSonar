# Side Scan Sonar — Usage Guide

This page is a usage reference for the `sss_node`, once it's built and
running. It covers four things: how to launch it, how to start/stop
pinging, how to start/stop on-disk logging, and what shows up on disk.

## Launching the node

Standalone:

```bash
ros2 launch blueboat_control SSS_launch.py
```

With overrides at launch time (any of the parameters listed in
`SSS_launch.py`):

**Note that default values are recommended - only range_length should matter for most cases.**
```bash
ros2 launch blueboat_control SSS_launch.py \
    range_length_mm:=50000 \
    gain_index:=4 \
    log_directory:=/Data/SSS_data
```

Typical launch line:
```bash
ros2 launch blueboat_control SSS_launch.py range_length_mm:=50000
```

From another launch file (for the future "boat + sss" composite):

```python
from simple_launch import SimpleLauncher

def generate_launch_description():
    sl = SimpleLauncher()
    # ...your other includes / nodes...
    sl.include('blueboat_control', 'SSS_launch.py')
    return sl.launch_description()
```

The node connects to both Omniscans on startup but **does not start
pinging or logging** — both are OFF until you flip them on with the
topics below.

## Start / stop pinging

Pinging is what actually fires the transducers and produces the data
streams on `/sss_node/port/profile` and `/sss_node/starboard/profile`.

```bash
# Start pinging (both sides at once)
ros2 topic pub --once /sss_node/ping/enable std_msgs/msg/Bool 'data: true'

# Stop pinging
ros2 topic pub --once /sss_node/ping/enable std_msgs/msg/Bool 'data: false'
```

Confirm data is flowing:

```bash
ros2 topic hz /sss_node/port/profile
ros2 topic hz /sss_node/starboard/profile
```

### Publishing rate

One ROS message is published per ping packet received — no batching.
The effective rate is set by the `msec_per_ping` parameter:

- `msec_per_ping = 0` (default) — pings as fast as the hardware can
  manage, which depends on range. Two-way travel time at 1500 m/s sets
  the ceiling: roughly **20–25 Hz at 30 m range**, **10 Hz at 75 m**,
  **~7 Hz at 100 m**.
- `msec_per_ping = N > 0` — lower-bounds the period at N ms. Set
  `msec_per_ping=50` for a steady **20 Hz** per side, `100` for 10 Hz,
  etc. Useful when downstream code expects a constant rate.

### Changing parameters mid-mission

The acquisition parameters (`range_length_mm`, `gain_index`,
`num_results`, `pulse_len_percent`, `msec_per_ping`, `range_start_mm`)
are read fresh on every "start". If you want to change range mid-mission:

```bash
# 1. stop, 2. retune, 3. restart
ros2 topic pub --once /sss_node/ping/enable std_msgs/msg/Bool 'data: false'
ros2 param  set /sss_node range_length_mm 50000
ros2 topic pub --once /sss_node/ping/enable std_msgs/msg/Bool 'data: true'
```

> ⚠️ Don't leave the Omniscans pinging for long periods out of water —
> Cerulean's docs note the transmit transducer can heat up and be damaged.
> A few minutes dry is fine.

## Start / stop raw logging

Logging writes the raw packet stream to a `.svlog` file in the
**SonarView single-file format**: both sides interleaved in one file,
distinguished by the per-packet `channel_number` field. This is the
same layout SonarView produces when you click its **Record** button —
the file opens directly in SonarView with both channels visible.

```bash
# Start logging
ros2 topic pub --once /sss_node/log/enable std_msgs/msg/Bool 'data: true'

# Stop logging
ros2 topic pub --once /sss_node/log/enable std_msgs/msg/Bool 'data: false'
```

Logging only writes packets that are actually arriving from the
devices, so **enable pinging first** (or both at the same time).
Logging with pinging off creates the file with only its metadata
header — nothing else gets written until pings start.

Each off→on transition rolls a brand new `.svlog` file. So a typical
recording session looks like:

```bash
ros2 topic pub --once /sss_node/ping/enable std_msgs/msg/Bool 'data: true'
ros2 topic pub --once /sss_node/log/enable  std_msgs/msg/Bool 'data: true'
# ...do the survey...
ros2 topic pub --once /sss_node/log/enable  std_msgs/msg/Bool 'data: false'
ros2 topic pub --once /sss_node/ping/enable std_msgs/msg/Bool 'data: false'
```

## Choosing the log folder

The folder is the `log_directory` parameter. Default is `/data/SSS_data`.

Override at launch time:

```bash
ros2 launch blueboat_control SSS_launch.py log_directory:=/data/SSS_data
```

Or in your composite launch file:

```python
sl.include('blueboat_control', 'SSS_launch.py',
           launch_arguments={'log_directory': '/data/SSS_data'})
```

The path can be absolute or use `~`. The directory (and the per-side
subdirectories) are created on startup if they don't exist. If you're
running the node on the BlueBoat onboard computer and want SonarView to
see your logs, point this at `/userdata/SonarView` (the folder
SonarView watches by default — see the BlueRobotics Omniscan 450 SS
integration guide).

## What ends up on disk

One `.svlog` file per recording session, in the directory you
configured:

```
/data/SSS_data/
├── 2026-05-08-14-03-27.svlog      # session 1 (started 14:03:27)
└── 2026-05-08-14-19-02.svlog      # session 2 (started 14:19:02)
```

Each file:

- Opens with a **JSON metadata packet** that declares both transducers
  in `session_devices` (`tcp://192.168.2.92:51200` and
  `tcp://192.168.2.93:51200` by default). SonarView reads this to set
  up the two display channels.
- Is then a stream of raw Ping-Protocol `os_mono_profile` packets from
  both devices, **interleaved in arrival order**. Each packet's
  `channel_number` field tells the player which side it came from.
- Each packet is framed exactly as Cerulean defines: `BR` sync bytes,
  little-endian payload length, message id (2198), device IDs, the
  52-byte fixed payload plus the `pwr_results` array (length =
  `num_results`), and a 2-byte checksum.

What you can do with it:

- **Replay them in SonarView** — open the file in the SonarView desktop
  or BlueOS extension to get the same waterfall view you'd see live.
- **Export to XTF or SL2** from SonarView if you need to feed the data
  into a different processing tool (ReefMaster etc.).
- **Replay them through this node** for offline ROS-side processing —
  point the `examples/omniscan450Example.py` from `bluerobotics/ping-python`
  at the `.svlog` and read it as if it were a live device.

## Quick health check

Useful one-liners for sanity-checking that the node is alive:

```bash
# Is the node up?
ros2 node info /sss_node

# Are subscribers attached to the control topics?
ros2 topic info /sss_node/ping/enable
ros2 topic info /sss_node/log/enable

# Is data actually arriving when ping is on?
ros2 topic echo /sss_node/port/profile --field ping_number
ros2 topic hz   /sss_node/starboard/profile
```

If `ros2 topic hz` reports 0 Hz right after enabling pinging, check that
both Omniscans are reachable (`ping 192.168.2.92`, `ping 192.168.2.93`)
and that the node logged "pinging started" for each side.
