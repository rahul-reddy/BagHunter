# Failure-oriented robustness

The `failure-oriented-robustness-v1` archive retains twelve fixed stress attempts from the
same fixture source and constrained portfolio engine. It never selects a winning policy.
The Research tools view displays every attempt, unavailable/rejected reasons, policy inputs,
selected exclusion ledgers and downloads of the complete JSON and Markdown reports.

The attempts remove the highest realized-contribution name and sector, widen costs twice,
halve the position cap, increase liquidity floors twice, lengthen filing processing lags twice,
exclude the declared `fixture-micro` bucket, assume zero proceeds for known delists, and request
an independent adjusted-price comparison. Contribution exclusions use later realized P&L and
are explicitly hindsight diagnostics. All other stresses are predeclared changes. The fixture
has no declared micro-bucket members; this unchanged comparison is labeled. Independent adjusted
prices are unavailable and receive no substituted metrics. Invalid stress policies stay rejected.

`portfolio-v2-unvalidated` preserves shared whole-share, cash, entry/exit cost, position/sector
cap, capacity and missing-mark boundaries. Immutable exclusions are validated and canonicalized.
A filing lag is an integer from 24 to 720 hours after the later acceptance/publication time;
raw source times do not change. Selection ledgers retain the available filing inputs and lag.
A zero-proceeds sensitivity applies only to validated, known delist actions. It does not supply
missing exit values or repair invalid source actions. Raw actions remain unchanged and the
assumption ledger records reported and assumed proceeds separately.

Daily risk additionally reports the deepest drawdown's recovery sessions, its status, and the
current underwater duration. An ongoing recovery remains unavailable. Daily-close statistics
omit intraday paths. Ranking sensitivity retains the original six weight variations plus six
leave-one-family-out runs with frozen original weights and missing-weight penalties; weights
are not redistributed. These ranking diagnostics use no outcomes.

Legacy archives expose an unavailable robustness report rather than recomputing under new code.
All results are fixture software diagnostics, not empirical regime/decade/capacity evidence or
untouched holdout validation. Real history, action semantics and independent price contracts
remain separate evidence gates.
