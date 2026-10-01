# Windows agent notes

Branch: `planner/session-sync`  
Commit to start from: `3bd578a` (plus any later commits on this branch)  
Fork only: https://github.com/asadian98/BabelBrain  
Do not push to ProteusMRIgHIFU/BabelBrain. Do not revert local packaging fixes.

## What this slice is

`BabelBrain/Planner/planner.py` opens a SimNIBS `m2m_` folder, shows the T1 and skin, and writes:

- a Brainsight version-14 trajectory (`{target}_planner.txt`)
- four one-path files in `%USERPROFILE%\.BabelBrainSync` on this Windows user, not on the shared SSD

BabelBrain already reads those files when started with `-bInUseWithBrainsight`. Use `BabelBrain\Run BabelBrain.bat` and conda env `C:\bb`. Do not start the unsigned `BabelBrain.exe`.

## Check

```bat
python BabelBrain\Planner\planner.py --check PATH\TO\m2m_subject PATH\TO\output
```

Expect the first line `OK` and a coordinate system of `NIfTI:S:*` or `NIfTI:Q:*` that matches the T1 `sform_code` or `qform_code`. `--check` does not write the sync folder.

Then run `python BabelBrain\Planner\planner.py`, open the m2m folder, place one target and one transducer, save, and confirm the four sync files. Launch BabelBrain from `Run BabelBrain.bat` with `-bInUseWithBrainsight` and confirm it loads that T1, m2m folder, and trajectory. Do not run a simulation unless the files load.

## Write back

Add a section below and push this same branch to `myfork` (`asadian98/BabelBrain`). Do not open a pull request to Proteus.

### Reply

- Commit tested:
- `--check` result:
- Sync files written (yes/no) and their directory:
- Brainsight launch result:
- What you need changed:
