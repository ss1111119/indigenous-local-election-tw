# column-oracle-documentation Specification

## Purpose

Each long table's columns carry semantics declared in `scripts/oracles.py` as
a manifest — provenance, the arithmetic and semantic checks that back each
column, and free-text caveats. A manifest that exists in source but is never
rendered anywhere is invisible to anyone who does not read the Python source,
which defeats its purpose as documentation.

This capability governs two things: that every manifest a build script
actively uses for column-consistency checking is rendered into the shared
`docs/schema/oracles.md` document, staying current automatically as the
manifest changes rather than needing a manual edit; and that where two
datasets share the same raw-value handling convention for a column, both
datasets' generators perform equivalent self-verification on that column,
so protection does not exist for one dataset only because its check happened
to be implemented first.

## Requirements

### Requirement: Every declared column manifest is rendered into the shared oracle document
`docs/schema/oracles.md` SHALL contain a section for every column manifest declared in `scripts/oracles.py` that a build script actively uses for column-consistency checking, and each section SHALL list every column that manifest declares.

#### Scenario: The legislative manifest gains a rendered section
- **WHEN** `scripts/build_legislative_election.py` completes a run
- **THEN** `docs/schema/oracles.md` contains sections covering all columns declared in `LEGISLATIVE_MANIFEST`'s `legislative_summary`, `legislative_candidates`, and `legislative_votes` entries

#### Scenario: The local-election sections are unaffected
- **WHEN** `scripts/build_local_election.py` completes a run after this change
- **THEN** the local-election sections of `docs/schema/oracles.md` are byte-identical to what they were before this change, for the same input data

#### Scenario: A manifest gains a new column
- **WHEN** a column is added to `LEGISLATIVE_MANIFEST`
- **THEN** the next run of `scripts/build_legislative_election.py` produces a `docs/schema/oracles.md` whose legislative section includes the new column, without requiring any manual edit to the document

#### Scenario: The party-list manifest gains a rendered section
- **WHEN** `scripts/build_party_list_election.py` completes a run
- **THEN** `docs/schema/oracles.md` contains sections covering all columns declared in `PARTY_LIST_MANIFEST`'s `party_list_summary`, `party_list_votes`, and `party_list_seats` entries

#### Scenario: The legislative and local-election sections stay unaffected by the party-list addition
- **WHEN** `scripts/build_party_list_election.py` completes a run after this change
- **THEN** the local-election and legislative sections of `docs/schema/oracles.md` are byte-identical to what they were before this change, for the same input data


<!-- @trace
source: party-list-oracle-doc
updated: 2026-08-25
code:
  - docs/schema/oracles.md
  - scripts/build_party_list_election.py
  - scripts/oracles.py
tests:
  - scripts/test_build_party_list_election.py
-->

---
### Requirement: Population column has parity in self-verification across datasets
Where two datasets share the same raw-value handling convention for a column (the value is preserved as a string, not converted, per the source format), the generator for each dataset SHALL perform equivalent parseability and validity checks on that column, not just the dataset whose check was implemented first.

#### Scenario: Legislative population values are checked for parseability
- **WHEN** `scripts/build_legislative_election.py` processes a row whose `人口數` value is not parseable as a decimal number
- **THEN** the build aborts with an error naming the offending row's administrative-area identifier and the invalid value

#### Scenario: Legislative population values are checked for non-negativity
- **WHEN** `scripts/build_legislative_election.py` processes a row whose `人口數` value parses as a negative decimal number
- **THEN** the build aborts with an error naming the offending row's administrative-area identifier and the value

#### Scenario: Valid population values pass through unaffected
- **WHEN** every row's `人口數` value is a non-negative decimal string (including `"0"` and values with a fractional component)
- **THEN** the build completes without raising an error from this check

<!-- @trace
source: legislative-oracle-doc-and-population-check
updated: 2026-08-25
code:
  - scratch/verify_crosswalk.py
  - scratch/expected.txt
  - scratch/build_1998_2002_crosswalk.py
  - docs/schema/oracles.md
  - scratch/add_legacy_sources.py
  - scratch/inventory_legacy.py
  - scratch/verify_pop.py
  - scratch/measure_2005d.py
  - scratch/gen_expected.py
  - scratch/gen_anomalies.py
  - scratch/measure_2005.py
  - scratch/measure_2005b.py
  - CLAUDE.md
  - GEMINI.md
  - scratch/probe_legacy_build.py
  - scratch/measure_town_codes.py
  - scratch/verify_claims.py
  - scratch/verify_21c.py
  - scratch/verify_33.py
  - scripts/oracles.py
  - scratch/measure_2005e.py
  - scratch/measure_2005f.py
  - scratch/dryrun_manifest.py
  - scratch/probe_districts.py
  - scratch/probe4.py
  - scratch/verify_strip.py
  - scratch/review_q4.md
  - scratch/probe5.py
  - scratch/probe_1994.py
  - scratch/verify_11.py
  - scratch/verify_identity.py
  - scratch/measure_auth_existing.py
  - scratch/review_q3.md
  - scratch/review_question.md
  - scratch/measure_ws2.py
  - scratch/baseline/candidates.csv
  - scratch/review_q6.md
  - scratch/probe2.py
  - scratch/inventory_legacy.json
  - scratch/verify_pop2.py
  - scratch/measure_town_feasible.py
  - scratch/baseline/summary.csv
  - scratch/review_q2.md
  - scratch/measure_2005c.py
  - scratch/verify_21.py
  - scratch/strip_experiment.py
  - scratch/gen_town_anom.py
  - .spectra.yaml
  - scratch/chk1998t2.py
  - scratch/probe6.py
  - scratch/verify_auth.py
  - scratch/measure_trunc.py
  - AGENTS.md
  - scratch/add_defect7.py
  - scratch/measure_2005_towns.py
  - scratch/measure_pop2.py
  - scratch/probe7.py
  - scratch/verify_review.py
  - scratch/measure_2005g.py
  - scratch/measure_whitespace.py
  - scratch/baseline/votes.csv
  - scripts/build_legislative_election.py
  - scratch/verify_32.py
  - scratch/review_q5.md
  - scratch/list_zip.py
  - scratch/review_q7.md
  - scratch/chk_cw.py
  - scratch/probe_anomalies.py
  - scratch/zip_names.json
  - scratch/measure_pop.py
  - scratch/probe3.py
  - scratch/probe_districts2.py
tests:
  - scripts/test_build_legislative_election.py
-->

---
### Requirement: Population column validation rejects non-finite and non-string values
The shared population-column check SHALL reject values that are not finite decimal numbers (including `Infinity`, `-Infinity`, and `NaN`) and values that are not strings, raising the project's unified validation exception in both cases, distinguishable from the "not a decimal number" and "negative value" failure messages.

#### Scenario: Infinity is rejected
- **WHEN** a row's population column value is `"Infinity"` or `"-Infinity"`
- **THEN** the build aborts with the project's unified validation exception, with a message distinguishable from the "not a decimal number" and "negative value" messages

#### Scenario: NaN is rejected without an unhandled exception
- **WHEN** a row's population column value is `"NaN"`
- **THEN** the build aborts with the project's unified validation exception, and no unrelated exception type (such as `decimal.InvalidOperation` propagating uncaught from a subsequent comparison) is raised instead

#### Scenario: A non-string input is rejected with the unified exception type
- **WHEN** a row's population column value is not a string (for example `None`)
- **THEN** the build aborts with the project's unified validation exception rather than an unwrapped `TypeError`

#### Scenario: Valid finite non-negative values still pass
- **WHEN** a row's population column value is a finite non-negative decimal string (including `"0"` and strings with a fractional component)
- **THEN** the check does not raise any exception


<!-- @trace
source: population-decimal-hardening-and-atomic-oracle-write
updated: 2026-08-25
code:
  - scratch/probe_districts.py
  - scratch/probe_districts2.py
  - scratch/measure_town_feasible.py
  - scratch/review_q5.md
  - scratch/measure_town_codes.py
  - scratch/review_q4.md
  - scratch/review_q6.md
  - scratch/measure_2005e.py
  - scratch/measure_trunc.py
  - scratch/gen_expected.py
  - scratch/measure_2005b.py
  - AGENTS.md
  - scratch/build_1998_2002_crosswalk.py
  - scratch/verify_strip.py
  - scratch/probe_anomalies.py
  - scratch/verify_review.py
  - scratch/verify_pop2.py
  - scratch/probe_legacy_build.py
  - scratch/verify_33.py
  - scratch/measure_2005c.py
  - scripts/build_legislative_election.py
  - scratch/add_legacy_sources.py
  - scratch/review_q7.md
  - scratch/baseline/candidates.csv
  - scratch/measure_pop.py
  - scratch/add_defect7.py
  - scratch/verify_11.py
  - scratch/measure_auth_existing.py
  - scratch/baseline/summary.csv
  - scratch/measure_ws2.py
  - scratch/baseline/votes.csv
  - scratch/gen_anomalies.py
  - scratch/verify_21.py
  - scratch/probe6.py
  - scratch/strip_experiment.py
  - CLAUDE.md
  - scratch/verify_32.py
  - scratch/measure_2005g.py
  - scratch/inventory_legacy.json
  - scratch/verify_pop.py
  - scratch/gen_town_anom.py
  - scratch/zip_names.json
  - scratch/verify_crosswalk.py
  - scratch/probe4.py
  - scratch/probe_1994.py
  - scripts/oracles.py
  - scratch/probe7.py
  - scratch/probe2.py
  - scratch/measure_whitespace.py
  - scripts/build_local_election.py
  - scratch/measure_2005d.py
  - scratch/measure_pop2.py
  - scratch/measure_2005.py
  - scratch/chk1998t2.py
  - scratch/verify_identity.py
  - scratch/review_q3.md
  - scratch/expected.txt
  - scratch/verify_auth.py
  - scratch/dryrun_manifest.py
  - GEMINI.md
  - scratch/measure_2005f.py
  - scratch/list_zip.py
  - .spectra.yaml
  - scratch/probe5.py
  - scratch/inventory_legacy.py
  - scratch/review_q2.md
  - scratch/measure_2005_towns.py
  - scratch/probe3.py
  - scratch/chk_cw.py
  - scratch/review_question.md
  - scratch/verify_21c.py
  - scratch/verify_claims.py
tests:
  - scripts/test_build_legislative_election.py
-->

---
### Requirement: The shared oracle document is written atomically
Writing `docs/schema/oracles.md` SHALL be atomic: the file SHALL always contain either its complete previous content or its complete new content, never a partial or interleaved write, regardless of which build script performs the write or whether the write is interrupted.

#### Scenario: A completed write replaces the file wholesale
- **WHEN** a build script finishes generating the oracle document content
- **THEN** the file on disk is replaced via an atomic filesystem operation rather than being overwritten in place, and its content after the write exactly matches the freshly generated content

#### Scenario: Both build scripts share one write path
- **WHEN** either `scripts/build_local_election.py` or `scripts/build_legislative_election.py` writes the oracle document
- **THEN** both invoke the same shared write function rather than each independently constructing the target path and performing its own file write

<!-- @trace
source: population-decimal-hardening-and-atomic-oracle-write
updated: 2026-08-25
code:
  - scratch/probe_districts.py
  - scratch/probe_districts2.py
  - scratch/measure_town_feasible.py
  - scratch/review_q5.md
  - scratch/measure_town_codes.py
  - scratch/review_q4.md
  - scratch/review_q6.md
  - scratch/measure_2005e.py
  - scratch/measure_trunc.py
  - scratch/gen_expected.py
  - scratch/measure_2005b.py
  - AGENTS.md
  - scratch/build_1998_2002_crosswalk.py
  - scratch/verify_strip.py
  - scratch/probe_anomalies.py
  - scratch/verify_review.py
  - scratch/verify_pop2.py
  - scratch/probe_legacy_build.py
  - scratch/verify_33.py
  - scratch/measure_2005c.py
  - scripts/build_legislative_election.py
  - scratch/add_legacy_sources.py
  - scratch/review_q7.md
  - scratch/baseline/candidates.csv
  - scratch/measure_pop.py
  - scratch/add_defect7.py
  - scratch/verify_11.py
  - scratch/measure_auth_existing.py
  - scratch/baseline/summary.csv
  - scratch/measure_ws2.py
  - scratch/baseline/votes.csv
  - scratch/gen_anomalies.py
  - scratch/verify_21.py
  - scratch/probe6.py
  - scratch/strip_experiment.py
  - CLAUDE.md
  - scratch/verify_32.py
  - scratch/measure_2005g.py
  - scratch/inventory_legacy.json
  - scratch/verify_pop.py
  - scratch/gen_town_anom.py
  - scratch/zip_names.json
  - scratch/verify_crosswalk.py
  - scratch/probe4.py
  - scratch/probe_1994.py
  - scripts/oracles.py
  - scratch/probe7.py
  - scratch/probe2.py
  - scratch/measure_whitespace.py
  - scripts/build_local_election.py
  - scratch/measure_2005d.py
  - scratch/measure_pop2.py
  - scratch/measure_2005.py
  - scratch/chk1998t2.py
  - scratch/verify_identity.py
  - scratch/review_q3.md
  - scratch/expected.txt
  - scratch/verify_auth.py
  - scratch/dryrun_manifest.py
  - GEMINI.md
  - scratch/measure_2005f.py
  - scratch/list_zip.py
  - .spectra.yaml
  - scratch/probe5.py
  - scratch/inventory_legacy.py
  - scratch/review_q2.md
  - scratch/measure_2005_towns.py
  - scratch/probe3.py
  - scratch/chk_cw.py
  - scratch/review_question.md
  - scratch/verify_21c.py
  - scratch/verify_claims.py
tests:
  - scripts/test_build_legislative_election.py
-->

---
### Requirement: Shared verification helpers carry mutation-test proof of discriminating power
Any function in `scripts/oracles.py` that a mutation-test script's test-selection filter can reach SHALL have that filter actually include the tests exercising it, and the corresponding mutation-test script SHALL contain at least one real-file mutation per shared function proven, by manual apply-and-revert verification, to turn the exercising test from passing to failing.

#### Scenario: A mutation-test script's selection filter is not silently stale
- **WHEN** a new test function is added to a `test_build_*.py` file that exercises a function in `scripts/oracles.py`
- **THEN** the corresponding `mutate_build_*.py` script's test-selection filter is updated to include that test function's name, so the mutation suite does not silently skip evaluating it

#### Scenario: check_population_column has a real-file mutation
- **WHEN** `check_population_column`'s finite-value check is removed via a real-file mutation applied to `scripts/oracles.py`
- **THEN** running the exercising test through the mutation-test script's harness reports the test as failing, and reverting the mutation restores it to passing

#### Scenario: write_oracle_document has a real-file mutation
- **WHEN** `write_oracle_document`'s write step is bypassed via a real-file mutation applied to `scripts/oracles.py`
- **THEN** running the exercising test through the mutation-test script's harness reports the test as failing, and reverting the mutation restores it to passing

#### Scenario: _render_manifest_sections has a real-file mutation covering the party-list call site
- **WHEN** the call to `_render_manifest_sections` that renders `PARTY_LIST_MANIFEST` is removed via a real-file mutation applied to `scripts/oracles.py`
- **THEN** running the exercising test through the mutation-test script's harness reports the test as failing, and reverting the mutation restores it to passing

<!-- @trace
source: oracles-shared-fn-mutation-coverage
updated: 2026-08-25
code:
  - scripts/mutate_build_legislative_election.py
  - scripts/mutate_build_party_list_election.py
-->