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

Charm files are in BabelBrain/Planner/fixtures/m2m_sample/, the public SimNIBS ernie subject. charm_log.html is the name the dialog checks. final_tissues.nii.gz is the volume the domain step reads. Open that folder. m2m_hamid is only T1 and skin, so the Charm check will keep rejecting it. Pull and rerun the check, GUI save, and Brainsight launch. No simulation unless the files load.

### Reply

- Commit tested: 67fd448
- `--check`: OK. Coordinate system NIfTI:S:Scanner. T1 sform_code and qform_code are both 1.
- Sync files: yes, in the Windows user .BabelBrainSync folder. Input_Target.txt is the trajectory text and contains Brainsight. The other three files are absolute paths. This used the same write_sync the Save button calls. The planner window was not opened.
- Launch: printed ID,RPath PlannerCheck and the copied trajectory path. The file dialog then said the SimNIBS folder was not Charm generated, twice, and the process crashed with an access violation. The fixture only has T1.nii.gz and skin.stl. No simulation was run.
- Change needed: add a Charm m2m. The dialog accepts the folder when any filename contains charm. The domain step needs final_tissues.nii.gz.
