# legacy-source-quirks Specification

## Purpose

The source election files change shape across eras: keys carry trailing whitespace in
some years, county codes are renumbered, town codes are re-issued per file, population
figures appear as decimal strings, and the elected-status mark is corrupt in specific
files. This capability governs how those defects are handled.

The standing rule is that source values are preserved as they came, never overwritten.
Where a value is wrong or ambiguous, the response is a named exception plus a
compensating check that would fail if the defect changed shape — not a silent repair
and not a relaxed validation.

It covers: which columns may be whitespace-normalized and which must not; the county
code crosswalk and the levels at which normalization is and is not attempted; the
preservation of population strings and the levels where that column is meaningful;
how authoritative elected status is derived when the source mark cannot be trusted;
and the compensating checks that bound each of these.

## Requirements

### Requirement: Relational Key Field Trailing Whitespace Normalization
The system SHALL strip surrounding whitespace from **relational key fields** — the
administrative code columns, the candidate number (`號次`) column, and the party code
columns — across all legacy and current files when reading CSVs. The key fields SHALL be
declared per source file kind as an explicit whitelist.

The system SHALL NOT normalize non-key fields. Values the project preserves verbatim
(`得票率`, `人口數`, `投票率`) and the officially defined four-value elected mark domain
(where a single space `" "` means "not elected") SHALL be read exactly as the source
provides them.

#### Scenario: Parsing unquoted codes with trailing spaces
- **WHEN** the administrative code in the raw CSV is "0 "
- **THEN** the system SHALL parse and store it as "0"

#### Scenario: Joining candidate numbers across files with inconsistent padding
- **WHEN** the 2005 `elctks` candidate number is "1 " and the same candidate's `elcand`
  candidate number is "1"
- **THEN** the system SHALL normalize both to "1" so the cross-file reference resolves

#### Scenario: Preserving whitespace in non-key fields
- **WHEN** a vote-share field is "1.58 " or an elected mark field is " "
- **THEN** the reader SHALL leave the value unchanged, because those columns are either
  preserved verbatim by project discipline or carry meaning in the official value domain


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
### Requirement: County Code Crosswalk
The system SHALL map the internally re-numbered county codes in the 1998 and 2002 T2 and T3 files to the authoritative regional codes for that term using a version-controlled crosswalk CSV.

#### Scenario: Resolving 1998 and 2002 county codes
- **WHEN** processing 1998 or 2002 T2 or T3 files
- **THEN** the system SHALL look up the internal county code in the crosswalk table and use the corresponding regional code

#### Scenario: Mismatched county names
- **WHEN** a county name does not match the crosswalk table
- **THEN** the system SHALL abort the build

##### Example: the three-step resolution

| Case | `local_code` | In crosswalk? | Same-term regional file | Result |
| --- | --- | --- | --- | --- |
| Mapped | `01005` (嘉義縣) | yes → `01010` | `01010` is 嘉義縣 | `010` |
| Identity | `01001` (臺北縣) | no | `01001` is 臺北縣 | `001` |
| Unknown code | `01999` (火星縣) | no | absent | **abort** |
| Name mismatch | `01001` (桃園縣) | no | `01001` is 臺北縣 | **abort** |
| Three-way name mismatch | `01005` (嘉義市) | yes → `01010` | `01010` is 嘉義縣 | **abort** |

#### Scenario: Crosswalk row never used
- **WHEN** the crosswalk contains a row for a term and election type that was processed, but
  no source record resolved through it
- **THEN** the build SHALL abort. Usage SHALL be judged including `elbase`, because the 1998
  plain-indigenous 嘉義縣 code appears only in `elbase` and would otherwise be misjudged as
  a stale row


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
### Requirement: Normalization Depth Is Limited To County Level
The system SHALL output the source administrative codes unchanged and SHALL add separate
normalized columns. The county normalized column SHALL carry the same-term regional code.
The town normalized column SHALL be empty for files whose town codes are renumbered
file-locally, rather than carrying the un-normalized source code.

#### Scenario: Town codes are renumbered file-locally
- **WHEN** processing the 1998, 2002, or 2005 mountain- or plain-indigenous county councilor
  files, whose town codes are renumbered from `001` within each file
- **THEN** the town normalized column SHALL be empty, so that a downstream join on the
  normalized columns fails to match rather than matching the wrong district

#### Scenario: County codes became term-global before town codes did
- **WHEN** processing 2005 files
- **THEN** the county code SHALL need no crosswalk conversion, but the town normalized column
  SHALL still be empty — "term-global from 2005" holds at county level only

#### Scenario: Combined indigenous city councilor files
- **WHEN** processing the 1994, 1998, 2002, or 2006 combined indigenous city councilor files,
  whose county and town codes match the same-term city regional file exactly
- **THEN** both normalized columns SHALL carry the source codes


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
### Requirement: Population String Preservation and Level Restriction
The system SHALL preserve the population field as a string exactly as provided (including decimal points) and SHALL restrict its valid applicability to county-level and above.

#### Scenario: Processing population values with decimals
- **WHEN** the population field contains "206740.12"
- **THEN** the system SHALL output "206740.12" without casting it to an integer

#### Scenario: Processing invalid population values at town level
- **WHEN** a population value exists for a town-level or village-level record
- **THEN** the system SHALL flag the population value with an applicability level indicator

##### Example: applicability by administrative level

| Administrative level | `人口數適用層級` |
| --- | --- |
| 檔別合計 | 縣市以上 |
| 直轄市縣市 | 縣市以上 |
| 選舉區 | 低於縣市_不適用 |
| 鄉鎮市區 | 低於縣市_不適用 |
| 村里 | 低於縣市_不適用 |
| 投開票所 | 低於縣市_不適用 |

#### Scenario: Electoral-district level is below county level
- **WHEN** the record is at the 選舉區 (electoral district) level
- **THEN** the system SHALL flag it as not applicable, because the requirement restricts
  applicability to county level and above and no oracle establishes validity below it

#### Scenario: Applicability does not assert value validity
- **WHEN** a record at county level or above is flagged `縣市以上`
- **THEN** the flag SHALL be read as "the column is applicable at this level" and NOT as
  "this value has been verified" — county-level values include non-integer figures
  (e.g. "206740.121634792") that cannot be a headcount, and the column has no arithmetic
  oracle and no verified upstream source


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
### Requirement: Authoritative Elected Status Derivation
The system SHALL preserve the `elcand` elected status column and the `當選` field derived
from it exactly as the source provides them, including where the source is known to be
corrupt (the 2005 county councilor files), and SHALL derive a separate
`elected_authoritative` field from the `elctks` vote breakdown, together with an
`elected_authoritative_basis` field recording which administrative level the value came
from.

Matching a candidate to `elctks` rows SHALL constrain only those administrative code
columns that are non-blank on the candidate record, and SHALL take the marks from the
highest administrative level among the matching rows. The elected marks are `*` and `!`
(both appear in `elctks`).

The system SHALL abort rather than guess when a candidate has no matching `elctks` row,
or when the marks at the chosen level disagree.

#### Scenario: Deriving elected status from vote breakdown
- **WHEN** the candidate's mark at the highest matching `elctks` level is `*` or `!`
- **THEN** `elected_authoritative` SHALL be true

#### Scenario: Candidate record is less specific than the vote breakdown
- **WHEN** the candidate's town column is blank (`000`) and the only `elctks` rows for that
  candidate are at town level — as for the 2005 mountain-indigenous Pingtung 16th district,
  which has no district-level aggregate row
- **THEN** the blank column SHALL NOT constrain the match, the value SHALL be derived from
  the town-level rows, and `elected_authoritative_basis` SHALL record `elctks_鄉鎮市區`

#### Scenario: Candidate record is less specific but the town column distinguishes candidates
- **WHEN** the candidate's electoral-district column is blank (`00`), as for indigenous
  district chief (D2) and district representative (R3) elections whose real unit is the town
- **THEN** the town column SHALL still constrain the match, so that candidates sharing a
  number in different towns are not merged

#### Scenario: Lower levels carry no mark information
- **WHEN** a candidate has rows at both district and town level, and the town-level marks
  are blank as in the 2002 plain-indigenous file
- **THEN** the district-level mark SHALL be used, because it is the highest matching level

#### Scenario: No elctks row for a candidate
- **WHEN** a candidate has no matching `elctks` row at any level
- **THEN** the build SHALL abort. The system SHALL NOT fall back to inferring election from
  `elprof` candidate/elected counts: no candidate in any covered file lacks an `elctks` row,
  and such a fallback would silently mark a whole district elected if `elctks` rows were
  lost, while still satisfying the per-district compensating check

#### Scenario: Conflicting marks at the chosen level
- **WHEN** the marks at the highest matching level disagree
- **THEN** the build SHALL abort rather than take a majority or treat any asterisk as elected


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
### Requirement: Elected Status Compensating Checks
The system SHALL validate `elected_authoritative` independently of the existing `elcand`
checks, so that adding the derived field does not remove the ability to detect `elcand`
corruption.

#### Scenario: Existing elcand checks stay unchanged
- **WHEN** the build validates `elprof` elected counts against `elcand`
- **THEN** that check SHALL continue to use the `elcand`-derived `當選` field

#### Scenario: Authoritative totals must reconcile
- **WHEN** the build validates `elected_authoritative`
- **THEN** the count SHALL equal the `elprof` elected count for the file, and for every
  electoral district present at district level in `elprof`

#### Scenario: Disagreement with elcand must be named per candidate
- **WHEN** `elected_authoritative` disagrees with the `elcand`-derived `當選`
- **THEN** the build SHALL abort unless that candidate is listed individually in the known
  anomaly set, and SHALL also abort if the set of disagreeing candidates is not exactly the
  listed set — naming a whole file SHALL NOT be accepted

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
### Requirement: Cross-Term Party Encoding Drift Is Named, Not Inferred
Where the source encodes the same party or party status under different codes or different names in
different terms, the project SHALL record the correspondence as an explicit named entry rather than
inferring it from string similarity, substring matching, or a shared code.

The measured drift in this dataset is: independents are code `99` name 「無」 in 1994 through 2006 and
code `999` name 「無黨籍及未經政黨推薦」 from 2009 onward; 民主進步黨 is code `2` before 2009 and code
`16` from 2009 while keeping one name; 新黨, 親民黨, 台灣團結聯盟, 無黨團結聯盟 and 勞動黨 each carry two
codes across eras; and codes `166`, `199`, `254`, `290` and `303` each carry two different names.

#### Scenario: Correspondence asserted without an explicit entry
- **WHEN** a rule would merge two source party identities on the basis of similar names or a shared
  code, without a named entry recording that they are the same entity
- **THEN** the project SHALL NOT merge them

#### Scenario: Substring matching on the independent category
- **WHEN** a rule matches independents by testing whether the party name contains 「無」 or starts with
  「無黨」
- **THEN** that rule is incorrect, because 無黨團結聯盟 is a distinct registered party that such a rule
  would absorb


<!-- @trace
source: fix-party-bucket-drift
updated: 2026-08-20
code:
  - README.md
  - scratch/verify_claims.py
  - scratch/review_q3.md
  - scratch/measure_2005.py
  - scratch/measure_2005_towns.py
  - scratch/verify_pop.py
  - scratch/measure_whitespace.py
  - scratch/review_q7.md
  - scratch/verify_pop2.py
  - scratch/strip_experiment.py
  - scratch/measure_ws2.py
  - scratch/verify_32.py
  - scratch/measure_town_codes.py
  - scratch/baseline/votes.csv
  - scratch/measure_pop2.py
  - scratch/probe_1994.py
  - scratch/zip_names.json
  - scratch/verify_identity.py
  - scratch/review_q4.md
  - GEMINI.md
  - scratch/probe_districts.py
  - scripts/mutate_build_site_data.py
  - scratch/list_zip.py
  - docs/index.html
  - .spectra.yaml
  - scratch/measure_auth_existing.py
  - scratch/gen_anomalies.py
  - scratch/gen_town_anom.py
  - scratch/verify_review.py
  - scripts/build_site_data.py
  - scratch/probe_anomalies.py
  - scratch/chk1998t2.py
  - scratch/verify_33.py
  - scratch/verify_21c.py
  - scratch/chk_cw.py
  - scratch/inventory_legacy.json
  - scratch/measure_2005b.py
  - scratch/probe7.py
  - scratch/probe_legacy_build.py
  - docs/roster.html
  - scratch/measure_2005g.py
  - scratch/review_q2.md
  - scratch/verify_crosswalk.py
  - scratch/review_q5.md
  - scratch/probe5.py
  - scratch/measure_trunc.py
  - scratch/probe_districts2.py
  - scratch/add_defect7.py
  - scratch/baseline/summary.csv
  - scratch/add_legacy_sources.py
  - scratch/probe6.py
  - scratch/gen_expected.py
  - scratch/probe4.py
  - scratch/verify_auth.py
  - scratch/verify_strip.py
  - CLAUDE.md
  - scratch/measure_2005e.py
  - scratch/review_q6.md
  - scratch/build_1998_2002_crosswalk.py
  - scratch/review_question.md
  - scratch/probe2.py
  - scratch/verify_21.py
  - scratch/baseline/candidates.csv
  - scratch/measure_2005c.py
  - AGENTS.md
  - scratch/measure_town_feasible.py
  - scratch/probe3.py
  - scratch/verify_11.py
  - scripts/palette_metrics.py
  - scratch/measure_2005d.py
  - scratch/measure_2005f.py
  - scratch/inventory_legacy.py
  - scratch/measure_pop.py
  - scratch/expected.txt
  - scratch/dryrun_manifest.py
tests:
  - scripts/test_build_site_data.py
  - scripts/test_site_invariants.py
-->

---
### Requirement: A Silently Zeroed Series Is Treated As A Defect
Where a category is present in the source for a term but reaches the published output with a count of
zero, that SHALL be treated as a defect in the classification, not as a fact about the term.

#### Scenario: Independents present in source but absent from output
- **WHEN** the source for a term contains rows whose party identity denotes independents, and the
  published output reports zero independents for that term
- **THEN** this SHALL be recorded as a classification defect and corrected, rather than published as
  a finding that no independents contested that term

<!-- @trace
source: fix-party-bucket-drift
updated: 2026-08-20
code:
  - README.md
  - scratch/verify_claims.py
  - scratch/review_q3.md
  - scratch/measure_2005.py
  - scratch/measure_2005_towns.py
  - scratch/verify_pop.py
  - scratch/measure_whitespace.py
  - scratch/review_q7.md
  - scratch/verify_pop2.py
  - scratch/strip_experiment.py
  - scratch/measure_ws2.py
  - scratch/verify_32.py
  - scratch/measure_town_codes.py
  - scratch/baseline/votes.csv
  - scratch/measure_pop2.py
  - scratch/probe_1994.py
  - scratch/zip_names.json
  - scratch/verify_identity.py
  - scratch/review_q4.md
  - GEMINI.md
  - scratch/probe_districts.py
  - scripts/mutate_build_site_data.py
  - scratch/list_zip.py
  - docs/index.html
  - .spectra.yaml
  - scratch/measure_auth_existing.py
  - scratch/gen_anomalies.py
  - scratch/gen_town_anom.py
  - scratch/verify_review.py
  - scripts/build_site_data.py
  - scratch/probe_anomalies.py
  - scratch/chk1998t2.py
  - scratch/verify_33.py
  - scratch/verify_21c.py
  - scratch/chk_cw.py
  - scratch/inventory_legacy.json
  - scratch/measure_2005b.py
  - scratch/probe7.py
  - scratch/probe_legacy_build.py
  - docs/roster.html
  - scratch/measure_2005g.py
  - scratch/review_q2.md
  - scratch/verify_crosswalk.py
  - scratch/review_q5.md
  - scratch/probe5.py
  - scratch/measure_trunc.py
  - scratch/probe_districts2.py
  - scratch/add_defect7.py
  - scratch/baseline/summary.csv
  - scratch/add_legacy_sources.py
  - scratch/probe6.py
  - scratch/gen_expected.py
  - scratch/probe4.py
  - scratch/verify_auth.py
  - scratch/verify_strip.py
  - CLAUDE.md
  - scratch/measure_2005e.py
  - scratch/review_q6.md
  - scratch/build_1998_2002_crosswalk.py
  - scratch/review_question.md
  - scratch/probe2.py
  - scratch/verify_21.py
  - scratch/baseline/candidates.csv
  - scratch/measure_2005c.py
  - AGENTS.md
  - scratch/measure_town_feasible.py
  - scratch/probe3.py
  - scratch/verify_11.py
  - scripts/palette_metrics.py
  - scratch/measure_2005d.py
  - scratch/measure_2005f.py
  - scratch/inventory_legacy.py
  - scratch/measure_pop.py
  - scratch/expected.txt
  - scratch/dryrun_manifest.py
tests:
  - scripts/test_build_site_data.py
  - scripts/test_site_invariants.py
-->

---
### Requirement: Sentinel Values Are Not Presented As Measurements
Where a source column carries a fixed value that stands for "not recorded" rather than a measurement,
the published output SHALL NOT present that value as if it were the measurement.

The substitution SHALL happen in the long table, at the point where the cleaned column is produced,
and the source's own value SHALL be preserved under an explicitly-marked name. It SHALL NOT be
deferred to the presentation layer alone: a consumer reading the long table directly never reaches
that layer, and gets the sentinel counted as a measurement with no error raised.

The measured instance is the candidate age column: it holds `99` for every one of the 483 candidates
in the 1994, 1998, 2002, 2005 and 2006 terms, and never holds `99` in the 2009-2010, 2014, 2018 or
2022 terms, whose ages range from 23 to 89.

#### Scenario: A term whose age column is uniformly the sentinel
- **WHEN** any consumer reads the cleaned column for a term in which every source value is the
  sentinel
- **THEN** the field SHALL be empty rather than carrying the sentinel, so that no claim is made about
  that person's age

#### Scenario: A term that records real ages
- **WHEN** a consumer reads the cleaned column for a term whose source values are real ages
- **THEN** the value SHALL be the source's value unchanged

#### Scenario: A consumer who needs the sentinel itself
- **WHEN** a consumer reads the explicitly-marked source column
- **THEN** the sentinel SHALL still be there, because preserving what the source wrote is what that
  column is for


<!-- @trace
source: candidate-age-valid-column
updated: 2026-08-21
code:
  - scratch/probe5.py
  - scratch/verify_crosswalk.py
  - scratch/probe4.py
  - GEMINI.md
  - scratch/inventory_legacy.json
  - scratch/measure_2005c.py
  - scratch/verify_33.py
  - scratch/verify_pop.py
  - scratch/measure_2005_towns.py
  - scratch/verify_review.py
  - scratch/list_zip.py
  - scratch/measure_2005.py
  - scratch/baseline/summary.csv
  - scratch/gen_expected.py
  - scratch/zip_names.json
  - scratch/measure_2005f.py
  - scratch/verify_claims.py
  - scratch/add_legacy_sources.py
  - .spectra.yaml
  - scratch/measure_2005e.py
  - scratch/review_q7.md
  - scratch/verify_21c.py
  - scratch/probe_districts2.py
  - scratch/verify_auth.py
  - scratch/measure_town_codes.py
  - scratch/review_q5.md
  - scratch/review_question.md
  - scratch/measure_2005d.py
  - AGENTS.md
  - scratch/gen_anomalies.py
  - scratch/measure_pop.py
  - scratch/strip_experiment.py
  - scratch/probe6.py
  - scratch/review_q4.md
  - scratch/add_defect7.py
  - scratch/measure_auth_existing.py
  - scratch/measure_2005b.py
  - scratch/measure_town_feasible.py
  - scratch/verify_identity.py
  - scratch/verify_32.py
  - scratch/baseline/votes.csv
  - scratch/verify_21.py
  - scratch/chk_cw.py
  - scratch/verify_11.py
  - scratch/review_q3.md
  - scratch/expected.txt
  - scratch/review_q2.md
  - scratch/verify_strip.py
  - scratch/gen_town_anom.py
  - CLAUDE.md
  - scratch/probe_legacy_build.py
  - scratch/measure_2005g.py
  - scratch/measure_whitespace.py
  - scratch/probe_anomalies.py
  - scratch/dryrun_manifest.py
  - scratch/chk1998t2.py
  - scratch/probe3.py
  - scratch/inventory_legacy.py
  - scratch/probe2.py
  - scratch/build_1998_2002_crosswalk.py
  - scratch/probe_districts.py
  - scratch/review_q6.md
  - scratch/baseline/candidates.csv
  - scratch/probe_1994.py
  - scratch/probe7.py
  - scratch/measure_pop2.py
  - scratch/verify_pop2.py
  - scratch/measure_ws2.py
  - scratch/measure_trunc.py
-->

---
### Requirement: Sentinel Recognition Is Named Per Term, Not Global
The set of terms in which a value is treated as a sentinel SHALL be an explicit named list. A value
SHALL NOT be treated as a sentinel merely because it once served that purpose, because the same
number can be a genuine measurement in another term.

Two checks SHALL bound the list, and both SHALL abort the build rather than adjust behaviour silently:
the listed terms SHALL contain no value other than the sentinel, and the unlisted terms SHALL contain
no occurrence of the sentinel.

#### Scenario: A listed term turns out to hold a real value
- **WHEN** a term on the list carries any age other than the sentinel
- **THEN** the build SHALL abort naming that term and the value, because the premise for listing it
  no longer holds and a real age would otherwise be discarded

#### Scenario: An unlisted term starts carrying the sentinel
- **WHEN** a term not on the list carries the sentinel value
- **THEN** the build SHALL abort naming that term, because either the sentinel convention has spread
  to a new term or a genuine value coincides with it, and the two cannot be told apart automatically


<!-- @trace
source: age-99-is-unrecorded
updated: 2026-08-21
code:
  - scratch/inventory_legacy.py
  - scratch/build_1998_2002_crosswalk.py
  - scratch/measure_2005_towns.py
  - scratch/verify_21c.py
  - scratch/probe3.py
  - scratch/verify_33.py
  - scratch/probe7.py
  - scratch/measure_auth_existing.py
  - scratch/measure_town_feasible.py
  - CLAUDE.md
  - scratch/baseline/summary.csv
  - scratch/strip_experiment.py
  - scratch/gen_anomalies.py
  - scratch/verify_strip.py
  - scratch/probe2.py
  - scratch/review_q2.md
  - scratch/measure_ws2.py
  - scratch/probe_districts2.py
  - scratch/zip_names.json
  - scratch/probe5.py
  - scratch/measure_whitespace.py
  - scratch/baseline/candidates.csv
  - scratch/dryrun_manifest.py
  - scratch/review_q7.md
  - scratch/review_question.md
  - scratch/inventory_legacy.json
  - scratch/chk1998t2.py
  - scratch/measure_trunc.py
  - scratch/verify_pop2.py
  - scratch/probe_1994.py
  - scratch/probe6.py
  - scratch/add_legacy_sources.py
  - scratch/baseline/votes.csv
  - scratch/verify_review.py
  - scratch/measure_2005g.py
  - scratch/review_q4.md
  - scratch/verify_identity.py
  - scratch/chk_cw.py
  - scratch/measure_2005f.py
  - scratch/verify_32.py
  - scratch/measure_pop.py
  - scratch/expected.txt
  - scratch/review_q3.md
  - scratch/verify_crosswalk.py
  - scratch/measure_2005.py
  - scratch/verify_21.py
  - AGENTS.md
  - scratch/probe_districts.py
  - scratch/measure_town_codes.py
  - scratch/measure_2005c.py
  - scratch/probe_legacy_build.py
  - .spectra.yaml
  - scratch/review_q6.md
  - scratch/verify_pop.py
  - scratch/verify_claims.py
  - scratch/measure_2005d.py
  - scratch/probe4.py
  - scratch/probe_anomalies.py
  - scratch/gen_town_anom.py
  - scratch/list_zip.py
  - scratch/verify_11.py
  - scratch/review_q5.md
  - scratch/measure_2005e.py
  - scratch/measure_2005b.py
  - scratch/add_defect7.py
  - GEMINI.md
  - scratch/gen_expected.py
  - scratch/verify_auth.py
  - scratch/measure_pop2.py
-->

---
### Requirement: Column Semantics Are Taken From The Source Format Document First
The authority for what a source column means is the format document shipped inside the source
archive. Before describing a column's semantics — and before claiming that no such description
exists — that document SHALL be consulted.

Where the format document does define the value, the project's documentation SHALL cite it. Only
where the document has been consulted and found silent may the meaning be described as inferred from
the data, and the documentation SHALL then say which measurement supports the inference.

For the age column the document is explicit: `年齡 Num(3) (部分選舉未必有資料，可能 0 或 99)`.

#### Scenario: A column whose meaning the format document defines
- **WHEN** the project documents what a value in that column means
- **THEN** it SHALL cite the format document, and SHALL NOT describe the meaning as inferred from
  the data distribution

#### Scenario: Two documented no-data values with different ambiguity
- **WHEN** the format document lists more than one no-data value for a column
- **THEN** each SHALL be handled according to whether it could also be a genuine measurement: a
  value outside the plausible range needs no per-term naming, while a value inside it does, because
  only the latter risks discarding a real measurement

<!-- @trace
source: age-99-is-unrecorded
updated: 2026-08-21
code:
  - scratch/inventory_legacy.py
  - scratch/build_1998_2002_crosswalk.py
  - scratch/measure_2005_towns.py
  - scratch/verify_21c.py
  - scratch/probe3.py
  - scratch/verify_33.py
  - scratch/probe7.py
  - scratch/measure_auth_existing.py
  - scratch/measure_town_feasible.py
  - CLAUDE.md
  - scratch/baseline/summary.csv
  - scratch/strip_experiment.py
  - scratch/gen_anomalies.py
  - scratch/verify_strip.py
  - scratch/probe2.py
  - scratch/review_q2.md
  - scratch/measure_ws2.py
  - scratch/probe_districts2.py
  - scratch/zip_names.json
  - scratch/probe5.py
  - scratch/measure_whitespace.py
  - scratch/baseline/candidates.csv
  - scratch/dryrun_manifest.py
  - scratch/review_q7.md
  - scratch/review_question.md
  - scratch/inventory_legacy.json
  - scratch/chk1998t2.py
  - scratch/measure_trunc.py
  - scratch/verify_pop2.py
  - scratch/probe_1994.py
  - scratch/probe6.py
  - scratch/add_legacy_sources.py
  - scratch/baseline/votes.csv
  - scratch/verify_review.py
  - scratch/measure_2005g.py
  - scratch/review_q4.md
  - scratch/verify_identity.py
  - scratch/chk_cw.py
  - scratch/measure_2005f.py
  - scratch/verify_32.py
  - scratch/measure_pop.py
  - scratch/expected.txt
  - scratch/review_q3.md
  - scratch/verify_crosswalk.py
  - scratch/measure_2005.py
  - scratch/verify_21.py
  - AGENTS.md
  - scratch/probe_districts.py
  - scratch/measure_town_codes.py
  - scratch/measure_2005c.py
  - scratch/probe_legacy_build.py
  - .spectra.yaml
  - scratch/review_q6.md
  - scratch/verify_pop.py
  - scratch/verify_claims.py
  - scratch/measure_2005d.py
  - scratch/probe4.py
  - scratch/probe_anomalies.py
  - scratch/gen_town_anom.py
  - scratch/list_zip.py
  - scratch/verify_11.py
  - scratch/review_q5.md
  - scratch/measure_2005e.py
  - scratch/measure_2005b.py
  - scratch/add_defect7.py
  - GEMINI.md
  - scratch/gen_expected.py
  - scratch/verify_auth.py
  - scratch/measure_pop2.py
-->

---
### Requirement: The Plainest Column Name Holds The Safest Data
Where a source column mixes a "not recorded" sentinel with real measurements, the plainest column
name SHALL hold the cleaned values — the value where one was recorded, empty where none was — and
the source's own value SHALL be preserved under an explicitly-marked name.

Adding a separate clean column beside the raw one is not sufficient. It opens a safe route without
closing the trap: the plainest name carries the strongest default pull, so a consumer who has not
read the documentation aggregates it and gets a wrong answer with no error. For the candidate age
column the nine-term mean moves from 50.80 over 7,335 recorded ages to 53.78 over 7,818 rows once
the 483 sentinels are counted as ages.

#### Scenario: A consumer who has not read the documentation
- **WHEN** a consumer aggregates the plainest-named column without consulting any documentation
- **THEN** the answer SHALL be correct, because rows with no recorded value are empty rather than
  carrying a stand-in number

#### Scenario: A consumer who needs exactly what the source wrote
- **WHEN** a consumer reads the explicitly-marked source column
- **THEN** it SHALL contain exactly what the source recorded, sentinel included, one row for one row

#### Scenario: Renaming changes what a published column means
- **WHEN** this exchange is made to a column that has already been published
- **THEN** the project SHALL record that the same column name now means something different from
  earlier revisions, because no error will be raised for a consumer who re-reads it


<!-- @trace
source: candidate-age-valid-column
updated: 2026-08-21
code:
  - scratch/probe5.py
  - scratch/verify_crosswalk.py
  - scratch/probe4.py
  - GEMINI.md
  - scratch/inventory_legacy.json
  - scratch/measure_2005c.py
  - scratch/verify_33.py
  - scratch/verify_pop.py
  - scratch/measure_2005_towns.py
  - scratch/verify_review.py
  - scratch/list_zip.py
  - scratch/measure_2005.py
  - scratch/baseline/summary.csv
  - scratch/gen_expected.py
  - scratch/zip_names.json
  - scratch/measure_2005f.py
  - scratch/verify_claims.py
  - scratch/add_legacy_sources.py
  - .spectra.yaml
  - scratch/measure_2005e.py
  - scratch/review_q7.md
  - scratch/verify_21c.py
  - scratch/probe_districts2.py
  - scratch/verify_auth.py
  - scratch/measure_town_codes.py
  - scratch/review_q5.md
  - scratch/review_question.md
  - scratch/measure_2005d.py
  - AGENTS.md
  - scratch/gen_anomalies.py
  - scratch/measure_pop.py
  - scratch/strip_experiment.py
  - scratch/probe6.py
  - scratch/review_q4.md
  - scratch/add_defect7.py
  - scratch/measure_auth_existing.py
  - scratch/measure_2005b.py
  - scratch/measure_town_feasible.py
  - scratch/verify_identity.py
  - scratch/verify_32.py
  - scratch/baseline/votes.csv
  - scratch/verify_21.py
  - scratch/chk_cw.py
  - scratch/verify_11.py
  - scratch/review_q3.md
  - scratch/expected.txt
  - scratch/review_q2.md
  - scratch/verify_strip.py
  - scratch/gen_town_anom.py
  - CLAUDE.md
  - scratch/probe_legacy_build.py
  - scratch/measure_2005g.py
  - scratch/measure_whitespace.py
  - scratch/probe_anomalies.py
  - scratch/dryrun_manifest.py
  - scratch/chk1998t2.py
  - scratch/probe3.py
  - scratch/inventory_legacy.py
  - scratch/probe2.py
  - scratch/build_1998_2002_crosswalk.py
  - scratch/probe_districts.py
  - scratch/review_q6.md
  - scratch/baseline/candidates.csv
  - scratch/probe_1994.py
  - scratch/probe7.py
  - scratch/measure_pop2.py
  - scratch/verify_pop2.py
  - scratch/measure_ws2.py
  - scratch/measure_trunc.py
-->

---
### Requirement: A Cleaned Column Holds Values, Not A Validity Flag
A column that exists to make sentinel-bearing data safe SHALL carry the usable value itself, not a
boolean saying whether the source value is usable.

A boolean requires the consumer to know the flag exists before it protects them, which leaves the
original failure mode intact for anyone who does not. A column that holds the value is self-directing:
its name tells the consumer which column to use.

#### Scenario: A consumer unaware of the derived column's existence
- **WHEN** a consumer aggregates the original column without knowing about the derived one
- **THEN** the project SHALL NOT treat that as protected, because no flag was consulted


<!-- @trace
source: candidate-age-valid-column
updated: 2026-08-21
code:
  - scratch/probe5.py
  - scratch/verify_crosswalk.py
  - scratch/probe4.py
  - GEMINI.md
  - scratch/inventory_legacy.json
  - scratch/measure_2005c.py
  - scratch/verify_33.py
  - scratch/verify_pop.py
  - scratch/measure_2005_towns.py
  - scratch/verify_review.py
  - scratch/list_zip.py
  - scratch/measure_2005.py
  - scratch/baseline/summary.csv
  - scratch/gen_expected.py
  - scratch/zip_names.json
  - scratch/measure_2005f.py
  - scratch/verify_claims.py
  - scratch/add_legacy_sources.py
  - .spectra.yaml
  - scratch/measure_2005e.py
  - scratch/review_q7.md
  - scratch/verify_21c.py
  - scratch/probe_districts2.py
  - scratch/verify_auth.py
  - scratch/measure_town_codes.py
  - scratch/review_q5.md
  - scratch/review_question.md
  - scratch/measure_2005d.py
  - AGENTS.md
  - scratch/gen_anomalies.py
  - scratch/measure_pop.py
  - scratch/strip_experiment.py
  - scratch/probe6.py
  - scratch/review_q4.md
  - scratch/add_defect7.py
  - scratch/measure_auth_existing.py
  - scratch/measure_2005b.py
  - scratch/measure_town_feasible.py
  - scratch/verify_identity.py
  - scratch/verify_32.py
  - scratch/baseline/votes.csv
  - scratch/verify_21.py
  - scratch/chk_cw.py
  - scratch/verify_11.py
  - scratch/review_q3.md
  - scratch/expected.txt
  - scratch/review_q2.md
  - scratch/verify_strip.py
  - scratch/gen_town_anom.py
  - CLAUDE.md
  - scratch/probe_legacy_build.py
  - scratch/measure_2005g.py
  - scratch/measure_whitespace.py
  - scratch/probe_anomalies.py
  - scratch/dryrun_manifest.py
  - scratch/chk1998t2.py
  - scratch/probe3.py
  - scratch/inventory_legacy.py
  - scratch/probe2.py
  - scratch/build_1998_2002_crosswalk.py
  - scratch/probe_districts.py
  - scratch/review_q6.md
  - scratch/baseline/candidates.csv
  - scratch/probe_1994.py
  - scratch/probe7.py
  - scratch/measure_pop2.py
  - scratch/verify_pop2.py
  - scratch/measure_ws2.py
  - scratch/measure_trunc.py
-->

---
### Requirement: One Implementation Of A Sentinel Rule
Where a sentinel rule decides what is presented, it SHALL be implemented once, at the point where the
cleaned column is produced. Consumers of the long tables — including this project's own site
generator — SHALL read the cleaned column rather than re-deriving the rule from the source column.

The checks that guard the rule's premises move with the rule; they are not dropped when the
re-derivation is removed.

#### Scenario: A second implementation of the same rule
- **WHEN** a consumer re-implements the sentinel rule instead of reading the derived column
- **THEN** that is a defect, because the two implementations will diverge and only one of them will
  be exercised by any given test

<!-- @trace
source: candidate-age-valid-column
updated: 2026-08-21
code:
  - scratch/probe5.py
  - scratch/verify_crosswalk.py
  - scratch/probe4.py
  - GEMINI.md
  - scratch/inventory_legacy.json
  - scratch/measure_2005c.py
  - scratch/verify_33.py
  - scratch/verify_pop.py
  - scratch/measure_2005_towns.py
  - scratch/verify_review.py
  - scratch/list_zip.py
  - scratch/measure_2005.py
  - scratch/baseline/summary.csv
  - scratch/gen_expected.py
  - scratch/zip_names.json
  - scratch/measure_2005f.py
  - scratch/verify_claims.py
  - scratch/add_legacy_sources.py
  - .spectra.yaml
  - scratch/measure_2005e.py
  - scratch/review_q7.md
  - scratch/verify_21c.py
  - scratch/probe_districts2.py
  - scratch/verify_auth.py
  - scratch/measure_town_codes.py
  - scratch/review_q5.md
  - scratch/review_question.md
  - scratch/measure_2005d.py
  - AGENTS.md
  - scratch/gen_anomalies.py
  - scratch/measure_pop.py
  - scratch/strip_experiment.py
  - scratch/probe6.py
  - scratch/review_q4.md
  - scratch/add_defect7.py
  - scratch/measure_auth_existing.py
  - scratch/measure_2005b.py
  - scratch/measure_town_feasible.py
  - scratch/verify_identity.py
  - scratch/verify_32.py
  - scratch/baseline/votes.csv
  - scratch/verify_21.py
  - scratch/chk_cw.py
  - scratch/verify_11.py
  - scratch/review_q3.md
  - scratch/expected.txt
  - scratch/review_q2.md
  - scratch/verify_strip.py
  - scratch/gen_town_anom.py
  - CLAUDE.md
  - scratch/probe_legacy_build.py
  - scratch/measure_2005g.py
  - scratch/measure_whitespace.py
  - scratch/probe_anomalies.py
  - scratch/dryrun_manifest.py
  - scratch/chk1998t2.py
  - scratch/probe3.py
  - scratch/inventory_legacy.py
  - scratch/probe2.py
  - scratch/build_1998_2002_crosswalk.py
  - scratch/probe_districts.py
  - scratch/review_q6.md
  - scratch/baseline/candidates.csv
  - scratch/probe_1994.py
  - scratch/probe7.py
  - scratch/measure_pop2.py
  - scratch/verify_pop2.py
  - scratch/measure_ws2.py
  - scratch/measure_trunc.py
-->