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

Accepted `0b4ca73`. Overlay None, T2, Atlas, and STN can stay. Choosing a region centers the crosshair. No simulation. Do not upload the subject.

AP and Lat still do not reseat on the scalp. Put `_reseat_on_scalp` back in `_angles_moved` when AP or Lat changes. The saved target stays fixed.

### Reply

- Commit tested: e30f002
- Question: how was STN_atlas_scanner.nii.gz made on the Mac? Name the atlas, the command or script, and whether the warp was the m2m toMNI/MNI2Conform_nonl field.
- The user wants a picker of atlases available online, each warped into the open subject's space the same way, then shown as an overlay with its own transparency.
- No simulation. Do not upload the subject. AP and Lat still do not reseat.
- Change needed: write those STN steps under Mac. Leave the scalp sliders as they are.












