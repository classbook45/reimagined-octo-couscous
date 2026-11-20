# Operation Beat Saver — milestone plan

Target: Beat Saber 1.45.3 (package 1.45.3_30054), Quest arm64-v8a, Android NDK 29, bs-cordl 4503, beatsaber-hook 9.1.1+.

Milestones are gates, not promises. A later gate is only marked complete when its evidence exists in the workflow run.

| # | Milestone | Completion evidence |
|---|---|---|
| 1 | Workflow and toolchain baseline | Workflow runs; Java, Python, Android SDK, NDK 29 and QPM are detected |
| 2 | Source inventory | All four repositories clone and their build/manifests are inspected |
| 3 | Dependency graph alignment | Every QPM dependency resolves against the target CORDL/Hook versions and upstream dependency constraints |
| 4 | Source/API migration | Project-specific C++ patches are reviewed, apply cleanly, and migrate obsolete Hook/CORDL APIs |
| 5 | CustomJSONData build | CustomJSONData compiles for arm64-v8a against the target dependency graph |
| 6 | Tracks build | Tracks compiles against the target graph and the compatible CustomJSONData build, where required |
| 7 | Chroma build | Chroma compiles against the target graph and compatible prerequisite mods |
| 8 | NoodleExtensions build | NoodleExtensions compiles against the target graph and compatible prerequisite mods |
| 9 | Package validation | Each expected QMOD exists, is non-empty, and contains the expected Quest native library |
| 10 | Release bundle validation | All four QMODs and build reports are present in the final artifact bundle |

## Rules

- Do not downgrade CORDL to an older Beat Saber generation merely to make dependency resolution pass.
- Do not treat changing version ranges as a source/API migration.
- Do not inject global C++23 flags as a substitute for fixing incompatible source code.
- Preserve upstream licenses and record each source patch.
- A failed prerequisite blocks a dependent build, but the workflow should still inspect the remaining repositories and collect diagnostics.
- A workflow run is not a success until all required milestones pass. No compatibility claim is made from a successful clone or dependency restore alone.
