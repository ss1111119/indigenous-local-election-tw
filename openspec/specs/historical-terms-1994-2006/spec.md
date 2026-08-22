# historical-terms-1994-2006 Specification

## Purpose

The dataset reaches back past 2009 to 1994, but the earlier terms are not simply
more of the same series. Three things change: some categories are different
institutions that happen to share a name, the administrative code scheme is
renumbered between terms, and one term's files cover a category that no longer
exists. This capability governs which historical records join the comparable
series and which are carried but held apart.

The distinction is by institution, not by date. The 1998, 2002, and 2005 mountain
and plain indigenous county councilors are the same office as the later terms and
belong to the main sequence. The 1994 provincial councilors and the combined
indigenous city councilor category are not, and they carry custom election type
codes so no query can reach them by asking for T2 or T3.

Whether a record is comparable is therefore a property of the record, declared in
the output as `is_main_sequence` and `admin_code_system`, rather than something a
reader is expected to infer from the year. A reader who sums a column without
filtering gets a wrong answer either way; the flags make the wrong answer
detectable instead of invisible.

## Requirements

### Requirement: T2 and T3 Main Sequence Inclusion
The system SHALL include the 1998, 2002, and 2005 mountain indigenous (T3) and plain indigenous (T2) county councilors in the dataset and flag them as part of the main sequence.

#### Scenario: Processing 1998-2005 T2-T3 files
- **WHEN** processing 1998, 2002, and 2005 county councilor files
- **THEN** the output records SHALL have the `is_main_sequence` flag set to true


<!-- @trace
source: include-1994-2006-terms
updated: 2026-08-20
code:
  - scratch/strip_experiment.py
  - scratch/verify_33.py
  - scratch/verify_auth.py
  - scratch/measure_2005_towns.py
  - scratch/measure_2005.py
  - scratch/review_q5.md
  - scratch/measure_trunc.py
  - scratch/verify_32.py
  - scratch/review_q7.md
  - scratch/baseline/votes.csv
  - CLAUDE.md
  - scratch/measure_town_feasible.py
  - scratch/measure_town_codes.py
  - data/processed/cec-local-election-votes-long.csv.gz
  - scratch/gen_anomalies.py
  - scratch/add_legacy_sources.py
  - scratch/probe3.py
  - AGENTS.md
  - scratch/measure_2005d.py
  - scratch/verify_pop2.py
  - scratch/measure_whitespace.py
  - scratch/review_q6.md
  - scratch/expected.txt
  - scratch/verify_claims.py
  - scratch/inventory_legacy.py
  - scratch/verify_pop.py
  - scratch/measure_2005e.py
  - scratch/list_zip.py
  - docs/schema/oracles.md
  - scratch/probe_1994.py
  - scratch/measure_pop2.py
  - scratch/review_q4.md
  - scratch/measure_2005b.py
  - .spectra.yaml
  - docs/schema/cec-local-election.md
  - data/processed/cec-local-election-candidates-long.csv
  - scratch/verify_identity.py
  - scratch/gen_expected.py
  - scratch/measure_2005c.py
  - data/processed/cec-local-election-summary-long.csv.gz
  - scratch/probe6.py
  - scratch/measure_2005g.py
  - scratch/probe4.py
  - scratch/measure_2005f.py
  - scratch/build_1998_2002_crosswalk.py
  - scratch/probe2.py
  - GEMINI.md
  - scratch/baseline/summary.csv
  - scratch/dryrun_manifest.py
  - scratch/measure_auth_existing.py
  - scratch/probe_anomalies.py
  - scratch/chk_cw.py
  - scripts/build_local_election.py
  - scratch/probe_legacy_build.py
  - scratch/add_defect7.py
  - HANDOFF.md
  - data/sources.json
  - scripts/oracles.py
  - scratch/verify_crosswalk.py
  - scratch/verify_strip.py
  - scratch/verify_review.py
  - scratch/zip_names.json
  - scratch/chk1998t2.py
  - README.md
  - scratch/review_q2.md
  - scratch/measure_pop.py
  - data/processed/validation-report.json
  - scratch/gen_town_anom.py
  - scratch/probe7.py
  - scratch/baseline/candidates.csv
  - scratch/probe5.py
  - scratch/measure_ws2.py
  - scratch/review_question.md
  - data/processed/cec-county-code-crosswalk-1998-2002.csv
  - scratch/review_q3.md
  - scratch/inventory_legacy.json
tests:
  - scripts/test_build_local_election.py
  - scratch/mutation_test.py
-->

---
### Requirement: Custom Election Type Codes
The system SHALL assign custom, project-specific election type codes for 1994 Taiwan Provincial Councilors and the "combo" indigenous city councilor category (which exists across multiple early terms).

#### Scenario: Assigning codes to 1994 provincial councilors
- **WHEN** processing 1994 provincial councilor files
- **THEN** the system SHALL assign a new custom code distinct from T2 and T3

#### Scenario: Assigning codes to combo indigenous city councilors
- **WHEN** processing combo indigenous city councilors
- **THEN** the system SHALL assign a custom combo code distinct from T2 and T3


<!-- @trace
source: include-1994-2006-terms
updated: 2026-08-20
code:
  - scratch/strip_experiment.py
  - scratch/verify_33.py
  - scratch/verify_auth.py
  - scratch/measure_2005_towns.py
  - scratch/measure_2005.py
  - scratch/review_q5.md
  - scratch/measure_trunc.py
  - scratch/verify_32.py
  - scratch/review_q7.md
  - scratch/baseline/votes.csv
  - CLAUDE.md
  - scratch/measure_town_feasible.py
  - scratch/measure_town_codes.py
  - data/processed/cec-local-election-votes-long.csv.gz
  - scratch/gen_anomalies.py
  - scratch/add_legacy_sources.py
  - scratch/probe3.py
  - AGENTS.md
  - scratch/measure_2005d.py
  - scratch/verify_pop2.py
  - scratch/measure_whitespace.py
  - scratch/review_q6.md
  - scratch/expected.txt
  - scratch/verify_claims.py
  - scratch/inventory_legacy.py
  - scratch/verify_pop.py
  - scratch/measure_2005e.py
  - scratch/list_zip.py
  - docs/schema/oracles.md
  - scratch/probe_1994.py
  - scratch/measure_pop2.py
  - scratch/review_q4.md
  - scratch/measure_2005b.py
  - .spectra.yaml
  - docs/schema/cec-local-election.md
  - data/processed/cec-local-election-candidates-long.csv
  - scratch/verify_identity.py
  - scratch/gen_expected.py
  - scratch/measure_2005c.py
  - data/processed/cec-local-election-summary-long.csv.gz
  - scratch/probe6.py
  - scratch/measure_2005g.py
  - scratch/probe4.py
  - scratch/measure_2005f.py
  - scratch/build_1998_2002_crosswalk.py
  - scratch/probe2.py
  - GEMINI.md
  - scratch/baseline/summary.csv
  - scratch/dryrun_manifest.py
  - scratch/measure_auth_existing.py
  - scratch/probe_anomalies.py
  - scratch/chk_cw.py
  - scripts/build_local_election.py
  - scratch/probe_legacy_build.py
  - scratch/add_defect7.py
  - HANDOFF.md
  - data/sources.json
  - scripts/oracles.py
  - scratch/verify_crosswalk.py
  - scratch/verify_strip.py
  - scratch/verify_review.py
  - scratch/zip_names.json
  - scratch/chk1998t2.py
  - README.md
  - scratch/review_q2.md
  - scratch/measure_pop.py
  - data/processed/validation-report.json
  - scratch/gen_town_anom.py
  - scratch/probe7.py
  - scratch/baseline/candidates.csv
  - scratch/probe5.py
  - scratch/measure_ws2.py
  - scratch/review_question.md
  - data/processed/cec-county-code-crosswalk-1998-2002.csv
  - scratch/review_q3.md
  - scratch/inventory_legacy.json
tests:
  - scripts/test_build_local_election.py
  - scratch/mutation_test.py
-->

---
### Requirement: Comparability Flags
The output long datasets SHALL include new flag columns: `is_main_sequence` (boolean) and `admin_code_system` (string) to indicate the schema year of the administrative codes.

#### Scenario: Flagging non-main sequence records
- **WHEN** the record is a 1994 provincial councilor or a combo indigenous city councilor
- **THEN** the `is_main_sequence` flag SHALL be set to false

#### Scenario: Setting admin code system version
- **WHEN** processing files from a specific election year
- **THEN** the `admin_code_system` SHALL reflect the corresponding system version

<!-- @trace
source: include-1994-2006-terms
updated: 2026-08-20
code:
  - scratch/strip_experiment.py
  - scratch/verify_33.py
  - scratch/verify_auth.py
  - scratch/measure_2005_towns.py
  - scratch/measure_2005.py
  - scratch/review_q5.md
  - scratch/measure_trunc.py
  - scratch/verify_32.py
  - scratch/review_q7.md
  - scratch/baseline/votes.csv
  - CLAUDE.md
  - scratch/measure_town_feasible.py
  - scratch/measure_town_codes.py
  - data/processed/cec-local-election-votes-long.csv.gz
  - scratch/gen_anomalies.py
  - scratch/add_legacy_sources.py
  - scratch/probe3.py
  - AGENTS.md
  - scratch/measure_2005d.py
  - scratch/verify_pop2.py
  - scratch/measure_whitespace.py
  - scratch/review_q6.md
  - scratch/expected.txt
  - scratch/verify_claims.py
  - scratch/inventory_legacy.py
  - scratch/verify_pop.py
  - scratch/measure_2005e.py
  - scratch/list_zip.py
  - docs/schema/oracles.md
  - scratch/probe_1994.py
  - scratch/measure_pop2.py
  - scratch/review_q4.md
  - scratch/measure_2005b.py
  - .spectra.yaml
  - docs/schema/cec-local-election.md
  - data/processed/cec-local-election-candidates-long.csv
  - scratch/verify_identity.py
  - scratch/gen_expected.py
  - scratch/measure_2005c.py
  - data/processed/cec-local-election-summary-long.csv.gz
  - scratch/probe6.py
  - scratch/measure_2005g.py
  - scratch/probe4.py
  - scratch/measure_2005f.py
  - scratch/build_1998_2002_crosswalk.py
  - scratch/probe2.py
  - GEMINI.md
  - scratch/baseline/summary.csv
  - scratch/dryrun_manifest.py
  - scratch/measure_auth_existing.py
  - scratch/probe_anomalies.py
  - scratch/chk_cw.py
  - scripts/build_local_election.py
  - scratch/probe_legacy_build.py
  - scratch/add_defect7.py
  - HANDOFF.md
  - data/sources.json
  - scripts/oracles.py
  - scratch/verify_crosswalk.py
  - scratch/verify_strip.py
  - scratch/verify_review.py
  - scratch/zip_names.json
  - scratch/chk1998t2.py
  - README.md
  - scratch/review_q2.md
  - scratch/measure_pop.py
  - data/processed/validation-report.json
  - scratch/gen_town_anom.py
  - scratch/probe7.py
  - scratch/baseline/candidates.csv
  - scratch/probe5.py
  - scratch/measure_ws2.py
  - scratch/review_question.md
  - data/processed/cec-county-code-crosswalk-1998-2002.csv
  - scratch/review_q3.md
  - scratch/inventory_legacy.json
tests:
  - scripts/test_build_local_election.py
  - scratch/mutation_test.py
-->

---
### Requirement: Town-Level Comparability Is Declared Per File, Not Assumed From The Term
Whether a record can be joined to other files at township level is a property of the file, not of the year. The 1998, 2002, and 2005 indigenous county councilor files re-number their town codes per file and SHALL carry a resolved code in the normalized town column. The combined indigenous city councilor files and the 1994 provincial councilor files do not re-number theirs and SHALL carry their own code unchanged, because it is already the term's code.

Once this capability applies, the normalized town column SHALL hold a value for every row of every file; no row SHALL carry an empty normalized town code. A reader SHALL be able to join on that column without first consulting a table of which files were fixed when.

#### Scenario: Reading town-level comparability
- **WHEN** a consumer needs to join a record to another file at township level
- **THEN** the normalized town column SHALL be comparable across files of the same term regardless of which file the record came from, and SHALL NOT require the consumer to know whether that file re-numbered its codes

#### Scenario: Six files gain town-level joinability
- **WHEN** the 1998, 2002, and 2005 plain- and mountain-indigenous county councilor files are processed
- **THEN** all of their township-level units SHALL carry a resolved normalized town code, and none SHALL be left empty

#### Scenario: These files carry no sub-township rows
- **WHEN** township-level normalization is applied to these six files
- **THEN** it SHALL NOT be extended to village or polling-station codes, because those files contain no rows below township level and a normalization declared for a level with no data would be a check that can never fail

<!-- @trace
source: normalise-town-codes-1998-2005
updated: 2026-08-22
code:
  - scratch/baseline/candidates.csv
  - README.md
  - scratch/chk1998t2.py
  - scratch/review_question.md
  - scratch/measure_pop.py
  - scratch/baseline/votes.csv
  - scratch/gen_anomalies.py
  - scratch/expected.txt
  - scratch/baseline/summary.csv
  - scratch/probe_1994.py
  - scratch/verify_pop2.py
  - data/reference/cec-town-code-crosswalk-1998-2005.csv
  - scratch/review_q4.md
  - scratch/verify_32.py
  - scratch/add_defect7.py
  - scratch/measure_auth_existing.py
  - scratch/verify_33.py
  - docs/index.html
  - scratch/verify_crosswalk.py
  - scratch/measure_ws2.py
  - GEMINI.md
  - scratch/review_q3.md
  - scratch/measure_2005e.py
  - scratch/probe7.py
  - scratch/review_q7.md
  - scratch/dryrun_manifest.py
  - scratch/verify_pop.py
  - scratch/verify_11.py
  - scratch/verify_strip.py
  - scratch/measure_whitespace.py
  - scratch/probe6.py
  - scratch/verify_review.py
  - scratch/list_zip.py
  - scratch/verify_identity.py
  - .spectra.yaml
  - scratch/review_q6.md
  - scratch/measure_2005g.py
  - scratch/strip_experiment.py
  - scratch/probe4.py
  - scratch/inventory_legacy.py
  - docs/三屆概況.md
  - scratch/probe2.py
  - scripts/build_local_election.py
  - docs/schema/cec-local-election.md
  - AGENTS.md
  - scratch/measure_2005d.py
  - scratch/measure_pop2.py
  - scratch/verify_21.py
  - scratch/verify_21c.py
  - scratch/measure_2005c.py
  - scratch/verify_auth.py
  - scratch/measure_2005_towns.py
  - scratch/probe_anomalies.py
  - scratch/measure_trunc.py
  - scratch/verify_claims.py
  - data/processed/cec-local-election-votes-long.csv.gz
  - data/processed/validation-report.json
  - data/processed/cec-local-election-candidates-long.csv
  - scratch/chk_cw.py
  - scratch/review_q2.md
  - scratch/zip_names.json
  - scratch/build_1998_2002_crosswalk.py
  - scratch/gen_expected.py
  - scratch/inventory_legacy.json
  - scratch/measure_2005b.py
  - scratch/probe_districts2.py
  - scratch/probe5.py
  - scratch/gen_town_anom.py
  - scripts/build_town_crosswalk.py
  - scratch/review_q5.md
  - scratch/probe3.py
  - scratch/measure_town_feasible.py
  - CLAUDE.md
  - scratch/measure_2005f.py
  - scripts/mutate_build_local_election.py
  - data/processed/cec-local-election-summary-long.csv.gz
  - scratch/probe_legacy_build.py
  - HANDOFF.md
  - scratch/measure_town_codes.py
  - scratch/add_legacy_sources.py
  - scratch/measure_2005.py
  - scratch/probe_districts.py
tests:
  - scripts/test_build_local_election.py
-->