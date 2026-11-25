"""The wrapper refuses reads beyond the information set and holds nothing hidden."""
from dataclasses import replace

import numpy as np
import pytest

from papere.generator import generate_f0r
from papere.infoset import (InformationSet, InformationSetViolation, OracleView,
                            StaticView, UNKNOWN)
from papere.instance import Cell, Instance

BASE = Cell(family="F0R", M=3, delta_A=2, delta_b=0, rho=0.95, r=0.3)
COMBOS = [(0, 0, 0), (5, 2, 0), (5, 0, 2), (10, 4, 1), (3, 4, 4), (23, 2, 0), (10, 1, 3),
          (1, 2, 0), (12, 0, 0)]


def history(inst, seed=0):
    """Random (not cap-feasible) setpoints and the resulting truth, for wrapper tests."""
    rng = np.random.default_rng(seed)
    N, H = inst.N, inst.H
    A = inst.availability()
    t_ = np.arange(H)[None, :]
    window = (t_ >= inst.a[:, None]) & (t_ < inst.d[:, None])
    x = rng.integers(0, 4, size=(N, H)) * window
    x = np.minimum(x, inst.P[:, None])
    r = inst.E.copy()
    y = np.zeros((N, H), dtype=np.int64)
    revealed = np.zeros((N, H), dtype=bool)
    for t in range(H):
        y[:, t] = np.minimum(x[:, t], r) * A[:, t]
        revealed[:, t] = (x[:, t] > 0) & (r > 0)
        r = r - y[:, t]
    A_masked = np.where(revealed, A, UNKNOWN).astype(np.int8)
    return x, y, A, A_masked


def make_view(t, dA, db, seed=0):
    cell = replace(BASE, delta_A=dA, delta_b=db)
    inst = generate_f0r(60000 + seed % 50, cell)
    x, y, A, Am = history(inst, seed)
    static = StaticView.from_instance(inst)
    view = InformationSet.build(static, t, x, Am, y, inst.b)
    return inst, view, x, y, A, Am


# ------------------------------------------------------------------ walker
def root_buffer(arr):
    """Follow ``.base`` through arrays to the underlying buffer object."""
    while isinstance(arr, np.ndarray) and arr.base is not None:
        arr = arr.base
    return arr


def reachable(root):
    """All objects reachable from ``root`` via slots, __dict__, containers, ndarray.base."""
    seen, out, stack = set(), [], [root]
    while stack:
        o = stack.pop()
        if id(o) in seen:
            continue
        seen.add(id(o))
        out.append(o)
        if isinstance(o, (str, bytes, int, float, bool, type(None), np.generic, type)):
            continue
        if isinstance(o, np.ndarray):
            if o.base is not None:
                stack.append(o.base)
            if o.dtype == object:
                stack.extend(o.ravel().tolist())
            continue
        if isinstance(o, dict):
            stack.extend(o.keys()), stack.extend(o.values())
            continue
        if isinstance(o, (list, tuple, set, frozenset)):
            stack.extend(o)
            continue
        for k in type(o).__mro__:
            for s in getattr(k, "__slots__", ()):
                try:
                    stack.append(object.__getattribute__(o, s))
                except AttributeError:
                    pass
        if hasattr(o, "__dict__"):
            stack.extend(vars(o).values())
    return out


@pytest.mark.parametrize("t,dA,db", COMBOS)
def test_reachability_no_hidden_data(t, dA, db):
    inst, view, x, y, A, Am = make_view(t, dA, db, seed=t + dA)
    objs = reachable(view)
    assert not any(isinstance(o, (Instance, Cell)) for o in objs)
    arrays = [o for o in objs if isinstance(o, np.ndarray)]
    assert arrays
    bufs = [o for o in objs if isinstance(o, bytes)]
    assert sorted(map(id, bufs)) == sorted({id(root_buffer(a)) for a in arrays})  # nothing else held
    n_conf = max(0, t - dA + 1)
    hidden = {"cls": inst.cls, "q": inst.q, "b": inst.b, "v": inst.v, "u": inst.u,
              "A_true": A, "y_full": y, "x_full": x}
    for arr in arrays:
        # immutable copy: backed by a bytes buffer holding exactly this array's data
        buf = root_buffer(arr)
        assert isinstance(buf, bytes) and len(buf) == arr.nbytes
        assert not arr.flags.writeable
        for name, h in hidden.items():
            assert not np.may_share_memory(arr, h), name
            if arr.size > 1 and arr.shape == h.shape and arr.dtype.kind == h.dtype.kind:
                assert not np.array_equal(arr, h), f"hidden {name} reachable by value"
    # the unmasked A prefix is not reachable where the mask hides differing entries
    A_prefix = A[:, :n_conf]
    differs = (Am[:, :n_conf] != A_prefix).any()
    for arr in arrays:
        if arr.shape == A_prefix.shape and arr.size and differs:
            assert not np.array_equal(arr, A_prefix)
    # nothing of the future: base load beyond the observed prefix, A beyond n_conf
    for arr in arrays:
        if arr.ndim == 2 and arr.shape[0] == inst.b.shape[0] and arr.shape[1] > max(0, t - db):
            assert not np.array_equal(arr[:, :inst.H], inst.b[:, :arr.shape[1]]) or \
                arr is view.L or arr is view.b_mean


def test_reachability_walker_finds_leaks():
    """The walker itself must detect a leaking wrapper (guards the guard)."""
    inst, view, *_ = make_view(5, 2, 0)

    class Leaky:
        def __init__(self):
            self.inst = inst
    assert any(isinstance(o, Instance) for o in reachable(Leaky()))
    leak = inst.b[:, :3]
    assert any(isinstance(o, np.ndarray) and np.may_share_memory(o, inst.b)
               for o in reachable(leak))


# ---------------------------------------------------------------- accessors
@pytest.mark.parametrize("t,dA,db", COMBOS)
def test_out_of_set_reads_raise(t, dA, db):
    inst, view, x, y, A, Am = make_view(t, dA, db, seed=3 * t + db)
    H = inst.H
    for s in list(range(t - dA + 1, H + 3)) + [-1, -H]:
        with pytest.raises(InformationSetViolation):
            view.availability(s)
        with pytest.raises(InformationSetViolation):
            view.delivered(s)
    for s in list(range(t - db, H + 3)) + [-1]:
        with pytest.raises(InformationSetViolation):
            view.base_load(s)
    for s in list(range(t, H + 3)) + [-1]:
        with pytest.raises(InformationSetViolation):
            view.setpoint(s)
    for bad in (1.0, "1", None):
        with pytest.raises(InformationSetViolation):
            view.availability(bad)
    with pytest.raises(InformationSetViolation):
        view.setpoint_cap(5)  # no such group
    # permitted reads equal the (masked) truth
    for s in range(0, t - dA + 1):
        assert np.array_equal(view.availability(s), Am[:, s])
        assert np.array_equal(view.delivered(s), y[:, s])
    for s in range(0, t - db):
        assert np.array_equal(view.base_load(s), inst.b[:, s])
    for s in range(0, t):
        assert np.array_equal(view.setpoint(s), x[:, s])


@pytest.mark.parametrize("t,dA,db", COMBOS)
def test_whole_arrays_are_exact_prefixes(t, dA, db):
    inst, view, x, y, A, Am = make_view(t, dA, db, seed=t)
    n_conf, n_b = max(0, t - dA + 1), max(0, t - db)
    assert view.A_confirmed.shape == (inst.N, n_conf) and view.A_confirmed.dtype == np.int8
    assert view.y_confirmed.shape == (inst.N, n_conf)      # A and y share one cutoff
    assert view.b_observed.shape == (1, n_b)               # delta_b is a separate lag
    assert view.x_past.shape == (inst.N, t)
    assert np.array_equal(view.A_confirmed, Am[:, :n_conf])
    assert np.array_equal(view.y_confirmed, y[:, :n_conf])
    assert np.array_equal(view.b_observed, inst.b[:, :n_b])
    assert np.array_equal(view.x_past, x[:, :t])
    assert set(np.unique(view.A_confirmed)) <= {-1, 0, 1}
    assert np.array_equal(view.confirmed_debt, inst.E - y[:, :n_conf].sum(axis=1))
    assert view.last_confirmed_slot == t - dA and view.last_base_slot == t - 1 - db
    assert (view.t, view.delta_A, view.delta_b) == (t, dA, db)


def test_delta_b_is_separate_from_delta_A():
    _, v1, *_ = make_view(8, 2, 0)
    _, v2, *_ = make_view(8, 2, 5)
    assert v1.A_confirmed.shape == v2.A_confirmed.shape
    assert v1.b_observed.shape[1] == 8 and v2.b_observed.shape[1] == 3


def test_masking_is_applied_to_what_the_wrapper_holds():
    inst, view, x, y, A, Am = make_view(15, 2, 0)
    n = 14
    assert (Am[:, :n] == UNKNOWN).any() and (Am[:, :n] != A[:, :n]).any()
    assert np.array_equal(view.A_confirmed, Am[:, :n])
    assert (view.A_confirmed == UNKNOWN).any()
    # y arrives for everyone, masked A or not, and equals the truth on the permitted prefix
    assert np.array_equal(view.y_confirmed, y[:, :n])
    assert (view.y_confirmed[view.A_confirmed == UNKNOWN] == 0).all()   # hidden A: nothing delivered


def test_arrays_read_only_and_copies():
    inst, view, *_ = make_view(10, 2, 1)
    for name in ("P", "E", "a", "d", "group", "L", "b_mean", "announced", "prior_A",
                 "prior_stuck", "x_past", "A_confirmed", "y_confirmed", "b_observed",
                 "confirmed_debt", "base_forecast", "active"):
        arr = getattr(view, name)
        assert isinstance(arr, np.ndarray)
        if name == "active":  # derived on each call
            continue
        assert not arr.flags.writeable, name
        with pytest.raises(ValueError):
            arr.flags.writeable = True          # cannot be re-enabled
        with pytest.raises(ValueError):
            arr.setflags(write=True)
        if arr.size:
            with pytest.raises(ValueError):
                arr[...] = 0
            with pytest.raises(ValueError):
                arr.reshape(-1)[:1].setflags(write=True)
    assert not view.availability(3).flags.writeable
    assert view.P is not inst.P and not np.may_share_memory(view.P, inst.P)
    assert not np.may_share_memory(view.prior_A, inst.prior_A)
    with pytest.raises(InformationSetViolation):
        view.t = 3
    with pytest.raises(InformationSetViolation):
        view.new_attr = 1


@pytest.mark.parametrize("name", ["A", "b", "cls", "q", "instance", "inst", "u", "v", "r",
                                  "cell", "x", "y", "rho", "_A", "_instance", "true_A"])
def test_hidden_attribute_names_raise(name):
    _, view, *_ = make_view(10, 2, 0)
    with pytest.raises(InformationSetViolation):
        getattr(view, name)
    static = StaticView.from_instance(generate_f0r(60001, BASE))
    with pytest.raises(InformationSetViolation):
        getattr(static, name)


def test_static_view_has_no_time_varying_data():
    static = StaticView.from_instance(generate_f0r(60001, BASE))
    for name in ("t", "x_past", "A_confirmed", "y_confirmed", "b_observed", "confirmed_debt",
                 "setpoint_cap", "availability"):
        with pytest.raises(InformationSetViolation):
            getattr(static, name)
    assert static.N == 30 and static.delta_A == 2 and static.M == 3
    objs = reachable(static)
    assert not any(isinstance(o, (Instance, Cell)) for o in objs)


def test_setpoint_cap_and_forecast():
    inst, v0, *_ = make_view(0, 2, 0)
    assert np.allclose(v0.base_forecast, inst.b_mean[:, 0])           # nothing observed yet
    assert v0.setpoint_cap(0) == int(np.floor(inst.L[0, 0] - inst.b_mean[0, 0] + 1e-9))
    inst, v, *_ = make_view(6, 2, 3)                                  # b observed through slot 2
    assert v.base_forecast[0] == inst.b[0, 2]
    assert v.setpoint_cap(0, 2) == int(np.floor(inst.L[0, 6] - inst.b[0, 2] - 2 + 1e-9))
    assert v.setpoint_caps(1)[0] == v.setpoint_cap(0, 1)
    inst, v, *_ = make_view(6, 2, 0)
    assert v.base_forecast[0] == inst.b[0, 5]


def test_construction_validates_shapes_and_values():
    inst = generate_f0r(60001, replace(BASE, delta_A=2))
    st = StaticView.from_instance(inst)
    N = inst.N
    ok = dict(x_past=np.zeros((N, 5)), A_obs=np.zeros((N, 4), np.int8),
              y_conf=np.zeros((N, 4)), b_obs=np.zeros((1, 5)))
    InformationSet(st, 5, **ok)
    with pytest.raises(ValueError):
        InformationSet(st, 5, **{**ok, "A_obs": np.zeros((N, 5), np.int8)})
    with pytest.raises(ValueError):
        InformationSet(st, 5, **{**ok, "b_obs": np.zeros((1, 6))})
    with pytest.raises(ValueError):
        InformationSet(st, 5, **{**ok, "A_obs": np.full((N, 4), 2, np.int8)})
    with pytest.raises(InformationSetViolation):
        InformationSet(st, 24, **ok)


def test_oracle_view_read_only():
    inst = generate_f0r(60001, BASE)
    o = OracleView.from_instance(inst)
    assert np.array_equal(o.cls, inst.cls) and np.array_equal(o.q, inst.q)
    assert not o.cls.flags.writeable and not np.may_share_memory(o.cls, inst.cls)
    with pytest.raises(AttributeError):
        o.cls = 1
