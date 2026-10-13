# Scientific methodology / gdb-technical 1.0.0

## Scope, not a universal intelligence score

This preview separates standardized direct model calls, complete agent systems, and internally authored fixtures. The delivered paid worker supports only the first category for a bounded browser task. Agentic configurations cannot silently enter that cohort. Fixtures are never AI evidence. No result from another benchmark has been copied into the leaderboard.

## Technical score

Each versioned task declares required assertion IDs. The current browser contract checks boot, canvas, runtime errors, start, keyboard movement, restart, mobile layout and the touch control. A positive finite weight is required for each check. Passed weight divided by total weight produces a 0-100 technical score. A failed blocking boot/start/runtime assertion caps the score at zero. Any `not_run` or `error` outcome leaves the score missing, not a pass. Missing/duplicate/mismatched assertion IDs prevent publication.

**These are smoke observations, not proof of complete gameplay quality.** Data attributes are candidate-controlled and can be gamed. Reviewers must inspect the actual project and gameplay, not just trust its reported `data-x` or score. Canvas color diversity proves rendering, not artistic merit. Mobile overflow and a pointer interaction do not certify native-touch usability or all devices. No performance-throughput score or complete-game aesthetic score is claimed.

## Reviews and publication

An explicit rubric covers artifact inspection, brief, controls, restart and score verification. A real model run requires two distinct, non-conflicted reviewer accounts, neither the campaign creator. A fixture needs one decision only to exercise the technical publication flow. Automated test decisions exist solely in temporary test databases and are not independent human reviews.

Published snapshots are append-only at the SQL level; the source artifacts and frozen configuration are hashed. This detects changed content but is not a cryptographically signed transparency service or a defense against a host administrator replacing the entire database. Public results omit private prompts/provider responses. Complete compatible campaigns are required before leaderboard inclusion; incomplete campaigns mean missing evidence, not success.

## pass@1 and pass@k

For n independent attempts with c successes, the implemented unbiased estimator is:

`pass@k = 1 - C(n-c,k) / C(n,k)` for `n >= k`.

Return missing for `n < k`. Do not extrapolate a pass@10 from one attempt. The implementation uses a product rather than factorials. Trials must share task, protocol and comparable budgets. Compute task-level values before aggregating over tasks; unequal trial counts must not silently weight easy tasks more heavily.

## Uncertainty

The descriptive score is the macro-average of per-task trial means. A seeded percentile bootstrap resamples **tasks**, retaining correlated trials within their task; it does not treat every attempt as an independent task. Fewer than five distinct tasks yields `insufficient`, a descriptive mean where available, and **no interval or confident rank**. Five is a preview display floor, not a theorem of adequacy. Small or unrepresentative task sets remain a limitation at larger n.

Wilson intervals are available for independent Bernoulli counts. They are not substitutes for clustered task uncertainty. Paired deltas use only shared tasks and bootstrap their differences. Percentile bootstrap coverage is not guaranteed for very small or highly skewed samples. Latency/cost summaries return medians and quartiles, not invented values for absent data.

## Human preference

The implemented Bradley-Terry utility estimator uses MM updates with a half-win regularization per side on each observed pair. Ties contribute half a win; this is an approximation, not a fitted Davidson tie model. `both_bad` is counted separately, not interpreted as equal positive quality. Disconnected comparison graphs do not yield a shared ranking. The result is **descriptive only**; rank intervals and campaign-level bootstrap remain unimplemented. Internal fixture votes are excluded from all AI preference statistics.

## Comparability and costs

Cohorts require matching suite/protocol, environment, mode, harness, task-set hash, output cap, time limit, tools hash and budget policy. Model reasoning is displayed, not erased. Cost is an estimate derived from recorded token usage and dated reference rates, not an invoice. Cached tokens and unknown usage are distinct; absent cache rates conservatively use input price. Provider/tool charges not observable in a response remain unknown. Supplier-side budget caps are necessary: application reservations cannot guarantee an external invoice ceiling.

## Sources and limitations

HumanEval reference estimator: https://github.com/openai/human-eval/blob/master/human_eval/evaluation.py

HELM's broader transparent evaluation context: https://crfm.stanford.edu/helm/

Wilson interval: Wilson, E. B. (1927), Journal of the American Statistical Association, 22(158), 209-212, DOI 10.1080/01621459.1927.10502953.

Bradley & Terry (1952), Biometrika 39(3/4), 324-345, DOI 10.2307/2334029. Bootstrap design and thresholds here are project decisions; they have not undergone external scientific peer review.

Public task contamination is possible. Private test version storage is supported and excluded from public projections, but secure private dataset governance, holdouts, anomaly detection and an external contest process require organizational work beyond these code controls.
