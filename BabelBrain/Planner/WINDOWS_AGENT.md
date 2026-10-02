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

Use the 1 mm max-prob label volumes under `/Users/amir/fsl/data/atlases`. Same `warp_volume` call as the STN, `order=0`. Region names are in the matching XML. Do not upload these files. No simulation. Scalp sliders stay until the Mac user says otherwise.

- `STN/STN-maxprob-thr25-0.5mm.nii.gz` — already done. Left and right STN.
- `HarvardOxford/HarvardOxford-sub-maxprob-thr25-1mm.nii.gz` — thalamus, caudate, putamen, pallidum, hippocampus, amygdala, accumbens, brainstem.
- `HarvardOxford/HarvardOxford-cort-maxprob-thr25-1mm.nii.gz` — cortical regions.
- `Thalamus/Thalamus-maxprob-thr25-1mm.nii.gz`
- `MNI/MNI-maxprob-thr25-1mm.nii.gz`
- `Juelich/Juelich-maxprob-thr25-1mm.nii.gz`
- `Cerebellum/Cerebellum-MNIfnirt-maxprob-thr25-1mm.nii.gz`
- `JHU/JHU-ICBM-labels-1mm.nii.gz`
- `Talairach/Talairach-labels-1mm.nii.gz`

Skip the probabilistic 4D volumes.

### Mac

The atlases are part of FSL 6.0.7, not a separate download. Installer: https://fsl.fmrib.ox.ac.uk/fsldownloads/fslinstaller.py
On this Mac they are in /Users/amir/fsl/data/atlases. The XML label tables are the .xml files in that same folder.
warp_volume is a SimNIBS call, so the FSL install alone does not warp them. Do not upload the atlases or the subject.
No simulation. Scalp sliders stay as they are.

### Reply

- Commit tested:
- `--check`:
- Sync files:
- Launch:
- Change needed:















