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

Accepted. Keep the Hamid Charm folder on that PC. Do not commit it to this fork. The public ernie sample was only a fallback.

No code change and no simulation. The check, the sync files, and the main window are enough. Watching this branch is enough, so do not create an automation. Stop, and leave Reply as it is.

### Reply

- Commit tested: 853ca96
- `--check`: already OK on the local Hamid folder. No simulation.
- Sync files: already written on this PC. The scan stays off this fork.
- Launch: this agent clicked CONTINUE. The main window opened as PlannerCheck. It was then closed. The user does not need to click.
- Change needed: next slice is the planner window on this PC. Open the local Hamid m2m, set one target and one transducer, and save. No simulation until the user asks. Keep replies short.
