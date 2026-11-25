# Corrections to the frozen confirmation protocol (added October 24, 2026, after the run)

The protocol file is frozen and is not edited. These notes sit beside it.

1. Section 1 says "The runner checks every hash and refuses to start on a mismatch." The runner (`src/papere/runner.py`) checks only that `results/TUNING_FROZEN.json` and `results/population_params.json` are committed and unchanged. No code reads `docs/MANIFEST_CONFIRMATION.json`. On October 24, 2026 the 26 hashes in the manifest were compared by hand against the files at commit 242c96e and all match, so the confirmation run used the frozen files. A manifest check in the runner would be an addition after the fact and is not claimed by the paper.
2. The runner docstring says tuning policy names make tie-break streams differ per configuration. `simulate` uses the fixed stream name `tiebreak`, so they do not. This affects no reported number: every policy in a cell saw the same stream, as the paired design requires.
