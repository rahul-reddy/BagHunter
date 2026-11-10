# Canonical research-table exports

`canonical-research-tables-v1` adds ten schema-stable Parquet files under each new fixture
run's `contracts/` directory. Existing silver/gold/hindsight outputs retain their separate
roles. `reports/canonical_contracts.json` records row counts, field names, null counts and
file checksums; the run's integrity manifest covers every generated artifact.

| Canonical table | Recorded meaning and limits |
| --- | --- |
| instrument | Permanent fixture ID, listing interval/type; optional supplied CIK/exchange/identifier version. Unknown identity metadata is null. |
| symbol_history | Dated mapping plus optional source. An absent mapping source is not inferred from a modern ticker lookup. |
| universe_membership | One selected-as-of listing/type snapshot, including exclusions. Dollar volume comes from the saved known feature; capitalization stays null. Eligibility is listing/type eligibility, not a strategy admission. |
| daily_bar | Raw OHLCV and availability timestamp. Optional vendor_recorded_at remains distinct and is not inferred from availability. |
| corporate_action | Explicit split factor or cash dividend/delist proceeds. Zero proceeds are preserved; no split value is reinterpreted as cash. |
| fundamental_fact | Original accepted/publication times, accession and citation; optional ingestion_at is not fabricated from filing dates. |
| event_evidence | Grouped recorded synthetic filing facts with public clocks and complete dataset digest. No catalyst/causal classification or confidence is inferred, and the digest is not represented as an original filing digest. |
| backtest_execution | Entry price, entry/exit costs, terminal wealth and exclusions from the constrained saved ledger. Session-only fills have null intraday timestamps; terminal wealth is not converted into a fictitious exit price. Rejection timestamps identify dated selection clocks, not transmitted orders. |
| thesis | Typed empty table when the generated run contains no theses. Browser-local drafts/exports and offline imported dossiers remain operator assertions in a separate archive. |
| source_manifest | Provider, source URL, licensing, coverage and checksum. Synthetic generation has null retrieval_at and GENERATED_NOT_RETRIEVED status. |

Boolean eligibility/amendment flags and integer volume retain their native types. Date/time
columns use ISO 8601 text to match the source archives; timezone-bearing source model fields
reject naive timestamps. Required non-null fields, exact columns and finite values are checked
before writing any table. Empty tables retain all declared fields and their Arrow types.

The pipeline writes inside its transactional staging directory. The read-only API serves only
fixed, allowlisted saved tables after checksum verification; it rejects missing/legacy tables
and corrupt artifacts rather than rebuilding them. Data Quality displays null counts and offers
Parquet/inventory downloads. No table activates quarantined external observations or changes a
research score. Existing archives are never rewritten or silently migrated.

Input models and historical imports now preserve optional CIK/identifier versions, mapping
sources, vendor recording and fact ingestion clocks when actually supplied. Their absence stays
explicit; these fields do not become historical availability evidence or certify provider vintages.

## Persist a source-bound Thesis Studio dossier

Download a fixture JSON dossier from Thesis Studio, then run:

```powershell
uv run baghunter import-thesis --dossier artifacts/thesis-dossier.json
```

The CLI verifies the complete saved run integrity and exact candidate/source binding, validates
explicit numeric assumptions and preserves the original dossier plus a one-row canonical thesis
Parquet under `data/research/thesis_assertions/fixture/<archive-id>/`. A receipt records hashes,
zero predictor promotions and zero verified real theses. Re-import verifies immutable content;
corruption rejects instead of repairing or overwriting. Staging publishes the bundle atomically.
The selected run and its CURRENT pointer are never changed.

Imported critique status is downgraded to UNVERIFIED_IMPORTED_ATTRIBUTION. Stored claimed review
status and request digest do not establish independence, factual accuracy or current context.
Narrative, peer/catalyst claims and exported scenario results remain unverified raw assertions;
no imported output is executed or promoted into screening. Real observation dossiers cannot
masquerade as fixture dossiers. This command makes no provider/model requests and prints no
narrative or source-input details on rejection. No credentials should be included in notes.
