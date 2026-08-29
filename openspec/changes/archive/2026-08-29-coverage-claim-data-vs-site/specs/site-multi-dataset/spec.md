## ADDED Requirements

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
