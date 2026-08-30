# site-district-geography Specification

## Purpose

The roster page groups candidates by electoral district, but a district number tells
the reader nothing about where it is. Indigenous districts in particular span several
townships and reach well beyond the mountain townships their name suggests, and the
numbering runs continuously across election types within a county, so the same number
means different places depending on which election is being read.

This capability governs how that geography is obtained and presented. The relationship
is already implicit in the long tables the site generator reads, so it is derived at
build time rather than stored as a second copy that can drift.

It covers: which of the source's disagreeing files decides a district's geography;
why a derived relationship is computed rather than versioned; how the four township
names the source truncated are restored for display without introducing a second copy
of the alias table; and why a claim that a district covers an entire county must be
verified against that county rather than inferred from the district count.

The reason it exists as its own capability is that each of these has a silent failure
mode. Deriving from the wrong file publishes one side of a source conflict without
saying so; storing a second copy lets it drift unnoticed; rendering the stored name
publishes four wrong names; and inferring whole-county coverage from arithmetic
publishes a claim nobody checked.

## Requirements

### Requirement: A District's Geography Comes From The Defining Side, Not The Vote Side
The source publishes each election as several files. One defines administrative and district names and codes, one reports results per administrative level, and one reports votes per polling station. These do not always agree about which district a township belongs to: in one named case the vote file records a township's votes under a different district than the defining files assign it to.

The question "which townships does this district cover" is a question about the district's definition. The system SHALL derive district geography from the defining side, and SHALL NOT derive it from the vote file, because the vote file answers where votes were recorded rather than how the district was drawn.

Where the two sides disagree, the published page SHALL present one answer, not both. The disagreement SHALL remain recorded in the project's source-anomaly record so it stays auditable. Presenting both assignments side by side SHALL be treated as misleading, because it invites the reader to believe two incompatible statements are equally supported.

#### Scenario: The vote file and the defining files disagree
- **WHEN** the vote file assigns a township to one district and the defining files assign it to another
- **THEN** the geography SHALL follow the defining files, and the vote file's assignment SHALL NOT be presented as an alternative

#### Scenario: Cross-term similarity is offered as evidence
- **WHEN** a district assignment in one term is defended on the grounds that later terms group the same townships together
- **THEN** that reasoning SHALL be rejected, because district boundaries are redrawn between terms and cross-term similarity is not evidence of same-term correctness


<!-- @trace
source: roster-district-township-coverage
updated: 2026-08-29
code:
  - scripts/build_site_data.py
  - docs/roster.html
  - HANDOFF.md
  - scripts/mutate_build_site_data.py
tests:
  - scripts/test_build_site_data.py
-->

---
### Requirement: Derived Relationships Are Computed, Not Stored As A Second Copy
The relationship between districts and townships is already present in the long tables the site generator reads. Writing it out as a separate versioned file would create a second copy that can drift from the tables it was derived from, and nothing would fail when it did.

Where a relationship can be derived from data the generator already reads, the system SHALL compute it at build time rather than storing it as an additional versioned artifact. Completeness SHALL instead be pinned by tests that fix the expected counts, so that a change in the derived relationship fails loudly.

#### Scenario: The derived relationship changes size
- **WHEN** the number of districts or the number of district-township relationships differs from the pinned counts
- **THEN** the build SHALL abort naming the actual values, because a silent change in coverage is indistinguishable from a correct one

#### Scenario: A district resolves to no townships
- **WHEN** any district in scope has an empty township list
- **THEN** the build SHALL abort naming that district, rather than rendering a district with no geography


<!-- @trace
source: roster-district-township-coverage
updated: 2026-08-29
code:
  - scripts/build_site_data.py
  - docs/roster.html
  - HANDOFF.md
  - scripts/mutate_build_site_data.py
tests:
  - scripts/test_build_site_data.py
-->

---
### Requirement: Truncated Source Names Are Restored Through The One Existing Alias Table
Four township names in the legacy mountain-indigenous files are missing their leading character, and the long tables preserve them as they came because source values are not overwritten. All four fall in the election category this page presents, so rendering the stored name directly would publish four visibly wrong names.

The system SHALL restore these names for display through the project's existing named alias table rather than defining a second list. The alias table SHALL remain the single source of truth, and the restored name SHALL NOT be written back into the long tables.

Where an alias entry is not exercised by the data being rendered, the build SHALL abort. An unused entry means either the source was corrected — in which case the patch should be removed — or the data no longer reaches the code path the entry exists for.

#### Scenario: A truncated name would reach the page
- **WHEN** a stored township name is one of the known truncated forms
- **THEN** the restored full name SHALL be displayed, and the presence of a truncated form on the published page SHALL be treated as a defect

#### Scenario: A second alias list is introduced
- **WHEN** the display layer defines its own copy of the alias mapping
- **THEN** that SHALL be treated as a defect, because two copies of one fact diverge without anything failing

#### Scenario: An alias entry is never used
- **WHEN** the build completes without exercising every alias entry
- **THEN** it SHALL abort, because an entry that matches nothing is indistinguishable from one whose data path has silently disappeared


<!-- @trace
source: roster-district-township-coverage
updated: 2026-08-29
code:
  - scripts/build_site_data.py
  - docs/roster.html
  - HANDOFF.md
  - scripts/mutate_build_site_data.py
tests:
  - scripts/test_build_site_data.py
-->

---
### Requirement: A Whole-County Claim Is Verified Against The County, Not Inferred From District Count
A county in which an election type has only one district is not thereby a county whose single district covers every township. The first is a fact about how many districts exist; the second is a claim about coverage, and the townships a source lists need not equal every township the county administratively contains.

Where the page states that a district covers an entire county, the system SHALL verify that the district's township set equals the county's township set for that term. Where it does not, the build SHALL abort rather than downgrade the district to an ordinary one and continue.

The comparison SHALL exclude names that carry a district suffix, because the lower-tier representative elections record names of the form "township, district N" at the township level, and those are not township names. The suffix form SHALL NOT be assumed constant across terms.

#### Scenario: A single-district county does not cover every township
- **WHEN** a county has one district for an election type but that district's townships are fewer than the county's
- **THEN** the build SHALL abort naming the difference, because publishing a whole-county claim that is not true is worse than publishing nothing

#### Scenario: The county baseline is contaminated by suffixed names
- **WHEN** the set used as the county's townships includes names carrying a district suffix
- **THEN** that baseline SHALL be treated as wrong, because those entries are districts within a township rather than townships

#### Scenario: The suffix appears in an unrecognized form
- **WHEN** a term writes the district suffix differently from the form the comparison recognizes
- **THEN** the unrecognized entries SHALL be treated as a defect of the comparison rather than as genuine townships

<!-- @trace
source: roster-district-township-coverage
updated: 2026-08-29
code:
  - scripts/build_site_data.py
  - docs/roster.html
  - HANDOFF.md
  - scripts/mutate_build_site_data.py
tests:
  - scripts/test_build_site_data.py
-->