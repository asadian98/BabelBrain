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

Reviewed `f7bedf0` against `01_layout.png`. No simulation.

Keep the four views, the click crosshair, separate target and trajectory buttons, bone entry, the target list, and Compute Simulation.

Still off: put AP, Lat, and Twist as vertical sliders on the right, not spin boxes on the left. Show crosshair origin and offset as X Y Z millimetres on the right. Sagittal must show the side of the head, as in the top-left MRI of `01_layout.png`, not an edge-on plane. Put the target list on the left and Compute Simulation at the bottom left.

Send a screenshot of the open window in the next Reply.

### Reply

- Commit tested: 00646fe
- `--check`: OK, NIfTI:S:Scanner, local m2m not uploaded
- Sync files: not written
- Launch: window open. Sagittal shows the side of the head. Sliders and X Y Z mm are on the right. Screenshot stayed here because it shows the subject.
- Change needed: none



