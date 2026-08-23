# site-multi-dataset Specification

## Purpose

The site presents three datasets: local public offices, indigenous
legislators, and a bounded estimate of party-list preference. They do not share
an electorate, a constituency, a term, or a coverage rate. A reader who arrives
on one page has no way to know that, and a figure lifted off a page carries
none of it.

This capability governs what the site must do about that. Its rules are
structural rather than editorial: the separation between datasets is a separate
page, not a caption; a bucket set belongs to one dataset and is declared there,
because a set shared across datasets silently drops whichever parties matter in
only one of them; and a qualifier sits in the same copyable block as the figure
it limits, because a footnote does not survive being copied.

The failure this exists to prevent is not a wrong number. Every number involved
is correct for its own dataset. The failure is a reader — or a newsroom —
combining two of them into a claim that neither supports, with nothing on the
page having gone visibly wrong.

## Requirements

### Requirement: Datasets With Different Populations Are Presented Apart
The site carries data from more than one election, and those elections do not
share an electorate, a constituency, or an office. Records from different
populations SHALL NOT appear in the same list, the same series, or the same
chart, and the separation SHALL be structural — a separate page or section —
rather than a flag on entries that otherwise sit side by side.

A boolean marker distinguishing comparable from non-comparable entries within
one dataset has already proved too weak once. Where two datasets differ in
what is being elected, the reader SHALL NOT have to notice a flag to avoid
comparing them.

#### Scenario: A cross-term line is drawn
- **WHEN** a chart plots a measure across terms
- **THEN** every series on it SHALL come from a single dataset, and a series
  from another dataset SHALL NOT be added to it under any marker

#### Scenario: A reader arrives on a page
- **WHEN** any page of the site loads
- **THEN** it SHALL state at the top which dataset it presents and which
  populations that dataset does not cover

#### Scenario: A combined view is requested
- **WHEN** a view merging datasets would be convenient
- **THEN** it SHALL NOT be provided, because the convenience is precisely what
  makes the comparison look legitimate


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
### Requirement: Bucket Sets Are Declared Per Dataset And Are Not Shared
Grouping parties into display buckets is a per-dataset decision, because the
parties that matter differ between elections. A bucket set that is adequate for
one dataset SHALL NOT be reused for another without checking what it discards.

Each bucket set SHALL have a single declared source that both the generator and
the page read, and the sets SHALL be verified to differ where the underlying
data differs.

#### Scenario: A party is significant in one dataset but not another
- **WHEN** a party takes a substantial share in one dataset and a negligible
  share in another
- **THEN** the dataset where it matters SHALL give it its own bucket, and
  folding it into a residual bucket there SHALL be treated as a defect

#### Scenario: Two bucket sets are silently unified
- **WHEN** the bucket sets for two datasets are made identical
- **THEN** a check SHALL fail, because unification hides whichever parties only
  mattered in one of them

#### Scenario: Bucket membership is duplicated
- **WHEN** bucket membership appears in more than one place
- **THEN** that SHALL be treated as a defect, because the copies will diverge
  and the page will disagree with the data it was generated from


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
### Requirement: A Page Built For General Readers Resists Extraction Of A Figure From Its Scope
Where the site presents a figure whose validity depends on a stated scope, the
scope SHALL travel with the figure in the same copyable block, and the page
SHALL be ordered so that the scope is read first.

An audience that quotes a page does not quote its footnotes. Ordering and
adjacency are the mechanism; a caveat placed after the number is not.

#### Scenario: Coverage precedes the figure
- **WHEN** a section presents a figure derived from a subset of the population
- **THEN** the coverage rate and the nature of the subset SHALL appear before
  any percentage in that section

#### Scenario: A heading names the population
- **WHEN** a heading introduces such a figure
- **THEN** it SHALL name the subset the figure describes, and SHALL NOT name
  the whole population

#### Scenario: A figure is copied out of the page
- **WHEN** a reader selects and copies the block containing the figure
- **THEN** the copied text SHALL include the qualifier that limits it

#### Scenario: The interval is narrow but the coverage is small
- **WHEN** an interval around a figure is narrow while the coverage behind it is
  a small share of the population
- **THEN** the presentation SHALL give visual weight to the coverage rather than
  to the interval, because the interval understates what is unknown

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