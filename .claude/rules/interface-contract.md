---
paths:
  - "BlueBoat-*/**/launch/**"
  - "BlueBoat-*/**/msg/*.msg"
  - "BlueBoat-*/**/srv/*.srv"
  - "BlueBoat-*/**/ros/**"
  - "BlueBoat-Control/blueboat_control/src/**"
  - "BlueBoat-SSS/blueboat_sss/src/**"
  - "tools/sim_record/**"
  - "link_guardian/**"
---
# Cross-module interface contract (superproject §4)

**Before adding, changing, consuming or debugging any topic, service, QoS profile, parameter, frame convention or
file-level handoff between modules, Read `.claude/interface-contract.md`** (sections §4.1–§4.7: per-topic producers and
consumers, QoS, frames, sonar acquisition defaults, ray-cast slow-down, MAVROS rates). It is not imported here because
it is longer than an on-demand file may be. The full text of the cross-module rules CM-1…CM-16, with their evidence,
is `docs/DESIGN.md` §5; file formats: skill `file-interfaces`; MAVROS boundary: skill `interface-inventory`.
