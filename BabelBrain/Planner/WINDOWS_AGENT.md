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

- Commit tested: 858dd2f
- `--check`: OK on the local Hamid Charm folder C:\t\HamidNew\m2m_ernie. NIfTI:S:Scanner. sform and qform are 1. This scan stays on this PC. It is not on the public fork.
- Sync files: yes, in the Windows .BabelBrainSync folder. Input_Target.txt is the trajectory and contains Brainsight.
- Launch: ID,RPath PlannerCheck. The dialog accepted that Charm folder and the T1. The main window started. No simulation.
- Change needed: none for the handshake. I have the Hamid m2m locally, including charm_log.html, final_tissues.nii.gz, T1.nii.gz, and skin.stl. I did not create a Cursor automation. This chat watches the branch.
