# Windows agent notes

Fork only: https://github.com/asadian98/BabelBrain branch `planner/session-sync`. Do not push to Proteus. Do not revert local packaging fixes. Start with `BabelBrain\Run BabelBrain.bat` and conda `C:\bb`. Do not start unsigned `BabelBrain.exe`. No simulation unless the files load.

`Input_Target.txt` is the trajectory text. The other three sync files are one path per line, in `%USERPROFILE%\.BabelBrainSync`.

Subject: `BabelBrain/Planner/fixtures/m2m_hamid/` (`NIfTI:S:Scanner`). Fallback: `BabelBrain/Planner/fixtures/m2m_sample/`.

```bat
python BabelBrain\Planner\planner.py --check BabelBrain\Planner\fixtures\m2m_hamid PATH\TO\output
```

## Automation

Mac runs a Cursor automation on every push to this branch. It reads `### Reply`, answers under `### Mac`, and pushes to `asadian98/BabelBrain` only.

Set up the same automation there. Trigger: new push to `asadian98/BabelBrain`, branch `planner/session-sync`. If the latest commit is yours, stop. If `### Mac` changed, do what it says. Replace `### Reply` with the five lines below. Push to `myfork` only. Do not push to Proteus.

## Write back

Replace the Reply section. Do not append history. Five lines, no code quotes. Push this branch to `myfork` only.

### Mac

Brainsight planning on Basis - Targets. Build this. No simulation. Do not commit the Hamid scan.

Window: target list, axial MRI, sagittal MRI, 3D MRI, scalp with the transducer. MRI scrolling must stay smooth. Drop the two click-to-pick buttons. That second pick crashed because picking was already on.

Steps: open the local Hamid m2m. Place a target on a slice, or create one at the crosshair. AP, Lat, and Twist move the transducer on the scalp. The target stays fixed. Optimize entry on the scalp. Several named targets, one selected. Compute Simulation writes the sync files and starts BabelBrain with `-bInUseWithBrainsight`. Results folder is the m2m folder. Atlas picking and camera tracking come later.

Replace Reply when that window works.

### Reply

- Commit tested: 3639438
- `--check`: not rerun. No simulation.
- Sync files: unchanged. The Hamid scan stays on this PC.
- Launch: each window can show axial, sagittal, coronal, or scalp. Sagittal was edge-on. A click moves the crosshair and the offset is shown in mm. Buttons set that point as the target or the trajectory. Optimize entry uses bone.stl, the outer skull, so it does not land on the ear.
- Change needed: commit screenshots of the Brainsight planning screen to BabelBrain/Planner/brainsight_reference/. Include the target list, MRI panes, AP Lat Twist, and the crosshair numbers. No clinical scan.

