"""Plan one target and one transducer pose, then hand them to BabelBrain.

Opens a SimNIBS m2m_ folder, shows the T1 and the skin, and writes a
Brainsight version-14 trajectory plus the four files in ~/.BabelBrainSync.
Launch BabelBrain afterwards with -bInUseWithBrainsight.

    python BabelBrain/Planner/planner.py
    python BabelBrain/Planner/planner.py --check M2M_FOLDER OUTPUT_FOLDER

--check does not open a window and does not write ~/.BabelBrainSync.
It writes a sample trajectory and reads it back with BabelBrain's parser.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_BABEL = Path(__file__).resolve().parents[1]
if str(_BABEL) not in sys.path:
    sys.path.insert(0, str(_BABEL))

from ConvMatTransform import GetBrainSightHeader, ReadTrajectoryBrainsight
from Planner.trajectory import (
    pose_matrix,
    trajectory_filename,
    write_sync,
    write_trajectory,
)


def find_t1(m2m: Path) -> Path:
    t1 = m2m / "T1.nii.gz"
    if not t1.is_file():
        raise FileNotFoundError(f"No T1.nii.gz in {m2m}")
    return t1


def find_skin(m2m: Path) -> Path | None:
    for rel in ("skin.stl", "skin.nii.gz", "skin.nii"):
        path = m2m / rel
        if path.is_file():
            return path
    return None


def load_t1_grid(t1_path: Path):
    import nibabel as nib
    import pyvista as pv

    img = nib.load(str(t1_path))
    data = np.asanyarray(img.dataobj, dtype=np.float32)
    affine = img.affine.astype(float)
    spacing = np.linalg.norm(affine[:3, :3], axis=0)
    direction = affine[:3, :3] / spacing
    grid = pv.ImageData(dimensions=data.shape, spacing=spacing, origin=affine[:3, 3])
    grid.direction_matrix = direction
    grid.point_data["T1"] = np.ravel(data, order="F")
    return grid


def load_skin(path: Path, t1_path: Path):
    import pyvista as pv

    if path.suffix.lower() == ".stl":
        mesh = pv.read(str(path))
    else:
        grid = load_t1_grid(path) if path.name.startswith("T1") else _mask_grid(path)
        mesh = grid.contour([0.5])
    try:
        if mesh.n_cells > 80000:
            mesh = mesh.decimate(0.85)
    except Exception:
        pass
    mesh = mesh.triangulate().clean()
    _ = t1_path
    return mesh


def _mask_grid(path: Path):
    import nibabel as nib
    import pyvista as pv

    img = nib.load(str(path))
    data = np.asanyarray(img.dataobj)
    data = (data > 0).astype(np.float32)
    affine = img.affine.astype(float)
    spacing = np.linalg.norm(affine[:3, :3], axis=0)
    direction = affine[:3, :3] / spacing
    grid = pv.ImageData(dimensions=data.shape, spacing=spacing, origin=affine[:3, 3])
    grid.direction_matrix = direction
    grid.point_data["mask"] = np.ravel(data, order="F")
    return grid


def default_points(grid, skin):
    center = np.array(grid.center, dtype=float)
    if skin is None or skin.n_points == 0:
        return center, center + np.array([0.0, 0.0, 40.0])
    idx = skin.find_closest_point(center + np.array([0.0, 60.0, 0.0]))
    return center, np.array(skin.points[idx], dtype=float)


def check(m2m: str, output: str) -> None:
    """Write a sample plan and confirm BabelBrain's reader accepts it."""
    m2m_path = Path(m2m)
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    t1 = find_t1(m2m_path)
    grid = load_t1_grid(t1)
    skin_path = find_skin(m2m_path)
    skin = load_skin(skin_path, t1) if skin_path else None
    target, transducer = default_points(grid, skin)
    mat = pose_matrix(target, transducer)
    dest = out / trajectory_filename("PlannerCheck")
    write_trajectory(dest, "PlannerCheck", mat, str(t1))
    header = GetBrainSightHeader(str(dest))
    read_back, name = ReadTrajectoryBrainsight(str(dest), bGetID=True)
    if header["Version"] not in ("14", "15"):
        raise SystemExit(f"bad version {header['Version']}")
    if "NIfTI" not in header["Coordinate system"]:
        raise SystemExit(header["Coordinate system"])
    if name != "PlannerCheck":
        raise SystemExit(f"target name {name}")
    if not np.allclose(read_back, mat, atol=1e-6):
        raise SystemExit("round trip matrix mismatch")
    print("OK")
    print("trajectory", dest)
    print("coordinate_system", header["Coordinate system"])
    print("target_mm", np.round(target, 2).tolist())
    print("transducer_mm", np.round(transducer, 2).tolist())
    print("skin", skin_path)


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == "--check":
        if len(sys.argv) != 4:
            raise SystemExit("usage: planner.py --check M2M_FOLDER OUTPUT_FOLDER")
        check(sys.argv[2], sys.argv[3])
        return
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = PlannerWindow()
    window.show()
    sys.exit(app.exec())


class PlannerWindow:
    """Imported lazily so --check does not need a display."""

    def __init__(self):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (
            QDoubleSpinBox,
            QFileDialog,
            QFormLayout,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QMessageBox,
            QPushButton,
            QVBoxLayout,
            QWidget,
        )
        from pyvistaqt import QtInteractor

        self._Qt = Qt
        self._QFileDialog = QFileDialog
        self._QMessageBox = QMessageBox
        self.m2m = None
        self.t1 = None
        self.grid = None
        self.skin = None
        self._picking = None

        self.widget = QWidget()
        self.widget.setWindowTitle("BabelBrain planner")
        self.widget.resize(1100, 700)
        root = QHBoxLayout(self.widget)
        self.plotter = QtInteractor(self.widget)
        root.addWidget(self.plotter.interactor, stretch=1)

        side = QVBoxLayout()
        root.addLayout(side)
        open_btn = QPushButton("Open m2m folder")
        open_btn.clicked.connect(self.open_m2m)
        side.addWidget(open_btn)
        self.path_label = QLabel("No project")
        self.path_label.setWordWrap(True)
        side.addWidget(self.path_label)

        form = QFormLayout()
        side.addLayout(form)
        self.name = QLineEdit("Target")
        form.addRow("Target name", self.name)
        self.target_spins = [self._spin() for _ in range(3)]
        self.tx_spins = [self._spin() for _ in range(3)]
        form.addRow("Target X Y Z mm", self._row(self.target_spins))
        form.addRow("Transducer X Y Z mm", self._row(self.tx_spins))
        for box in self.target_spins + self.tx_spins:
            box.valueChanged.connect(self._refresh_markers)

        pick_target = QPushButton("Click slice to set target")
        pick_tx = QPushButton("Click skin to set transducer")
        pick_target.clicked.connect(lambda: self._arm_pick("target"))
        pick_tx.clicked.connect(lambda: self._arm_pick("transducer"))
        side.addWidget(pick_target)
        side.addWidget(pick_tx)

        out_btn = QPushButton("Choose output folder")
        out_btn.clicked.connect(self.choose_output)
        side.addWidget(out_btn)
        self.output = QLineEdit()
        side.addWidget(self.output)

        save = QPushButton("Save trajectory and sync files")
        save.clicked.connect(self.save)
        side.addWidget(save)
        self.status = QLabel(
            "Column 2 of the trajectory points from the target toward the transducer. "
            "BabelBrain fires the beam the other way."
        )
        self.status.setWordWrap(True)
        side.addWidget(self.status)
        side.addStretch(1)
        self.widget.__dict__["_planner"] = self

    def show(self):
        self.widget.show()

    def _spin(self):
        from PySide6.QtWidgets import QDoubleSpinBox
        box = QDoubleSpinBox()
        box.setRange(-400, 400)
        box.setDecimals(2)
        box.setSingleStep(1.0)
        return box

    def _row(self, spins):
        from PySide6.QtWidgets import QHBoxLayout, QWidget
        wrap = QWidget()
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        for box in spins:
            lay.addWidget(box)
        return wrap

    def open_m2m(self):
        folder = self._QFileDialog.getExistingDirectory(self.widget, "SimNIBS m2m folder")
        if not folder:
            return
        self._load(Path(folder))

    def _load(self, m2m: Path):
        try:
            t1 = find_t1(m2m)
            grid = load_t1_grid(t1)
            skin_path = find_skin(m2m)
            skin = load_skin(skin_path, t1) if skin_path else None
        except Exception as exc:
            self._QMessageBox.critical(self.widget, "Planner", str(exc))
            return
        self.m2m = m2m
        self.t1 = t1
        self.grid = grid
        self.skin = skin
        target, transducer = default_points(grid, skin)
        self._set_spins(self.target_spins, target)
        self._set_spins(self.tx_spins, transducer)
        if not self.output.text().strip():
            self.output.setText(str(m2m))
        self.path_label.setText(str(m2m))
        self._draw()

    def choose_output(self):
        folder = self._QFileDialog.getExistingDirectory(self.widget, "Simulation output folder")
        if folder:
            self.output.setText(folder)

    def _set_spins(self, spins, xyz):
        for box, value in zip(spins, xyz):
            box.blockSignals(True)
            box.setValue(float(value))
            box.blockSignals(False)

    def _xyz(self, spins):
        return np.array([box.value() for box in spins], dtype=float)

    def _arm_pick(self, which: str):
        if self.grid is None:
            return
        self._picking = which
        self.status.setText(f"Click the view to set the {which}.")
        self.plotter.enable_surface_point_picking(
            callback=self._on_pick, show_message=False, show_point=False, left_clicking=True,
        )

    def _on_pick(self, point):
        point = np.asarray(point, dtype=float).reshape(3)
        if self._picking == "target":
            self._set_spins(self.target_spins, point)
        elif self._picking == "transducer":
            self._set_spins(self.tx_spins, point)
        self._refresh_markers()

    def _draw(self):
        self.plotter.clear()
        if self.skin is not None:
            self.plotter.add_mesh(self.skin, color="#d8c3a5", opacity=0.25, name="skin")
        self._refresh_markers()
        self.plotter.reset_camera()
        self.plotter.enable_trackball_style()

    def _refresh_markers(self):
        if self.grid is None:
            return
        target = self._xyz(self.target_spins)
        transducer = self._xyz(self.tx_spins)
        slices = self.grid.slice_orthogonal(x=target[0], y=target[1], z=target[2])
        self.plotter.add_mesh(slices, cmap="gray", name="slices", show_scalar_bar=False)
        self.plotter.add_mesh(
            self._sphere(target, 2.0), color="red", name="target_marker",
        )
        self.plotter.add_mesh(
            self._sphere(transducer, 3.0), color="#1f4e79", name="tx_marker",
        )
        import pyvista as pv
        line = pv.Line(target, transducer)
        self.plotter.add_mesh(line, color="#1f4e79", line_width=3, name="beam")

    def _sphere(self, center, radius):
        import pyvista as pv
        return pv.Sphere(radius=radius, center=center)

    def save(self):
        if self.t1 is None or self.m2m is None:
            self._QMessageBox.warning(self.widget, "Planner", "Open an m2m folder first.")
            return
        output = self.output.text().strip()
        if not output:
            self._QMessageBox.warning(self.widget, "Planner", "Choose an output folder.")
            return
        out = Path(output)
        out.mkdir(parents=True, exist_ok=True)
        name = self.name.text().strip() or "Target"
        try:
            mat = pose_matrix(self._xyz(self.target_spins), self._xyz(self.tx_spins))
        except ValueError as exc:
            self._QMessageBox.warning(self.widget, "Planner", str(exc))
            return
        dest = out / trajectory_filename(name)
        write_trajectory(dest, name, mat, str(self.t1))
        folder = write_sync(str(dest), str(self.t1), str(self.m2m), str(out))
        self.status.setText(f"Wrote {dest}\nand {folder}")
        self._QMessageBox.information(
            self.widget,
            "Planner",
            f"Trajectory:\n{dest}\n\nSync files:\n{folder}\n\n"
            "Start BabelBrain with -bInUseWithBrainsight.",
        )


if __name__ == "__main__":
    main()
