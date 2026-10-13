"""Statistics independent of UI/storage. No LLM-as-judge scoring.

References and assumptions: docs/METHODOLOGY.md. Intervals describe sampling
uncertainty, not dataset representativeness or an immutable provider snapshot.
"""
from collections import defaultdict
from math import isfinite, sqrt
from statistics import median, mean
from random import Random
from typing import Iterable


def counts(successes: int, trials: int) -> None:
    if isinstance(successes, bool) or isinstance(trials, bool):
        raise ValueError('Counts must be integers, not booleans')
    if not isinstance(successes, int) or not isinstance(trials, int) or not 0 <= successes <= trials:
        raise ValueError('Require integer counts: 0 <= successes <= trials')


def pass_at_k(n: int, c: int, k: int) -> float | None:
    """Unbiased HumanEval estimator 1-C(n-c,k)/C(n,k); None when n<k."""
    counts(c, n)
    if not isinstance(k, int) or isinstance(k, bool) or k < 1:
        raise ValueError('k must be a positive integer')
    if n < k:
        return None
    if n - c < k:
        return 1.0
    failure = 1.0
    for i in range(k):
        failure *= (n - c - i) / (n - i)
    return max(0.0, min(1.0, 1.0 - failure))


def wilson(successes: int, trials: int, z: float = 1.959963984540054) -> tuple[float, float] | None:
    """Wilson score interval, 95% by default. Trials must be independent."""
    counts(successes, trials)
    if not isfinite(z) or z <= 0:
        raise ValueError('z must be positive and finite')
    if trials == 0:
        return None
    p = successes / trials
    d = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / d
    margin = z * sqrt(p * (1-p) / trials + z*z / (4*trials*trials)) / d
    return (0.0 if successes == 0 else max(0.0, center-margin)), (1.0 if successes == trials else min(1.0, center+margin))


def percentile(values: list[float], q: float) -> float:
    if not values or not 0 <= q <= 1 or any(not isfinite(x) for x in values):
        raise ValueError('Nonempty values and q in [0,1] required')
    ordered = sorted(values)
    at = (len(ordered)-1) * q
    lo = int(at)
    hi = min(lo+1, len(ordered)-1)
    return ordered[lo] * (hi-at) + ordered[hi] * (at-lo) if hi != lo else ordered[lo]


def task_bootstrap(task_scores: dict[str, list[float]], draws: int = 2000, seed: int = 20261013) -> dict:
    """Task-cluster percentile bootstrap of the macro task mean.

    Resamples tasks, not correlated trials. Does not invent within-task samples.
    With <5 tasks, returns a descriptive mean but no confident interval/rank.
    """
    if not isinstance(draws, int) or isinstance(draws, bool) or draws < 100 or draws > 100_000:
        raise ValueError('draws must be between 100 and 100000')
    means = []
    n = 0
    for values in task_scores.values():
        if not values:
            continue
        if any(not isfinite(x) or not 0 <= x <= 100 for x in values):
            raise ValueError('Scores must be finite and in [0,100]')
        means.append(mean(values))
        n += len(values)
    result = dict(mean=mean(means) if means else None, interval=None, tasks=len(means),
                  trials=n, seed=seed, draws=draws, evidence='insufficient')
    if len(means) >= 5:
        rng = Random(seed)
        samples = [mean(rng.choices(means, k=len(means))) for _ in range(draws)]
        result.update(interval=[percentile(samples, .025), percentile(samples, .975)], evidence='preliminary')
    return result


def paired_difference(a: dict[str, list[float]], b: dict[str, list[float]], seed: int = 20261013) -> dict:
    common = sorted(k for k in a.keys() & b.keys() if a[k] and b[k])
    diffs = [mean(a[k])-mean(b[k]) for k in common]
    if any(not isfinite(x) for x in diffs):
        raise ValueError('Finite scores required')
    result = {'difference': mean(diffs) if diffs else None, 'tasks': len(common), 'interval': None}
    if len(common) >= 5:
        rng = Random(seed)
        samples = [mean(rng.choices(diffs, k=len(diffs))) for _ in range(2000)]
        result['interval'] = [percentile(samples, .025), percentile(samples, .975)]
    return result


def bradley_terry(votes: Iterable[tuple[str, str, str]], iterations: int = 500) -> dict:
    """Regularized MM Bradley-Terry estimates; ties are half-wins (approximation).

    'both_bad' is excluded from preference wins, but counted separately. Absolute
    quality and ranking are different outcomes. No inferential rank is claimed;
    intervals need a campaign-level bootstrap, not a binomial shortcut.
    """
    if not isinstance(iterations, int) or isinstance(iterations, bool) or not 1 <= iterations <= 10000:
        raise ValueError('iterations must be an integer between 1 and 10000')
    pairs = defaultdict(float)
    wins = defaultdict(float)
    graph = defaultdict(set)
    rejected = 0
    total = 0
    for a, b, vote in votes:
        if a == b or vote not in ('a', 'b', 'tie', 'both_bad'):
            raise ValueError('Invalid pairwise vote')
        if vote == 'both_bad':
            rejected += 1
            continue
        graph[a].add(b)
        graph[b].add(a)
        pairs[tuple(sorted((a,b)))] += 1
        wins[a] += 1 if vote == 'a' else .5 if vote == 'tie' else 0
        wins[b] += 1 if vote == 'b' else .5 if vote == 'tie' else 0
        total += 1
    names = sorted(graph)
    if not names:
        return {'strengths': {}, 'connected': False, 'votes': 0, 'both_bad': rejected, 'evidence': 'insufficient'}
    reached, pending = set(), [names[0]]
    while pending:
        name = pending.pop()
        if name not in reached:
            reached.add(name)
            pending.extend(graph[name]-reached)
    if len(reached) != len(names):
        return {'strengths': {}, 'connected': False, 'votes': total, 'both_bad': rejected, 'evidence': 'insufficient'}
    strength = {name: 1.0 for name in names}
    for _ in range(iterations):
        new = {}
        for name in names:
            denom = 0.0
            for other in graph[name]:
                denom += (pairs[tuple(sorted((name, other)))]+1.0) / (strength[name]+strength[other])
            new[name] = (wins[name]+.5*len(graph[name])) / denom
        norm = mean(new.values())
        new = {k: v/norm for k,v in new.items()}
        delta = max(abs(new[k]-strength[k]) for k in names)
        strength = new
        if delta < 1e-10:
            break
    return {'strengths': strength, 'connected': True, 'votes': total, 'both_bad': rejected,
            'evidence': 'descriptive_only', 'intervals': None, 'ties': 'half-win approximation', 'regularization':'half win per side on each observed pair'}


def summary(values: list[float]) -> dict:
    if any(not isfinite(x) or x < 0 for x in values):
        raise ValueError('Finite nonnegative values required')
    return {'n': len(values), 'median': median(values) if values else None,
            'p25': percentile(values,.25) if values else None,
            'p75': percentile(values,.75) if values else None}
