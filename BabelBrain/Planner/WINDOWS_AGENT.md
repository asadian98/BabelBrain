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

Keep the single New button and Kind of Target or Trajectory from `a151b3e`. No simulation. Do not upload the subject.

The Mac session is `02_lat_moved.png`. AP and Lat slide the transducer on the scalp. The crosshair target stays fixed. That was not a request to leave the sliders off the skin. Atlas waits until that pose is back.

### Reply

- Commit tested: b2eab8e
- `--check`: round trip of both exchange files passed. No simulation.
- Sync files: not written
- Launch: window open. The name is drawn on the target point. Offset mark stays unlabeled.
- Change needed: import fixtures/brainsight_exchange/Planner_Target.txt (XYZ 15, 0, 38 mm, AP 0, Lat 0, Twist 0) and Planner_Trajectory.txt (XYZ 10, 20, 30 mm, AP 20, Lat 30, Twist 15), both NIfTI:S:Scanner. Photograph sagittal and inline in Brainsight and commit the pictures on this branch.








