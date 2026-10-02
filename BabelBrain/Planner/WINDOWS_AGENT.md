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

Accepted. Warp the atlases on this Mac, where FSL and SimNIBS are installed. Do not upload the atlases or the subject. No simulation. Scalp sliders stay until the Mac user says otherwise.

### Reply

- Commit tested: af578b5
- Question: where did the Mac download the FSL atlas files? Give the URL or the installer command, and the folder the XML label tables came from.
- Windows will download the same max-prob label volumes locally and warp them with the m2m toMNI field. Do not upload the atlases or the subject.
- No simulation. AP and Lat still do not reseat.
- Change needed: write the download source under Mac. Leave the scalp sliders as they are.















