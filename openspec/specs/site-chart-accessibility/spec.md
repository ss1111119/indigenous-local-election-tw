# site-chart-accessibility Specification

## Purpose

The published charts carry data in color: which series a bar belongs to, which
party a slice represents. Color is therefore not decoration here — it is the
encoding, and a reader who cannot separate two hues cannot read the number.

This capability governs how that encoding is kept legible. It covers the four
ways it silently fails: adjacent series that are distinguishable to normal
vision but collapse under protan or deutan simulation; labels drawn inside a
mark against a fill they were never measured against; values omitted from marks
too small to hold them and reachable only by hovering, which excludes keyboard,
screen reader, print, and forced-colors readers; and a dark theme derived by
inverting the light one rather than stepped and measured on its own surface.

The standing rule is that color separation is a measured quantity, not a design
opinion. A palette is admissible because its pairwise distances were computed
and recorded, in both themes and under both simulations — never because it looks
distinct on the author's screen. Where a threshold is claimed, the measurement
that establishes it SHALL be in the repository and re-runnable, so a later
palette edit that quietly crosses the line turns a check red instead of shipping.

## Requirements

### Requirement: Categorical Colors Are Measured Against Each Other
Where a chart encodes identity by color, every adjacent pair in the series order SHALL be separated by at least ΔE 15 (OKLab ×100) under normal vision and at least ΔE 8 under protan and deutan simulation, in both the light and the dark theme, each measured against that theme's own chart surface. The dark theme SHALL be stepped and measured separately, never derived by inverting the light theme.

#### Scenario: A series pair falls below the normal-vision floor
- **WHEN** two adjacent series are separated by less than ΔE 15 under normal vision
- **THEN** the palette SHALL be re-stepped before shipping, because readers with full color vision cannot tell the pair apart and no secondary encoding excuses this case

##### Example: the pair that failed, measured before and after

| Theme | Pair | Normal ΔE | Protan/Deutan ΔE | Verdict |
| --- | --- | ---: | ---: | --- |
| light | `#1baf7a` ↔ `#9BA0A5` | 14.5 | 5.5 | fails both floors |
| dark | `#199e70` ↔ `#7C838A` | 12.9 | 4.5 | fails both floors |
| light | `#1baf7a` ↔ `#ADB3B9` | 16.9 | 9.0 | passes |
| dark | `#1da77a` ↔ `#6A7178` | 16.6 | 9.7 | passes |


#### Scenario: A hue carries real-world meaning
- **WHEN** a series color is fixed by outside convention, such as a political party's color
- **THEN** the adjustment SHALL be made on a series whose color carries no such meaning, such as an "other" aggregate bucket, and the conventional hue SHALL be left in place

##### Example: which series may move

| Series | Color fixed by convention? | Re-stepping allowed |
| --- | --- | --- |
| 中國國民黨 (blue) | yes | no |
| 民主進步黨 (green) | yes | hue-preserving nudge only |
| 無黨籍及未經政黨推薦 (orange) | weakly | avoid |
| 其他各政黨 (gray) | no — an aggregate bucket | yes, this is where the fix goes |

#### Scenario: A conventional color is borrowed by a bucket it does not belong to
- **WHEN** a series is an aggregate or residual bucket rather than the entity whose color is conventional
- **THEN** it SHALL NOT be given that entity's conventional color, so that an "other parties" bucket is never rendered in a party's own blue, green, or orange, however convenient the separation would be

##### Example: allowed and forbidden assignments for the residual bucket

| Candidate color for 其他各政黨 | Allowed | Why |
| --- | --- | --- |
| gray `#ADB3B9` | yes | no party claims it |
| a fourth hue, e.g. purple | yes | not conventional for any party here |
| green | no | reads as 民主進步黨 |
| blue | no | reads as 中國國民黨 |
| orange | no | conventional for 親民黨; forbidden by this clause whether or not another bucket currently uses it |


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

---
### Requirement: Labels Drawn Inside A Mark Meet 4.5:1 Against That Mark
Text placed inside a colored mark SHALL reach at least 4.5:1 against the fill it sits on, in both themes. The ink SHALL be chosen per series from its own fill, not applied uniformly across series.

#### Scenario: White text fails on a light fill
- **WHEN** white text on a series fill measures below 4.5:1
- **THEN** that series SHALL switch to a dark ink rather than the fill being lightened or darkened, and where the fill carries conventional meaning both black and white SHALL be tried before the fill is touched at all

##### Example: the KMT blue case, where changing the fill was the wrong fix

| Ink on `#2a78d6` | Contrast | Outcome |
| --- | ---: | --- |
| `#fff` | 4.42 | below 4.5 — the reason the fill was wrongly re-stepped to `#2670cc` |
| `#16181A` (page ink) | 4.03 | below 4.5 |
| `#000` | 4.76 | passes — so the conventional fill never needed to move |


#### Scenario: A new series is added
- **WHEN** a series is added or a fill is re-stepped
- **THEN** the ink for that series SHALL be recomputed, because a fill change can flip which ink passes

##### Example: the same bucket takes opposite inks in the two themes

| Theme | 其他 fill | Ink | Contrast |
| --- | --- | --- | ---: |
| light | `#ADB3B9` | `#16181A` | 8.41 |
| dark | `#6A7178` | `#fff` | 4.95 |


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

---
### Requirement: Color-Encoded Data Has A Tabular Equivalent
Where a chart omits labels on marks too small to hold them, the omitted values SHALL be reachable without color and without pointer hover. A tooltip alone SHALL NOT satisfy this, because it does not exist for keyboard users, screen readers, print, or forced-colors mode.

#### Scenario: A mark is too narrow to label
- **WHEN** a segment is too narrow for its value to be drawn inside it
- **THEN** the value SHALL appear in a table on the same page, and the chart SHALL reference that table so assistive technology can find it

##### Example: values only the table carries

| Type | Term | Segment omitted from the chart | Value in the table |
| --- | --- | --- | ---: |
| T2 | 2002 | 民主進步黨 | 1 |
| T3 | 1998 | 其他各政黨 | 1 |
| T-COMBO | 1994 | 無黨籍及未經政黨推薦 | 1 |


#### Scenario: Building the tabular equivalent
- **WHEN** the table is generated
- **THEN** it SHALL be derived from the same embedded constant the chart reads, never from a separately maintained copy

##### Example: one source, two renderings

| Consumer | Reads | Result for T3 2005 |
| --- | --- | --- |
| stacked bar | `DATA` | 20 / 8 / 0 / 2 |
| `#t-party` table | the same `DATA` | 20 / 8 / 0 / 2, total 30 |


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

---
### Requirement: Print And Forced Colors Do Not Erase The Encoding
The data encoding SHALL survive printing and forced-colors mode.

#### Scenario: Printing while the dark theme is active
- **WHEN** the page is printed with the dark theme in effect
- **THEN** the light palette SHALL be applied for print and fills SHALL be preserved, so that light text is never printed onto white paper and the bars are never dropped as background decoration

##### Example: what the dark theme would otherwise print as

| Token | Dark theme on screen | Under `@media print` |
| --- | --- | --- |
| `--paper` | `#16181A` | `#fff` |
| `--lab4` (ink inside 其他) | `#fff` — invisible on paper | `#16181A` |
| bar fills | dropped as background by ink-saving | kept via `print-color-adjust:exact` |


#### Scenario: Forced-colors mode is active
- **WHEN** the operating system forces its own colors
- **THEN** marks whose color is data SHALL keep their own colors rather than collapsing to a single system color, while the surrounding interface follows the system

##### Example: scope of the opt-out

| Element | `forced-color-adjust` | Why |
| --- | --- | --- |
| `svg` (bars, gender squares) | `none` | the fill is the datum |
| `.sw` (legend swatch) | `none` | must match the bar it names |
| `.pty` (roster party badge) | `none` | the badge color is the party |
| everything else | inherited (system wins) | it is interface, not data |


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

---
### Requirement: Pages Declare Encoding, Language, And Viewport
Each published page SHALL declare its character encoding, document language, and viewport in the document itself, not rely on headers supplied by the host.

#### Scenario: The file is opened outside the host
- **WHEN** a reader saves the page and opens it from the local filesystem
- **THEN** the text SHALL render correctly, because the site's stated design is a single self-contained file that works offline

##### Example: the failure this prevents

| Delivery | Charset source | Result |
| --- | --- | --- |
| GitHub Pages | HTTP header sets utf-8 | correct |
| saved file opened locally | none — falls back to the OS locale (cp950 here) | every Chinese character mojibake |
| local server without charset header | none | same mojibake |


#### Scenario: The page is opened on a phone
- **WHEN** the page is opened on a narrow viewport
- **THEN** it SHALL lay out to the device width rather than rendering at desktop width and scaling down

##### Example: with and without the declaration

| `meta viewport` | Layout width on a 390px phone | Legibility |
| --- | --- | --- |
| absent | ~980px, then scaled to fit | text far below readable size |
| `width=device-width, initial-scale=1` | 390px | panels reflow, text at intended size |


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

---
### Requirement: Color Verification Is Recorded, Not Asserted
Any claim that a palette is readable SHALL be recorded with the tool used, the color-vision-deficiency types simulated, the threshold applied, and the measured values. A bare statement that a palette was "checked" SHALL NOT satisfy this requirement.

A record SHALL be reproducible by a later reader: it SHALL name the command that produced it, and the command SHALL be one that can fail. Where a palette grows a new series, the record SHALL cover every pair of the enlarged palette rather than only the pairs the previous record covered.

#### Scenario: A palette or ink is changed
- **WHEN** a series fill or a label ink is added or re-stepped
- **THEN** the record SHALL name the tool, the simulated deficiency types, the threshold, and the resulting numbers for every pair or combination affected, so a later reader can tell a measurement from an opinion

##### Example: the record this change carries

| Field | Value |
| --- | --- |
| tool | `scripts/palette_metrics.py` in this repo (OKLab ΔE ×100; Machado 2009 CVD matrices on linear RGB) for separation; WCAG relative-luminance contrast for inks. Calibrated against an external validator to ≤0.04 for normal vision and ≤0.03 for protan/deutan |
| CVD types simulated | protan, deutan (in-repo tool). tritan measured once with the external validator (9.6 light / 15.1 dark) and **not reproducible in-repo** — see `palette_metrics.py` docstring |
| thresholds | ΔE 15 normal vision / ΔE 8 CVD for adjacent pairs; 4.5:1 for text inside a mark |
| measured | separation 16.9 (light) / 16.6 (dark), CVD 9.0 / 9.7; eight ink-on-fill combinations 4.58–8.41 |

##### Example: the six-series legislative palette

| Field | Value |
| --- | --- |
| why a second palette | the legislative page needs five party buckets, not three: 親民黨 took 27.7% in 2001 and 無黨團結聯盟 26.0% in 2004, and the local-office three-bucket set drops both into 其他 |
| pairs measured | all 15 pairs, not the 5 adjacent ones — a legend that wraps on a narrow screen puts non-adjacent series next to each other |
| light fills | `#2a78d6 #1baf7a #ee7700 #c0397a #3A4046 #ADB3B9`; worst normal ΔE 16.9, worst CVD ΔE 9.0 |
| dark fills | `#3987e5 #1da77a #ee7700 #cc2244 #C9CED3 #6A7178`; worst normal ΔE 16.6, worst CVD ΔE 9.3 |
| inks inside marks | light 4.76–10.49, dark 4.89–11.23 (floor 4.5:1) |
| record | `docs/schema/palette-legislative.md`, holding the unedited output of both commands |
| the measurement can fail | 親民黨 `#ee7700`→`#22b884` gives 2 failing pairs, exit 1; 無黨團結聯盟's ink `#fff`→`#16181A` gives 3.48:1, exit 1; unmutated baseline exits 0 |

#### Scenario: Only a claim is offered
- **WHEN** a change states that colors were verified but names no tool, no simulation, and no numbers
- **THEN** the claim SHALL be treated as unverified, because "checked" is not reproducible

##### Example: what does and does not count as a record

| Statement | Counts |
| --- | --- |
| "配色已檢查，色盲下可辨識" | no — no tool, no type, no number |
| "palette_metrics.py，protan/deutan，門檻 ΔE 8，實測 9.0／9.7" | yes |

#### Scenario: The recorded numbers are all passes
- **WHEN** a record shows every measured pair above the threshold
- **THEN** the record SHALL also show that the measurement is capable of reporting a failure, by naming a mutation of the palette that the same command rejects, because a check that cannot fail records nothing

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
### Requirement: Hover-Only Content Is Also Reachable By Keyboard
Any information a chart reveals only on pointer hover SHALL be reachable by keyboard focus as well. A tooltip that appears on `pointerenter` and disappears on `pointerleave` SHALL appear on `focus` and disappear on `blur` using the same content and the same trigger element, not a separate keyboard-only implementation.

#### Scenario: A chart data point is tabbed to
- **WHEN** a keyboard user tabs to a chart's hit target
- **THEN** the same tooltip content that pointer hover would show SHALL appear, and it SHALL disappear on blur

#### Scenario: Keyboard and pointer paths diverge
- **WHEN** a tooltip's content or trigger condition is implemented separately for keyboard than for pointer
- **THEN** that duplication SHALL be treated as a defect, because a rule implemented twice drifts


<!-- @trace
source: site-chart-interactivity
updated: 2026-08-24
code:
  - scratch/review_q4.md
  - scratch/verify_21c.py
  - scratch/verify_32.py
  - scratch/verify_review.py
  - scratch/expected.txt
  - scratch/measure_2005c.py
  - scratch/measure_pop2.py
  - scratch/probe4.py
  - scratch/review_q5.md
  - scratch/verify_strip.py
  - scratch/measure_2005.py
  - scratch/measure_2005_towns.py
  - scratch/review_q7.md
  - scratch/measure_2005b.py
  - scratch/build_1998_2002_crosswalk.py
  - scratch/zip_names.json
  - scratch/baseline/candidates.csv
  - scratch/measure_2005f.py
  - scratch/probe_anomalies.py
  - scratch/probe_districts.py
  - scratch/gen_anomalies.py
  - CLAUDE.md
  - scratch/probe6.py
  - scratch/inventory_legacy.json
  - scratch/measure_whitespace.py
  - scratch/verify_auth.py
  - scratch/measure_pop.py
  - scratch/verify_claims.py
  - docs/index.html
  - scratch/verify_pop2.py
  - docs/legislative.html
  - scratch/inventory_legacy.py
  - scratch/verify_identity.py
  - scratch/verify_21.py
  - .spectra.yaml
  - scripts/mutate_build_site_data.py
  - docs/en/legislative.html
  - scratch/measure_2005g.py
  - AGENTS.md
  - scratch/list_zip.py
  - scratch/review_q6.md
  - scratch/measure_ws2.py
  - scratch/measure_auth_existing.py
  - scratch/add_legacy_sources.py
  - scratch/dryrun_manifest.py
  - scratch/verify_11.py
  - scratch/verify_crosswalk.py
  - GEMINI.md
  - scratch/add_defect7.py
  - scratch/measure_town_codes.py
  - scratch/gen_town_anom.py
  - scratch/probe7.py
  - scratch/chk_cw.py
  - scratch/measure_2005e.py
  - scratch/measure_2005d.py
  - scratch/strip_experiment.py
  - scratch/probe_legacy_build.py
  - HANDOFF.md
  - scratch/probe3.py
  - scratch/review_q2.md
  - scratch/baseline/summary.csv
  - scratch/gen_expected.py
  - scratch/verify_pop.py
  - docs/en/index.html
  - scratch/measure_trunc.py
  - scratch/review_q3.md
  - scratch/review_question.md
  - scratch/baseline/votes.csv
  - scratch/probe_1994.py
  - scratch/verify_33.py
  - scratch/probe5.py
  - scratch/probe2.py
  - scratch/chk1998t2.py
  - scratch/measure_town_feasible.py
  - scratch/probe_districts2.py
tests:
  - scripts/test_build_site_data.py
-->

---
### Requirement: A Chart Point Representing A Term And Category May Link To Its Detail Page
Where a page presents an aggregate figure for one (term, election type) pair, and another page on the site presents the record-level detail for that same pair, the aggregate's chart SHALL let a reader navigate from the point to that detail — reachable by pointer click, keyboard activation, and touch alike — using a native link element rather than a script-driven redirect.

This linking SHALL NOT be added where no corresponding detail page exists for the dataset being charted.

#### Scenario: A turnout or seat chart point is activated
- **WHEN** a reader clicks, taps, or presses Enter on a chart point for a given term and election type
- **THEN** navigation SHALL go to the detail page filtered to that same term and election type, using the page's existing addressing scheme rather than a new one

#### Scenario: A dataset has no detail page
- **WHEN** a chart presents a dataset for which the site has no record-level detail page
- **THEN** its points SHALL remain keyboard- and pointer-accessible for their tooltip content, but SHALL NOT be turned into links to an unrelated or non-existent page

#### Scenario: The link target is native, not scripted
- **WHEN** a chart point becomes navigable
- **THEN** it SHALL be implemented as an anchor element a browser handles natively — opening in a new tab, copying the link, and screen-reader link semantics SHALL all work without additional script

<!-- @trace
source: site-chart-interactivity
updated: 2026-08-24
code:
  - scratch/review_q4.md
  - scratch/verify_21c.py
  - scratch/verify_32.py
  - scratch/verify_review.py
  - scratch/expected.txt
  - scratch/measure_2005c.py
  - scratch/measure_pop2.py
  - scratch/probe4.py
  - scratch/review_q5.md
  - scratch/verify_strip.py
  - scratch/measure_2005.py
  - scratch/measure_2005_towns.py
  - scratch/review_q7.md
  - scratch/measure_2005b.py
  - scratch/build_1998_2002_crosswalk.py
  - scratch/zip_names.json
  - scratch/baseline/candidates.csv
  - scratch/measure_2005f.py
  - scratch/probe_anomalies.py
  - scratch/probe_districts.py
  - scratch/gen_anomalies.py
  - CLAUDE.md
  - scratch/probe6.py
  - scratch/inventory_legacy.json
  - scratch/measure_whitespace.py
  - scratch/verify_auth.py
  - scratch/measure_pop.py
  - scratch/verify_claims.py
  - docs/index.html
  - scratch/verify_pop2.py
  - docs/legislative.html
  - scratch/inventory_legacy.py
  - scratch/verify_identity.py
  - scratch/verify_21.py
  - .spectra.yaml
  - scripts/mutate_build_site_data.py
  - docs/en/legislative.html
  - scratch/measure_2005g.py
  - AGENTS.md
  - scratch/list_zip.py
  - scratch/review_q6.md
  - scratch/measure_ws2.py
  - scratch/measure_auth_existing.py
  - scratch/add_legacy_sources.py
  - scratch/dryrun_manifest.py
  - scratch/verify_11.py
  - scratch/verify_crosswalk.py
  - GEMINI.md
  - scratch/add_defect7.py
  - scratch/measure_town_codes.py
  - scratch/gen_town_anom.py
  - scratch/probe7.py
  - scratch/chk_cw.py
  - scratch/measure_2005e.py
  - scratch/measure_2005d.py
  - scratch/strip_experiment.py
  - scratch/probe_legacy_build.py
  - HANDOFF.md
  - scratch/probe3.py
  - scratch/review_q2.md
  - scratch/baseline/summary.csv
  - scratch/gen_expected.py
  - scratch/verify_pop.py
  - docs/en/index.html
  - scratch/measure_trunc.py
  - scratch/review_q3.md
  - scratch/review_question.md
  - scratch/baseline/votes.csv
  - scratch/probe_1994.py
  - scratch/verify_33.py
  - scratch/probe5.py
  - scratch/probe2.py
  - scratch/chk1998t2.py
  - scratch/measure_town_feasible.py
  - scratch/probe_districts2.py
tests:
  - scripts/test_build_site_data.py
-->