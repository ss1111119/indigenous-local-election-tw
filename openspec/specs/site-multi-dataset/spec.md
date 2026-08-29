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
  - README.md
  - CLAUDE.md
  - docs/legislative.html
  - docs/schema/palette-legislative.md
  - scripts/palette_metrics.py
  - HANDOFF.md
  - .spectra.yaml
  - docs/sitemap.xml
  - scripts/mutate_build_site_data.py
  - docs/roster.html
  - GEMINI.md
  - AGENTS.md
  - docs/index.html
  - scripts/build_site_data.py
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
  - README.md
  - CLAUDE.md
  - docs/legislative.html
  - docs/schema/palette-legislative.md
  - scripts/palette_metrics.py
  - HANDOFF.md
  - .spectra.yaml
  - docs/sitemap.xml
  - scripts/mutate_build_site_data.py
  - docs/roster.html
  - GEMINI.md
  - AGENTS.md
  - docs/index.html
  - scripts/build_site_data.py
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
  - README.md
  - CLAUDE.md
  - docs/legislative.html
  - docs/schema/palette-legislative.md
  - scripts/palette_metrics.py
  - HANDOFF.md
  - .spectra.yaml
  - docs/sitemap.xml
  - scripts/mutate_build_site_data.py
  - docs/roster.html
  - GEMINI.md
  - AGENTS.md
  - docs/index.html
  - scripts/build_site_data.py
tests:
  - scripts/test_build_site_data.py
-->

---
### Requirement: An election type present in the data is either presented or excluded by name
The site builder derives the set of election types from the long tables, so a type added to the data layer reaches the site by default. That default is wrong for types the project has decided not to present yet, and it is also wrong to let such a type disappear without anyone stating that it did.

Every election type present in the long tables SHALL either be presented on the site or appear in a declared exclusion list carrying the reason it is excluded. A type that is neither presented nor declared SHALL abort the build naming that type.

Aborting SHALL be preferred over skipping. A type that vanishes from the site because a build step silently stepped over it is indistinguishable from a type that was never there, and this project has already published a wrong figure that survived a full day because the check that would have caught it was never invoked.

#### Scenario: A new election type appears in the long tables
- **WHEN** the long tables carry an election type that is neither presented nor declared as excluded
- **THEN** the build SHALL abort naming that type, rather than omitting it from the site

#### Scenario: A type is deliberately not presented
- **WHEN** the project decides a type belongs in the data layer but not yet on the site
- **THEN** the exclusion SHALL be declared with its reason, so that the decision is visible where the omission happens

#### Scenario: An excluded type later becomes presentable
- **WHEN** an excluded type is to be presented
- **THEN** removing its declaration SHALL be sufficient to make the build require it, so that the declaration is the only place the decision lives

---
### Requirement: A presented type's national figures come from the source's own aggregate row
The site shows national electorate and turnout per election type. Those figures are read from the aggregate row the source publishes for that type, not recomputed by the site builder from detail rows.

Where an election type carries no such aggregate row, the builder SHALL NOT synthesise one. Synthesising it would place a figure on the site that the source never published, and would do so as a side effect of a build step rather than as a decision.

#### Scenario: A type has no aggregate row
- **WHEN** an election type in the long tables has no aggregate row of its own
- **THEN** the builder SHALL treat it as not presentable and require a declared exclusion, rather than summing detail rows to produce one

#### Scenario: Aggregate rows are split across files
- **WHEN** a type's aggregate figures are published as more than one row because the source splits the electorate across mutually exclusive files
- **THEN** those rows SHALL be added together, because each is a genuine published aggregate and neither alone is the national figure

---
### Requirement: A Coverage Claim Separates What The Data Lacks From What The Site Withholds
The site tells readers which offices it does not cover. That statement can be untrue in two different ways: the data layer may have gained an office the page still lists as absent, or the page may present an office the data layer never had. A single sentence that conflates "the project has no data for this" with "the site does not show this" becomes half-true the moment either side changes, and nothing fails when it does.

Where a page states what it does not cover, the statement SHALL distinguish offices absent from the data layer from offices present in the data layer but not presented on the site. For the latter, the statement SHALL name the office rather than leaving it inside a general category, because a reader cannot tell that a named category has an unnamed exception.

Where an office is present in the data but withheld from the site for more than one reason, the statement SHALL NOT give only one of them. A structural bar and an editorial decision are different things, and a reader who is told only the editorial one will believe the bar does not exist.

This requirement governs the prose claim, not the machinery. Whether an election type is presented or declared as excluded is already enforced elsewhere in this capability; that enforcement operates on the exclusion list, and does not read the page's sentences. That gap SHALL be recorded rather than presumed closed, because an enforced adjacent rule invites the belief that this one is enforced too.

#### Scenario: The data layer gains an office the page lists as uncovered
- **WHEN** an office named in a page's coverage claim is added to the data layer
- **THEN** the claim SHALL be rewritten to say the data covers it and the site does not present it, rather than left standing because the site's behaviour did not change

#### Scenario: A qualifier attaches to only part of a list
- **WHEN** a coverage claim lists several offices and narrows one of them with a parenthetical qualifier
- **THEN** the sentence SHALL be written so that the qualifier's scope is unambiguous, because a reader who attaches it to the wrong item reads a claim the project did not make

#### Scenario: Two reasons withhold one office
- **WHEN** an office is absent from the site both because a structural rule bars it and because a decision was deferred
- **THEN** both SHALL be stated, because naming only the deferral implies that lifting the deferral would be sufficient

#### Scenario: The claim exists in more than one language
- **WHEN** a coverage claim appears in a translated page
- **THEN** every language SHALL carry the same distinctions, because a translation that merges the two kinds of absence reintroduces the defect in that language alone

#### Scenario: The claim is assumed to be machine-verified
- **WHEN** a reader or maintainer relies on the build to catch a stale coverage claim
- **THEN** that reliance SHALL be treated as unfounded unless a check that reads the page's prose exists, and the absence of such a check SHALL be recorded where maintainers will see it

<!-- @trace
source: coverage-claim-data-vs-site
updated: 2026-08-29
code:
  - HANDOFF.md
-->