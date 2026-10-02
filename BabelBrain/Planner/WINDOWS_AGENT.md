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

STN file: FSL `STN-maxprob-thr25-0.5mm.nii.gz` (Forstmann, labels 1 left and 2 right). It is in the same MNI space as the SimNIBS MNI template. Warp with SimNIBS 4.6 `warp_volume(src, m2m, out, transformation_direction="mni2subject", transformation_type="nonl", reference=m2m/T1.nii.gz, order=0)`. That uses the m2m `toMNI` nonlinear field. `order=0` keeps labels. Output must match the T1 shape and affine. Same call for any other MNI atlas. No simulation. Do not upload the subject. Scalp sliders stay until the Mac user says otherwise.

### Reply

- Commit tested: 55c606b
- `--check`: not rerun. No simulation.
- Sync files: not written
- Launch: unchanged. The STN overlay stays the Forstmann map warped onto the T1. AP and Lat keep the current offset.
- Change needed: list the other MNI atlas files already on the Mac, with region names, so the planner can offer them with the same warp.













