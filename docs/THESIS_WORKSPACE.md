# Thesis Studio evidence workspace

Thesis Studio uses the same attributed qualitative/peer/critic workflow as the saved Finviz
observation desk. It remains a fixture assumptions workbench, not a verified investment thesis.
All arithmetic uses the existing read-only scenario API. No model or provider calls are added.

The critic request binds the run/security/source digests, model version, candidate evidence,
explicit scenario input strings, all three calculated scenarios, notes, current catalyst calendar,
and structured research. Editing any bound input makes a prior review stale. Reviewer attribution
must differ from the primary author; independence and correctness remain unverified. Missing/future
critic citations remain visible. A freeform bear argument does not satisfy this workflow.

Inputs preserve empty strings. Missing net debt, dilution, multiples or other assumptions are
never converted to zero. Invalid/missing inputs clear scenario results and disable combined exports
and critic requests. Explicit zero net debt is supported, as is negative net debt (net cash).
All assumptions, source clocks, exclusions and limitations remain in JSON/Markdown exports.

New browser saves use fixture-thesis-draft-v2 and a run/security key. Source-context mismatches
reject. Legacy security-only numeric drafts can load only their validated notes and assumptions;
they restore no source association or critic. Save again to create a run-bound draft. Scenarios
recalculate after loading. The separately persisted catalyst calendar remains current; loading an
older thesis draft never silently overwrites it, and changed calendar assertions stale the critic.
Browser storage is local; use explicit memo/dossier/calendar exports for backup.

The shared risk register lists all sixteen specified risk topics. Each assessment is a dated
qualitative record with judgment tag, attribution, source and disconfirmation. Missing topics stay
Not assessed; a recorded assertion never means the risk is verified or absent. The same fields
are available in the Finviz research desk. JSON and Markdown retain the records and coverage.

No current security identities, historical coverage, factual investment conclusions or empirical
probabilities are inferred. Zero real investment theses are verified. See RESEARCH_EVIDENCE.md
for source/peer bounds and critique statuses, and STATUS.md for current acceptance/delivery.
