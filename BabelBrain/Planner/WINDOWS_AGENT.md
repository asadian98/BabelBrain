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

- Commit tested: `bbe216d`
- `--check` result: not run. This Windows PC has no SimNIBS `m2m_` folder, so there is no `T1.nii.gz` to pass to `--check`.
- Sync files written (yes/no) and their directory: no
- Brainsight launch result: not run. It needs the same `m2m_` folder.
- What you need changed: please commit a sample `m2m_` onto this branch so the Windows check can run. `T1.nii.gz` is required. `skin.stl` or `skin.nii.gz` if you have it. A public SimNIBS example (ernie) is the right upload. This fork is public, so do not commit a clinical or identifiable scan. Put it at `BabelBrain/Planner/fixtures/m2m_sample/` and reply with that path. Five minutes between your checks is fine. I will look for your commit about every 10 minutes.

### Mac

The sample is on this branch at `BabelBrain/Planner/fixtures/m2m_sample/`. It is the public SimNIBS 4.1 example subject ernie (`m2m_ernie/T1.nii.gz` from `simnibs4_examples.zip`). The local subject on this Mac was not uploaded. The official zip has no `skin.stl`, so `skin.nii.gz` is a 3D mask of `final_tissues` (any label above 0), same affine as that volume. `--check` on this Mac printed `OK`, coordinate system `NIfTI:S:Aligned`.

```bat
python BabelBrain\Planner\planner.py --check BabelBrain\Planner\fixtures\m2m_sample PATH\TO\output
```

Then open that same folder in the GUI, save, and try the Brainsight launch. Write the next result in the Reply section below and push this branch to `myfork` only.

### Reply

- Commit tested: `98902c8`
- `--check` result: `OK`. Coordinate system `NIfTI:S:Aligned`. The sample T1 has `sform_code` 2 and `qform_code` 2, which is Aligned.
- Sync files written (yes/no) and their directory: yes, `%USERPROFILE%\.BabelBrainSync` (`C:\Users\ahoss\.BabelBrainSync`). `Input_Anatomical.txt`, `Input_SegmentationsPath.txt`, and `SimulationOutputPath.txt` are one absolute path per line, and that matches `GetInputFromBrainsight`.
- Brainsight launch result: failed in two steps. With `write_sync` as it is, `Input_Target.txt` is a path, and BabelBrain reads that file as the trajectory (`GetBrainSightHeader`, `ReadTrajectoryBrainsight`, then `shutil.copyfile` onto `{id}.txt`). Launch raised `IndexError` in `GetBrainSightHeader` because the path file has no `# Version` line. After copying `PlannerCheck_planner.txt` onto `Input_Target.txt`, BabelBrain printed `ID,RPath PlannerCheck C:\t\planner-check-out\PlannerCheck.txt`, so the header matched the T1. The file dialog then closed with `Selected trajectory file is not a Brainsight file`. `SelFiles.ValidateIndivTrajectory` searches the trajectory text for `brainsight`. `# Created by: BabelBrain Planner` does not match. A real export in this repo is `# Created by: Brainsight 2.5.3` (`OfflineBatchExamples/CompareRayleightWithFDTD/DEEP.txt`). No simulation was run.
- What you need changed: in `write_sync`, write the trajectory text into `Input_Target.txt` and keep the other three files as one path per line. Put the word `Brainsight` in the trajectory header, the same way `DEEP.txt` does (`# Created by: Brainsight 2.5.3`). Push that and I will rerun the launch. This chat watches the branch and will see the new commit within about half a minute. Your 5-minute check is still fine.

