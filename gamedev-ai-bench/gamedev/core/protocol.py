from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING
from hashlib import sha256
import json
import math

HARNESS_VERSION = 'gdb-standard/1.0.0'
PROTOCOL_VERSION = 'gdb-technical/1.0.0'
STATES = {
    'pending': {'preparing', 'cancelled'},
    'preparing': {'running', 'failed', 'cancelled'},
    'running': {'evaluating', 'failed', 'cancelled'},
    'evaluating': {'awaiting-review', 'failed', 'cancelled'},
    'awaiting-review': {'completed', 'failed', 'cancelled'},
    'completed': set(), 'failed': set(), 'cancelled': set(),
}


def transition(current: str, target: str) -> str:
    if target not in STATES.get(current, set()):
        raise ValueError(f'Invalid run transition: {current} -> {target}')
    return target


def canonical_hash(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                             allow_nan=False).encode()).hexdigest()


def compare_configurations(a: dict, b: dict) -> dict:
    fields = ('suite_version', 'protocol_version', 'environment', 'mode', 'harness_version',
              'task_set_hash', 'max_output_tokens', 'time_limit_seconds', 'tools_hash', 'budget_policy')
    differences = [key for key in fields if key not in a or key not in b or a[key] != b[key]]
    return {'comparable': not differences, 'differences': differences,
            'reason': 'matched_protocol' if not differences else 'incompatible_or_missing_metadata'}


def technical_score(assertions: list[dict]) -> dict:
    """Missing required checks are not passes. Blocking failures cap score at zero."""
    if not assertions:
        return {'score': None, 'passed': False, 'complete': False, 'blocking_failure': False}
    if len({a['id'] for a in assertions}) != len(assertions):
        raise ValueError('Duplicate assertion IDs')
    for item in assertions:
        if item.get('outcome') not in ('passed', 'failed', 'not_run', 'error'):
            raise ValueError('Unknown assertion outcome')
        if not isinstance(item.get('weight'), (int, float)) or isinstance(item.get('weight'), bool) or not math.isfinite(item['weight']) or item['weight'] <= 0:
            raise ValueError('Weights must be finite and positive')
    complete = all(a['outcome'] in ('passed', 'failed') for a in assertions)
    blocking = any(a.get('blocking') and a['outcome'] != 'passed' for a in assertions)
    score = 100 * sum(a['weight'] for a in assertions if a['outcome'] == 'passed') / sum(a['weight'] for a in assertions)
    return {'score': round(0 if blocking else score, 2) if complete else None,
            'passed': complete and all(a['outcome'] == 'passed' for a in assertions),
            'complete': complete, 'blocking_failure': blocking}


@dataclass(frozen=True)
class Price:
    input_per_million: Decimal
    output_per_million: Decimal
    cached_per_million: Decimal | None = None
    source: str = ''
    checked_at: str = ''

    def estimate_microusd(self, input_tokens: int, output_tokens: int, cached_tokens: int = 0) -> int:
        for count in (input_tokens, output_tokens, cached_tokens):
            if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                raise ValueError('Token counts must be nonnegative integers')
        if cached_tokens > input_tokens:
            raise ValueError('Cached tokens cannot exceed input tokens')
        cached_rate = self.cached_per_million if self.cached_per_million is not None else self.input_per_million
        for rate in (self.input_per_million, self.output_per_million, cached_rate):
            if not rate.is_finite() or rate < 0:
                raise ValueError('Rates must be finite and nonnegative')
        # 1 USD = 1e6 microUSD; price/token = price/1e6, so factors cancel.
        micro = (input_tokens-cached_tokens)*self.input_per_million + output_tokens*self.output_per_million + cached_tokens*cached_rate
        return int(micro.to_integral_value(rounding=ROUND_CEILING))


def validate_budget(authorized: int, reserved: int, spent: int, request: int) -> None:
    if any(not isinstance(x, int) or isinstance(x, bool) or x < 0 for x in (authorized, reserved, spent, request)):
        raise ValueError('Budget values must be nonnegative integer microUSD')
    if reserved + spent + request > authorized:
        raise ValueError('Campaign spending authorization exceeded')
