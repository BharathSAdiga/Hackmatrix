# PARTSINTEL Regression Report

Date: 2026-11-05

## Source status

No controller, evaluator, or simulator source was changed during the twist-readiness audit. The existing stable version, including the missing-wattage clarification fix from the previous evaluation, remains in place.

## Ordinary regression results

| Check | Result |
|---|---:|
| Unit suite | 91 passed |
| Episode suite | 1 passed |
| Ordinary training mock | 40/40 scored; score 97.329; unsafe 0; unavailable 0; invalid 0 |
| Ordinary practice mock | 12/12 scored; score 99.583; unsafe 0; unavailable 0; invalid 0 |

The mock provider is not genuine inference. These scores test the local deterministic pipeline only and do not prove official eligibility.

## Original edge-case coverage retained

The passing unit suite continues to cover:

- approved/draft revisions, late old retries, duplicate deliveries, document conflicts, and malformed metadata;
- unit conversion, connector aliases, missing wattage, prose parsing, and voltage/connector/wattage compatibility;
- stale stock, false-positive/false-negative snapshots, dispatch consumption, repeated verification, changed-policy stock evidence, and exhausted budget;
- malformed or empty model text, bounded gateway messages, state serialization, call limits, unknown IDs, duplicate decisions, and unsafe dispatch rejection;
- six-ticket completion and the 60-action cap.

## Twist-specific status

The portal had not reached its posted twist-release time when checked, and no release or changed dataset was available in the repository or public repository ref. Thus there is no genuine post-twist regression result to report. Do not replace the passing implementation based only on the pre-existing simulator fixture. Compare the actual release and run the ordinary and changed suites before adopting any twist-specific patch.
