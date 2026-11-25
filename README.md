# paperE-benchmark

This repository holds the code, synthetic data and results for scheduling recovery under late delivery confirmation.

It accompanies the Applied Energy manuscript. This is release v1.0.

## Data

All data are synthetic. The code generates them from seeds. No customer record or personal record is used.

## Requirements

- Python 3.12 or 3.13
- [uv](https://docs.astral.sh/uv/)
- pandoc, for the manuscript build
- pdflatex, bibtex and the elsarticle class, for the PDF

The `aaai` build profile needs a third-party author kit. The kit is not included. Only the `journal` profile runs here.

## Reproduce the results

Clone the repository with git. Do not use a source archive. Run the steps in this order.

1. Install the environment.

   ```
   uv sync
   ```

2. Run the tests. Expect 964 to pass.

   ```
   uv run pytest -q
   ```

3. Unpack the saved rows. Keep the `.gz` files.

   ```
   gunzip -k results/*/rows.jsonl.gz
   ```

4. Rebuild the analysis files.

   ```
   uv run python -m papere.analysis --all --frozen results/TUNING_FROZEN.json
   uv run python -m papere.analysis --g2 results/f0r_dev --frozen results/TUNING_FROZEN.json
   ```

5. Run the post hoc and confirmation scripts.

   ```
   uv run python scripts/posthoc_oblivious_share.py
   uv run python scripts/posthoc_g3_runs.py
   uv run python scripts/posthoc_ranker.py
   uv run python scripts/posthoc_applied_energy.py
   uv run python scripts/posthoc_sllf_nc1_exact.py
   uv run python scripts/confirm_analysis.py --rows results/f0r_dev/rows.jsonl.gz --seeds 61000-61099 --out results/confirm_check_dev.json
   uv run python scripts/confirm_analysis.py --rows results/f0r_confirm/rows.jsonl --seeds 500000-500199 --out results/confirm_numbers.json
   uv run python scripts/e3_conditioned.py
   uv run python scripts/make_dev_tables.py
   uv run python scripts/check_ledger.py
   ```

   Every numeric value should match the committed JSON to within 1e-15. Only commit, time and runtime fields differ.

6. Build and check the manuscript.

   ```
   uv run python paper/build.py --profile journal all
   uv run python paper/check.py --profile journal
   ```

   The fill and tex steps need pandoc only. The PDF step needs the full TeX tools.

## Traps

1. Rows are stored only as `.gz`. The analysis code reads plain `rows.jsonl`. Run the `gunzip` step first.
2. `scripts/posthoc_oblivious_share.py` skips the confirmation block when `results/f0r_confirm/rows.jsonl` is missing. It raises no error. The output then has 58 keys instead of 62.
3. Tests and several scripts call git. One test fails outside a git checkout with a commit. Clone the repository.
4. The PDF step needs pandoc, pdflatex, bibtex and elsarticle. The `aaai` profile cannot run without its kit.
5. The commit ids in result metadata and manifests refer to the private development history. They do not exist in this repository.
6. The `kcopy_dev` rows unpack to 632 MiB. The build rewrites `paper/journal/highlights.docx` and `graphical_abstract.pdf`. Those two files are not byte-stable.

## Verify the frozen files

`docs/MANIFEST_CONFIRMATION.json` lists a SHA-256 hash for 26 files under `files_sha256`. Check each one with `shasum -a 256`.

```
shasum -a 256 run_study.py pyproject.toml uv.lock src/papere/runner.py
```

Compare each output with the matching entry in the manifest. Do not edit these files. The manifest and the `results/*/manifest.json` files also keep the hashes of the derived results.

## Licence

The code is under the MIT licence. See `LICENSE`. The results, docs and manuscript text and figures are under CC BY 4.0. See `LICENSE-DATA.md`.

## Citation

Cite this work through `CITATION.cff`. GitHub shows a "Cite this repository" button from that file.
