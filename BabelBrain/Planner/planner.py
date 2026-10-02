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
    brainsight_matrix,
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


def find_tx_stl(m2m: Path) -> Path | None:
    """Local REMOPD housing. The face is z=0 and the housing extends in +Z."""
    names = ("PART_REMOPD-#5_500kHz.STL", "PART_REMOPD-#5_500kHz.stl")
    folders = [m2m, m2m.parent, m2m.parent.parent, Path(r"C:\Users\ahoss\Desktop\TUSPlanning"), Path(r"Y:\\")]
    for folder in folders:
        for name in names:
            path = folder / name
            if path.is_file():
                return path
    return None


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


def ijk_to_world(affine, ijk) -> np.ndarray:
    vec = np.array([ijk[0], ijk[1], ijk[2], 1.0], dtype=float)
    return (affine @ vec)[:3]


def _carry_horizontal(previous, z_axis) -> np.ndarray:
    """Keep the inline picture rolling. A fresh world axis flips the slice near 90 degrees."""
    z_axis = np.asarray(z_axis, dtype=float)
    z_axis = z_axis / max(float(np.linalg.norm(z_axis)), 1e-8)
    prev = np.array([1.0, 0.0, 0.0]) if previous is None else np.asarray(previous, dtype=float)
    horizontal = prev - z_axis * float(np.dot(prev, z_axis))
    if float(np.linalg.norm(horizontal)) < 1e-6:
        for candidate in (
            np.array([0.0, 1.0, 0.0]),
            np.array([0.0, 0.0, 1.0]),
            np.array([1.0, 0.0, 0.0]),
        ):
            horizontal = candidate - z_axis * float(np.dot(candidate, z_axis))
            if float(np.linalg.norm(horizontal)) > 1e-6:
                break
    horizontal = horizontal / max(float(np.linalg.norm(horizontal)), 1e-8)
    if float(np.dot(horizontal, prev)) < 0.0:
        horizontal = -horizontal
    return horizontal


def _rotate(vector, axis, degrees) -> np.ndarray:
    axis = np.asarray(axis, dtype=float)
    axis = axis / np.linalg.norm(axis)
    theta = np.deg2rad(degrees)
    cos, sin = np.cos(theta), np.sin(theta)
    return (
        vector * cos
        + np.cross(axis, vector) * sin
        + axis * np.dot(axis, vector) * (1.0 - cos)
    )


def _outer_hit(surface, origin, direction):
    """Outermost intersection along a ray. A nearest vertex can land on the ear."""
    origin = np.asarray(origin, dtype=float).reshape(3)
    direction = np.asarray(direction, dtype=float).reshape(3)
    length = float(np.linalg.norm(direction))
    if length < 1e-8:
        return None
    direction = direction / length
    hits, _ = surface.ray_trace(origin - direction * 30.0, origin + direction * 400.0)
    if len(hits) == 0:
        return None
    hits = np.atleast_2d(np.asarray(hits, dtype=float))
    return hits[int(np.argmax(hits @ direction))]


def best_skull_entry(target, surface) -> tuple[np.ndarray, np.ndarray]:
    """Seat the transducer on the outer crown, not on the ear and not on a vertex."""
    target = np.asarray(target, dtype=float).reshape(3)
    points = np.asarray(surface.points, dtype=float)
    z_top = float(np.max(points[:, 2]))
    best_hit = None
    best_dir = None
    best_score = 1e18
    samples = 240
    for n in range(samples):
        z = 1.0 - 2.0 * ((n + 0.5) / samples)
        if z < 0.45:
            continue
        radius = float(np.sqrt(max(0.0, 1.0 - z * z)))
        phi = np.pi * (1.0 + 5.0 ** 0.5) * n
        direction = np.array([radius * np.cos(phi), radius * np.sin(phi), z])
        hit = _outer_hit(surface, target, direction)
        if hit is None:
            continue
        outward = hit - target
        dist = float(np.linalg.norm(outward))
        if dist < 1e-3:
            continue
        horiz = float(np.linalg.norm(hit[:2] - target[:2]))
        if horiz > 50.0 and hit[2] < z_top - 20.0:
            continue
        score = (z_top - float(hit[2])) * 4.0 + horiz * 0.15
        if score < best_score:
            best_score = score
            best_hit = hit
            best_dir = outward / dist
    if best_hit is None:
        horiz = np.linalg.norm(points[:, :2] - target[:2], axis=1)
        band = points[:, 2] >= (z_top - 25.0)
        pool = np.where(band)[0] if np.any(band) else np.arange(len(points))
        pool = pool[np.argsort(horiz[pool])[:800]]
        idx = int(pool[np.argmax(points[pool, 2])])
        best_hit = points[idx]
        best_dir = best_hit - target
        best_dir = best_dir / max(float(np.linalg.norm(best_dir)), 1e-3)
    return best_hit, best_dir


def transducer_on_skin(target, skin, ap_deg, lat_deg, base_dir=None) -> np.ndarray:
    """Tilt the ray from the target and put the transducer face on the outer surface."""
    target = np.asarray(target, dtype=float).reshape(3)
    if base_dir is None:
        hit, base_dir = best_skull_entry(target, skin)
        if abs(ap_deg) < 1e-6 and abs(lat_deg) < 1e-6:
            return hit
    base = np.asarray(base_dir, dtype=float)
    base = base / np.linalg.norm(base)
    up = np.array([0.0, 0.0, 1.0])
    if abs(float(np.dot(up, base))) > 0.9:
        up = np.array([0.0, 1.0, 0.0])
    lat_axis = np.cross(base, up)
    lat_axis = lat_axis / np.linalg.norm(lat_axis)
    ap_axis = np.cross(lat_axis, base)
    direction = _rotate(base, ap_axis, lat_deg)
    direction = _rotate(direction, lat_axis, ap_deg)
    direction = direction / np.linalg.norm(direction)
    hit = _outer_hit(skin, target, direction)
    if hit is None:
        hit, _ = best_skull_entry(target, skin)
    return hit


def slice_mesh(image, origin, du, dv):
    """World-space slice. An ImageData can stay edge-on when its direction is ignored."""
    import pyvista as pv

    step_r = max(1, int(np.ceil(image.shape[0] / 512)))
    step_c = max(1, int(np.ceil(image.shape[1] / 512)))
    img = np.ascontiguousarray(image[::step_r, ::step_c])
    nr, nc = img.shape
    rows = np.arange(nr, dtype=float) * step_r
    cols = np.arange(nc, dtype=float) * step_c
    cc, rr = np.meshgrid(cols, rows, indexing="xy")
    pts = (
        np.asarray(origin, dtype=float)
        + rr.reshape(-1, 1) * np.asarray(dv, dtype=float)
        + cc.reshape(-1, 1) * np.asarray(du, dtype=float)
    )
    grid = pv.StructuredGrid()
    grid.points = pts
    grid.dimensions = (nc, nr, 1)
    grid.point_data["T1"] = img.ravel(order="C")
    return grid


def load_volume(t1_path: Path):
    import nibabel as nib

    img = nib.load(str(t1_path))
    data = np.asanyarray(img.dataobj, dtype=np.float32)
    return data, img.affine.astype(float)


def main() -> None:
    args = sys.argv[1:]
    if args and args[0] == "--check":
        if len(args) != 3:
            raise SystemExit("usage: planner.py --check M2M_FOLDER OUTPUT_FOLDER")
        check(args[1], args[2])
        return
    open_path = None
    if len(args) == 2 and args[0] == "--open":
        open_path = Path(args[1])
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = PlannerWindow()
    window.show()
    if open_path is not None:
        window.load_m2m(open_path)
    sys.exit(app.exec())


class PlannerWindow:
    """Brainsight-style Targets window. A click moves the crosshair only."""

    _CHOICES = (
        "Sagittal & Targets",
        "Coronal & Targets",
        "Transverse & Targets",
        "Inline & Targets",
        "Inline 90 & Targets",
        "Perpendicular & Targets",
        "3D MPR & Targets",
        "Scalp & Targets",
    )
    _FLAT = ("sagittal", "coronal", "transverse", "inline", "inline90", "perpendicular")
    _LOCKED = _FLAT

    def __init__(self):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (
            QComboBox,
            QFileDialog,
            QGridLayout,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QListWidget,
            QMessageBox,
            QPushButton,
            QSlider,
            QVBoxLayout,
            QWidget,
        )
        from pyvistaqt import QtInteractor

        class Host(QWidget):
            def closeEvent(self, event):
                for plotter in list(getattr(self._owner, "views", {}).values()):
                    try:
                        plotter.close()
                    except Exception:
                        pass
                super().closeEvent(event)

        self._Qt = Qt
        self._QFileDialog = QFileDialog
        self._QMessageBox = QMessageBox
        self.m2m = None
        self.t1 = None
        self.data = None
        self.affine = None
        self.skin = None
        self.tx_mesh = None
        self.bone = None
        self.targets = []
        self.selection = None
        self.ap_deg = 0.0
        self.lat_deg = 0.0
        self.twist_deg = 0.0
        self._frame_h = None
        self.offset_mm = 0.0
        self.clim = (0.0, 1.0)
        self._suspend = False
        self._sig = {}
        self._aimed = set()
        self.views = {}
        self.modes = {}

        self.widget = Host()
        self.widget._owner = self
        self.widget.setWindowTitle("Basis - Targets")
        self.widget.resize(1600, 960)
        root = QHBoxLayout(self.widget)

        left = QVBoxLayout()
        left_box = QWidget()
        left_box.setFixedWidth(250)
        left_box.setLayout(left)
        root.addWidget(left_box)
        open_btn = QPushButton("Open m2m folder")
        open_btn.clicked.connect(self.open_m2m)
        left.addWidget(open_btn)
        self.path_label = QLabel("No project")
        self.path_label.setWordWrap(True)
        left.addWidget(self.path_label)
        left.addWidget(QLabel("Name"))
        self.names = QListWidget()
        self.names.currentRowChanged.connect(self._select_target)
        left.addWidget(self.names, stretch=1)
        new_btn = QPushButton("New")
        new_btn.clicked.connect(self._new_entry)
        left.addWidget(new_btn)
        self.name = QLineEdit("Target")
        self.name.editingFinished.connect(self._rename)
        left.addWidget(self.name)
        left.addWidget(QLabel("Kind"))
        self.kind = QComboBox()
        self.kind.addItems(["Target", "Trajectory"])
        self.kind.currentTextChanged.connect(self._kind_changed)
        left.addWidget(self.kind)
        scalp_btn = QPushButton("Bring transducer to scalp")
        scalp_btn.clicked.connect(self._bring_to_scalp)
        left.addWidget(scalp_btn)
        go = QPushButton("Compute Simulation")
        go.clicked.connect(self._compute)
        left.addWidget(go)
        self.status = QLabel("Click a 2D image to move the crosshair. New adds it to the list.")
        self.status.setWordWrap(True)
        left.addWidget(self.status)

        grid = QGridLayout()
        root.addLayout(grid, stretch=1)
        defaults = (
            "3D MPR & Targets",
            "Inline 90 & Targets",
            "Scalp & Targets",
            "Inline & Targets",
        )
        for index, (row, col) in enumerate(((0, 0), (0, 1), (1, 0), (1, 1))):
            box = QVBoxLayout()
            choice = QComboBox()
            choice.addItems(self._CHOICES)
            choice.setCurrentText(defaults[index])
            choice.currentTextChanged.connect(lambda _text, key=index: self._mode_changed(key))
            box.addWidget(choice)
            plotter = QtInteractor(self.widget)
            box.addWidget(plotter.interactor, stretch=1)
            grid.addLayout(box, row, col)
            self.views[index] = plotter
            self.modes[index] = choice
            self._watch_clicks(plotter, index)

        right = QVBoxLayout()
        right_box = QWidget()
        right_box.setFixedWidth(250)
        right_box.setLayout(right)
        root.addWidget(right_box)
        angles = QHBoxLayout()
        self.ap, self.ap_read = self._vslider("AP", "sagittal")
        self.lat, self.lat_read = self._vslider("Lat", "inline")
        self.twist, self.twist_read = self._vslider("Twist", "roll")
        for slider, read in (
            (self.ap, self.ap_read),
            (self.lat, self.lat_read),
            (self.twist, self.twist_read),
        ):
            column = QVBoxLayout()
            column.addWidget(read[0])
            column.addWidget(slider, stretch=1)
            column.addWidget(read[1])
            column.addWidget(read[2])
            angles.addLayout(column)
            slider.valueChanged.connect(self._angles_moved)
        right.addLayout(angles)
        right.addWidget(QLabel("Offset from point"))
        self.offset_slider = QSlider(self._Qt.Orientation.Horizontal)
        self.offset_slider.setRange(0, 180)
        self.offset_slider.setValue(0)
        self.offset_read = QLabel("0 mm")
        self.offset_slider.valueChanged.connect(self._offset_moved)
        right.addWidget(self.offset_slider)
        right.addWidget(self.offset_read)
        nudge = QHBoxLayout()
        up = QPushButton("Nudge origin up")
        up.clicked.connect(lambda: self._nudge(1))
        down = QPushButton("Nudge origin down")
        down.clicked.connect(lambda: self._nudge(-1))
        nudge.addWidget(up)
        nudge.addWidget(down)
        right.addLayout(nudge)
        self.coord_label = QLabel("Coordinate system")
        self.coord_label.setWordWrap(True)
        right.addWidget(self.coord_label)
        self.origin_edits = self._xyz_block(right, "Crosshairs Origin")
        self.offset_edits = self._xyz_block(right, "Crosshairs Offset")
        self.delta = QLabel("Transducer - target    —")
        self.delta.setWordWrap(True)
        self.delta.setStyleSheet("font-size: 16px; font-weight: 700;")
        right.addWidget(self.delta)
        right.addStretch(1)

    def show(self):
        self.widget.show()
        self.widget.raise_()
        self.widget.activateWindow()

    def _vslider(self, title, note):
        from PySide6.QtWidgets import QLabel, QLineEdit, QSlider

        slider = QSlider(self._Qt.Orientation.Vertical)
        slider.setRange(-1800, 1800)
        slider.setValue(0)
        slider.setMinimumHeight(160)
        name = QLabel(title)
        name.setAlignment(self._Qt.AlignmentFlag.AlignHCenter)
        value = QLineEdit("0.0")
        value.setAlignment(self._Qt.AlignmentFlag.AlignHCenter)
        value.setMaximumWidth(72)
        value.editingFinished.connect(self._angle_edited)
        plane = QLabel(note)
        plane.setAlignment(self._Qt.AlignmentFlag.AlignHCenter)
        return slider, (name, value, plane)

    def _xyz_block(self, layout, title):
        from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit

        layout.addWidget(QLabel(title))
        edits = []
        for axis in ("X", "Y", "Z"):
            row = QHBoxLayout()
            row.addWidget(QLabel(axis))
            edit = QLineEdit("0.00")
            edit.setReadOnly(True)
            row.addWidget(edit)
            row.addWidget(QLabel("mm"))
            layout.addLayout(row)
            edits.append(edit)
        return edits

    def _watch_clicks(self, plotter, key):
        from vtkmodules.vtkRenderingCore import vtkCellPicker

        picker = vtkCellPicker()
        picker.SetTolerance(0.01)

        def _press(_obj, _event):
            kind = self._kind(self.modes[key].currentText())
            if kind not in self._LOCKED:
                return
            x, y = plotter.interactor.GetEventPosition()
            picker.Pick(x, y, 0, plotter.renderer)
            if picker.GetCellId() < 0:
                return
            self._click(picker.GetPickPosition())

        plotter.interactor.AddObserver("LeftButtonPressEvent", _press)

    def _kind(self, text):
        if text.startswith("3D"):
            return "mpr"
        if text.startswith("Inline 90"):
            return "inline90"
        if text.startswith("Inline"):
            return "inline"
        if text.startswith("Perpendicular"):
            return "perpendicular"
        if text.startswith("Sagittal"):
            return "sagittal"
        if text.startswith("Coronal"):
            return "coronal"
        if text.startswith("Transverse"):
            return "transverse"
        return "scalp"

    def open_m2m(self):
        folder = self._QFileDialog.getExistingDirectory(self.widget, "SimNIBS m2m folder")
        if folder:
            self.load_m2m(Path(folder))

    def load_m2m(self, m2m: Path):
        from PySide6.QtWidgets import QApplication

        try:
            t1 = find_t1(m2m)
            data, affine = load_volume(t1)
            skin_path = find_skin(m2m)
            skin = load_skin(skin_path, t1) if skin_path else None
            bone_path = m2m / "bone.stl"
            bone = load_skin(bone_path, t1) if bone_path.is_file() else None
            tx_path = find_tx_stl(m2m)
            tx_mesh = None
            if tx_path is not None:
                import pyvista as pv
                tx_mesh = pv.read(str(tx_path))
            from Planner.trajectory import coordinate_system
            coord = coordinate_system(str(t1))
        except Exception as exc:
            self._QMessageBox.critical(self.widget, "Planner", str(exc))
            return
        self.m2m = m2m
        self.t1 = t1
        self.data = data
        self.affine = affine
        self.skin = skin
        self.bone = bone
        self.tx_mesh = tx_mesh
        self.targets = []
        self.names.clear()
        self._sig.clear()
        self._aimed.clear()
        positive = data[data > 0]
        self.clim = tuple(float(v) for v in np.percentile(positive, [1, 99])) if positive.size else (0.0, 1.0)
        self.selection = tuple(int(n // 2) for n in data.shape)
        self.path_label.setText(str(m2m))
        self.coord_label.setText(coord)
        self._frame_h = None
        self._set_angles(0.0, 0.0, 0.0)
        self.offset_mm = 0.0
        self._set_offset_slider(0.0)
        self.status.setText("Click a 2D image to move the crosshair. New adds it to the list.")
        QApplication.processEvents()
        self._bring_to_scalp()

    def _surface(self):
        if self.skin is not None:
            return self.skin
        return self.bone

    def _seat(self, target, direction):
        """Face on the outer scalp, along a direction chosen on the skull."""
        if self.skin is not None:
            hit = _outer_hit(self.skin, target, direction)
            if hit is not None:
                return hit
        return _outer_hit(self._surface(), target, direction)

    def _direction(self, ap, lat):
        """AP tilts in the sagittal plane. Lat tilts in the coronal plane. Zero points up."""
        ap_r = np.deg2rad(float(ap))
        lat_r = np.deg2rad(float(lat))
        vec = np.array([
            np.sin(lat_r),
            np.sin(ap_r) * np.cos(lat_r),
            np.cos(ap_r) * np.cos(lat_r),
        ])
        return vec / max(float(np.linalg.norm(vec)), 1e-8)

    def _live_transducer(self):
        origin = ijk_to_world(self.affine, self.selection)
        return origin + self._direction(self.ap_deg, self.lat_deg) * float(self.offset_mm)

    def _set_offset_slider(self, mm):
        self.offset_slider.blockSignals(True)
        self.offset_slider.setValue(int(round(float(mm))))
        self.offset_slider.blockSignals(False)
        self.offset_read.setText(f"{float(mm):.0f} mm")

    def _offset_moved(self):
        self.offset_mm = float(self.offset_slider.value())
        self.offset_read.setText(f"{self.offset_mm:.0f} mm")
        self._draw()

    def _click(self, pos):
        if self.data is None:
            return
        self.selection = self._world_to_ijk(pos)
        self._draw()
        self.status.setText("Point selected. Save it if this should be the target.")

    def _append(self, name, ijk, kind):
        item = {
            "name": name,
            "ijk": tuple(int(v) for v in ijk),
            "ap": self.ap_deg,
            "lat": self.lat_deg,
            "twist": self.twist_deg,
            "distance": self.offset_mm,
            "kind": kind,
        }
        self.targets.append(item)
        self.names.blockSignals(True)
        self.names.addItem(name)
        self.names.setCurrentRow(len(self.targets) - 1)
        self.names.blockSignals(False)
        self.name.setText(name)
        if not self._suspend:
            self._draw()

    def _current(self):
        row = self.names.currentRow()
        if row < 0 or row >= len(self.targets):
            return None
        return self.targets[row]

    def _rename(self):
        item = self._current()
        if item is None or self.names.currentItem() is None:
            return
        item["name"] = self.name.text().strip() or item["name"]
        self.names.currentItem().setText(item["name"])

    def _select_target(self, _row):
        item = self._current()
        if item is None:
            return
        self.name.setText(item["name"])
        self.kind.blockSignals(True)
        self.kind.setCurrentText("Trajectory" if item.get("kind") == "trajectory" else "Target")
        self.kind.blockSignals(False)
        self.selection = tuple(int(v) for v in item["ijk"])
        self._set_angles(item["ap"], item["lat"], item["twist"])
        self.offset_mm = float(item.get("distance", self.offset_mm))
        self._set_offset_slider(self.offset_mm)
        self._draw()
        self.status.setText("Showing this list entry. The crosshair is at its point.")

    def _mode_changed(self, key):
        self._sig.pop(key, None)
        self._aimed.discard(key)
        self._draw()

    def _nudge(self, step):
        if self.selection is None or self.data is None:
            return
        i, j, k = self.selection
        k = int(np.clip(k + step, 0, self.data.shape[2] - 1))
        self.selection = (i, j, k)
        self._draw()

    def _world_to_ijk(self, world):
        inv = np.linalg.inv(self.affine)
        point = np.append(np.asarray(world, dtype=float)[:3], 1.0)
        ijk = inv @ point
        return tuple(
            int(np.clip(round(float(ijk[axis])), 0, self.data.shape[axis] - 1))
            for axis in range(3)
        )

    def _target_world(self, item):
        return ijk_to_world(self.affine, item["ijk"])

    def _angles_moved(self):
        ap = self.ap.value() / 10.0
        lat = self.lat.value() / 10.0
        twist = self.twist.value() / 10.0
        self.ap_deg = ap
        self.lat_deg = lat
        self.twist_deg = twist
        self.ap_read[1].setText(f"{self.ap_deg:.1f}")
        self.lat_read[1].setText(f"{self.lat_deg:.1f}")
        self.twist_read[1].setText(f"{self.twist_deg:.1f}")
        self._remember_pose()
        self._draw()

    def _angle_edited(self):
        for edit, slider in (
            (self.ap_read[1], self.ap),
            (self.lat_read[1], self.lat),
            (self.twist_read[1], self.twist),
        ):
            if not edit.isModified():
                continue
            edit.setModified(False)
            try:
                value = float(edit.text().strip())
            except ValueError:
                edit.setText(f"{slider.value() / 10.0:.1f}")
                continue
            value = float(np.clip(value, -180.0, 180.0))
            ticks = int(round(value * 10.0))
            if slider.value() == ticks:
                edit.setText(f"{value:.1f}")
            else:
                slider.setValue(ticks)

    def _reseat_on_scalp(self):
        """Move the transducer out to the scalp along the current direction. Sliders do not call this."""
        if self.selection is None or self.affine is None:
            return False
        origin = ijk_to_world(self.affine, self.selection)
        direction = self._direction(self.ap_deg, self.lat_deg)
        surface = self.skin if self.skin is not None else self.bone
        hit = _outer_hit(surface, origin, direction) if surface is not None else None
        if hit is None:
            return False
        self.offset_mm = float(np.linalg.norm(np.asarray(hit) - origin))
        self._set_offset_slider(self.offset_mm)
        return True

    def _remember_pose(self):
        """Store the beam on the current target. The target point itself stays put."""
        item = self._current()
        if item is None or self.selection is None:
            return
        if tuple(int(v) for v in item["ijk"]) != tuple(int(v) for v in self.selection):
            return
        item["ap"] = self.ap_deg
        item["lat"] = self.lat_deg
        item["twist"] = self.twist_deg
        item["distance"] = self.offset_mm

    def _set_angles(self, ap, lat, twist):
        self.ap_deg = float(ap)
        self.lat_deg = float(lat)
        self.twist_deg = float(twist)
        for slider, read, value in (
            (self.ap, self.ap_read, ap),
            (self.lat, self.lat_read, lat),
            (self.twist, self.twist_read, twist),
        ):
            slider.blockSignals(True)
            slider.setValue(int(round(float(value) * 10)))
            slider.blockSignals(False)
            read[1].setText(f"{float(value):.1f}")

    def _new_entry(self):
        if self.selection is None or self.data is None:
            self.status.setText("Click a 2D image first. New uses the crosshair.")
            return
        kind = "trajectory" if self.kind.currentText() == "Trajectory" else "target"
        label = "Trajectory" if kind == "trajectory" else "Target"
        number = 1 + sum(1 for item in self.targets if item.get("kind") == kind)
        self._append(f"{label} {number}", self.selection, kind)
        self.status.setText(f"Added {label} {number} at the crosshair.")

    def _kind_changed(self, text):
        item = self._current()
        if item is None:
            return
        item["kind"] = "trajectory" if text == "Trajectory" else "target"
        self._draw()

    def _bring_to_scalp(self):
        if not self._reseat_on_scalp():
            self.status.setText("That direction does not meet the scalp.")
            self._draw()
            return
        self._remember_pose()
        self._draw()
        self.status.setText("Transducer is on the scalp. The saved target stays where it was.")

    def _show_offset(self):
        if self.selection is None or self.affine is None:
            for edit in self.origin_edits + self.offset_edits:
                edit.setText("0.00")
            self.delta.setText("Offset from the selected point")
            return
        origin = ijk_to_world(self.affine, self.selection)
        delta = self._live_transducer() - origin
        for edit, value in zip(self.origin_edits, origin):
            edit.setText(f"{float(value):.2f}")
        for edit, value in zip(self.offset_edits, delta):
            edit.setText(f"{float(value):.2f}")
        self.delta.setText(
            "Offset from point (mm)\nX  {0:.2f}\nY  {1:.2f}\nZ  {2:.2f}".format(*delta)
        )

    def _draw(self):
        if self.data is None or self._suspend:
            return
        self._show_offset()
        for key, plotter in self.views.items():
            self._draw_one(key, plotter)

    def _image_sig(self, kind):
        i, j, k = self.selection
        if kind == "scalp":
            return ("scalp",)
        if kind == "mpr":
            return ("mpr", i, j, k)
        if kind in ("inline", "inline90", "perpendicular"):
            return (kind, i, j, k, round(self.ap_deg, 1), round(self.lat_deg, 1), round(self.twist_deg, 1))
        if kind == "sagittal":
            return ("sagittal", i)
        if kind == "coronal":
            return ("coronal", j)
        return ("transverse", k)

    def _slices(self):
        i, j, k = self.selection
        ai, aj, ak = self.affine[:3, 0], self.affine[:3, 1], self.affine[:3, 2]
        transverse = (self.data[:, :, k], ijk_to_world(self.affine, (0, 0, k)), aj, ai, ak)
        return {
            "transverse": transverse,
            "sagittal": (self.data[i, :, :], ijk_to_world(self.affine, (i, 0, 0)), ak, aj, ai),
            "coronal": (self.data[:, j, :], ijk_to_world(self.affine, (0, j, 0)), ak, ai, aj),
        }

    def _beam_axes(self, kind):
        """Inline contains the beam. Perpendicular looks along the beam, at the transducer face."""
        z_axis = self._direction(self.ap_deg, self.lat_deg)
        horizontal = _carry_horizontal(self._frame_h, z_axis)
        self._frame_h = horizontal
        horizontal = _rotate(horizontal, z_axis, self.twist_deg)
        if kind == "inline90":
            horizontal = np.cross(z_axis, horizontal)
            horizontal = horizontal / max(float(np.linalg.norm(horizontal)), 1e-8)
        if kind == "perpendicular":
            vertical = np.cross(z_axis, horizontal)
            vertical = vertical / max(float(np.linalg.norm(vertical)), 1e-8)
            normal = z_axis
        else:
            vertical = z_axis
            normal = np.cross(horizontal, vertical)
            normal = normal / max(float(np.linalg.norm(normal)), 1e-8)
        origin = ijk_to_world(self.affine, self.selection)
        return horizontal, vertical, normal, origin

    def _view_axes(self, kind):
        if kind in ("sagittal", "coronal", "transverse"):
            _image, origin, du, dv, normal = self._slices()[kind]
            return du, dv, normal, origin
        return self._beam_axes(kind)

    def _oblique_mesh(self, origin, du, dv):
        import pyvista as pv
        from scipy.ndimage import map_coordinates

        spacing = float(min(np.linalg.norm(self.affine[:3, axis]) for axis in range(3)))
        spacing = max(spacing, 0.5)
        span = 220.0
        count = int(np.clip(round(span / spacing) + 1, 32, 360))
        coords = np.linspace(-span / 2.0, span / 2.0, count)
        uu, vv = np.meshgrid(coords, coords, indexing="xy")
        horizontal = np.asarray(du, dtype=float)
        vertical = np.asarray(dv, dtype=float)
        horizontal = horizontal / max(float(np.linalg.norm(horizontal)), 1e-8)
        vertical = vertical / max(float(np.linalg.norm(vertical)), 1e-8)
        world = np.asarray(origin, dtype=float) + uu[..., None] * horizontal + vv[..., None] * vertical
        inv = np.linalg.inv(self.affine)
        hom = np.concatenate([world, np.ones(uu.shape + (1,))], axis=-1)
        ijk = hom @ inv.T
        values = map_coordinates(
            self.data,
            [ijk[..., 0], ijk[..., 1], ijk[..., 2]],
            order=1,
            mode="constant",
            cval=0.0,
            prefilter=False,
        ).astype(np.float32)
        grid = pv.StructuredGrid()
        grid.points = np.ascontiguousarray(world.reshape(-1, 3))
        grid.dimensions = (count, count, 1)
        grid.point_data["T1"] = np.ascontiguousarray(values).ravel(order="C")
        return grid

    def _drop(self, plotter, names):
        for name in names:
            if name in plotter.actors:
                plotter.remove_actor(name, reset_camera=False, render=False)

    def _add_slice(self, plotter, spec, name):
        image, origin, du, dv, _normal = spec
        mesh = slice_mesh(image, origin, du, dv)
        plotter.add_mesh(
            mesh, scalars="T1", cmap="gray", clim=self.clim,
            show_scalar_bar=False, lighting=False, name=name,
        )
        return image, origin, du, dv

    def _aim(self, plotter, focal, normal, scale, parallel, up=None):
        normal = np.asarray(normal, dtype=float)
        normal = normal / max(float(np.linalg.norm(normal)), 1e-8)
        if up is None:
            up = np.array([0.0, 0.0, 1.0])
            if abs(float(np.dot(up, normal))) > 0.85:
                up = np.array([0.0, 1.0, 0.0])
        else:
            up = np.asarray(up, dtype=float)
            up = up / max(float(np.linalg.norm(up)), 1e-8)
        camera = plotter.camera
        camera.focal_point = np.asarray(focal, dtype=float)
        camera.position = camera.focal_point + normal * max(float(scale) * 4.0, 300.0)
        camera.up = up
        if parallel:
            camera.parallel_projection = True
            camera.parallel_scale = max(float(scale), 1.0)
        else:
            camera.parallel_projection = False
        camera.clipping_range = (1.0, 8000.0)

    def _style(self, plotter, kind):
        if kind in self._LOCKED:
            from vtkmodules.vtkInteractionStyle import vtkInteractorStyleImage
            plotter.interactor.SetInteractorStyle(vtkInteractorStyleImage())
            plotter.enable_parallel_projection()
        else:
            from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
            plotter.interactor.SetInteractorStyle(vtkInteractorStyleTrackballCamera())

    def _draw_one(self, key, plotter):
        kind = self._kind(self.modes[key].currentText())
        sig = self._image_sig(kind)
        if self._sig.get(key) != sig:
            self._drop(plotter, ("img", "img_ax", "img_sag", "img_cor", "skin"))
            self._sig[key] = sig
            self._style(plotter, kind)
            if kind == "scalp":
                plotter.set_background("#b9b9b9")
                if self.skin is not None:
                    plotter.add_mesh(self.skin, color="#c4a484", name="skin")
            else:
                plotter.set_background("black")
                specs = self._slices()
                if kind == "mpr":
                    self._add_slice(plotter, specs["transverse"], "img_ax")
                    self._add_slice(plotter, specs["sagittal"], "img_sag")
                    self._add_slice(plotter, specs["coronal"], "img_cor")
                elif kind in ("inline", "inline90", "perpendicular"):
                    du, dv, _normal, origin = self._beam_axes(kind)
                    plotter.add_mesh(
                        self._oblique_mesh(origin, du, dv),
                        scalars="T1", cmap="gray", clim=self.clim,
                        show_scalar_bar=False, lighting=False, name="img",
                    )
                else:
                    self._add_slice(plotter, specs[kind], "img")
        self._drop(plotter, ("target", "cross", "beam", "tx", "hx", "hy", "hz", "contact", "arrow", "mark", "label"))
        self._add_overlays(plotter, kind)
        if kind in self._LOCKED or key not in self._aimed:
            self._aim_view(plotter, kind)
            if kind not in self._LOCKED:
                self._aimed.add(key)
        plotter.render()

    def _aim_view(self, plotter, kind):
        if kind == "scalp":
            focal = np.array(self.skin.center) if self.skin is not None else np.zeros(3)
            if self.selection is not None and self.offset_mm > 1.0:
                focal = 0.55 * focal + 0.45 * self._live_transducer()
            self._aim(plotter, focal, np.array([0.45, -1.0, 0.72]), 190.0, False)
            return
        if kind == "mpr":
            focal = ijk_to_world(self.affine, np.array(self.data.shape) / 2.0)
            # Sagittal slice lies in YZ. Look along X so it shows the side of the head.
            self._aim(plotter, focal, np.array([1.0, -0.32, 0.2]), 150.0, False)
            return
        du, dv, normal, origin = self._view_axes(kind)
        if kind in ("inline", "inline90"):
            self._aim(plotter, origin, normal, 110.0, True, up=dv)
            return
        if kind == "perpendicular":
            self._aim(plotter, origin, normal, 110.0, True, up=dv)
            return
        image, origin, du, dv, normal = self._slices()[kind]
        focal = origin + du * (image.shape[1] / 2.0) + dv * (image.shape[0] / 2.0)
        span = max(np.linalg.norm(du) * image.shape[1], np.linalg.norm(dv) * image.shape[0])
        self._aim(plotter, focal, normal, 0.5 * float(span), True)

    def _name_label(self, plotter, point, text):
        """Name sits on the target point. The offset mark is the transducer, and it stays unlabeled."""
        try:
            plotter.add_point_labels(
                [np.asarray(point, dtype=float)], [text], name="label", font_size=14,
                text_color="#00e5ff", show_points=False, shape_opacity=0,
                reset_camera=False, render=False,
            )
        except Exception:
            pass

    def _add_overlays(self, plotter, kind):
        import pyvista as pv

        selected = ijk_to_world(self.affine, self.selection)
        placed = self._live_transducer()
        if kind in self._FLAT:
            du, dv, _normal, _origin = self._view_axes(kind)
            du = du / max(float(np.linalg.norm(du)), 1e-8)
            dv = dv / max(float(np.linalg.norm(dv)), 1e-8)
            plotter.add_mesh(pv.Line(selected - du * 220, selected + du * 220), color="#39ff14", line_width=2, name="hx")
            plotter.add_mesh(pv.Line(selected - dv * 220, selected + dv * 220), color="#39ff14", line_width=2, name="hy")
            in_plane = du * float(np.dot(placed - selected, du)) + dv * float(np.dot(placed - selected, dv))
            if float(np.linalg.norm(in_plane)) > 1.5:
                tip = selected + in_plane
                plotter.add_mesh(pv.Line(selected, tip), color="#00e5ff", line_width=2, name="arrow")
                plotter.add_mesh(pv.Line(tip - du * 6, tip + du * 6), color="#ff5a5a", line_width=3, name="mark")
                plotter.add_mesh(pv.Line(tip - dv * 6, tip + dv * 6), color="#ff5a5a", line_width=3, name="contact")
            item = self._current()
            if item is not None:
                self._name_label(plotter, self._target_world(item), item["name"])
            return
        item = self._current()
        if item is not None:
            center = self._target_world(item)
            plotter.add_mesh(pv.Sphere(radius=2.0, center=center), color="red", name="target")
            self._name_label(plotter, center, item["name"])
        if float(self.offset_mm) > 1.0:
            plotter.add_mesh(pv.Line(selected, placed), color="#00e5ff", line_width=3, name="beam")
            if self.tx_mesh is not None:
                direction = placed - selected
                mat = brainsight_matrix(selected, self.ap_deg, self.lat_deg, self.twist_deg)
                mesh = self.tx_mesh.copy(deep=True)
                mesh.points = (mat[:3, :3] @ np.asarray(self.tx_mesh.points).T).T + placed
                plotter.add_mesh(mesh, color="#3cb44b", name="tx")
                _ = direction

    def _matrix(self, item):
        origin = self._target_world(item)
        return brainsight_matrix(origin, item.get("ap", 0.0), item.get("lat", 0.0), item.get("twist", 0.0))

    def _compute(self):
        item = self._current()
        if item is None or self.m2m is None:
            self._QMessageBox.warning(self.widget, "Planner", "Add a target or trajectory first.")
            return
        item["name"] = self.name.text().strip() or item["name"]
        dest = self.m2m / trajectory_filename(item["name"])
        try:
            mat = self._matrix(item)
        except ValueError as exc:
            self._QMessageBox.warning(self.widget, "Planner", str(exc))
            return
        write_trajectory(dest, item["name"], mat, str(self.t1))
        folder = write_sync(str(dest), str(self.t1), str(self.m2m), str(self.m2m))
        self.status.setText(f"Wrote {dest.name}. BabelBrain was not started.")
        self._QMessageBox.information(
            self.widget,
            "Planner",
            f"Trajectory:\n{dest}\n\nSync files:\n{folder}\n\nBabelBrain was not started.",
        )


if __name__ == "__main__":
    main()
