# Independent issuer evidence dossiers

`audit-issuer` audits one local dossier for one explicitly selected candidate in an existing
reference batch. It verifies source binding and document bytes, then reports attributed operator
transcriptions and text comparisons. It performs no requests, writes, automatic identity decisions,
or research activation. A checksum proves byte integrity relative to the supplied manifest;
it does not authenticate the document's origin or validate its assertions.

## Executed single-candidate investigation

The first ticker in the already queried batch is A. The issuer's
[annual-report index](https://www.investor.agilent.com/financials/annual-reports/default.aspx)
links its [2025 Form 10-K PDF](https://s24.q4cdn.com/305549747/files/doc_financials/2025/ar/A-ARS-10-K-BMK-2025.pdf).
The cover page identifies Agilent as registrant and associates its common equity class with ticker A
and the NYSE. The [SEC filing cover](https://www.sec.gov/Archives/edgar/data/1090872/000109087225000087/a-20251031.htm)
corroborates that association. This is filing-era class evidence, not proof of identity continuity
through the Finviz or OpenFIGI retrieval times. No financial values were extracted for research.

On 2026-10-26, the issuer-hosted PDF was downloaded successfully (HTTP 200, 774,535 bytes),
after direct issuer overview and SEC archive downloads returned 403. Those failures were not
retried or archived as evidence. The public web reader could inspect the SEC cover; its output
was not substituted for the downloaded PDF. The annual-report index is a discovery citation,
not a second archived document or independent provider. No SEC contact identity was invented.

Local bundle: ignored `data/issuer-evidence/agilent/`, containing `annual-report.pdf`, download
`receipt.json`, `dossier.json` and the executed `audit.json`. Full vendor rows and raw issuer files
are not committed. The manifest's locator is PDF page 1, registrant and Section 12(b) table.
The exact first-public timestamp of this issuer-hosted PDF has not been established, so
`published_at` is null. The fiscal year end is not a publication timestamp.

- PDF SHA-256: `b0af6fb8e0e1bd47206fd0071c4dfa0fdeeee567024dbe6ad5780fa56c96a473`
- Dossier SHA-256: `61899e6d70006dd2fa681fa670863a0eb58edee74c98c2a27c6b32d947d84020`
- Audit SHA-256: `97d2124719a0129f4d6533ac85e0d96e7986a9e9636d40e589bef71b81d2196f`

Both saved provider company names differ from the legal registrant transcription under the
existing punctuation/suffix-preserving text policy. The dossier records the suffix/abbreviation
differences without normalizing them away. Ticker text agrees. This supports a manual review
hypothesis, not an approved current mapping: the filing supplies no independent FIGI assignment,
and the gap between filing-era evidence and source retrieval remains unresolved.

Assessment: **REVIEW_REQUIRED; zero identity promotions**. No current identity decision is proposed.
No Finviz permanent ID/type, reference archive, fixture output, market-cap scale, price currency,
historical membership, delisting gate, thesis or sample size changed. Exactly one next step:
obtain independently attributable evidence tying this candidate's FIGI identifiers to this
registered class with validity covering the saved source times, before proposing a decision.

## Reproduce the audit

With the saved local source, reference and dossier archives available:

```powershell
uv run baghunter audit-issuer --bundle data/issuer-evidence/agilent --snapshot 84f34ecbc902a7c007e448a27afb83b93a7a5483fb1a5be5f48bbb2dac748567 --reference c713cfb8f3a2d9700defc22d9fa8d386095f7e9ebec913b3af5662fc47df58ae --mode EXTERNAL_UNVERIFIED
```

The CLI prints policy, source/dossier/report digests, document count and disposition only.
It suppresses raw values on errors and exits 2. It cannot download or create a dossier.
Use `packages.data.issuer.audit_issuer` locally for the detailed report; do not publish provider
records or treat transcriptions as established facts. API/UI integration is not implemented.

## Bundle format and boundaries

`dossier.json` uses version `issuer-evidence-dossier-v1` and contains mode (`FIXTURE` or
`EXTERNAL_UNVERIFIED`), `base_snapshot_id`, `reference_id`, exact queried `ticker`, selected
`candidate_figi`, one to three `documents`, and one to twenty nonempty `unresolved` items.
The separately supplied CLI source IDs and mode must match. The source/reference readers
revalidate their original immutable archives; ticker and candidate must exist in that batch.
Other candidates and ambiguity remain visible in the original reference evidence; selecting
a candidate for investigation never resolves them.

Each document requires these fields; all unknown fields are rejected:

| Field | Meaning |
| --- | --- |
| filename | Simple local basename, no paths; unique case-insensitively, not dossier.json |
| sha256 / bytes | Exact raw-document checksum / positive integer size, at most 20 MiB |
| source_url | Attributed public HTTPS document URL |
| discovered_from | Public HTTPS index/citation URL used to find the document |
| retrieved_at | Actual timezone-aware retrieval time, not in the future |
| published_at | Timezone-aware first-public time if established, otherwise explicit null |
| locator | Operator-supplied page/table/section locator |
| issuer_name / ticker / exchange / class_title | Operator transcription, always requires review |

URLs cannot contain credentials, query strings, fragments, whitespace or nonstandard ports.
URL shape is checked offline, not domain ownership, accessibility or publisher authenticity.
The manifest cap is 64 KiB; each file is read with a bounded read. Duplicate document names,
symlinks/junctions in the bundle or its ancestors, missing/corrupt files, invalid dates, control
characters, and out-of-batch selections fail closed. Published time cannot exceed retrieved time.
Unknown publication time does not unlock PIT usage. The format intentionally has no approval field.

Report policy `issuer-evidence-audit-v1` binds the raw manifest checksum, the prior reconciliation
digest, all document checksums/metadata/transcriptions and unresolved notes. Its digest follows
the existing canonical UTF-8 JSON policy, excluding `report_sha256` itself. It reports ticker
agreement and both name comparisons without interpreting class/exchange text as verified.
All results have false identity/share-class verification and zero promotions, including exact
text agreement, conflicting assertions, ambiguous candidates and fixture dossiers. Determinism
applies to accepted frozen inputs; impossible future retrievals are rejected against the audit clock.

No source allowlist, signature check, PDF/HTML extraction, claim adjudication, historical inference,
network fallback, global archive registry or dashboard activation is provided by this audit.
