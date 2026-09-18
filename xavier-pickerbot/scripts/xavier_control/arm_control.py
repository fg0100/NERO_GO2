"""MOCK-ONLY arm/gripper command builder for the Xavier Pickerbot Mini's
4-DOF arm (Wheeltec `mini_mec_four_arm` + `mini_mec_four_arm_moveit_config`).

Status (2026-09-18): this module NEVER talks to a real robot. It never
imports rospy, actionlib, moveit_commander, or any ROS client library, and
it never constructs or publishes to a real topic/action name. Everything
`send()` produces is only appended to `self.sent` for tests/UI to inspect.
There is no env-var, flag, or code path anywhere in this file that enables
a real send — mirroring the Go2 dashboard's lowcmd_sender.py house pattern,
the real publish path is simply NOT IMPLEMENTED here, not merely disabled,
so nothing can be flipped on by mistake.

WHY mock-only, unlike base_drive.py's real-capable (if gated) design:
`/cmd_vel` with a Twist message is the universal, well-documented
Wheeltec/ROS convention (used by their own `wheeltec_joy_control`), so it
was judged safe to build for real (if ARMED-gated) sending once live-
verified. The arm has NO such fallback: this robot's actual joint limits,
topic name(s), message type(s), and field names have not been read from
`mini_mec_four_arm_moveit_config`'s URDF/SRDF or verified via `rostopic`/
`rosservice` against the live robot (which was unreachable this session).
Sending real motion commands to a 4-DOF arm with guessed limits risks a
collision with the gripper, base, or whatever the arm is holding. So this
module stays mock-only until someone reads the real joint limits off the
robot and deliberately builds a real sender the way lowcmd_sender.py was
eventually built for Go2 — as a clearly separate, clearly labeled module.

PLACEHOLDER JOINT LIMITS BELOW — NOT FROM THIS ROBOT'S URDF.
These are generic, conservative radian ranges for a small 4-DOF educational
arm, invented for shape/testing purposes only. They MUST be replaced with
the real `mini_mec_four_arm_moveit_config` joint limits (read from its
URDF/SRDF, or from `rosparam get /robot_description` on the live robot)
before any real send path is ever enabled. Treat any test or UI text that
looks like a real number here as fiction until that replacement happens.

4-DOF ARM NOTE: with only 4 joints, this arm cannot reach an arbitrary 6D
(position + orientation) pose — that needs at least 6 DOF. Only a
position-based target (x, y, z, and whatever orientation degrees of
freedom happen to fall out of 4 joints) makes sense here; full pose IK is
not offered by this module and should not be assumed to work later either
without checking the arm's actual reachable orientation subspace.
"""

from __future__ import annotations

import time

# PLACEHOLDER — NOT from this robot's URDF, must be replaced with real
# mini_mec_four_arm_moveit_config joint limits before any real send is
# enabled. Generic small-educational-arm radian ranges, one entry per
# joint, base-to-tip order assumed (unverified — the real joint ORDER is
# also unverified).
PLACEHOLDER_JOINT_LIMITS_RAD = [
    (-1.57, 1.57),   # joint 1 (assumed base yaw) — PLACEHOLDER
    (-1.20, 1.20),   # joint 2 (assumed shoulder pitch) — PLACEHOLDER
    (-1.90, 1.90),   # joint 3 (assumed elbow pitch) — PLACEHOLDER
    (-1.57, 1.57),   # joint 4 (assumed wrist) — PLACEHOLDER
]
NUM_JOINTS = len(PLACEHOLDER_JOINT_LIMITS_RAD)

# PLACEHOLDER gripper travel — not a measured value, just a 0..1 "closed to
# open" fraction so the mock has something concrete to clamp and log.
GRIPPER_CLOSED = 0.0
GRIPPER_OPEN = 1.0


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


class ArmSafety:
    """Clamps a requested joint-angle list to PLACEHOLDER_JOINT_LIMITS_RAD.
    Kept as its own small class (mirroring Go2's JointSafetyManager split
    from LowCmdSender) so the clamp logic can be unit-tested and reused
    independently of the mock sender."""

    def __init__(self, limits=PLACEHOLDER_JOINT_LIMITS_RAD):
        self.limits = list(limits)

    def clamp_joints(self, q):
        if len(q) != len(self.limits):
            raise ValueError(f"expected {len(self.limits)} joint values, got {len(q)}")
        return [_clamp(float(v), lower, upper) for v, (lower, upper) in zip(q, self.limits)]

    def clamp_gripper(self, value: float) -> float:
        return _clamp(float(value), GRIPPER_CLOSED, GRIPPER_OPEN)

    def is_safe(self, q) -> bool:
        if len(q) != len(self.limits):
            return False
        return all(lower <= v <= upper for v, (lower, upper) in zip(q, self.limits))


class MockArmSender:
    """Records mock arm/gripper commands. NEVER sends anything to a real
    robot — see module docstring. Every public method just clamps via
    ArmSafety and appends a plain dict to self.sent; there is no other
    public entry point that could bypass the clamp.
    """

    def __init__(self, safety: ArmSafety | None = None):
        self.safety = safety or ArmSafety()
        self.sent = []  # list of {"kind": "joints"|"gripper", ...}, oldest first

    def send_joint_targets(self, q):
        """MOCK send of a joint-angle target. Clamps via ArmSafety, records
        the command, and returns it. No topic is published; no ROS API is
        called."""
        safe_q = self.safety.clamp_joints(q)
        command = {
            "kind": "joints",
            "q": safe_q,
            "note": "MOCK ONLY — not sent to any real topic/robot",
            "recorded_at_monotonic": time.monotonic(),
        }
        self.sent.append(command)
        return command

    def send_gripper(self, value: float):
        """MOCK send of a gripper open/close command (0.0 closed .. 1.0
        open). Clamps via ArmSafety, records the command, and returns it."""
        safe_value = self.safety.clamp_gripper(value)
        command = {
            "kind": "gripper",
            "value": safe_value,
            "note": "MOCK ONLY — not sent to any real topic/robot",
            "recorded_at_monotonic": time.monotonic(),
        }
        self.sent.append(command)
        return command

    def open_gripper(self):
        """Convenience wrapper for send_gripper(GRIPPER_OPEN)."""
        return self.send_gripper(GRIPPER_OPEN)

    def close_gripper(self):
        """Convenience wrapper for send_gripper(GRIPPER_CLOSED)."""
        return self.send_gripper(GRIPPER_CLOSED)
