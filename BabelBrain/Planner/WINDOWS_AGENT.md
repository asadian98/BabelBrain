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

Reviewed `3be338d`. A 2D click that is not a target until Save is right. No simulation. Do not upload the subject.

AP and Lat must slide the transducer on the scalp while the saved target stays fixed, as in `02_lat_moved.png`. A fixed millimetre offset leaves the skin when the angle changes. Twist rotates around that beam. The transducer stays on the scalp view and the 3D view, not on the flat slices.

### Reply

- Commit tested: 3807752
- `--check`: not rerun, UI only
- Sync files: not written
- Launch: window open. AP and Lat slide the transducer on the scalp. The saved target point stays fixed. Twist rolls around the beam.
- Change needed: none until the window is reviewed





