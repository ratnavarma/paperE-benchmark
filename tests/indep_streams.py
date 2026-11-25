"""Test helper: independent tie-break streams per ``simulate`` call.

``simulate`` now gives every policy the same stream per (seed, cell), so tests that average
over tie-break noise cannot get replicates by renaming policies. Inside this context each
call to ``papere.sim.policy_rng`` returns a fresh, independent generator instead.
"""
import itertools
from contextlib import contextmanager

import numpy as np

import papere.sim as sim


@contextmanager
def independent_tiebreaks(tag: int = 0):
    orig = sim.policy_rng
    counter = itertools.count()
    sim.policy_rng = lambda seed, cell_id, name: np.random.default_rng([97, int(tag), next(counter)])
    try:
        yield
    finally:
        sim.policy_rng = orig
