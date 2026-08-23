# site-data-generation Specification

## Purpose

The constants embedded in the published site pages are derived from the project's
long tables by a generator, not maintained by hand. This capability governs how that
derivation works and what it must preserve.

It covers: where the numbers come from (the long tables, never a second hand-kept
copy); the requirement to reproduce the existing published values before extending
coverage; which source field decides whether a candidate was elected; which election
types may be joined into a cross-term line; and how a term in which an election did
not exist is distinguished from one in which it returned zero seats.

The reason this capability exists is that the site's constants were once hand-maintained,
and drifted four terms behind the dataset without anything failing.

## Requirements

### Requirement: Site Data Is Generated From The Long Tables
The site data constants embedded in the site's HTML pages SHALL be produced by a script that reads `data/processed/`, and SHALL NOT be maintained by hand. The script SHALL replace only the data constant line in each HTML file, leaving every other byte unchanged.

The script SHALL read every dataset the site presents, not only the first one it was written for. Where a page presents a dataset, that page's constants SHALL be generated from that dataset's long tables by the same mechanism, with its own marker line.

#### Scenario: Regenerating after a dataset change
- **WHEN** the long tables are rebuilt and the site generator is run
- **THEN** every HTML page SHALL carry data covering every term present in the long tables it presents

#### Scenario: Marker line missing
- **WHEN** an HTML file does not contain the marker line that delimits one of its data constants
- **THEN** the generator SHALL abort rather than fall back to a fuzzy match

#### Scenario: Required column missing
- **WHEN** a long table lacks a column the generator depends on, such as the authoritative elected field
- **THEN** the generator SHALL abort and SHALL NOT write a partial result

#### Scenario: A new dataset is added to the site
- **WHEN** a page is added that presents a dataset the generator did not previously read
- **THEN** the generator SHALL be extended to read that dataset's long tables, and the page's constants SHALL NOT be written by hand even once


<!-- @trace
source: site-legislative-and-party-preference
updated: 2026-08-23
code:
  - scratch/review_q7.md
  - scratch/verify_identity.py
  - scratch/measure_pop2.py
  - scratch/review_q4.md
  - scratch/verify_strip.py
  - README.md
  - scratch/measure_trunc.py
  - scratch/probe7.py
  - scratch/probe6.py
  - CLAUDE.md
  - scratch/measure_2005e.py
  - scratch/probe_1994.py
  - scratch/verify_pop2.py
  - scratch/verify_pop.py
  - scratch/probe_legacy_build.py
  - scratch/review_q5.md
  - scratch/inventory_legacy.py
  - scratch/baseline/summary.csv
  - scratch/measure_ws2.py
  - scratch/measure_town_codes.py
  - scratch/measure_2005c.py
  - scratch/dryrun_manifest.py
  - scratch/measure_2005_towns.py
  - scratch/verify_21c.py
  - scratch/measure_whitespace.py
  - scratch/chk1998t2.py
  - scratch/probe3.py
  - scratch/review_q2.md
  - scratch/review_q6.md
  - docs/legislative.html
  - scratch/verify_crosswalk.py
  - scratch/chk_cw.py
  - scratch/measure_2005.py
  - scratch/probe2.py
  - scratch/probe_districts2.py
  - docs/schema/palette-legislative.md
  - scratch/gen_expected.py
  - scripts/palette_metrics.py
  - scratch/probe4.py
  - HANDOFF.md
  - scratch/measure_auth_existing.py
  - scratch/probe_districts.py
  - .spectra.yaml
  - docs/sitemap.xml
  - scripts/mutate_build_site_data.py
  - scratch/measure_2005d.py
  - scratch/expected.txt
  - docs/roster.html
  - scratch/gen_town_anom.py
  - scratch/probe_anomalies.py
  - scratch/verify_21.py
  - scratch/baseline/votes.csv
  - scratch/strip_experiment.py
  - GEMINI.md
  - AGENTS.md
  - scratch/add_defect7.py
  - scratch/list_zip.py
  - scratch/measure_pop.py
  - scratch/build_1998_2002_crosswalk.py
  - scratch/add_legacy_sources.py
  - docs/index.html
  - scratch/verify_auth.py
  - scratch/probe5.py
  - scratch/verify_11.py
  - scratch/measure_2005f.py
  - scripts/build_site_data.py
  - scratch/measure_town_feasible.py
  - scratch/review_question.md
  - scratch/verify_32.py
  - scratch/baseline/candidates.csv
  - scratch/measure_2005b.py
  - scratch/review_q3.md
  - scratch/measure_2005g.py
  - scratch/zip_names.json
  - scratch/verify_claims.py
  - scratch/gen_anomalies.py
  - scratch/verify_review.py
  - scratch/verify_33.py
  - scratch/inventory_legacy.json
tests:
  - scripts/test_build_site_data.py
-->

---
### Requirement: Existing Terms Must Be Reproduced Before Extending
The generator SHALL provide a mode that emits only the terms already present in the site, so its output can be compared key by key against the current hand-maintained constants. Any difference SHALL be named and explained before the site is extended to further terms.

#### Scenario: Reproduction differs from the current site
- **WHEN** the reproduction mode produces a value that differs from the current site constant
- **THEN** the build SHALL abort unless that difference is recorded in a named list stating whether the site's old value or the generator is wrong

#### Scenario: Reproduction matches
- **WHEN** every key matches
- **THEN** the generator SHALL emit every term present in the long tables


<!-- @trace
source: update-site-to-nine-terms
updated: 2026-08-20
code:
  - scratch/measure_2005.py
  - scratch/verify_strip.py
  - scratch/measure_2005e.py
  - scratch/review_q6.md
  - scratch/probe5.py
  - scratch/probe_districts2.py
  - scratch/inventory_legacy.json
  - scratch/zip_names.json
  - scratch/review_question.md
  - scripts/build_site_data.py
  - docs/roster.html
  - scratch/measure_2005_towns.py
  - scratch/measure_2005g.py
  - scratch/chk_cw.py
  - HANDOFF.md
  - scratch/review_q4.md
  - scratch/review_q3.md
  - scratch/verify_identity.py
  - scratch/verify_33.py
  - docs/index.html
  - scratch/build_1998_2002_crosswalk.py
  - scratch/strip_experiment.py
  - scratch/baseline/summary.csv
  - scratch/verify_crosswalk.py
  - scratch/measure_auth_existing.py
  - scratch/verify_11.py
  - scratch/gen_anomalies.py
  - scratch/list_zip.py
  - scratch/measure_2005d.py
  - scratch/probe3.py
  - scratch/probe4.py
  - scratch/verify_pop.py
  - scratch/measure_pop2.py
  - scratch/measure_trunc.py
  - scratch/mutation_test_site_data.py
  - CLAUDE.md
  - scratch/gen_expected.py
  - scratch/probe7.py
  - scratch/probe_anomalies.py
  - scratch/probe2.py
  - scratch/verify_21c.py
  - scratch/chk1998t2.py
  - scratch/measure_2005c.py
  - AGENTS.md
  - scratch/measure_town_codes.py
  - scratch/gen_town_anom.py
  - scratch/measure_whitespace.py
  - scratch/verify_review.py
  - README.md
  - scratch/verify_21.py
  - .spectra.yaml
  - scratch/verify_auth.py
  - scratch/probe6.py
  - scratch/probe_1994.py
  - scratch/probe_legacy_build.py
  - scratch/dryrun_manifest.py
  - scratch/probe_districts.py
  - scratch/measure_2005f.py
  - scratch/measure_town_feasible.py
  - scratch/expected.txt
  - scratch/verify_claims.py
  - scratch/verify_pop2.py
  - scratch/measure_2005b.py
  - scratch/review_q2.md
  - scratch/measure_pop.py
  - GEMINI.md
  - scratch/review_q7.md
  - scratch/add_defect7.py
  - scratch/baseline/candidates.csv
  - scratch/add_legacy_sources.py
  - scratch/baseline/votes.csv
  - scratch/verify_32.py
  - scratch/review_q5.md
  - scratch/measure_ws2.py
  - scratch/inventory_legacy.py
tests:
  - scripts/test_build_site_data.py
  - scratch/mutation_test.py
-->

---
### Requirement: Seats Come From The Authoritative Elected Field
Every seat count, elected marker, and statistic derived from winners SHALL be computed from the `當選` field, which holds the cross-file authoritative determination. They SHALL NOT be recomputed from `當選註記`, which preserves the source's own marking and carries its known corruption.

#### Scenario: Displaying 2005 county councilor seats
- **WHEN** the site shows seats for the 2005 mountain-indigenous or plain-indigenous county councilors
- **THEN** it SHALL show 30 and 27 respectively, not the 18 and 20 that `當選註記` yields

#### Scenario: Marking winners in the roster
- **WHEN** the roster marks a candidate as elected
- **THEN** the marking SHALL follow `當選`, while the women's-quota (`!`) and displaced (`-`) distinctions SHALL still come from `當選註記`

#### Scenario: A consumer reads the most plainly named elected field
- **WHEN** a reader takes the field named `當選` without consulting documentation first
- **THEN** the value they receive SHALL be the authoritative one, so that being uninformed yields correct seat counts rather than silently wrong ones


<!-- @trace
source: elected-column-swap
updated: 2026-08-21
code:
  - scratch/probe_districts.py
  - scratch/measure_town_codes.py
  - scratch/expected.txt
  - scratch/review_q3.md
  - scratch/chk1998t2.py
  - scratch/verify_21c.py
  - scratch/verify_33.py
  - scratch/verify_pop.py
  - scratch/zip_names.json
  - .spectra.yaml
  - scratch/measure_2005c.py
  - scratch/measure_2005f.py
  - scratch/add_defect7.py
  - AGENTS.md
  - scratch/verify_auth.py
  - GEMINI.md
  - scratch/probe3.py
  - scratch/review_q4.md
  - scratch/verify_crosswalk.py
  - scratch/strip_experiment.py
  - scratch/verify_claims.py
  - scratch/measure_2005.py
  - scratch/measure_2005b.py
  - scratch/dryrun_manifest.py
  - scratch/gen_expected.py
  - scratch/verify_pop2.py
  - scratch/add_legacy_sources.py
  - scratch/verify_11.py
  - scratch/verify_21.py
  - scratch/probe6.py
  - scratch/chk_cw.py
  - scratch/probe2.py
  - scratch/measure_2005d.py
  - scratch/verify_identity.py
  - scratch/inventory_legacy.json
  - scratch/measure_2005e.py
  - scratch/gen_anomalies.py
  - scratch/list_zip.py
  - scratch/inventory_legacy.py
  - scratch/measure_trunc.py
  - scratch/measure_pop.py
  - scratch/gen_town_anom.py
  - scratch/review_q5.md
  - scratch/build_1998_2002_crosswalk.py
  - CLAUDE.md
  - scratch/measure_auth_existing.py
  - scratch/measure_whitespace.py
  - scratch/verify_32.py
  - scratch/probe4.py
  - scratch/review_question.md
  - scratch/probe_anomalies.py
  - scratch/review_q6.md
  - scratch/measure_town_feasible.py
  - scratch/verify_review.py
  - scratch/baseline/candidates.csv
  - scratch/measure_2005g.py
  - scratch/probe_legacy_build.py
  - scratch/probe5.py
  - scratch/measure_ws2.py
  - scratch/verify_strip.py
  - scratch/baseline/summary.csv
  - scratch/measure_pop2.py
  - scratch/review_q2.md
  - scratch/probe_1994.py
  - scratch/probe7.py
  - scratch/measure_2005_towns.py
  - scratch/review_q7.md
  - scratch/probe_districts2.py
  - scratch/baseline/votes.csv
-->

---
### Requirement: Cross-Term Lines Are Restricted To The Main Sequence
Any chart that connects values across terms SHALL include only rows whose `is_main_sequence` is `true`. The project-defined election type codes SHALL be presented in a separate block that states why they cannot be added to the main sequence.

#### Scenario: Plotting a cross-term line
- **WHEN** the site draws a line across terms
- **THEN** rows for `T-PRV2`, `T-PRV3`, and `T-COMBO` SHALL be excluded

#### Scenario: Presenting the excluded types
- **WHEN** the site presents the 1994 provincial councilors or the combined indigenous city councilors
- **THEN** it SHALL do so outside the cross-term lines and SHALL state that the provincial assembly was abolished in 1998, and that the combined category is not split into plain and mountain indigenous


<!-- @trace
source: update-site-to-nine-terms
updated: 2026-08-20
code:
  - scratch/measure_2005.py
  - scratch/verify_strip.py
  - scratch/measure_2005e.py
  - scratch/review_q6.md
  - scratch/probe5.py
  - scratch/probe_districts2.py
  - scratch/inventory_legacy.json
  - scratch/zip_names.json
  - scratch/review_question.md
  - scripts/build_site_data.py
  - docs/roster.html
  - scratch/measure_2005_towns.py
  - scratch/measure_2005g.py
  - scratch/chk_cw.py
  - HANDOFF.md
  - scratch/review_q4.md
  - scratch/review_q3.md
  - scratch/verify_identity.py
  - scratch/verify_33.py
  - docs/index.html
  - scratch/build_1998_2002_crosswalk.py
  - scratch/strip_experiment.py
  - scratch/baseline/summary.csv
  - scratch/verify_crosswalk.py
  - scratch/measure_auth_existing.py
  - scratch/verify_11.py
  - scratch/gen_anomalies.py
  - scratch/list_zip.py
  - scratch/measure_2005d.py
  - scratch/probe3.py
  - scratch/probe4.py
  - scratch/verify_pop.py
  - scratch/measure_pop2.py
  - scratch/measure_trunc.py
  - scratch/mutation_test_site_data.py
  - CLAUDE.md
  - scratch/gen_expected.py
  - scratch/probe7.py
  - scratch/probe_anomalies.py
  - scratch/probe2.py
  - scratch/verify_21c.py
  - scratch/chk1998t2.py
  - scratch/measure_2005c.py
  - AGENTS.md
  - scratch/measure_town_codes.py
  - scratch/gen_town_anom.py
  - scratch/measure_whitespace.py
  - scratch/verify_review.py
  - README.md
  - scratch/verify_21.py
  - .spectra.yaml
  - scratch/verify_auth.py
  - scratch/probe6.py
  - scratch/probe_1994.py
  - scratch/probe_legacy_build.py
  - scratch/dryrun_manifest.py
  - scratch/probe_districts.py
  - scratch/measure_2005f.py
  - scratch/measure_town_feasible.py
  - scratch/expected.txt
  - scratch/verify_claims.py
  - scratch/verify_pop2.py
  - scratch/measure_2005b.py
  - scratch/review_q2.md
  - scratch/measure_pop.py
  - GEMINI.md
  - scratch/review_q7.md
  - scratch/add_defect7.py
  - scratch/baseline/candidates.csv
  - scratch/add_legacy_sources.py
  - scratch/baseline/votes.csv
  - scratch/verify_32.py
  - scratch/review_q5.md
  - scratch/measure_ws2.py
  - scratch/inventory_legacy.py
tests:
  - scripts/test_build_site_data.py
  - scratch/mutation_test.py
-->

---
### Requirement: Absent Election Types Are Marked Rather Than Zero-Filled
Where an election type did not exist in a term, the generated constant SHALL carry `null` for that
(type, term) pair rather than a zero-valued record, and the site SHALL render it as absent rather
than as a zero.

#### Scenario: A type absent from a term
- **WHEN** the site renders indigenous district chief (D2) figures for 1998, a term in which that election did not exist
- **THEN** the constant SHALL hold `null` for that pair, and the rendering SHALL leave the line chart
  without a plotted point and SHALL write 「無此選舉」 or 「—」 in cross-term tables, so that
  "did not exist" is distinguishable from "zero seats"

#### Scenario: A type present but with no winners
- **WHEN** an election type exists in a term but no candidate is elected under the authoritative field
- **THEN** the constant SHALL hold a record with `seats` of `0` and `perSeat` of `null`, because
  "zero seats" and "did not exist" are different facts and only the former is a measured zero

<!-- @trace
source: update-site-to-nine-terms
updated: 2026-08-20
code:
  - scratch/measure_2005.py
  - scratch/verify_strip.py
  - scratch/measure_2005e.py
  - scratch/review_q6.md
  - scratch/probe5.py
  - scratch/probe_districts2.py
  - scratch/inventory_legacy.json
  - scratch/zip_names.json
  - scratch/review_question.md
  - scripts/build_site_data.py
  - docs/roster.html
  - scratch/measure_2005_towns.py
  - scratch/measure_2005g.py
  - scratch/chk_cw.py
  - HANDOFF.md
  - scratch/review_q4.md
  - scratch/review_q3.md
  - scratch/verify_identity.py
  - scratch/verify_33.py
  - docs/index.html
  - scratch/build_1998_2002_crosswalk.py
  - scratch/strip_experiment.py
  - scratch/baseline/summary.csv
  - scratch/verify_crosswalk.py
  - scratch/measure_auth_existing.py
  - scratch/verify_11.py
  - scratch/gen_anomalies.py
  - scratch/list_zip.py
  - scratch/measure_2005d.py
  - scratch/probe3.py
  - scratch/probe4.py
  - scratch/verify_pop.py
  - scratch/measure_pop2.py
  - scratch/measure_trunc.py
  - scratch/mutation_test_site_data.py
  - CLAUDE.md
  - scratch/gen_expected.py
  - scratch/probe7.py
  - scratch/probe_anomalies.py
  - scratch/probe2.py
  - scratch/verify_21c.py
  - scratch/chk1998t2.py
  - scratch/measure_2005c.py
  - AGENTS.md
  - scratch/measure_town_codes.py
  - scratch/gen_town_anom.py
  - scratch/measure_whitespace.py
  - scratch/verify_review.py
  - README.md
  - scratch/verify_21.py
  - .spectra.yaml
  - scratch/verify_auth.py
  - scratch/probe6.py
  - scratch/probe_1994.py
  - scratch/probe_legacy_build.py
  - scratch/dryrun_manifest.py
  - scratch/probe_districts.py
  - scratch/measure_2005f.py
  - scratch/measure_town_feasible.py
  - scratch/expected.txt
  - scratch/verify_claims.py
  - scratch/verify_pop2.py
  - scratch/measure_2005b.py
  - scratch/review_q2.md
  - scratch/measure_pop.py
  - GEMINI.md
  - scratch/review_q7.md
  - scratch/add_defect7.py
  - scratch/baseline/candidates.csv
  - scratch/add_legacy_sources.py
  - scratch/baseline/votes.csv
  - scratch/verify_32.py
  - scratch/review_q5.md
  - scratch/measure_ws2.py
  - scratch/inventory_legacy.py
tests:
  - scripts/test_build_site_data.py
  - scratch/mutation_test.py
-->

---
### Requirement: Party Buckets Are Keyed By Source Identity
The generator SHALL assign each candidate to a chart bucket using a named lookup table keyed by the
pair `(政黨代號, 政黨名稱)` taken from the source row, not by party name alone and not by party code
alone. Identities absent from the table SHALL fall into the residual bucket.

Both single-field keys are known to be wrong for this dataset: the same party appears under two codes
across eras (民主進步黨 is `2` before 2009 and `16` from 2009), and the same concept appears under two
names across eras (independents are `99`/「無」 before 2009 and `999`/「無黨籍及未經政黨推薦」 from 2009).

#### Scenario: The same concept under two source encodings
- **WHEN** the generator buckets a 1998 candidate whose source row carries code `99` and name 「無」
- **THEN** that candidate SHALL be counted in the same bucket as a 2018 candidate carrying code `999`
  and name 「無黨籍及未經政黨推薦」

#### Scenario: The same party under two source codes
- **WHEN** the generator buckets a 2002 candidate carrying code `2` and name 「民主進步黨」
- **THEN** that candidate SHALL be counted in the same bucket as a 2018 candidate carrying code `16`
  and the same name

#### Scenario: One code reused for two names
- **WHEN** two source rows share a party code but carry different party names, and neither pair is
  listed in the lookup table
- **THEN** the generator SHALL NOT merge them on the strength of the shared code, and both SHALL fall
  into the residual bucket, so that a recycled code cannot silently misattribute one party's results
  to another


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
### Requirement: The Independent Bucket Is Non-Empty In Every Term
The test suite SHALL assert that the independent bucket has a non-zero candidate count in every term
the dataset covers. This is a named domain claim about this dataset, not a general rule that every
bucket is non-empty in every term.

No statistical threshold is used for this, because measurement showed the obvious candidates do not
work: a "largest residual member must stay under 5% of the term's candidates" rule still fails after
the defect is fixed (2002 residual is led by 親民黨 at 28 of 164, 17.1%), and a "residual members must
be smaller than named buckets" rule misfires because 民主進步黨 fielded only 3 to 7 candidates per term
before 2009.

#### Scenario: A bucket silently emptied by encoding drift
- **WHEN** the lookup table loses the entry that maps a term's encoding of independents
- **THEN** the assertion SHALL fail for that term, naming the term and the bucket


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
### Requirement: Bucket Membership Has A Single Source
Every page that colours or groups candidates by bucket SHALL derive that grouping from the same
lookup table, emitted by the generator into the page. No page SHALL carry a hand-maintained copy of
the bucket membership.

#### Scenario: The roster page groups by bucket
- **WHEN** the roster page assigns a colour slot to a candidate's party badge
- **THEN** it SHALL use a mapping emitted by the generator, so that a change to the lookup table
  reaches every page without a second hand edit

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
### Requirement: Constant-To-Long-Table Consistency Is Enforced, Not Merely Checkable
The comparison between the embedded site constants and the long tables SHALL be executed by the test suite, not left to a command someone remembers to run. A difference that is not in the named-and-explained list SHALL fail the suite.

#### Scenario: The bucketing logic changes but the site is not regenerated
- **WHEN** a change to party identity mapping, seat attribution, or any other derivation alters a value the site already publishes
- **THEN** the test suite SHALL fail naming the differing keys, so the site cannot stay on stale figures while the dataset moves on

##### Example: the drift this would have caught on the day it appeared

| Key | Site constant | Long tables | Consequence if unnoticed |
| --- | ---: | ---: | --- |
| `T2.2005.party.無黨籍[0]` | 0 | 7 | seven seats attributed to 「其他各政黨」 |
| `T3.2005.party.無黨籍[0]` | 0 | 8 | eight seats attributed to 「其他各政黨」 |
| `T3.1998.party.其他[0]` | 4 | 1 | inflated aggregate bucket |


#### Scenario: A difference is intended
- **WHEN** the generator legitimately adds keys the site does not yet carry, such as a newly introduced field
- **THEN** those keys SHALL be listed as expected additions and SHALL NOT fail the suite, while any unlisted difference still does

##### Example: intended additions versus drift

| Difference | Listed as expected | Suite result |
| --- | --- | --- |
| new `mainSequence` field on every type | yes | passes |
| new `types` array | yes | passes |
| a seat count that changed value | no | fails, naming the key |

<!-- @trace
source: site-accessibility-baseline
updated: 2026-08-22
code:
  - scratch/gen_anomalies.py
  - scratch/inventory_legacy.json
  - scratch/measure_town_feasible.py
  - scratch/probe_1994.py
  - .spectra.yaml
  - scratch/measure_2005.py
  - scratch/review_q7.md
  - data/processed/cec-legislative-election-candidates-long.csv
  - scratch/review_q5.md
  - CLAUDE.md
  - scratch/verify_strip.py
  - data/processed/cec-legislative-election-summary-long.csv.gz
  - data/processed/cec-legislative-election-votes-long.csv.gz
  - scratch/review_q2.md
  - data/processed/legislative-validation-report.json
  - docs/schema/oracles.md
  - scratch/verify_11.py
  - scratch/measure_2005g.py
  - scratch/probe_anomalies.py
  - scratch/review_q6.md
  - scripts/palette_metrics.py
  - scratch/measure_town_codes.py
  - scratch/probe2.py
  - scripts/build_legislative_election.py
  - scratch/chk_cw.py
  - scratch/chk1998t2.py
  - scratch/measure_2005f.py
  - scratch/verify_21.py
  - docs/schema/cec-local-election.md
  - scratch/zip_names.json
  - scratch/measure_2005d.py
  - scratch/inventory_legacy.py
  - scratch/baseline/candidates.csv
  - docs/roster.html
  - data/processed/validation-report.json
  - scratch/build_1998_2002_crosswalk.py
  - scratch/probe4.py
  - scratch/baseline/summary.csv
  - scratch/list_zip.py
  - scratch/review_question.md
  - data/processed/cec-local-election-candidates-long.csv
  - scripts/build_site_data.py
  - docs/index.html
  - scratch/expected.txt
  - scratch/dryrun_manifest.py
  - docs/schema/cec-legislative-election.md
  - data/reference/cec-legislative-county-crosswalk.csv
  - docs/三屆概況.md
  - README.md
  - scratch/measure_auth_existing.py
  - scratch/probe_legacy_build.py
  - scratch/review_q4.md
  - scratch/probe7.py
  - AGENTS.md
  - scratch/verify_pop.py
  - scratch/measure_2005e.py
  - scratch/verify_review.py
  - scripts/mutate_build_legislative_election.py
  - scratch/probe5.py
  - scratch/measure_2005b.py
  - scratch/verify_21c.py
  - scratch/verify_crosswalk.py
  - scratch/verify_identity.py
  - GEMINI.md
  - scratch/measure_pop.py
  - scratch/verify_auth.py
  - scratch/probe_districts.py
  - HANDOFF.md
  - scratch/add_legacy_sources.py
  - scratch/measure_2005_towns.py
  - scratch/probe_districts2.py
  - scratch/verify_32.py
  - scratch/gen_town_anom.py
  - scratch/verify_33.py
  - scratch/verify_pop2.py
  - scripts/oracles.py
  - scratch/measure_ws2.py
  - scratch/measure_trunc.py
  - scratch/baseline/votes.csv
  - scripts/mutate_build_site_data.py
  - scripts/build_local_election.py
  - scratch/measure_2005c.py
  - scratch/measure_pop2.py
  - scratch/measure_whitespace.py
  - data/sources.json
  - scratch/strip_experiment.py
  - scratch/probe6.py
  - scratch/review_q3.md
  - scratch/verify_claims.py
  - scratch/add_defect7.py
  - scratch/probe3.py
  - data/reference/cec-county-code-crosswalk-1998-2002.csv
  - scratch/gen_expected.py
  - scripts/mutate_build_local_election.py
  - data/processed/cec-county-code-crosswalk-1998-2002.csv
tests:
  - scripts/test_build_legislative_election.py
  - scripts/test_build_local_election.py
  - scripts/test_site_invariants.py
  - scripts/test_build_site_data.py
-->