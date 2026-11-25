"""scripts/make_figures.py runs on a tiny synthetic data file and writes Type 3-free vector PDFs."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "make_figures.py"


def _load():
    spec = importlib.util.spec_from_file_location("make_figures", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _synthetic() -> dict:
    nums = {"e3/summary/n_points": {"value": 3 * 9}}
    for q in (0.14, 0.4, 0.5):
        for c in range(0, 17, 2):
            g = q * c / 2 if c <= 8 else q * (8 - c / 2)
            nums[f"e3/gap_oracle/pooled/q{q:g}/c{c}/M0"] = {
                "value": g, "mc_se": 0.05, "n_seeds": 100, "K": 8,
                "simultaneous_lo": g - 0.2, "simultaneous_hi": g + 0.2}
    for cap in ("pooled", "per_copy"):
        for q in (0.14, 0.4, 0.5):
            for M in (0, 1, 3, 5):
                g = 0.3 * q * M
                nums[f"e3/gap_e1/{cap}/q{q:g}/c8/M{M}"] = {
                    "value": g, "mc_se": 0.05, "n_seeds": 100, "K": 8, "predicted": g + 0.05,
                    "simultaneous_lo": g - 0.2, "simultaneous_hi": g + 0.2}
    for rho in (0.95, 1.15):
        for d in (0, 1, 2, 4):
            for layer, v in (("planning", 1.0), ("hedging", 2.0), ("targeting", 0.5)):
                nums[f"layers/M3_rho{rho:g}/dA{d}/{layer}"] = {
                    "value": v, "ci_lo": v - 0.3, "ci_hi": v + 0.3}
    return {"meta": {}, "numbers": nums}


def test_make_figures_writes_type42_pdfs(tmp_path):
    data = tmp_path / "numbers.json"
    data.write_text(json.dumps(_synthetic()))
    out = tmp_path / "figs"
    assert _load().main(["--data", str(data), "--out", str(out)]) == 0
    for name in ("fig_e3.pdf", "fig_layers.pdf"):
        raw = (out / name).read_bytes()
        assert raw.startswith(b"%PDF")
        assert b"/Type3" not in raw


def _asym() -> dict:
    """Synthetic data with asymmetric, distinguishable bounds."""
    d = _synthetic()
    for i, (k, r) in enumerate(sorted(d["numbers"].items())):
        if k.startswith("e3/gap_oracle"):
            r["value"] = 0.01 * i
            r["simultaneous_lo"] = r["value"] - 0.1
            r["simultaneous_hi"] = r["value"] + 0.3
        elif k.startswith("layers/"):
            r["value"] = 0.1 * i
            r["ci_lo"] = r["value"] - 0.2
            r["ci_hi"] = r["value"] + 0.5
    return d


def test_plotted_values_equal_data_file_values():
    mod = _load()
    nums = _asym()["numbers"]
    for q, sr in mod.e3_series(nums).items():
        for c, y, lo, hi in zip(sr["c"], sr["y"], sr["lo"], sr["hi"]):
            rec = nums[f"e3/gap_oracle/pooled/q{q:g}/c{int(c)}/M{mod.E3_M}"]
            assert (y, lo, hi) == (rec["value"], rec["simultaneous_lo"], rec["simultaneous_hi"])
    for (rho, layer), sr in mod.layer_series(nums).items():
        for d, y, lo, hi in zip(mod.LAYER_DAS, sr["y"], sr["lo"], sr["hi"]):
            rec = nums[f"layers/M{mod.LAYER_M}_rho{rho:g}/dA{d}/{layer}"]
            assert (y, lo, hi) == (rec["value"], rec["ci_lo"], rec["ci_hi"])


def test_prop3_plotted_values_equal_data_file_values():
    mod = _load()
    nums = _synthetic()["numbers"]
    for i, (k, r) in enumerate(sorted(nums.items())):
        if k.startswith("e3/gap_e1"):
            r.update(value=0.01 * i, predicted=0.02 * i, simultaneous_lo=0.01 * i - 0.1,
                     simultaneous_hi=0.01 * i + 0.3)
    series = mod.e3_prop3_series(nums)
    assert len(series) == 6
    for (cap, q), sr in series.items():
        for M, y, lo, hi, pr in zip(sr["M"], sr["y"], sr["lo"], sr["hi"], sr["pred"]):
            rec = nums[f"e3/gap_e1/{cap}/q{q:g}/c8/M{int(M)}"]
            assert (y, lo, hi, pr) == (rec["value"], rec["simultaneous_lo"],
                                       rec["simultaneous_hi"], rec["predicted"])


@pytest.mark.parametrize("drop", ["e3/gap_oracle/pooled/q0.4/c6/M0",
                                  "e3/gap_e1/per_copy/q0.5/c8/M3",
                                  "layers/M3_rho1.15/dA2/planning"])
def test_missing_key_raises_nonzero_and_names_key(tmp_path, drop):
    d = _synthetic()
    del d["numbers"][drop]
    data = tmp_path / "numbers.json"
    data.write_text(json.dumps(d))
    with pytest.raises(SystemExit) as ei:
        _load().main(["--data", str(data), "--out", str(tmp_path / "figs")])
    assert ei.value.code not in (0, None)
    assert drop in str(ei.value.code)
    assert not (tmp_path / "figs").exists()


def test_missing_stored_bound_needs_explicit_flag(tmp_path):
    d = _synthetic()
    del d["numbers"]["e3/gap_oracle/pooled/q0.14/c4/M0"]["simultaneous_lo"]
    data = tmp_path / "numbers.json"
    data.write_text(json.dumps(d))
    with pytest.raises(SystemExit) as ei:
        _load().main(["--data", str(data), "--out", str(tmp_path / "figs")])
    assert "simultaneous" in str(ei.value.code)
    d["numbers"]["e3/summary/n_points"] = {"value": 27}
    data.write_text(json.dumps(d))
    assert _load().main(["--data", str(data), "--out", str(tmp_path / "figs"),
                         "--allow-se-fallback"]) == 0
