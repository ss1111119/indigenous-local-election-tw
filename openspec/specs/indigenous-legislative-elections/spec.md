# indigenous-legislative-elections Specification

## Purpose

Indigenous legislators are elected from a single nationwide constituency per
category — mountain-indigenous and plain-indigenous — so the electorate is the
indigenous population itself rather than a geographic proxy. That makes these
elections the one place in this project's sources where indigenous voting can be
read without ecological inference.

This capability governs their coverage and shape: which terms are included and
how many seats each returned (the total is not constant across terms); why the
data is published separately from local office rather than merged into it; how a
column that looks like a constituency identifier but carries no constituency
meaning is marked as such; how a term's published breakdown is declared, and the
difference between a source losing rows and this project choosing not to publish
rows it knows to be incomplete; which column carries elected status and which
carries the source's own claim; why geographic codes are not published as though
they were stable across terms; and that the candidate file's personal data never
reaches any output.

The reason this capability exists separately from the local-office ones is that
almost every structural assumption differs: there is no constituency level, the
seat total changes twice across the nine terms, the age sentinel covers different
terms, and the county code system changes three times with one era renumbering
into the range another era already used.

## Requirements

### Requirement: Nine Terms Of Indigenous Legislative Elections Are Covered
The dataset SHALL cover the mountain-indigenous and plain-indigenous legislative elections of 1995, 1998, 2001, 2004, 2008, 2012, 2016, 2020, and 2024, for both categories in every term. A term that is present in the source archive and absent from the output SHALL abort the build rather than produce a partial dataset.

#### Scenario: Counting seats per term
- **WHEN** a consumer counts elected candidates per term and category
- **THEN** the counts SHALL be 3 for each category in 1995, 4 for each category in 1998, 2001 and 2004, and 3 for each category in 2008, 2012, 2016, 2020 and 2024

#### Scenario: A source term fails to parse
- **WHEN** any one of the ninety source files (eighteen term-category parts of five files each) cannot be parsed
- **THEN** the build SHALL abort naming the term and category, and SHALL NOT write any output file


<!-- @trace
source: add-indigenous-legislative-elections
updated: 2026-08-21
code:
  - scratch/verify_33.py
  - scratch/measure_2005d.py
  - scratch/verify_strip.py
  - scratch/measure_2005b.py
  - data/sources.json
  - scratch/dryrun_manifest.py
  - README.md
  - scratch/baseline/votes.csv
  - scratch/inventory_legacy.py
  - .spectra.yaml
  - AGENTS.md
  - scratch/zip_names.json
  - scratch/add_defect7.py
  - scratch/review_q4.md
  - scratch/verify_21.py
  - scratch/probe_districts2.py
  - scratch/verify_21c.py
  - scratch/measure_2005g.py
  - scratch/review_question.md
  - scratch/verify_claims.py
  - scratch/probe_anomalies.py
  - docs/schema/cec-legislative-election.md
  - scratch/probe5.py
  - scratch/review_q6.md
  - scratch/baseline/summary.csv
  - scratch/measure_ws2.py
  - scratch/review_q3.md
  - scratch/build_1998_2002_crosswalk.py
  - scratch/probe4.py
  - scratch/probe_districts.py
  - CLAUDE.md
  - scratch/strip_experiment.py
  - scratch/measure_town_codes.py
  - scratch/chk_cw.py
  - scratch/verify_11.py
  - scratch/measure_trunc.py
  - scratch/measure_pop.py
  - scratch/chk1998t2.py
  - data/processed/cec-legislative-election-summary-long.csv.gz
  - scratch/review_q5.md
  - scratch/verify_identity.py
  - scratch/gen_anomalies.py
  - scratch/measure_2005c.py
  - data/reference/cec-legislative-county-crosswalk.csv
  - scratch/measure_pop2.py
  - scratch/measure_whitespace.py
  - scratch/probe_1994.py
  - scripts/oracles.py
  - data/processed/legislative-validation-report.json
  - scratch/measure_2005.py
  - scratch/probe6.py
  - scratch/verify_crosswalk.py
  - scripts/build_legislative_election.py
  - data/processed/cec-legislative-election-votes-long.csv.gz
  - scratch/probe_legacy_build.py
  - scratch/verify_auth.py
  - scratch/measure_2005f.py
  - scratch/verify_pop2.py
  - scratch/review_q7.md
  - scratch/add_legacy_sources.py
  - scratch/expected.txt
  - HANDOFF.md
  - scripts/mutate_build_legislative_election.py
  - scratch/list_zip.py
  - scratch/probe7.py
  - scratch/measure_auth_existing.py
  - scratch/verify_32.py
  - scratch/measure_2005e.py
  - scratch/measure_2005_towns.py
  - GEMINI.md
  - scratch/measure_town_feasible.py
  - scratch/probe3.py
  - scratch/verify_pop.py
  - scratch/verify_review.py
  - scratch/review_q2.md
  - scratch/baseline/candidates.csv
  - scratch/gen_town_anom.py
  - scratch/probe2.py
  - data/processed/cec-legislative-election-candidates-long.csv
  - scratch/gen_expected.py
  - scratch/inventory_legacy.json
tests:
  - scripts/test_build_legislative_election.py
-->

---
### Requirement: Legislative Data Is Published Separately From Local Office Data
The indigenous legislative elections SHALL be published as their own long tables, distinct from the local-office long tables. Adding legislative coverage SHALL NOT change the columns, row count, or bytes of the local-office long tables.

#### Scenario: A consumer of the local-office tables rebuilds after this change
- **WHEN** the local-office long tables are rebuilt with legislative coverage present in the project
- **THEN** their content SHALL be byte-identical to the content produced before legislative coverage existed

#### Scenario: Distinguishing the two datasets by election type code
- **WHEN** a consumer reads the election type code in the legislative tables
- **THEN** plain-indigenous legislators SHALL be coded `L2` and mountain-indigenous legislators `L3`, and the documentation SHALL state that these are project-assigned codes rather than codes taken from the source


<!-- @trace
source: add-indigenous-legislative-elections
updated: 2026-08-21
code:
  - scratch/verify_33.py
  - scratch/measure_2005d.py
  - scratch/verify_strip.py
  - scratch/measure_2005b.py
  - data/sources.json
  - scratch/dryrun_manifest.py
  - README.md
  - scratch/baseline/votes.csv
  - scratch/inventory_legacy.py
  - .spectra.yaml
  - AGENTS.md
  - scratch/zip_names.json
  - scratch/add_defect7.py
  - scratch/review_q4.md
  - scratch/verify_21.py
  - scratch/probe_districts2.py
  - scratch/verify_21c.py
  - scratch/measure_2005g.py
  - scratch/review_question.md
  - scratch/verify_claims.py
  - scratch/probe_anomalies.py
  - docs/schema/cec-legislative-election.md
  - scratch/probe5.py
  - scratch/review_q6.md
  - scratch/baseline/summary.csv
  - scratch/measure_ws2.py
  - scratch/review_q3.md
  - scratch/build_1998_2002_crosswalk.py
  - scratch/probe4.py
  - scratch/probe_districts.py
  - CLAUDE.md
  - scratch/strip_experiment.py
  - scratch/measure_town_codes.py
  - scratch/chk_cw.py
  - scratch/verify_11.py
  - scratch/measure_trunc.py
  - scratch/measure_pop.py
  - scratch/chk1998t2.py
  - data/processed/cec-legislative-election-summary-long.csv.gz
  - scratch/review_q5.md
  - scratch/verify_identity.py
  - scratch/gen_anomalies.py
  - scratch/measure_2005c.py
  - data/reference/cec-legislative-county-crosswalk.csv
  - scratch/measure_pop2.py
  - scratch/measure_whitespace.py
  - scratch/probe_1994.py
  - scripts/oracles.py
  - data/processed/legislative-validation-report.json
  - scratch/measure_2005.py
  - scratch/probe6.py
  - scratch/verify_crosswalk.py
  - scripts/build_legislative_election.py
  - data/processed/cec-legislative-election-votes-long.csv.gz
  - scratch/probe_legacy_build.py
  - scratch/verify_auth.py
  - scratch/measure_2005f.py
  - scratch/verify_pop2.py
  - scratch/review_q7.md
  - scratch/add_legacy_sources.py
  - scratch/expected.txt
  - HANDOFF.md
  - scripts/mutate_build_legislative_election.py
  - scratch/list_zip.py
  - scratch/probe7.py
  - scratch/measure_auth_existing.py
  - scratch/verify_32.py
  - scratch/measure_2005e.py
  - scratch/measure_2005_towns.py
  - GEMINI.md
  - scratch/measure_town_feasible.py
  - scratch/probe3.py
  - scratch/verify_pop.py
  - scratch/verify_review.py
  - scratch/review_q2.md
  - scratch/baseline/candidates.csv
  - scratch/gen_town_anom.py
  - scratch/probe2.py
  - data/processed/cec-legislative-election-candidates-long.csv
  - scratch/gen_expected.py
  - scratch/inventory_legacy.json
tests:
  - scripts/test_build_legislative_election.py
-->

---
### Requirement: The Nationwide Constituency Is Stated, Not Implied
Indigenous legislators are elected from a single nationwide constituency per category. The district column carries no constituency meaning in these files, and its raw value differs across terms. The dataset SHALL preserve the raw value and SHALL publish, alongside it, an explicit statement of whether the column carries constituency meaning in that term.

#### Scenario: A consumer groups by district column
- **WHEN** a consumer groups the legislative tables by the district column expecting separate constituencies
- **THEN** the accompanying meaning column SHALL tell them the column carries no constituency meaning, so that the grouping is recognised as meaningless rather than silently producing plausible subtotals

#### Scenario: The district column takes an undeclared value
- **WHEN** the district column in a term contains a value outside the set declared for that term and category
- **THEN** the build SHALL abort naming the term, category, file, the declared set, and the value found


<!-- @trace
source: add-indigenous-legislative-elections
updated: 2026-08-21
code:
  - scratch/verify_33.py
  - scratch/measure_2005d.py
  - scratch/verify_strip.py
  - scratch/measure_2005b.py
  - data/sources.json
  - scratch/dryrun_manifest.py
  - README.md
  - scratch/baseline/votes.csv
  - scratch/inventory_legacy.py
  - .spectra.yaml
  - AGENTS.md
  - scratch/zip_names.json
  - scratch/add_defect7.py
  - scratch/review_q4.md
  - scratch/verify_21.py
  - scratch/probe_districts2.py
  - scratch/verify_21c.py
  - scratch/measure_2005g.py
  - scratch/review_question.md
  - scratch/verify_claims.py
  - scratch/probe_anomalies.py
  - docs/schema/cec-legislative-election.md
  - scratch/probe5.py
  - scratch/review_q6.md
  - scratch/baseline/summary.csv
  - scratch/measure_ws2.py
  - scratch/review_q3.md
  - scratch/build_1998_2002_crosswalk.py
  - scratch/probe4.py
  - scratch/probe_districts.py
  - CLAUDE.md
  - scratch/strip_experiment.py
  - scratch/measure_town_codes.py
  - scratch/chk_cw.py
  - scratch/verify_11.py
  - scratch/measure_trunc.py
  - scratch/measure_pop.py
  - scratch/chk1998t2.py
  - data/processed/cec-legislative-election-summary-long.csv.gz
  - scratch/review_q5.md
  - scratch/verify_identity.py
  - scratch/gen_anomalies.py
  - scratch/measure_2005c.py
  - data/reference/cec-legislative-county-crosswalk.csv
  - scratch/measure_pop2.py
  - scratch/measure_whitespace.py
  - scratch/probe_1994.py
  - scripts/oracles.py
  - data/processed/legislative-validation-report.json
  - scratch/measure_2005.py
  - scratch/probe6.py
  - scratch/verify_crosswalk.py
  - scripts/build_legislative_election.py
  - data/processed/cec-legislative-election-votes-long.csv.gz
  - scratch/probe_legacy_build.py
  - scratch/verify_auth.py
  - scratch/measure_2005f.py
  - scratch/verify_pop2.py
  - scratch/review_q7.md
  - scratch/add_legacy_sources.py
  - scratch/expected.txt
  - HANDOFF.md
  - scripts/mutate_build_legislative_election.py
  - scratch/list_zip.py
  - scratch/probe7.py
  - scratch/measure_auth_existing.py
  - scratch/verify_32.py
  - scratch/measure_2005e.py
  - scratch/measure_2005_towns.py
  - GEMINI.md
  - scratch/measure_town_feasible.py
  - scratch/probe3.py
  - scratch/verify_pop.py
  - scratch/verify_review.py
  - scratch/review_q2.md
  - scratch/baseline/candidates.csv
  - scratch/gen_town_anom.py
  - scratch/probe2.py
  - data/processed/cec-legislative-election-candidates-long.csv
  - scratch/gen_expected.py
  - scratch/inventory_legacy.json
tests:
  - scripts/test_build_legislative_election.py
-->

---
### Requirement: A Term's Breakdown Is Declared, And Narrows Only Deliberately
The finest administrative level available differs by term. A term's published breakdown SHALL be declared, and SHALL NOT become narrower than its declaration without the build aborting. A term MAY be published deliberately coarser than its source supports when the finer levels are known to be incomplete; such a narrowing SHALL be declared separately from the source's own depth, so that "the source lost rows" and "we chose not to publish these rows" remain distinguishable.

#### Scenario: Fine-grained rows disappear from a source term
- **WHEN** a term whose source has carried polling-station rows yields only township-level rows
- **THEN** the build SHALL abort, because the totals would otherwise remain correct while the breakdown silently coarsened, and nothing in the output would say so

#### Scenario: A term whose finer levels are known incomplete
- **WHEN** a term's source reaches polling-station level but that level is known to be incomplete
- **THEN** the incomplete levels SHALL be absent from the published tables rather than published with a caveat in the documentation, because a consumer reading the tables does not read the documentation first and the incomplete figures look entirely reasonable

#### Scenario: A consumer checks what breakdown a term supports
- **WHEN** a consumer needs to know whether a term can be analysed at polling-station level
- **THEN** the documentation SHALL state the published finest level per term, so that an empty result is distinguishable from an unsupported query


<!-- @trace
source: add-indigenous-legislative-elections
updated: 2026-08-21
code:
  - scratch/verify_33.py
  - scratch/measure_2005d.py
  - scratch/verify_strip.py
  - scratch/measure_2005b.py
  - data/sources.json
  - scratch/dryrun_manifest.py
  - README.md
  - scratch/baseline/votes.csv
  - scratch/inventory_legacy.py
  - .spectra.yaml
  - AGENTS.md
  - scratch/zip_names.json
  - scratch/add_defect7.py
  - scratch/review_q4.md
  - scratch/verify_21.py
  - scratch/probe_districts2.py
  - scratch/verify_21c.py
  - scratch/measure_2005g.py
  - scratch/review_question.md
  - scratch/verify_claims.py
  - scratch/probe_anomalies.py
  - docs/schema/cec-legislative-election.md
  - scratch/probe5.py
  - scratch/review_q6.md
  - scratch/baseline/summary.csv
  - scratch/measure_ws2.py
  - scratch/review_q3.md
  - scratch/build_1998_2002_crosswalk.py
  - scratch/probe4.py
  - scratch/probe_districts.py
  - CLAUDE.md
  - scratch/strip_experiment.py
  - scratch/measure_town_codes.py
  - scratch/chk_cw.py
  - scratch/verify_11.py
  - scratch/measure_trunc.py
  - scratch/measure_pop.py
  - scratch/chk1998t2.py
  - data/processed/cec-legislative-election-summary-long.csv.gz
  - scratch/review_q5.md
  - scratch/verify_identity.py
  - scratch/gen_anomalies.py
  - scratch/measure_2005c.py
  - data/reference/cec-legislative-county-crosswalk.csv
  - scratch/measure_pop2.py
  - scratch/measure_whitespace.py
  - scratch/probe_1994.py
  - scripts/oracles.py
  - data/processed/legislative-validation-report.json
  - scratch/measure_2005.py
  - scratch/probe6.py
  - scratch/verify_crosswalk.py
  - scripts/build_legislative_election.py
  - data/processed/cec-legislative-election-votes-long.csv.gz
  - scratch/probe_legacy_build.py
  - scratch/verify_auth.py
  - scratch/measure_2005f.py
  - scratch/verify_pop2.py
  - scratch/review_q7.md
  - scratch/add_legacy_sources.py
  - scratch/expected.txt
  - HANDOFF.md
  - scripts/mutate_build_legislative_election.py
  - scratch/list_zip.py
  - scratch/probe7.py
  - scratch/measure_auth_existing.py
  - scratch/verify_32.py
  - scratch/measure_2005e.py
  - scratch/measure_2005_towns.py
  - GEMINI.md
  - scratch/measure_town_feasible.py
  - scratch/probe3.py
  - scratch/verify_pop.py
  - scratch/verify_review.py
  - scratch/review_q2.md
  - scratch/baseline/candidates.csv
  - scratch/gen_town_anom.py
  - scratch/probe2.py
  - data/processed/cec-legislative-election-candidates-long.csv
  - scratch/gen_expected.py
  - scratch/inventory_legacy.json
tests:
  - scripts/test_build_legislative_election.py
-->

---
### Requirement: Elected Status Follows The Project's Established Column Convention
The legislative tables SHALL carry elected status under the same convention as the local-office tables: the plainest-named elected column holds the cross-file determined value, the source's own mark and its decoding remain available unchanged, and the basis of the determination is published alongside. This convention SHALL hold even in terms where the source's mark and the official summary agree.

#### Scenario: Counting seats without reading documentation
- **WHEN** a consumer counts elected candidates from the plainest-named elected column
- **THEN** the count SHALL equal the seat total stated by the official summary file for that term and category

#### Scenario: The source mark disagrees with the official summary in a future term
- **WHEN** a term is added or re-issued in which the source mark and the official summary disagree
- **THEN** the build SHALL abort rather than publish either figure silently, because the compensating check exists for the source going wrong later, not only for defects already known


<!-- @trace
source: add-indigenous-legislative-elections
updated: 2026-08-21
code:
  - scratch/verify_33.py
  - scratch/measure_2005d.py
  - scratch/verify_strip.py
  - scratch/measure_2005b.py
  - data/sources.json
  - scratch/dryrun_manifest.py
  - README.md
  - scratch/baseline/votes.csv
  - scratch/inventory_legacy.py
  - .spectra.yaml
  - AGENTS.md
  - scratch/zip_names.json
  - scratch/add_defect7.py
  - scratch/review_q4.md
  - scratch/verify_21.py
  - scratch/probe_districts2.py
  - scratch/verify_21c.py
  - scratch/measure_2005g.py
  - scratch/review_question.md
  - scratch/verify_claims.py
  - scratch/probe_anomalies.py
  - docs/schema/cec-legislative-election.md
  - scratch/probe5.py
  - scratch/review_q6.md
  - scratch/baseline/summary.csv
  - scratch/measure_ws2.py
  - scratch/review_q3.md
  - scratch/build_1998_2002_crosswalk.py
  - scratch/probe4.py
  - scratch/probe_districts.py
  - CLAUDE.md
  - scratch/strip_experiment.py
  - scratch/measure_town_codes.py
  - scratch/chk_cw.py
  - scratch/verify_11.py
  - scratch/measure_trunc.py
  - scratch/measure_pop.py
  - scratch/chk1998t2.py
  - data/processed/cec-legislative-election-summary-long.csv.gz
  - scratch/review_q5.md
  - scratch/verify_identity.py
  - scratch/gen_anomalies.py
  - scratch/measure_2005c.py
  - data/reference/cec-legislative-county-crosswalk.csv
  - scratch/measure_pop2.py
  - scratch/measure_whitespace.py
  - scratch/probe_1994.py
  - scripts/oracles.py
  - data/processed/legislative-validation-report.json
  - scratch/measure_2005.py
  - scratch/probe6.py
  - scratch/verify_crosswalk.py
  - scripts/build_legislative_election.py
  - data/processed/cec-legislative-election-votes-long.csv.gz
  - scratch/probe_legacy_build.py
  - scratch/verify_auth.py
  - scratch/measure_2005f.py
  - scratch/verify_pop2.py
  - scratch/review_q7.md
  - scratch/add_legacy_sources.py
  - scratch/expected.txt
  - HANDOFF.md
  - scripts/mutate_build_legislative_election.py
  - scratch/list_zip.py
  - scratch/probe7.py
  - scratch/measure_auth_existing.py
  - scratch/verify_32.py
  - scratch/measure_2005e.py
  - scratch/measure_2005_towns.py
  - GEMINI.md
  - scratch/measure_town_feasible.py
  - scratch/probe3.py
  - scratch/verify_pop.py
  - scratch/verify_review.py
  - scratch/review_q2.md
  - scratch/baseline/candidates.csv
  - scratch/gen_town_anom.py
  - scratch/probe2.py
  - data/processed/cec-legislative-election-candidates-long.csv
  - scratch/gen_expected.py
  - scratch/inventory_legacy.json
tests:
  - scripts/test_build_legislative_election.py
-->

---
### Requirement: Geographic Keys Are Not Published As Falsely Joinable
County and township codes in these files are re-issued across terms: the same township carries different codes in different terms, and counties change both their code and their identity as they are upgraded to municipalities. The dataset SHALL NOT publish raw geographic codes as though they were stable keys. Either a normalised key that is comparable across terms SHALL be published alongside the raw value, or the field SHALL be left explicitly empty to mark it as not normalised.

#### Scenario: A consumer joins two terms on township code
- **WHEN** a consumer joins rows from two terms using the published normalised township key
- **THEN** rows SHALL only match when they refer to the same township, and SHALL NOT match a different township that happens to reuse the code

#### Scenario: A term whose codes cannot be normalised
- **WHEN** a term's geographic codes cannot be mapped to a stable identity
- **THEN** the normalised field SHALL be empty rather than carrying the raw code, because a raw code in a field named as normalised would join successfully against the wrong unit and report no error

#### Scenario: A county that was upgraded to a municipality
- **WHEN** a consumer follows one area across a term in which it was upgraded
- **THEN** the normalised key SHALL identify it as the same area on both sides of the upgrade, or the documentation SHALL state that this particular area is not traceable across that boundary


<!-- @trace
source: add-indigenous-legislative-elections
updated: 2026-08-21
code:
  - scratch/verify_33.py
  - scratch/measure_2005d.py
  - scratch/verify_strip.py
  - scratch/measure_2005b.py
  - data/sources.json
  - scratch/dryrun_manifest.py
  - README.md
  - scratch/baseline/votes.csv
  - scratch/inventory_legacy.py
  - .spectra.yaml
  - AGENTS.md
  - scratch/zip_names.json
  - scratch/add_defect7.py
  - scratch/review_q4.md
  - scratch/verify_21.py
  - scratch/probe_districts2.py
  - scratch/verify_21c.py
  - scratch/measure_2005g.py
  - scratch/review_question.md
  - scratch/verify_claims.py
  - scratch/probe_anomalies.py
  - docs/schema/cec-legislative-election.md
  - scratch/probe5.py
  - scratch/review_q6.md
  - scratch/baseline/summary.csv
  - scratch/measure_ws2.py
  - scratch/review_q3.md
  - scratch/build_1998_2002_crosswalk.py
  - scratch/probe4.py
  - scratch/probe_districts.py
  - CLAUDE.md
  - scratch/strip_experiment.py
  - scratch/measure_town_codes.py
  - scratch/chk_cw.py
  - scratch/verify_11.py
  - scratch/measure_trunc.py
  - scratch/measure_pop.py
  - scratch/chk1998t2.py
  - data/processed/cec-legislative-election-summary-long.csv.gz
  - scratch/review_q5.md
  - scratch/verify_identity.py
  - scratch/gen_anomalies.py
  - scratch/measure_2005c.py
  - data/reference/cec-legislative-county-crosswalk.csv
  - scratch/measure_pop2.py
  - scratch/measure_whitespace.py
  - scratch/probe_1994.py
  - scripts/oracles.py
  - data/processed/legislative-validation-report.json
  - scratch/measure_2005.py
  - scratch/probe6.py
  - scratch/verify_crosswalk.py
  - scripts/build_legislative_election.py
  - data/processed/cec-legislative-election-votes-long.csv.gz
  - scratch/probe_legacy_build.py
  - scratch/verify_auth.py
  - scratch/measure_2005f.py
  - scratch/verify_pop2.py
  - scratch/review_q7.md
  - scratch/add_legacy_sources.py
  - scratch/expected.txt
  - HANDOFF.md
  - scripts/mutate_build_legislative_election.py
  - scratch/list_zip.py
  - scratch/probe7.py
  - scratch/measure_auth_existing.py
  - scratch/verify_32.py
  - scratch/measure_2005e.py
  - scratch/measure_2005_towns.py
  - GEMINI.md
  - scratch/measure_town_feasible.py
  - scratch/probe3.py
  - scratch/verify_pop.py
  - scratch/verify_review.py
  - scratch/review_q2.md
  - scratch/baseline/candidates.csv
  - scratch/gen_town_anom.py
  - scratch/probe2.py
  - data/processed/cec-legislative-election-candidates-long.csv
  - scratch/gen_expected.py
  - scratch/inventory_legacy.json
tests:
  - scripts/test_build_legislative_election.py
-->

---
### Requirement: Personal Data Fields Are Never Published
The source candidate files contain date of birth, place of birth, and education. These SHALL NOT appear in any published output of this capability, in any form, including derived fields from which they could be reconstructed.

#### Scenario: A consumer looks for date of birth
- **WHEN** a consumer inspects every column of the published legislative tables
- **THEN** date of birth, place of birth, and education SHALL be absent, while age SHALL be present as a value that does not identify a birth date

<!-- @trace
source: add-indigenous-legislative-elections
updated: 2026-08-21
code:
  - scratch/verify_33.py
  - scratch/measure_2005d.py
  - scratch/verify_strip.py
  - scratch/measure_2005b.py
  - data/sources.json
  - scratch/dryrun_manifest.py
  - README.md
  - scratch/baseline/votes.csv
  - scratch/inventory_legacy.py
  - .spectra.yaml
  - AGENTS.md
  - scratch/zip_names.json
  - scratch/add_defect7.py
  - scratch/review_q4.md
  - scratch/verify_21.py
  - scratch/probe_districts2.py
  - scratch/verify_21c.py
  - scratch/measure_2005g.py
  - scratch/review_question.md
  - scratch/verify_claims.py
  - scratch/probe_anomalies.py
  - docs/schema/cec-legislative-election.md
  - scratch/probe5.py
  - scratch/review_q6.md
  - scratch/baseline/summary.csv
  - scratch/measure_ws2.py
  - scratch/review_q3.md
  - scratch/build_1998_2002_crosswalk.py
  - scratch/probe4.py
  - scratch/probe_districts.py
  - CLAUDE.md
  - scratch/strip_experiment.py
  - scratch/measure_town_codes.py
  - scratch/chk_cw.py
  - scratch/verify_11.py
  - scratch/measure_trunc.py
  - scratch/measure_pop.py
  - scratch/chk1998t2.py
  - data/processed/cec-legislative-election-summary-long.csv.gz
  - scratch/review_q5.md
  - scratch/verify_identity.py
  - scratch/gen_anomalies.py
  - scratch/measure_2005c.py
  - data/reference/cec-legislative-county-crosswalk.csv
  - scratch/measure_pop2.py
  - scratch/measure_whitespace.py
  - scratch/probe_1994.py
  - scripts/oracles.py
  - data/processed/legislative-validation-report.json
  - scratch/measure_2005.py
  - scratch/probe6.py
  - scratch/verify_crosswalk.py
  - scripts/build_legislative_election.py
  - data/processed/cec-legislative-election-votes-long.csv.gz
  - scratch/probe_legacy_build.py
  - scratch/verify_auth.py
  - scratch/measure_2005f.py
  - scratch/verify_pop2.py
  - scratch/review_q7.md
  - scratch/add_legacy_sources.py
  - scratch/expected.txt
  - HANDOFF.md
  - scripts/mutate_build_legislative_election.py
  - scratch/list_zip.py
  - scratch/probe7.py
  - scratch/measure_auth_existing.py
  - scratch/verify_32.py
  - scratch/measure_2005e.py
  - scratch/measure_2005_towns.py
  - GEMINI.md
  - scratch/measure_town_feasible.py
  - scratch/probe3.py
  - scratch/verify_pop.py
  - scratch/verify_review.py
  - scratch/review_q2.md
  - scratch/baseline/candidates.csv
  - scratch/gen_town_anom.py
  - scratch/probe2.py
  - data/processed/cec-legislative-election-candidates-long.csv
  - scratch/gen_expected.py
  - scratch/inventory_legacy.json
tests:
  - scripts/test_build_legislative_election.py
-->