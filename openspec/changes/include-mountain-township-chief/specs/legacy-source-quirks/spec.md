## MODIFIED Requirements

### Requirement: Sentinel Recognition Is Named Per Term, Not Global
The scope in which a value is treated as a sentinel SHALL be an explicit named list. A value
SHALL NOT be treated as a sentinel merely because it once served that purpose, because the same
number can be a genuine measurement elsewhere.

The named scope SHALL be a term where every file of that term shares one convention, and SHALL be
narrowed to a term and election type where they do not. Files issued for the same term have been
found to use different sentinel values from one another, so a term-wide list cannot express which
value applies without either discarding real measurements in the files that disagree or admitting
a sentinel as a measurement in the files that agree.

Two checks SHALL bound the list, and both SHALL abort the build rather than adjust behaviour
silently: a listed scope SHALL contain no value other than the sentinels named for it, and a scope
not listed for a given sentinel SHALL contain no occurrence of that sentinel.

A named narrowing that is never exercised SHALL abort the build, because a declaration that no
longer matches any file is indistinguishable from one that was never correct.

#### Scenario: A listed term turns out to hold a real value
- **WHEN** a term on the list carries any age other than the sentinel
- **THEN** the build SHALL abort naming that term and the value, because the premise for listing it
  no longer holds and a real age would otherwise be discarded

#### Scenario: An unlisted term starts carrying the sentinel
- **WHEN** a term not on the list carries the sentinel value
- **THEN** the build SHALL abort naming that term, because either the sentinel convention has spread
  to a new term or a genuine value coincides with it, and the two cannot be told apart automatically

#### Scenario: One file of a term uses a different sentinel from the rest
- **WHEN** the files of a single term do not share one sentinel convention
- **THEN** the narrower value SHALL be named against that term and election type rather than against
  the term as a whole, so that the files which do not use it keep the value as a measurement

#### Scenario: A narrowed declaration stops matching any file
- **WHEN** a sentinel named for a term and election type no longer occurs in that scope
- **THEN** the build SHALL abort naming the declaration, because an unexercised narrowing silently
  widens what the remaining checks accept

#### Scenario: A narrowed sentinel appears outside its declared scope
- **WHEN** a value named as a sentinel for one election type occurs in another election type of the
  same term
- **THEN** the build SHALL abort, because it is either a spreading convention or a genuine
  measurement, and treating it as a measurement by default would publish a wrong figure
