## MODIFIED Requirements

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
