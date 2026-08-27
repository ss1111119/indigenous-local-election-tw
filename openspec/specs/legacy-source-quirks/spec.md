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
  - CLAUDE.md
  - data/processed/cec-local-election-votes-long.csv.gz
  - AGENTS.md
  - docs/schema/oracles.md
  - .spectra.yaml
  - docs/schema/cec-local-election.md
  - data/processed/cec-local-election-candidates-long.csv
  - data/processed/cec-local-election-summary-long.csv.gz
  - GEMINI.md
  - scripts/build_local_election.py
  - HANDOFF.md
  - data/sources.json
  - scripts/oracles.py
  - README.md
  - data/processed/validation-report.json
  - data/reference/cec-county-code-crosswalk-1998-2002.csv
tests:
  - scripts/test_build_local_election.py
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
  - CLAUDE.md
  - data/processed/cec-local-election-votes-long.csv.gz
  - AGENTS.md
  - docs/schema/oracles.md
  - .spectra.yaml
  - docs/schema/cec-local-election.md
  - data/processed/cec-local-election-candidates-long.csv
  - data/processed/cec-local-election-summary-long.csv.gz
  - GEMINI.md
  - scripts/build_local_election.py
  - HANDOFF.md
  - data/sources.json
  - scripts/oracles.py
  - README.md
  - data/processed/validation-report.json
  - data/reference/cec-county-code-crosswalk-1998-2002.csv
tests:
  - scripts/test_build_local_election.py
-->

---
### Requirement: Normalization Depth Reaches Township, Not Below
The system SHALL output the source administrative codes unchanged and SHALL add separate
normalized columns. The county normalized column SHALL carry the same-term regional code.
The town normalized column SHALL also carry the same-term regional code, resolved through
the town crosswalk for files whose town codes are renumbered file-locally. Normalization
now reaches township level; it SHALL NOT reach village or polling-station level, because
the files that renumber their town codes contain no rows below township.

The town normalized column SHALL NOT be empty for any file. Leaving it empty would make
one representation carry two meanings — "this file needs no normalization" and "this row
could not be resolved" — and a downstream reader cannot tell those apart.

#### Scenario: Town codes are renumbered file-locally
- **WHEN** processing the 1998, 2002, or 2005 mountain- or plain-indigenous county councilor
  files, whose town codes are renumbered from `001` within each file
- **THEN** the town normalized column SHALL carry the same-term regional file's town code,
  and the source town column SHALL retain the file's own code unchanged

#### Scenario: County codes became term-global before town codes did
- **WHEN** processing 2005 files
- **THEN** the county code SHALL need no crosswalk conversion, but the town code SHALL still
  require it — "term-global from 2005" holds at county level only

#### Scenario: Combined indigenous city councilor files
- **WHEN** processing the 1994, 1998, 2002, or 2006 combined indigenous city councilor files,
  whose county and town codes match the same-term city regional file exactly
- **THEN** both normalized columns SHALL carry the source codes

#### Scenario: Rows above township level
- **WHEN** a row aggregates above township level, so its source town code is all zeros
- **THEN** the town normalized column SHALL carry that same all-zero code, matching what
  every other file emits for such rows, rather than being left empty

#### Scenario: Normalization is not extended below township
- **WHEN** considering village or polling-station level normalization for these files
- **THEN** it SHALL NOT be added, because those files contain no rows at those levels and a
  normalization declared for a level with no data is a rule that can never be exercised

<!-- @trace
source: include-1994-2006-terms
updated: 2026-08-20
code:
  - CLAUDE.md
  - data/processed/cec-local-election-votes-long.csv.gz
  - AGENTS.md
  - docs/schema/oracles.md
  - .spectra.yaml
  - docs/schema/cec-local-election.md
  - data/processed/cec-local-election-candidates-long.csv
  - data/processed/cec-local-election-summary-long.csv.gz
  - GEMINI.md
  - scripts/build_local_election.py
  - HANDOFF.md
  - data/sources.json
  - scripts/oracles.py
  - README.md
  - data/processed/validation-report.json
  - data/reference/cec-county-code-crosswalk-1998-2002.csv
tests:
  - scripts/test_build_local_election.py
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
  - CLAUDE.md
  - data/processed/cec-local-election-votes-long.csv.gz
  - AGENTS.md
  - docs/schema/oracles.md
  - .spectra.yaml
  - docs/schema/cec-local-election.md
  - data/processed/cec-local-election-candidates-long.csv
  - data/processed/cec-local-election-summary-long.csv.gz
  - GEMINI.md
  - scripts/build_local_election.py
  - HANDOFF.md
  - data/sources.json
  - scripts/oracles.py
  - README.md
  - data/processed/validation-report.json
  - data/reference/cec-county-code-crosswalk-1998-2002.csv
tests:
  - scripts/test_build_local_election.py
-->

---
### Requirement: Authoritative Elected Status Derivation
Where the source's own elected mark is known to be corrupt, the project SHALL derive elected status by
cross-file reconciliation and SHALL publish that derived status under the plainest column name, so
that a consumer who aggregates seats without reading any documentation gets the correct count.

The source's own claim SHALL remain available: the raw mark and its decoding stay in the long table
unchanged. The project SHALL NOT publish a second column holding the same derived status under a
longer name, because two columns carrying one fact will drift.

The basis of the derivation — which level of the votes file it was taken from — SHALL be published
alongside, because the levels differ in strength.

#### Scenario: Counting seats without reading documentation
- **WHEN** a consumer counts elected candidates from the plainest-named elected column
- **THEN** the count SHALL be the cross-file derived one, not the source's corrupt claim

#### Scenario: Recovering what the source claimed
- **WHEN** a consumer needs the source's own claim
- **THEN** the raw mark and its decoded meaning SHALL still be present, unchanged, one row for one row


<!-- @trace
source: elected-column-swap
updated: 2026-08-21
code:
  - .spectra.yaml
  - AGENTS.md
  - GEMINI.md
  - CLAUDE.md
-->

---
### Requirement: Elected Status Compensating Checks
The compensating check that bounds the named mark anomalies SHALL compare the value derived from the
source mark against the cross-file derived value. It SHALL NOT compare the published elected column
against the cross-file value once those two hold the same thing.

A check whose two sides are the same value passes for every row and raises nothing. The named anomaly
list it guards then becomes a list nothing tests, and the corruption it was written to catch would
reappear unnoticed.

#### Scenario: The two sides of the check become the same value
- **WHEN** the published elected column is changed to hold the cross-file derived value
- **THEN** the check SHALL be re-pointed at the value derived from the source mark, and a mutation
  restoring the same-value comparison SHALL be detected by the test suite

#### Scenario: A check that asserts what the source claimed
- **WHEN** a validation asserts whether the source file's own stated total is internally consistent
- **THEN** it SHALL count from the source mark, not from the published elected column, because
  counting from the published column makes the assertion compare the authoritative value against
  itself — it then holds for every file, raises nothing, and reports no error while having stopped
  detecting source corruption entirely

#### Scenario: A report field labelled as the source's count
- **WHEN** the validation report publishes both the source's count and the authoritative count
- **THEN** the two SHALL be computed from different columns, so that a term whose source is corrupt
  shows two different numbers rather than one number twice

#### Scenario: A mark anomaly outside the named list
- **WHEN** a candidate's source-derived status disagrees with the cross-file derived status and that
  candidate is not on the named list
- **THEN** the build SHALL abort, naming the term, election type, candidate and mark


<!-- @trace
source: elected-column-swap
updated: 2026-08-21
code:
  - .spectra.yaml
  - AGENTS.md
  - GEMINI.md
  - CLAUDE.md
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
  - GEMINI.md
  - scripts/mutate_build_site_data.py
  - docs/index.html
  - .spectra.yaml
  - scripts/build_site_data.py
  - docs/roster.html
  - CLAUDE.md
  - AGENTS.md
  - scripts/palette_metrics.py
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
  - GEMINI.md
  - scripts/mutate_build_site_data.py
  - docs/index.html
  - .spectra.yaml
  - scripts/build_site_data.py
  - docs/roster.html
  - CLAUDE.md
  - AGENTS.md
  - scripts/palette_metrics.py
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
  - GEMINI.md
  - .spectra.yaml
  - AGENTS.md
  - CLAUDE.md
-->

---
### Requirement: Sentinel Recognition Is Named Per Term, Not Global
The scope in which a value is treated as a sentinel SHALL be an explicit named list. A value
SHALL NOT be treated as a sentinel merely because it once served that purpose, because the same
number can be a genuine measurement elsewhere.

The named scope SHALL be a term where every file of that term shares one convention, and SHALL be
narrowed to a term and election type where they do not. Files issued for the same term have been
found to use different sentinel values from one another, so a term-wide list cannot express which
value applies without either discarding real measurements in the files that disagree or admitting
a sentinel as a measurement in the files that agree.

Two checks SHALL bound the list, and both SHALL abort the build rather than adjust behaviour
silently: a listed scope SHALL contain no value other than the sentinels named for it, and a scope
not listed for a given sentinel SHALL contain no occurrence of that sentinel.

A named narrowing that is never exercised SHALL abort the build, because a declaration that no
longer matches any file is indistinguishable from one that was never correct.

#### Scenario: A listed term turns out to hold a real value
- **WHEN** a term on the list carries any age other than the sentinel
- **THEN** the build SHALL abort naming that term and the value, because the premise for listing it
  no longer holds and a real age would otherwise be discarded

#### Scenario: An unlisted term starts carrying the sentinel
- **WHEN** a term not on the list carries the sentinel value
- **THEN** the build SHALL abort naming that term, because either the sentinel convention has spread
  to a new term or a genuine value coincides with it, and the two cannot be told apart automatically

#### Scenario: One file of a term uses a different sentinel from the rest
- **WHEN** the files of a single term do not share one sentinel convention
- **THEN** the narrower value SHALL be named against that term and election type rather than against
  the term as a whole, so that the files which do not use it keep the value as a measurement

#### Scenario: A narrowed declaration stops matching any file
- **WHEN** a sentinel named for a term and election type no longer occurs in that scope
- **THEN** the build SHALL abort naming the declaration, because an unexercised narrowing silently
  widens what the remaining checks accept

#### Scenario: A narrowed sentinel appears outside its declared scope
- **WHEN** a value named as a sentinel for one election type occurs in another election type of the
  same term
- **THEN** the build SHALL abort, because it is either a spreading convention or a genuine
  measurement, and treating it as a measurement by default would publish a wrong figure

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
  - CLAUDE.md
  - AGENTS.md
  - .spectra.yaml
  - GEMINI.md
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
  - GEMINI.md
  - .spectra.yaml
  - AGENTS.md
  - CLAUDE.md
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
  - GEMINI.md
  - .spectra.yaml
  - AGENTS.md
  - CLAUDE.md
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
  - GEMINI.md
  - .spectra.yaml
  - AGENTS.md
  - CLAUDE.md
-->

---
### Requirement: A Change In Key Formatting Aborts Rather Than Silently Failing To Match
Some source files carry a leading apostrophe on their key columns, an artefact of spreadsheet export. Keys that differ only by such an artefact SHALL NOT be treated as different units, and a file whose key formatting differs from the formatting it has previously carried SHALL abort the build.

#### Scenario: A file that previously carried the artefact stops carrying it
- **WHEN** a file whose keys have carried leading apostrophes is re-issued without them
- **THEN** the build SHALL abort, so that the change is seen rather than absorbed

#### Scenario: A file that never carried the artefact starts carrying it
- **WHEN** a file whose keys have not carried leading apostrophes is re-issued with them
- **THEN** the build SHALL abort naming the term, election type and file, rather than cross-file joins silently matching nothing and yielding zero rows

#### Scenario: Only the affected file is altered
- **WHEN** the artefact is removed from the file that carries it
- **THEN** the key values of every other file SHALL be byte-identical to what the source contained, because a blanket cleanup would also alter keys that were never affected


<!-- @trace
source: add-indigenous-legislative-elections
updated: 2026-08-21
code:
  - data/sources.json
  - README.md
  - .spectra.yaml
  - AGENTS.md
  - docs/schema/cec-legislative-election.md
  - CLAUDE.md
  - data/processed/cec-legislative-election-summary-long.csv.gz
  - data/reference/cec-legislative-county-crosswalk.csv
  - scripts/oracles.py
  - data/processed/legislative-validation-report.json
  - scripts/build_legislative_election.py
  - data/processed/cec-legislative-election-votes-long.csv.gz
  - HANDOFF.md
  - scripts/mutate_build_legislative_election.py
  - GEMINI.md
  - data/processed/cec-legislative-election-candidates-long.csv
tests:
  - scripts/test_build_legislative_election.py
-->

---
### Requirement: Superseded Duplicate Source Directories Are Excluded By Name
The source archive contains a superseded copy of at least one term alongside the current one, distinguished only by a path segment. The two copies are the same election published under different administrative code systems; they agree on national totals but differ in their breakdown row counts, and one may be more internally consistent than the other. The project SHALL take exactly one copy by name, SHALL exclude the other by name, and SHALL abort if the excluded copy reaches the parser. The choice SHALL NOT be made by row count, by internal consistency alone, or by whichever path was found first.

#### Scenario: A superseded copy is resolved as a source path
- **WHEN** the set of resolved source paths contains the excluded copy
- **THEN** the build SHALL abort naming that path, rather than silently choosing between the copies

#### Scenario: The excluded copy is the internally consistent one
- **WHEN** the copy that is excluded is more internally consistent than the copy that is used
- **THEN** the choice SHALL still be recorded with its reasoning, and the consequences for the copy that is used SHALL be handled explicitly rather than inherited silently

#### Scenario: A consumer asks which copy the figures came from
- **WHEN** a consumer needs to know which of two disagreeing copies a published figure was taken from
- **THEN** the named-defect record SHALL state which copy was used, how the copies differ, and why that copy was chosen


<!-- @trace
source: add-indigenous-legislative-elections
updated: 2026-08-21
code:
  - data/sources.json
  - README.md
  - .spectra.yaml
  - AGENTS.md
  - docs/schema/cec-legislative-election.md
  - CLAUDE.md
  - data/processed/cec-legislative-election-summary-long.csv.gz
  - data/reference/cec-legislative-county-crosswalk.csv
  - scripts/oracles.py
  - data/processed/legislative-validation-report.json
  - scripts/build_legislative_election.py
  - data/processed/cec-legislative-election-votes-long.csv.gz
  - HANDOFF.md
  - scripts/mutate_build_legislative_election.py
  - GEMINI.md
  - data/processed/cec-legislative-election-candidates-long.csv
tests:
  - scripts/test_build_legislative_election.py
-->

---
### Requirement: Aggregate Rows That Disagree With Their Own Detail Are Named, And The Detail Wins
A source file may carry an aggregate row whose figures disagree with the sum of the finer-level rows beneath it. Where this occurs, the finer levels SHALL be treated as authoritative and the aggregate row SHALL be recorded as the defect. The set of disagreeing units SHALL be named exactly; a disagreement outside the named set, or a named unit that stops disagreeing, SHALL abort the build.

#### Scenario: An aggregate row omits one unit's votes
- **WHEN** a county-level row's total is short by exactly one township's votes, and that township's own rows are present and correct
- **THEN** the township rows SHALL be published unchanged and the county row SHALL be recorded as the defect, naming the township and the amount

#### Scenario: The check is pointed the wrong way
- **WHEN** the comparison is written so that the aggregate row is treated as authoritative
- **THEN** the correct finer-level rows would be reported as anomalous — the opposite of what happened — so the direction of the comparison SHALL be stated where the check is defined

#### Scenario: A published rate contradicts its own numerator and denominator
- **WHEN** a rate column states zero while the counts it derives from are non-zero
- **THEN** the source value SHALL be preserved in its own column, the recomputed value SHALL be published alongside, and the affected rows SHALL be named exactly

#### Scenario: A named aggregate defect stops appearing
- **WHEN** a re-issued source no longer contains one of the named disagreements
- **THEN** the build SHALL abort, because the record has become stale and would otherwise keep asserting a defect that no longer exists


<!-- @trace
source: add-indigenous-legislative-elections
updated: 2026-08-21
code:
  - data/sources.json
  - README.md
  - .spectra.yaml
  - AGENTS.md
  - docs/schema/cec-legislative-election.md
  - CLAUDE.md
  - data/processed/cec-legislative-election-summary-long.csv.gz
  - data/reference/cec-legislative-county-crosswalk.csv
  - scripts/oracles.py
  - data/processed/legislative-validation-report.json
  - scripts/build_legislative_election.py
  - data/processed/cec-legislative-election-votes-long.csv.gz
  - HANDOFF.md
  - scripts/mutate_build_legislative_election.py
  - GEMINI.md
  - data/processed/cec-legislative-election-candidates-long.csv
tests:
  - scripts/test_build_legislative_election.py
-->

---
### Requirement: A Term's Seat Total Is Fixed By History, Not By Whatever The Source Currently Says
The number of seats contested is not constant across terms of the same office. Each term's seat total is a historical fact that SHALL NOT change because a source file was re-issued. A published seat total that differs from the historical one SHALL abort the build instead of being adopted.

#### Scenario: A term's seat total changes in the source
- **WHEN** the seat total parsed for a term differs from that term's historical total
- **THEN** the build SHALL abort naming the term, election type, both figures, rather than accepting the new figure as the current truth

#### Scenario: A reader assumes a constant seat total across terms
- **WHEN** a consumer reads the documentation for this office
- **THEN** it SHALL state the seat total per term rather than a single figure, so that the change across terms is visible without inspecting the data

<!-- @trace
source: add-indigenous-legislative-elections
updated: 2026-08-21
code:
  - data/sources.json
  - README.md
  - .spectra.yaml
  - AGENTS.md
  - docs/schema/cec-legislative-election.md
  - CLAUDE.md
  - data/processed/cec-legislative-election-summary-long.csv.gz
  - data/reference/cec-legislative-county-crosswalk.csv
  - scripts/oracles.py
  - data/processed/legislative-validation-report.json
  - scripts/build_legislative_election.py
  - data/processed/cec-legislative-election-votes-long.csv.gz
  - HANDOFF.md
  - scripts/mutate_build_legislative_election.py
  - GEMINI.md
  - data/processed/cec-legislative-election-candidates-long.csv
tests:
  - scripts/test_build_legislative_election.py
-->

---
### Requirement: A Compensating Check Is Not Considered Tested Until An Input Exists That Trips It
This capability's standing response to a source defect is a named exception plus a compensating check. A compensating check whose condition never becomes true on the available data is indistinguishable from one that has been deleted: the build passes, the output is byte-identical, and no test turns red. Every such check SHALL therefore have an input that makes its condition true and its abort observable. A check without one SHALL NOT be described as tested, in documentation or in commit messages.

#### Scenario: A guard is disabled and nothing turns red
- **WHEN** a compensating check is changed so that its condition can never be true
- **THEN** at least one test SHALL fail, and the failure SHALL be attributable to that specific check rather than to a general build failure

#### Scenario: A guard has never fired on the available data
- **WHEN** a check's condition has not become true on any source file the project has processed
- **THEN** this SHALL NOT be taken as evidence that the condition is impossible, and the check SHALL NOT be removed as dead code on that basis alone

#### Scenario: Distinguishing "not yet triggered" from "cannot trigger"
- **WHEN** deciding whether a check is redundant
- **THEN** the decision SHALL rest on measurement of whether the branch is reached, not on reading the surrounding code, because a branch that executes but whose condition is false is reachable by definition

#### Scenario: Another check intercepts the input first
- **WHEN** an input intended to trip one check is caught by a different check earlier in the pipeline
- **THEN** the test SHALL be treated as not yet covering its target, because an abort from elsewhere proves nothing about the check under test

#### Scenario: A check is made vacuous rather than removed
- **WHEN** a change makes a check's assertion always hold instead of removing the check
- **THEN** the test SHALL assert on a value that the change alters, not on whether the build aborted, because a vacuous assertion aborts on nothing

<!-- @trace
source: test-unguarded-source-checks
updated: 2026-08-22
code:
  - scripts/mutate_build_local_election.py
  - CLAUDE.md
  - HANDOFF.md
  - .spectra.yaml
  - AGENTS.md
  - GEMINI.md
tests:
  - scripts/test_build_local_election.py
-->

---
### Requirement: Town Codes Re-Numbered Per File Are Resolved Through The Same-Term Regional File
The 1998, 2002, and 2005 plain-indigenous (T2) and mountain-indigenous (T3) county councilor files number their town codes internally, so the same township carries a different code than it does in the same-term regional file. The system SHALL resolve every town in those six files to the same-term regional file's town code and record it in the normalized town column. Resolution SHALL key on the pair (county name, town name), because the county codes in those terms are themselves re-numbered per file and cannot serve as a join key.

The regional file is the canonical target for the term. Agreement between the two files establishes that they can be reconciled; it does not establish that the regional file's codes are externally correct, and documentation SHALL NOT claim the stronger property.

#### Scenario: A town resolves to a different code than it carries locally
- **WHEN** a town in one of the six files matches exactly one town of the same name in the same county of the same-term regional file
- **THEN** the normalized town column SHALL hold the regional file's town code, and the source town column SHALL retain the file's own code unchanged

##### Example: the four resolution outcomes

| Case | Term / type | County | Source name | Source code | Resolved code |
| --- | --- | --- | --- | --- | --- |
| Exact, code differs | 2002 T3 | 屏東縣 | 霧臺鄉 | `033` | `027` |
| Exact, code already agrees | 2005 T2 | 花蓮縣 | 吉安鄉 | `004` | `004` |
| Named alias | 2002 T3 | 嘉義縣 | 里山鄉 | file-local | code of 阿里山鄉 |
| Unknown name | any | any | 火星鄉 | any | **abort** |

Across the six files 1,290 towns resolve, of which 829 receive a code that
differs from the one they carry locally and 4 resolve through a named alias.

#### Scenario: No matching town in the target
- **WHEN** a town name in one of the six files has no same-named town in that county of the regional file, and no named alias covers it
- **THEN** the build SHALL abort naming the term, election type, county, and town name

#### Scenario: More than one matching town in the target
- **WHEN** a town name matches more than one town in that county of the regional file
- **THEN** the build SHALL abort, because a single match reached by chance is not a resolution

#### Scenario: Target-side names are not assumed unique
- **WHEN** the regional file contains two towns with the same name in the same county
- **THEN** the build SHALL abort, and this SHALL be checked at build time rather than relied upon from a one-time census

#### Scenario: Two source towns resolve to one target
- **WHEN** two towns in the same source file resolve to the same (province, county, town) triple in the regional file
- **THEN** the build SHALL abort, because merging two townships keeps every total balanced and leaves no other trace

---
### Requirement: Truncated Town Names Are Named, Never Pattern-Matched
Four town names in these files are missing their leading character: 里山鄉, 地門鄉, and 麻里鄉 in the 2002 mountain-indigenous file, and 麻里鄉 in the 2005 mountain-indigenous file. The system SHALL resolve these through an explicit alias list keyed on (term, election type, county name, source name) and SHALL NOT use any string rule such as dropping a leading character, matching on a suffix, or edit distance.

The causes are not uniform: in the 2002 mountain-indigenous file no town name exceeds three characters and all three four-character names are truncated, while the 2005 mountain-indigenous file preserves 三地門鄉 and 阿里山鄉 and truncates only 太麻里鄉. A length rule therefore fails on 2005, and a leading-character rule produces false positives against the legitimate two-character district names present in the plain-indigenous files.

#### Scenario: A truncated name resolves through its alias
- **WHEN** a source town name matches an alias entry for that term, election type, and county
- **THEN** the town SHALL resolve to the target named by that alias entry

#### Scenario: An alias entry is never used
- **WHEN** the build completes and an alias entry was not applied
- **THEN** the build SHALL abort, because a stale alias list is itself a defect

#### Scenario: An alias is applied a different number of times than declared
- **WHEN** an alias entry's application count differs from its declared expected count
- **THEN** the build SHALL abort, because "used at least once" does not establish that it was used where intended

#### Scenario: An alias points at a target that does not agree
- **WHEN** an alias entry names a target town code whose name in the regional file differs from the alias's target name
- **THEN** the build SHALL abort

#### Scenario: A new truncation appears in a future source revision
- **WHEN** a source file is revised and introduces a truncated name not covered by the alias list
- **THEN** the build SHALL abort rather than resolve it by inference

---
### Requirement: An Unresolved Town Is An Abort, Not An Empty Cell
An empty normalized town column previously meant one thing only: that the project performed no town-level normalization for that file. Once resolution is attempted, an empty cell would acquire a second meaning — that a particular row could not be resolved — and the two are indistinguishable downstream. They SHALL NOT share a representation. The system SHALL either write a resolved code or abort the build; it SHALL NOT write an empty value to represent a failed lookup.

#### Scenario: Resolution fails partway through a file
- **WHEN** any town in a covered file cannot be resolved
- **THEN** the build SHALL abort and SHALL NOT write an empty normalized value for that row, because a downstream reader cannot distinguish a deliberate blank from a failed lookup
