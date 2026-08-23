## ADDED Requirements

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

### Requirement: The Weight Is The Share Of Voters, Not The Share Of Registered Electors
The decomposition that the bounds rest on is weighted by each group's share of the votes actually cast, not its share of the registered electorate. Those two quantities differ whenever the groups turn out at different rates. The build SHALL compute both and SHALL use the share of voters in the bounds.

Both SHALL be published, so a reader can see how far apart they are rather than being told they are close.

#### Scenario: The two shares diverge
- **WHEN** a stratum's share of registered electors differs from its share of voters
- **THEN** the bounds SHALL be computed from the share of voters, and both figures SHALL appear in the output

#### Scenario: A small divergence is not treated as licence to interchange them
- **WHEN** the two shares are found to be close in the strata currently published
- **THEN** that SHALL NOT justify using the electorate share in the bounds, because a bound computed from the wrong weight is still shaped like a bound

### Requirement: Estimates Are Separated From Official Figures By Table And By Column Name
Figures the project observed and figures it inferred SHALL NOT share a table, and SHALL NOT share a column-naming convention. Every inferred column SHALL carry a prefix marking it as observed-in-stratum, lower bound, or upper bound, and every row SHALL carry the scope that produced it: the threshold, the number of units, the population covered, the coverage rate, and both weights.

A consumer reading a single column SHALL NOT be able to mistake an inferred figure for an official result.

#### Scenario: A downstream consumer reads one column
- **WHEN** a consumer selects a vote-share column from a published table
- **THEN** the column name SHALL make clear whether the figure is an official count or an inferred bound

#### Scenario: Scope travels with the number
- **WHEN** an inferred figure is published
- **THEN** the same row SHALL carry the threshold and coverage that produced it, so the figure cannot be quoted without its scope

### Requirement: Coverage And Its Skew Are Stated Before The Figure, Not After It
The strata that support tight bounds cover a minority of the population of interest, and they are not a random minority: they are geographically concentrated. Documentation SHALL state the coverage rate and the concentration before presenting any figure derived from those strata.

A bound that is arithmetically certain about a stratum SHALL NOT be described as if it were about the whole population.

#### Scenario: Describing a stratum-derived figure
- **WHEN** a figure derived from the high-density strata is described
- **THEN** it SHALL be described as pertaining to those strata, and SHALL NOT be described as the whole group's behaviour

#### Scenario: The uncovered remainder
- **WHEN** the population outside the strata is discussed
- **THEN** the documentation SHALL state that arithmetic bounds are uninformative there, rather than implying the published interval covers them
