## ADDED Requirements

### Requirement: Comparing two rates each taken within one counted population does not by itself require estimation
The distinction between a frozen historical figure and an interpretive indicator turns on whether the figure needs estimation, not on whether it carries a direction. A difference between two figures each obtained by summing official counts within its own counted population is still obtained by summing official counts.

Subtracting one such rate from another SHALL NOT be treated as division across populations that were not counted together. The divisions each occur within a single counted population; the subtraction is not a division. Where no step of the calculation estimates, extrapolates, or stands in for a group that was not counted, the first part of the test is not satisfied and the figure is frozen historical data however directional it reads.

This SHALL NOT be extended to a comparison whose published claim reaches beyond what the two sides actually counted. Where the claim a publication makes covers a population wider than the counts it rests on, or treats the counted population as standing in for a different one, the comparison carries estimation and is classified accordingly.

The classification SHALL follow the population the publication claims to describe, not the arithmetic alone and not any single phrase. A heading that widens the claim widens the classification even where the body is careful, because what was published is the wider claim. This is not a loophole for wording: the test is whether the claimed population matches the counted one, which is checkable, rather than whether particular words appear.

#### Scenario: Two rates from different ballots over the same places are compared
- **WHEN** a party's share of one ballot type is compared with its share of another ballot type, over the same set of polling places, using each ballot type's own official totals
- **THEN** the comparison SHALL be classified as frozen historical data, because each share is complete within its own count and the two ballots not being paired per voter does not make either share an estimate

#### Scenario: Two separate but fully counted populations are compared
- **WHEN** rates from two different populations are compared, each rate complete within its own count, with neither standing in for the other and nothing extrapolated to anything uncounted
- **THEN** the comparison SHALL be classified as frozen historical data, because populations being counted separately is not what makes a figure an estimate

#### Scenario: A heading claims more than the counts cover
- **WHEN** a publication's body describes the places that were counted while its heading describes a wider group
- **THEN** the classification SHALL follow the wider claim, because that is what was published

#### Scenario: The same comparison is made about a subgroup the counts do not isolate
- **WHEN** such a comparison is presented as describing a group that shares polling places with others rather than the polling places themselves
- **THEN** it SHALL be classified as an interpretive indicator, because reaching that group requires bounding or proxying what it did

#### Scenario: A directional figure is assumed to be interpretive because it is directional
- **WHEN** a figure is classified on the strength of carrying a direction alone
- **THEN** that classification SHALL be rejected, because both parts of the test must hold and the estimation part is what separates the two categories

### Requirement: A recorded classification states a reason that matches what the page contains
The record exists so that the next person judging a similar case has something to compare against. A reason that contradicts the page it describes is worse than no reason, because it will be reused.

Each recorded classification SHALL state a reason that is true of the page. Where a page carries directional statements and is nonetheless classified as frozen historical data, the reason SHALL say so and SHALL rest on the absence of estimation rather than on the absence of direction.

A contradiction between a stated reason and the page's contents SHALL be detectable mechanically wherever the contradiction is mechanical, and SHALL abort naming the page. Reasons whose correctness needs a human reader remain outside what any check can settle, and that limit SHALL be stated rather than implied by silence.

#### Scenario: A reason claims an absence the page contradicts
- **WHEN** a classification's reason asserts that a page carries no directional quantity, and the page carries one
- **THEN** the check SHALL abort naming that page, because the reason will be reused on the next case

#### Scenario: A page is directional and correctly classified as frozen
- **WHEN** a page carries directional comparisons that need no estimation
- **THEN** the recorded reason SHALL rest on the absence of estimation, and the presence of direction SHALL be acknowledged rather than denied

### Requirement: The record covers what is published, not only what is HTML
The coverage check exists because nobody remembers to classify a page that was added since the rule was written. That failure does not depend on the file's format.

Published material that carries election figures SHALL appear in the record regardless of file type. Where the project publishes such material outside the pages the check currently walks, either the check's scope SHALL be widened to include it or its exclusion SHALL be recorded with a reason.

#### Scenario: Published material carrying election figures is not HTML
- **WHEN** a file that is published and carries election figures is not among the file types the coverage check walks
- **THEN** it SHALL still be classified in the record, and the check SHALL be widened to cover it rather than the gap being left implicit

#### Scenario: A file type is deliberately left out of scope
- **WHEN** the project decides a published file type need not be classified
- **THEN** that decision SHALL be recorded with its reason, so that the omission is visible where the check defines its scope
