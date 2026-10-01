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


def _first_hit(surface, origin, direction):
    origin = np.asarray(origin, dtype=float).reshape(3)
    direction = np.asarray(direction, dtype=float).reshape(3)
    direction = direction / np.linalg.norm(direction)
    start = origin + direction * 2.0
    far = origin + direction * 400.0
    hits, _ = surface.ray_trace(start, far)
    if len(hits) == 0:
        return None
    hits = np.atleast_2d(np.asarray(hits, dtype=float))
    return hits[int(np.argmin(np.linalg.norm(hits - origin, axis=1)))]


def best_skull_entry(target, surface) -> tuple[np.ndarray, np.ndarray]:
    """Entry on the outer surface. The nearest point can be the ear."""
    target = np.asarray(target, dtype=float).reshape(3)
    if "Normals" not in surface.point_data:
        surface.compute_normals(inplace=True, cell_normals=False, point_normals=True)
    normals = np.asarray(surface.point_data["Normals"])
    best_hit = None
    best_dir = None
    best_score = 1e18
    for n in range(64):
        theta = np.arccos(1.0 - 2.0 * ((n + 0.5) / 64.0))
        phi = np.pi * (1.0 + 5.0 ** 0.5) * n
        direction = np.array([
            np.sin(theta) * np.cos(phi),
            np.sin(theta) * np.sin(phi),
            np.cos(theta),
        ])
        if direction[2] < -0.15:
            continue
        hit = _first_hit(surface, target, direction)
        if hit is None:
            continue
        outward = hit - target
        dist = float(np.linalg.norm(outward))
        if dist < 1e-3:
            continue
        outward = outward / dist
        idx = int(surface.find_closest_point(hit))
        normal = normals[idx]
        if float(np.dot(normal, outward)) < 0:
            normal = -normal
        align = float(np.dot(normal, outward))
        score = dist * (1.5 - align)
        if hit[2] < target[2] - 15.0:
            score += 100.0
        if score < best_score:
            best_score = score
            best_hit = hit
            best_dir = outward
    if best_hit is None:
        idx = int(surface.find_closest_point(target + np.array([0.0, 0.0, 40.0])))
        best_hit = np.array(surface.points[idx], dtype=float)
        best_dir = best_hit - target
        best_dir = best_dir / max(np.linalg.norm(best_dir), 1e-3)
    return best_hit, best_dir


def transducer_on_skin(target, skin, ap_deg, lat_deg, base_dir=None) -> np.ndarray:
    """Tilt the ray from the target and put the transducer face on the surface."""
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
    hit = _first_hit(skin, target, direction)
    if hit is None:
        hit, _ = best_skull_entry(target, skin)
    return hit


def apply_twist(mat: np.ndarray, degrees: float) -> np.ndarray:
    out = np.array(mat, dtype=float, copy=True)
    theta = np.deg2rad(degrees)
    cos, sin = np.cos(theta), np.sin(theta)
    x_col, y_col = out[:3, 0].copy(), out[:3, 1].copy()
    out[:3, 0] = cos * x_col + sin * y_col
    out[:3, 1] = -sin * x_col + cos * y_col
    return out


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
    """Target list, MRI slices, scalp, and AP / Lat / Twist. No point-picking."""

    def __init__(self):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (
            QDoubleSpinBox,
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
        self._planes = {}
        self._locked = set()

        self.widget = QWidget()
        self.widget.setWindowTitle("BabelBrain planner")
        self.widget.resize(1400, 800)
        root = QHBoxLayout(self.widget)

        side = QVBoxLayout()
        root.addLayout(side)
        side.addWidget(QLabel("Transducer offset from target"))
        self.ap = self._angle()
        self.lat = self._angle()
        self.twist = self._angle()
        for box, label in ((self.ap, "AP"), (self.lat, "Lat"), (self.twist, "Twist")):
            row = QHBoxLayout()
            name = QLabel(label)
            name.setMinimumWidth(48)
            row.addWidget(name)
            row.addWidget(box)
            side.addLayout(row)
            box.valueChanged.connect(self._pose_changed)
        self.offset_label = QLabel("Crosshair offset  —")
        self.offset_label.setWordWrap(True)
        self.offset_label.setStyleSheet("font-size: 16px; font-weight: 700;")
        side.addWidget(self.offset_label)
        as_target = QPushButton("Set selection as target")
        as_target.clicked.connect(self._set_as_target)
        side.addWidget(as_target)
        as_traj = QPushButton("Set selection as trajectory")
        as_traj.clicked.connect(self._set_as_trajectory)
        side.addWidget(as_traj)
        opt = QPushButton("Optimize entry")
        opt.clicked.connect(self._optimize)
        side.addWidget(opt)
        open_btn = QPushButton("Open m2m folder")
        open_btn.clicked.connect(self.open_m2m)
        side.addWidget(open_btn)
        self.path_label = QLabel("No project")
        self.path_label.setWordWrap(True)
        side.addWidget(self.path_label)
        self.names = QListWidget()
        self.names.currentRowChanged.connect(self._select_target)
        side.addWidget(self.names)
        self.name = QLineEdit("Target")
        side.addWidget(self.name)
        go = QPushButton("Compute Simulation")
        go.clicked.connect(self._compute)
        side.addWidget(go)
        self.status = QLabel("Click a view to move the crosshair. Then set it as the target or the trajectory.")
        self.status.setWordWrap(True)
        side.addWidget(self.status)

        grid = QGridLayout()
        root.addLayout(grid, stretch=1)
        self.views = {}
        self.modes = {}
        defaults = ("Axial", "Sagittal", "Coronal", "Scalp")
        for index, (row, col) in enumerate(((0, 0), (0, 1), (1, 0), (1, 1))):
            box = QVBoxLayout()
            from PySide6.QtWidgets import QComboBox
            choice = QComboBox()
            choice.addItems(["Axial", "Sagittal", "Coronal", "Scalp"])
            choice.setCurrentText(defaults[index])
            choice.currentTextChanged.connect(lambda _text, key=index: self._mode_changed(key))
            box.addWidget(choice)
            plotter = QtInteractor(self.widget)
            box.addWidget(plotter.interactor, stretch=1)
            grid.addLayout(box, row, col)
            self.views[index] = plotter
            self.modes[index] = choice
            self._lock_view(plotter)
        self.k_slider = self._slider("Axial slice")
        self.i_slider = self._slider("Sagittal slice")
        side.addWidget(self.k_slider)
        side.addWidget(self.i_slider)
        self.k_slider.valueChanged.connect(self._slice_sliders)
        self.i_slider.valueChanged.connect(self._slice_sliders)

    def show(self):
        self.widget.show()

    def _lock_view(self, plotter):
        from vtkmodules.vtkInteractionStyle import vtkInteractorStyleImage
        from vtkmodules.vtkRenderingCore import vtkCellPicker
        plotter.interactor.SetInteractorStyle(vtkInteractorStyleImage())
        plotter.enable_parallel_projection()
        picker = vtkCellPicker()
        picker.SetTolerance(0.005)

        def _press(_obj, _event):
            x, y = plotter.interactor.GetEventPosition()
            picker.Pick(x, y, 0, plotter.renderer)
            if picker.GetCellId() < 0:
                return
            self._click_target(picker.GetPickPosition())

        plotter.interactor.AddObserver("LeftButtonPressEvent", _press)

    def _angle(self):
        from PySide6.QtWidgets import QDoubleSpinBox
        box = QDoubleSpinBox()
        box.setRange(-180, 180)
        box.setDecimals(1)
        box.setSingleStep(1.0)
        return box

    def _slider(self, label):
        from PySide6.QtWidgets import QSlider
        slider = QSlider(self._Qt.Orientation.Horizontal)
        slider.setObjectName(label)
        return slider

    def open_m2m(self):
        folder = self._QFileDialog.getExistingDirectory(self.widget, "SimNIBS m2m folder")
        if folder:
            self.load_m2m(Path(folder))

    def load_m2m(self, m2m: Path):
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
        self.k_slider.blockSignals(True)
        self.i_slider.blockSignals(True)
        self.k_slider.setRange(0, data.shape[2] - 1)
        self.i_slider.setRange(0, data.shape[0] - 1)
        self.k_slider.setValue(data.shape[2] // 2)
        self.i_slider.setValue(data.shape[0] // 2)
        self.k_slider.blockSignals(False)
        self.i_slider.blockSignals(False)
        self.selection = (data.shape[0] // 2, data.shape[1] // 2, data.shape[2] // 2)
        self.path_label.setText(str(m2m))
        self._planes.clear()
        self._draw_slices()
        self.status.setText("Click a view to move the crosshair. Then set it as the target or the trajectory.")

    def _ijk(self):
        if self.selection is not None:
            return self.selection
        j = self.data.shape[1] // 2
        return (self.i_slider.value(), j, self.k_slider.value())

    def _slice_sliders(self):
        if self.data is None:
            return
        if self.selection is None:
            j = self.data.shape[1] // 2
        else:
            j = self.selection[1]
        self.selection = (self.i_slider.value(), j, self.k_slider.value())
        self._draw_slices()

    def _mode_changed(self, key):
        self._planes.pop(key, None)
        self._draw_slices()

    def _look(self, plotter, key, normal, focal):
        if key in self._planes:
            return
        normal = np.asarray(normal, dtype=float)
        normal = normal / np.linalg.norm(normal)
        plotter.camera.position = np.asarray(focal, dtype=float) + normal * 400.0
        plotter.camera.focal_point = focal
        up = np.array([0.0, 0.0, 1.0])
        if abs(float(np.dot(up, normal))) > 0.9:
            up = np.array([0.0, 1.0, 0.0])
        plotter.camera.up = up
        plotter.reset_camera()
        self._planes[key] = True

    def _draw_slices(self):
        if self.data is None:
            return
        i, j, k = self._ijk()
        ai, aj, ak = self.affine[:3, 0], self.affine[:3, 1], self.affine[:3, 2]
        slices = {
            "Axial": (self.data[:, :, k], ijk_to_world(self.affine, (0, 0, k)), ai, aj, ak),
            "Sagittal": (self.data[i, :, :], ijk_to_world(self.affine, (i, 0, 0)), aj, ak, ai),
            "Coronal": (self.data[:, j, :], ijk_to_world(self.affine, (0, j, 0)), ai, ak, aj),
        }
        for key, plotter in self.views.items():
            mode = self.modes[key].currentText()
            if mode == "Scalp":
                if self.skin is not None:
                    plotter.add_mesh(self.skin, color="#d8c3a5", opacity=0.35, name="img")
                focal = np.array(self.skin.center) if self.skin is not None else np.zeros(3)
                self._look(plotter, key, np.array([0.0, -1.0, 0.0]), focal)
            else:
                image, origin, du, dv, normal = slices[mode]
                grid = self._plane(image, origin, du, dv)
                plotter.add_mesh(grid, scalars="T1", cmap="gray", name="img", show_scalar_bar=False)
                center = origin + du * (image.shape[1] / 2.0) + dv * (image.shape[0] / 2.0)
                self._look(plotter, key, normal, center)
        self._mark_target()

    def _plane(self, image, origin, du, dv):
        import pyvista as pv
        height, width = image.shape
        grid = pv.ImageData(dimensions=(width, height, 1), spacing=(1, 1, 1))
        grid.point_data["T1"] = np.ravel(np.ascontiguousarray(image.T), order="F")
        grid.origin = origin
        direction = np.eye(3)
        direction[:, 0] = du
        direction[:, 1] = dv
        normal = np.cross(du, dv)
        norm = np.linalg.norm(normal)
        direction[:, 2] = normal / norm if norm else np.array([0.0, 0.0, 1.0])
        grid.direction_matrix = direction
        return grid

    def _current(self):
        row = self.names.currentRow()
        if row < 0 or row >= len(self.targets):
            return None
        return self.targets[row]

    def _click_target(self, pos):
        if self.data is None:
            return
        inv = np.linalg.inv(self.affine)
        ijk = inv @ np.array([pos[0], pos[1], pos[2], 1.0], dtype=float)
        i = int(np.clip(round(float(ijk[0])), 0, self.data.shape[0] - 1))
        j = int(np.clip(round(float(ijk[1])), 0, self.data.shape[1] - 1))
        k = int(np.clip(round(float(ijk[2])), 0, self.data.shape[2] - 1))
        self.selection = (i, j, k)
        self.i_slider.blockSignals(True)
        self.k_slider.blockSignals(True)
        self.i_slider.setValue(i)
        self.k_slider.setValue(k)
        self.i_slider.blockSignals(False)
        self.k_slider.blockSignals(False)
        self._draw_slices()

    def _set_as_target(self):
        if self.selection is None:
            return
        item = self._current()
        if item is None:
            self._add_target(self.selection)
            return
        item["ijk"] = self.selection
        self._draw_slices()

    def _set_as_trajectory(self):
        item = self._current()
        surface = self.bone if self.bone is not None else self.skin
        if item is None or self.selection is None or surface is None:
            self._QMessageBox.warning(self.widget, "Planner", "Set a target first, then a trajectory.")
            return
        target = self._target_world(item)
        point = ijk_to_world(self.affine, self.selection)
        direction = point - target
        if np.linalg.norm(direction) < 1.0:
            return
        direction = direction / np.linalg.norm(direction)
        hit = _first_hit(surface, target, direction)
        if hit is None:
            hit, direction = best_skull_entry(target, surface)
        item["base"] = direction
        item["entry"] = hit
        item["ap"] = 0.0
        item["lat"] = 0.0
        for box in (self.ap, self.lat):
            box.blockSignals(True)
            box.setValue(0.0)
            box.blockSignals(False)
        self._mark_target()

    def _add_target(self, ijk):
        item = {
            "name": self.name.text().strip() or f"Target {len(self.targets) + 1}",
            "ijk": ijk,
            "ap": self.ap.value(),
            "lat": self.lat.value(),
            "twist": self.twist.value(),
        }
        self.targets.append(item)
        self.names.addItem(item["name"])
        self.names.setCurrentRow(len(self.targets) - 1)

    def _new_target(self):
        if self.data is None:
            return
        ijk = self._ijk()
        item = {
            "name": self.name.text().strip() or f"Target {len(self.targets) + 1}",
            "ijk": ijk,
            "ap": 0.0,
            "lat": 0.0,
            "twist": 0.0,
        }
        self.targets.append(item)
        self.names.addItem(item["name"])
        self.names.setCurrentRow(len(self.targets) - 1)
        self._optimize()

    def _select_target(self, row):
        item = self._current()
        if item is None:
            return
        self.name.setText(item["name"])
        self.i_slider.blockSignals(True)
        self.k_slider.blockSignals(True)
        self.i_slider.setValue(int(item["ijk"][0]))
        self.k_slider.setValue(int(item["ijk"][2]))
        self.i_slider.blockSignals(False)
        self.k_slider.blockSignals(False)
        for box, key in ((self.ap, "ap"), (self.lat, "lat"), (self.twist, "twist")):
            box.blockSignals(True)
            box.setValue(float(item[key]))
            box.blockSignals(False)
        self._draw_slices()

    def _pose_changed(self):
        item = self._current()
        if item is None:
            return
        item["name"] = self.name.text().strip() or item["name"]
        item["ap"] = self.ap.value()
        item["lat"] = self.lat.value()
        item["twist"] = self.twist.value()
        self.names.currentItem().setText(item["name"])
        self._mark_target()

    def _optimize(self):
        item = self._current()
        surface = self.bone if self.bone is not None else self.skin
        for box in (self.ap, self.lat):
            box.blockSignals(True)
            box.setValue(0.0)
            box.blockSignals(False)
        if item is None or surface is None:
            return
        hit, direction = best_skull_entry(self._target_world(item), surface)
        item["ap"] = 0.0
        item["lat"] = 0.0
        item["base"] = direction
        item["entry"] = hit
        self._mark_target()

    def _target_world(self, item):
        return ijk_to_world(self.affine, item["ijk"])

    def _transducer_world(self, item):
        target = self._target_world(item)
        surface = self.bone if self.bone is not None else self.skin
        if surface is None:
            return target + np.array([0.0, 0.0, 40.0])
        if item.get("base") is None:
            hit, direction = best_skull_entry(target, surface)
            item["base"] = direction
            item["entry"] = hit
        return transducer_on_skin(target, surface, item["ap"], item["lat"], item["base"])

    def _show_offset(self):
        if self.selection is None or self.affine is None:
            self.offset_label.setText("Crosshair offset  —")
            return
        selected = ijk_to_world(self.affine, self.selection)
        item = self._current()
        if item is None:
            self.offset_label.setText("Crosshair  {0:.1f}   {1:.1f}   {2:.1f} mm".format(*selected))
            return
        offset = selected - self._target_world(item)
        self.offset_label.setText("Crosshair offset  {0:.1f}   {1:.1f}   {2:.1f} mm".format(*offset))

    def _mark_target(self):
        self._show_offset()
        if self.data is None:
            return
        import pyvista as pv
        item = self._current()
        i, j, k = self._ijk()
        selected = ijk_to_world(self.affine, (i, j, k))
        target = self._target_world(item) if item is not None else None
        transducer = self._transducer_world(item) if item is not None else None
        ai, aj, ak = self.affine[:3, 0], self.affine[:3, 1], self.affine[:3, 2]
        axes = {
            "Axial": (ai, aj),
            "Sagittal": (aj, ak),
            "Coronal": (ai, ak),
        }
        placed = None
        if item is not None and self.tx_mesh is not None and transducer is not None:
            mat = self._matrix(item)
            placed = self.tx_mesh.copy(deep=True)
            placed.points = (mat[:3, :3] @ np.asarray(self.tx_mesh.points).T).T + transducer
        for key, plotter in self.views.items():
            mode = self.modes[key].currentText()
            if mode == "Scalp":
                if target is not None:
                    plotter.add_mesh(pv.Sphere(radius=2.0, center=target), color="red", name="target")
                plotter.add_mesh(pv.Sphere(radius=3.0, center=selected), color="yellow", name="cross")
                if transducer is not None:
                    plotter.add_mesh(pv.Line(target, transducer), color="#1f4e79", line_width=3, name="beam")
                if placed is not None:
                    plotter.add_mesh(placed, color="#1f4e79", opacity=0.85, name="tx")
                continue
            du, dv = axes[mode]
            du = du / np.linalg.norm(du)
            dv = dv / np.linalg.norm(dv)
            plotter.add_mesh(pv.Line(selected - du * 12, selected + du * 12), color="yellow", line_width=4, name="hx")
            plotter.add_mesh(pv.Line(selected - dv * 12, selected + dv * 12), color="yellow", line_width=4, name="hy")
            if target is not None:
                plotter.add_mesh(pv.Sphere(radius=2.0, center=target), color="red", name="target")

    def _matrix(self, item):
        target = self._target_world(item)
        transducer = self._transducer_world(item)
        return apply_twist(pose_matrix(target, transducer), item["twist"])

    def _compute(self):
        item = self._current()
        if item is None or self.m2m is None:
            self._QMessageBox.warning(self.widget, "Planner", "Open an m2m folder and add a target.")
            return
        item["name"] = self.name.text().strip() or item["name"]
        out = self.m2m
        dest = out / trajectory_filename(item["name"])
        try:
            mat = self._matrix(item)
        except ValueError as exc:
            self._QMessageBox.warning(self.widget, "Planner", str(exc))
            return
        write_trajectory(dest, item["name"], mat, str(self.t1))
        folder = write_sync(str(dest), str(self.t1), str(self.m2m), str(out))
        self.status.setText(f"Wrote {dest.name} and the sync files.")
        self._launch_brainsight()
        self._QMessageBox.information(self.widget, "Planner", f"Trajectory:\n{dest}\n\nSync files:\n{folder}")

    def _launch_brainsight(self):
        import os
        import subprocess
        launcher = Path(r"C:\t\launch_brainsight.py")
        python = Path(r"C:\bb\python.exe")
        if not python.is_file():
            python = Path(sys.executable)
        env = os.environ.copy()
        env["PATH"] = r"C:\bb;C:\bb\Library\bin;C:\bb\Scripts;" + env.get("PATH", "")
        if launcher.is_file():
            subprocess.Popen([str(python), "-u", str(launcher)], env=env)
            return
        babel = _BABEL / "BabelBrain.py"
        env["PYTHONPATH"] = str(_BABEL) + os.pathsep + str(_BABEL.parent)
        subprocess.Popen([str(python), str(babel), "-bInUseWithBrainsight"], env=env, cwd=str(_BABEL))


if __name__ == "__main__":
    main()
