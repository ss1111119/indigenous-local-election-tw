# election-period-publication Specification

## Purpose

An election does not change whether a figure is accurate. It changes what the
figure is used for. A gap between population share and seat share, or a party's
share in one set of polling stations, reads as description in a quiet month and
as ammunition during a campaign — and nothing on the page distinguishes the two.

This capability governs publication timing, which no other capability in this
project does. The others govern correctness: which column is authoritative,
which bucket a party belongs in, whether a bound is stated with its coverage.
All of them can be satisfied completely while publishing something that should
have waited.

Two beliefs are rejected here, both of which this project held before writing
it down. The first is that historical figures are inherently safe during a
campaign; two external reviews rejected that reasoning in 2026-08, and a past
gap is as usable as a present one. The second is that a figure built entirely
from official files is therefore not an estimate — an estimate's inputs are
always official, which is exactly why provenance cannot decide the question.

The rules are deliberately mechanical: a stated two-part test for what counts
as an interpretive indicator, a record that must cover every published page in
both directions, and a phase that defaults to the stricter reading when the
polling date is unverified. Mechanical because the judgement is being made by
whoever is publishing, at the moment they want to publish, which is when
judgement is least reliable.

## Requirements

### Requirement: Publication Is Phased Around The Election
An election turns published historical figures into campaign material. The project SHALL therefore gate publication on which phase of the election cycle it is in, rather than on whether a figure is accurate.

Three phases govern what may be published:

- **Before the campaign**: methodology, data dictionaries, frozen historical data, and fixed calculation rules MAY be published. Indicators about the current term SHALL NOT be published.
- **During the election period**: no newly derived interpretive indicator SHALL be published, and retained historical material SHALL state that it does not represent the current term.
- **After official results are confirmed**: the current term's official aggregates MAY be published, together with the snapshot, the definitions, the known gaps, and the calculation.

The reasoning that historical figures are inherently safe during a campaign SHALL NOT be relied upon. A historical gap is as usable as campaign material as a current one.

#### Scenario: A new figure is proposed before the election
- **WHEN** a figure that did not previously exist is proposed for publication and the phase is not "after official results"
- **THEN** it SHALL be classified before it is published, and an interpretive indicator SHALL be withheld or published only under the conditions this capability sets

#### Scenario: The phase is not established
- **WHEN** the polling date has not been verified against an official source
- **THEN** the project SHALL treat the phase as the election period, which is the stricter phase, rather than assuming the permissive one

#### Scenario: Historical material is retained during the election period
- **WHEN** material derived from past terms remains published while an election is underway
- **THEN** it SHALL carry a statement that it does not represent the current term, in the same copyable block as the figures themselves


<!-- @trace
source: election-period-publication
updated: 2026-08-23
code:
  - scripts/build_site_data.py
  - docs/legislative.html
  - AGENTS.md
  - .spectra.yaml
  - GEMINI.md
  - README.md
  - HANDOFF.md
  - docs/規劃-2026地方選舉.md
  - CLAUDE.md
  - scripts/mutate_build_site_data.py
  - docs/發布判定紀錄.md
tests:
  - scripts/test_build_site_data.py
-->

---
### Requirement: An Interpretive Indicator Is Distinguished From Frozen Historical Data
The distinction that governs publication SHALL be decidable by a stated test, not by the judgement of whoever is publishing at the time.

A figure is an **interpretive indicator** when both of the following hold:

1. It cannot be obtained by summing officially published counts — it requires estimation, extrapolation, or division across populations that were not counted together.
2. It carries a direction — a gap, a shortfall, a preference, a leaning — rather than being a count or a rate within one counted population.

A figure that fails either test is **frozen historical data**: its value follows from officially published results and a calculation rule held in version control, and recomputing it yields the same number.

Provenance alone SHALL NOT decide the classification. An estimate built entirely from official files is still an estimate.

#### Scenario: A rate within one counted population
- **WHEN** a turnout, vote share, or seat count is derived by summing official counts for one election
- **THEN** it SHALL be classified as frozen historical data

#### Scenario: A bounded estimate about a subgroup
- **WHEN** a figure is derived by bounding what one group's behaviour could have been, from ballots the whole electorate cast together
- **THEN** it SHALL be classified as an interpretive indicator, because it requires estimation and carries a direction, regardless of every input being official

#### Scenario: Classification is attempted by source
- **WHEN** a figure is defended as publishable because its inputs are official data
- **THEN** that defence SHALL NOT be accepted on its own, because it does not distinguish a count from an estimate


<!-- @trace
source: election-period-publication
updated: 2026-08-23
code:
  - scripts/build_site_data.py
  - docs/legislative.html
  - AGENTS.md
  - .spectra.yaml
  - GEMINI.md
  - README.md
  - HANDOFF.md
  - docs/規劃-2026地方選舉.md
  - CLAUDE.md
  - scripts/mutate_build_site_data.py
  - docs/發布判定紀錄.md
tests:
  - scripts/test_build_site_data.py
-->

---
### Requirement: Every Published Page Carries A Recorded Classification
A rule that is applied only to the pages someone remembered to consider is not a rule. The project SHALL keep a record covering every published page, and the covering SHALL be verifiable.

The record SHALL name, for each published page: the page, what class of content it carries, the classification decision, the reason, and the date the decision was made. It SHALL also state the polling date with its source, or state that the polling date is unverified.

Coverage SHALL be checked in both directions: a published page missing from the record, and a record entry naming a page that does not exist, SHALL each abort with the file named.

#### Scenario: A page is added without being classified
- **WHEN** a page is published that does not appear in the record
- **THEN** the check SHALL fail and name that file, because the failure being guarded against is nobody remembering to classify it

#### Scenario: A required statement is absent
- **WHEN** the record classifies a page as carrying historical election figures and the page does not carry the statement that it does not represent the current term
- **THEN** the check SHALL fail and name that page

#### Scenario: The check is written against an incidental string
- **WHEN** the check for the statement matches something that appears on the page for another reason, such as the year appearing in an update date
- **THEN** the check SHALL be treated as invalid, because it would pass after the statement was removed


<!-- @trace
source: election-period-publication
updated: 2026-08-23
code:
  - scripts/build_site_data.py
  - docs/legislative.html
  - AGENTS.md
  - .spectra.yaml
  - GEMINI.md
  - README.md
  - HANDOFF.md
  - docs/規劃-2026地方選舉.md
  - CLAUDE.md
  - scripts/mutate_build_site_data.py
  - docs/發布判定紀錄.md
tests:
  - scripts/test_build_site_data.py
-->

---
### Requirement: A Frozen Indicator Is Not Extended
Freezing an interpretive indicator means its shape does not grow, not merely that its numbers are not refreshed.

While an indicator is frozen, terms, thresholds, parties, and breakdowns SHALL NOT be added to it. An addition that leaves every published number unchanged is still an extension, because it enlarges what the indicator asserts.

#### Scenario: A term is added to a frozen indicator
- **WHEN** an additional term, threshold, or category is proposed for an indicator that is frozen
- **THEN** it SHALL be deferred until official results are confirmed, even though the existing figures would not change

<!-- @trace
source: election-period-publication
updated: 2026-08-23
code:
  - scripts/build_site_data.py
  - docs/legislative.html
  - AGENTS.md
  - .spectra.yaml
  - GEMINI.md
  - README.md
  - HANDOFF.md
  - docs/規劃-2026地方選舉.md
  - CLAUDE.md
  - scripts/mutate_build_site_data.py
  - docs/發布判定紀錄.md
tests:
  - scripts/test_build_site_data.py
-->