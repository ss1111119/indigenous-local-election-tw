# bounded-estimates Specification

## Purpose

Some questions this project is asked cannot be answered by
counting. Party preference within one group, read from ballots that the whole
electorate casts together, is one of them. This capability governs what the
project is allowed to publish when it must infer rather than observe.

The rule is that an inferred figure ships with an interval that arithmetic
alone establishes, and that the interval is recomputed at build time as a
guard rather than recorded as a footnote. An interval derived without
statistical assumptions can be checked; a point estimate from a fitted model
cannot, and its failure mode is silent — the number stays precise-looking long
after it stops meaning anything.

Two things follow. Inferred figures never share a table or a column-naming
convention with counted ones, and every inferred row carries the scope that
produced it, so the number cannot be quoted apart from its coverage. And
coverage is stated before the figure, not after: where the strata that support
tight bounds cover a minority of the population and are geographically
concentrated, an interval that is arithmetically certain about those strata
would otherwise be read as certainty about everyone.

## Requirements

### Requirement: An Estimate Ships With Bounds That Arithmetic Alone Establishes
Where the project publishes a figure it did not observe — a group's behaviour inferred from aggregate data — that figure SHALL ship with an interval derived by arithmetic alone, not by a statistical model. For a stratum with observed share `y` and indigenous share of voters `q`, the indigenous share necessarily lies in `[max(0, (y - (1 - q)) / q), min(1, y / q)]`. This holds without any assumption about how the two groups behave.

The interval is not decoration. It SHALL be recomputed at build time and SHALL act as a guard: an estimate that falls outside its own bounds means the weight or the formula is wrong, and the build SHALL abort.

#### Scenario: Bounds contain the observation
- **WHEN** bounds are computed for a stratum
- **THEN** the relation `0 <= lower <= observed <= upper <= 1` SHALL hold, and a violation SHALL abort the build

##### Example: the 2024 highest-density stratum

| Party | Observed | Indigenous share necessarily in | Width |
| --- | ---: | --- | ---: |
| 中國國民黨 | 68.10% | [67.13%, 70.17%] | 3.0pp |
| 台灣民眾黨 | 14.09% | [11.47%, 14.51%] | 3.0pp |
| 民主進步黨 | 12.09% | [9.42%, 12.46%] | 3.0pp |

Stratum: 90 polling stations at ≥95% indigenous electors, 32,635 valid party
votes, q = 0.9705.

#### Scenario: A model extrapolation is not presented as an observation
- **WHEN** a figure is produced by extrapolating a fitted relationship to a value outside the range the data supports
- **THEN** it SHALL be labelled as a model prediction under a stated specification, and SHALL NOT be described as an observed or measured group behaviour

#### Scenario: Bounds are too wide to be informative
- **WHEN** a stratum's bounds span most of the unit interval, as happens where the group is a small minority of voters
- **THEN** the bounds SHALL still be published rather than replaced by a point estimate, because a wide interval reports what the data can support and a point estimate does not


<!-- @trace
source: add-party-list-votes
updated: 2026-08-23
code:
  - scratch/review_q7.md
  - scratch/verify_21.py
  - scratch/verify_32.py
  - scratch/measure_2005b.py
  - scratch/list_zip.py
  - scratch/measure_2005g.py
  - scratch/gen_anomalies.py
  - scratch/baseline/candidates.csv
  - scratch/measure_whitespace.py
  - scratch/verify_pop.py
  - scratch/inventory_legacy.py
  - scratch/verify_identity.py
  - HANDOFF.md
  - scratch/measure_2005c.py
  - data/sources.json
  - scratch/measure_ws2.py
  - scratch/chk1998t2.py
  - scratch/measure_town_codes.py
  - scratch/probe7.py
  - README.md
  - scratch/probe5.py
  - data/processed/cec-party-list-votes-long.csv.gz
  - scratch/baseline/votes.csv
  - scripts/build_party_list_election.py
  - scratch/add_legacy_sources.py
  - docs/schema/cec-party-list-election.md
  - scratch/review_q3.md
  - scratch/verify_33.py
  - scratch/verify_pop2.py
  - scratch/dryrun_manifest.py
  - scratch/probe_districts2.py
  - scratch/verify_strip.py
  - scripts/oracles.py
  - scratch/review_q4.md
  - scratch/measure_2005f.py
  - scratch/verify_review.py
  - scratch/review_question.md
  - scratch/strip_experiment.py
  - scratch/measure_town_feasible.py
  - scratch/measure_pop.py
  - scratch/measure_pop2.py
  - scratch/build_1998_2002_crosswalk.py
  - scratch/probe2.py
  - scratch/add_defect7.py
  - GEMINI.md
  - scratch/verify_11.py
  - scripts/mutate_build_party_list_election.py
  - scratch/verify_21c.py
  - scratch/measure_auth_existing.py
  - scratch/probe_1994.py
  - scratch/review_q2.md
  - scratch/gen_town_anom.py
  - scratch/measure_2005.py
  - scratch/verify_auth.py
  - scratch/measure_trunc.py
  - data/processed/indigenous-party-preference-bounds.csv
  - scratch/chk_cw.py
  - scratch/measure_2005e.py
  - scratch/measure_2005_towns.py
  - scratch/probe_legacy_build.py
  - scratch/review_q6.md
  - scratch/baseline/summary.csv
  - scratch/probe_districts.py
  - scratch/zip_names.json
  - .spectra.yaml
  - AGENTS.md
  - scratch/review_q5.md
  - scratch/expected.txt
  - scratch/probe4.py
  - scratch/probe_anomalies.py
  - scratch/verify_crosswalk.py
  - scratch/inventory_legacy.json
  - scratch/verify_claims.py
  - scratch/measure_2005d.py
  - scratch/probe3.py
  - data/processed/cec-party-list-summary-long.csv.gz
  - CLAUDE.md
  - scratch/gen_expected.py
  - scratch/probe6.py
  - data/processed/cec-party-list-seats.csv
tests:
  - scripts/test_build_party_list_election.py
-->

---
### Requirement: The Weight Is The Share Of Voters, Not The Share Of Registered Electors
The decomposition that the bounds rest on is weighted by each group's share of the votes actually cast, not its share of the registered electorate. Those two quantities differ whenever the groups turn out at different rates. The build SHALL compute both and SHALL use the share of voters in the bounds.

Both SHALL be published, so a reader can see how far apart they are rather than being told they are close.

#### Scenario: The two shares diverge
- **WHEN** a stratum's share of registered electors differs from its share of voters
- **THEN** the bounds SHALL be computed from the share of voters, and both figures SHALL appear in the output

#### Scenario: A small divergence is not treated as licence to interchange them
- **WHEN** the two shares are found to be close in the strata currently published
- **THEN** that SHALL NOT justify using the electorate share in the bounds, because a bound computed from the wrong weight is still shaped like a bound


<!-- @trace
source: add-party-list-votes
updated: 2026-08-23
code:
  - scratch/review_q7.md
  - scratch/verify_21.py
  - scratch/verify_32.py
  - scratch/measure_2005b.py
  - scratch/list_zip.py
  - scratch/measure_2005g.py
  - scratch/gen_anomalies.py
  - scratch/baseline/candidates.csv
  - scratch/measure_whitespace.py
  - scratch/verify_pop.py
  - scratch/inventory_legacy.py
  - scratch/verify_identity.py
  - HANDOFF.md
  - scratch/measure_2005c.py
  - data/sources.json
  - scratch/measure_ws2.py
  - scratch/chk1998t2.py
  - scratch/measure_town_codes.py
  - scratch/probe7.py
  - README.md
  - scratch/probe5.py
  - data/processed/cec-party-list-votes-long.csv.gz
  - scratch/baseline/votes.csv
  - scripts/build_party_list_election.py
  - scratch/add_legacy_sources.py
  - docs/schema/cec-party-list-election.md
  - scratch/review_q3.md
  - scratch/verify_33.py
  - scratch/verify_pop2.py
  - scratch/dryrun_manifest.py
  - scratch/probe_districts2.py
  - scratch/verify_strip.py
  - scripts/oracles.py
  - scratch/review_q4.md
  - scratch/measure_2005f.py
  - scratch/verify_review.py
  - scratch/review_question.md
  - scratch/strip_experiment.py
  - scratch/measure_town_feasible.py
  - scratch/measure_pop.py
  - scratch/measure_pop2.py
  - scratch/build_1998_2002_crosswalk.py
  - scratch/probe2.py
  - scratch/add_defect7.py
  - GEMINI.md
  - scratch/verify_11.py
  - scripts/mutate_build_party_list_election.py
  - scratch/verify_21c.py
  - scratch/measure_auth_existing.py
  - scratch/probe_1994.py
  - scratch/review_q2.md
  - scratch/gen_town_anom.py
  - scratch/measure_2005.py
  - scratch/verify_auth.py
  - scratch/measure_trunc.py
  - data/processed/indigenous-party-preference-bounds.csv
  - scratch/chk_cw.py
  - scratch/measure_2005e.py
  - scratch/measure_2005_towns.py
  - scratch/probe_legacy_build.py
  - scratch/review_q6.md
  - scratch/baseline/summary.csv
  - scratch/probe_districts.py
  - scratch/zip_names.json
  - .spectra.yaml
  - AGENTS.md
  - scratch/review_q5.md
  - scratch/expected.txt
  - scratch/probe4.py
  - scratch/probe_anomalies.py
  - scratch/verify_crosswalk.py
  - scratch/inventory_legacy.json
  - scratch/verify_claims.py
  - scratch/measure_2005d.py
  - scratch/probe3.py
  - data/processed/cec-party-list-summary-long.csv.gz
  - CLAUDE.md
  - scratch/gen_expected.py
  - scratch/probe6.py
  - data/processed/cec-party-list-seats.csv
tests:
  - scripts/test_build_party_list_election.py
-->

---
### Requirement: Estimates Are Separated From Official Figures By Table And By Column Name
Figures the project observed and figures it inferred SHALL NOT share a table, and SHALL NOT share a column-naming convention. Every inferred column SHALL carry a prefix marking it as observed-in-stratum, lower bound, or upper bound, and every row SHALL carry the scope that produced it: the threshold, the number of units, the population covered, the coverage rate, and both weights.

A consumer reading a single column SHALL NOT be able to mistake an inferred figure for an official result.

#### Scenario: A downstream consumer reads one column
- **WHEN** a consumer selects a vote-share column from a published table
- **THEN** the column name SHALL make clear whether the figure is an official count or an inferred bound

#### Scenario: Scope travels with the number
- **WHEN** an inferred figure is published
- **THEN** the same row SHALL carry the threshold and coverage that produced it, so the figure cannot be quoted without its scope


<!-- @trace
source: add-party-list-votes
updated: 2026-08-23
code:
  - scratch/review_q7.md
  - scratch/verify_21.py
  - scratch/verify_32.py
  - scratch/measure_2005b.py
  - scratch/list_zip.py
  - scratch/measure_2005g.py
  - scratch/gen_anomalies.py
  - scratch/baseline/candidates.csv
  - scratch/measure_whitespace.py
  - scratch/verify_pop.py
  - scratch/inventory_legacy.py
  - scratch/verify_identity.py
  - HANDOFF.md
  - scratch/measure_2005c.py
  - data/sources.json
  - scratch/measure_ws2.py
  - scratch/chk1998t2.py
  - scratch/measure_town_codes.py
  - scratch/probe7.py
  - README.md
  - scratch/probe5.py
  - data/processed/cec-party-list-votes-long.csv.gz
  - scratch/baseline/votes.csv
  - scripts/build_party_list_election.py
  - scratch/add_legacy_sources.py
  - docs/schema/cec-party-list-election.md
  - scratch/review_q3.md
  - scratch/verify_33.py
  - scratch/verify_pop2.py
  - scratch/dryrun_manifest.py
  - scratch/probe_districts2.py
  - scratch/verify_strip.py
  - scripts/oracles.py
  - scratch/review_q4.md
  - scratch/measure_2005f.py
  - scratch/verify_review.py
  - scratch/review_question.md
  - scratch/strip_experiment.py
  - scratch/measure_town_feasible.py
  - scratch/measure_pop.py
  - scratch/measure_pop2.py
  - scratch/build_1998_2002_crosswalk.py
  - scratch/probe2.py
  - scratch/add_defect7.py
  - GEMINI.md
  - scratch/verify_11.py
  - scripts/mutate_build_party_list_election.py
  - scratch/verify_21c.py
  - scratch/measure_auth_existing.py
  - scratch/probe_1994.py
  - scratch/review_q2.md
  - scratch/gen_town_anom.py
  - scratch/measure_2005.py
  - scratch/verify_auth.py
  - scratch/measure_trunc.py
  - data/processed/indigenous-party-preference-bounds.csv
  - scratch/chk_cw.py
  - scratch/measure_2005e.py
  - scratch/measure_2005_towns.py
  - scratch/probe_legacy_build.py
  - scratch/review_q6.md
  - scratch/baseline/summary.csv
  - scratch/probe_districts.py
  - scratch/zip_names.json
  - .spectra.yaml
  - AGENTS.md
  - scratch/review_q5.md
  - scratch/expected.txt
  - scratch/probe4.py
  - scratch/probe_anomalies.py
  - scratch/verify_crosswalk.py
  - scratch/inventory_legacy.json
  - scratch/verify_claims.py
  - scratch/measure_2005d.py
  - scratch/probe3.py
  - data/processed/cec-party-list-summary-long.csv.gz
  - CLAUDE.md
  - scratch/gen_expected.py
  - scratch/probe6.py
  - data/processed/cec-party-list-seats.csv
tests:
  - scripts/test_build_party_list_election.py
-->

---
### Requirement: Coverage And Its Skew Are Stated Before The Figure, Not After It
The strata that support tight bounds cover a minority of the population of interest, and they are not a random minority: they are geographically concentrated. Documentation SHALL state the coverage rate and the concentration before presenting any figure derived from those strata.

This applies wherever the figure is presented, not only in documentation. On a published page the ordering is the mechanism: the coverage rate and the nature of the subset SHALL appear before any percentage in the section that carries the figure, and the heading SHALL name the subset rather than the whole population.

Where the interval around such a figure is narrow while the coverage behind it is small, the presentation SHALL give visual weight to the coverage rather than to the interval. A narrow interval invites the reader to treat the figure as settled, and what is unsettled is not inside the interval.

A bound that is arithmetically certain about a stratum SHALL NOT be described as if it were about the whole population.

#### Scenario: Describing a stratum-derived figure
- **WHEN** a figure derived from the high-density strata is described
- **THEN** it SHALL be described as pertaining to those strata, and SHALL NOT be described as the whole group's behaviour

#### Scenario: The uncovered remainder
- **WHEN** the population outside the strata is discussed
- **THEN** the documentation SHALL state that arithmetic bounds are uninformative there, rather than implying the published interval covers them

#### Scenario: The figure appears on a page rather than in a document
- **WHEN** the figure is published on a page read by people who did not read the documentation
- **THEN** the coverage rate SHALL precede any percentage in that section, and the qualifier limiting the figure SHALL sit in the same copyable block as the figure itself

#### Scenario: Presenting more than one threshold
- **WHEN** several thresholds trade coverage against precision
- **THEN** they SHALL be presented together rather than one being chosen for the reader, because choosing one hides the trade-off that determines how far the figure generalises

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