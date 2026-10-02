"""Write a Brainsight version-14 trajectory and the four BabelBrain sync files.

The column order matches ConvMatTransform.ReadTrajectoryBrainsight:
translation in the first three numbers, then the three columns of the
rotation. BabelBrain points the acoustic beam along the negative of
column 2, so column 2 is the direction from the target toward the
transducer.

This module does not modify BabelBrain's own trajectory code.
"""
from __future__ import annotations

import os
from pathlib import Path

import nibabel as nib
import numpy as np

_XFORM = {
    1: "Scanner",
    2: "Aligned",
    3: "MNI-152",
    4: "Talairach",
    5: "Other-Template",
}


def coordinate_system(t1_path: str) -> str:
    """NIfTI:S:* or NIfTI:Q:* string that matches the T1 header codes."""
    header = nib.load(t1_path).header
    sform = int(header["sform_code"])
    qform = int(header["qform_code"])
    if sform in _XFORM:
        return f"NIfTI:S:{_XFORM[sform]}"
    if qform in _XFORM:
        return f"NIfTI:Q:{_XFORM[qform]}"
    raise ValueError(
        f"T1 qform_code={qform} sform_code={sform} is not a Brainsight NIfTI code"
    )


def pose_matrix(target_mm, transducer_mm) -> np.ndarray:
    """4x4 Brainsight matrix. Column 2 points from the target to the transducer."""
    target = np.asarray(target_mm, dtype=float).reshape(3)
    transducer = np.asarray(transducer_mm, dtype=float).reshape(3)
    z_col = transducer - target
    length = np.linalg.norm(z_col)
    if length < 1e-3:
        raise ValueError("Transducer and target are the same point")
    z_col = z_col / length
    helper = np.array([0.0, 1.0, 0.0]) if abs(z_col[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
    x_col = np.cross(helper, z_col)
    x_col = x_col / np.linalg.norm(x_col)
    y_col = np.cross(z_col, x_col)
    mat = np.eye(4)
    mat[:3, 0] = x_col
    mat[:3, 1] = y_col
    mat[:3, 2] = z_col
    mat[:3, 3] = target
    return mat


def brainsight_matrix(target_mm, ap_deg, lat_deg, twist_deg) -> np.ndarray:
    """Version-14 pose. Location is the crosshair. AP, Lat, and Twist are the rotation.

    Checked against Brainsight 2.5 exports: straight up is AP 0, Lat 0, Twist 0
    with columns (-Y, +X, +Z). Lat rotates about Y, AP about X, Twist about the beam.
    """
    ap = np.deg2rad(float(ap_deg))
    lat = np.deg2rad(float(lat_deg))
    twist = np.deg2rad(float(twist_deg))
    ca, sa = np.cos(ap), np.sin(ap)
    cl, sl = np.cos(lat), np.sin(lat)
    ry = np.array([[cl, 0.0, sl], [0.0, 1.0, 0.0], [-sl, 0.0, cl]])
    rx = np.array([[1.0, 0.0, 0.0], [0.0, ca, sa], [0.0, -sa, ca]])
    upright = np.array([[0.0, 1.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    rot = rx @ ry @ upright
    cos, sin = np.cos(twist), np.sin(twist)
    x_col, y_col = rot[:, 0].copy(), rot[:, 1].copy()
    rot[:, 0] = cos * x_col + sin * y_col
    rot[:, 1] = -sin * x_col + cos * y_col
    mat = np.eye(4)
    mat[:3, :3] = rot
    mat[:3, 3] = np.asarray(target_mm, dtype=float).reshape(3)
    return mat


def write_trajectory(path, target_name: str, mat: np.ndarray, t1_path: str) -> None:
    """Write one target in the version-14 text BabelBrain already reads."""
    mat = np.asarray(mat, dtype=float)
    if mat.shape != (4, 4):
        raise ValueError("mat must be 4x4")
    name = target_name.replace("\t", " ").strip() or "Target"
    values = np.concatenate((mat[:3, 3], mat[:3, 0], mat[:3, 1], mat[:3, 2]))
    row = "\t".join([name] + [f"{v:10.9f}" for v in values])
    text = "\n".join([
        "# Version: 14",
        f"# Coordinate system: {coordinate_system(t1_path)}",
        "# Created by: BabelBrain Planner (Brainsight)",
        "# Units: millimetres, degrees, milliseconds, and microvolts",
        "# Encoding: UTF-8",
        "# Notes: Each column is delimited by a tab. Each value within a column is delimited by a semicolon.",
        "# Target Name\tLoc. X\tLoc. Y\tLoc. Z\tm0n0\tm0n1\tm0n2\tm1n0\tm1n1\tm1n2\tm2n0\tm2n1\tm2n2",
        row,
        "",
    ])
    Path(path).write_text(text, encoding="utf-8")


def sync_dir() -> Path:
    """~/.BabelBrainSync on the computer running the session."""
    return Path.home() / ".BabelBrainSync"


def write_sync(trajectory_path: str, t1_path: str, m2m_path: str, output_path: str) -> Path:
    """Write the sync files GetInputFromBrainsight reads.

    Input_Target.txt is the trajectory text. BabelBrain reads that file
    with GetBrainSightHeader and then copies it next to the output.
    The other three files are one absolute path per line.
    """
    folder = sync_dir()
    folder.mkdir(parents=True, exist_ok=True)
    trajectory = Path(trajectory_path).read_text(encoding="utf-8")
    (folder / "Input_Target.txt").write_text(trajectory, encoding="utf-8")
    paths = {
        "Input_Anatomical.txt": t1_path,
        "Input_SegmentationsPath.txt": m2m_path,
        "SimulationOutputPath.txt": output_path,
    }
    for name, value in paths.items():
        (folder / name).write_text(os.path.abspath(value) + "\n", encoding="utf-8")
    return folder


def trajectory_filename(target_name: str) -> str:
    """Not `{id}.txt`, because BabelBrain copies the sync trajectory onto that name."""
    safe = "".join(ch if ch not in '\\/:*?"<>|' else "_" for ch in target_name.strip())
    return (safe or "Target") + "_planner.txt"
