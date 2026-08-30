## REMOVED Requirements

### Requirement: Publication Is Phased Around The Election
**Reason**: The three-phase gate is a self-imposed editorial position, not a legal obligation. The project's own README distinguishes the two: the requirement not to publish dates of birth and education is marked as a legal requirement, and this one is not. The gate is blocking work that is otherwise ready.
**Migration**: No replacement. Publication timing is no longer gated on the election calendar. The current-term statement on the published pages is retained because it states a fact that does not depend on this rule, and it remains enforced by its own build check.

### Requirement: An Interpretive Indicator Is Distinguished From Frozen Historical Data
**Reason**: The two-part test exists only to decide what the phase gate withholds. With the gate removed the classification has nothing to govern.
**Migration**: No replacement. Figures are no longer classified before publication.

### Requirement: Every Published Page Carries A Recorded Classification
**Reason**: The record's entries are classifications made under the two-part test. Once that test is removed the entries have no standard behind them, and retaining the file would suggest the standard still applies.
**Migration**: The record file is deleted. Its contents remain retrievable from git history. The build checks that enforced its coverage in both directions are removed with it.

### Requirement: A Frozen Indicator Is Not Extended
**Reason**: Freezing is a consequence of the phase gate. With no phase gate nothing is frozen.
**Migration**: No replacement. Indicators may be extended without reference to the election calendar.

### Requirement: Comparing two rates each taken within one counted population does not by itself require estimation
**Reason**: This requirement refines the boundary of the two-part test, which is itself removed.
**Migration**: No replacement.

### Requirement: A recorded classification states a reason that matches what the page contains
**Reason**: The consistency check operates on the record being deleted.
**Migration**: No replacement. The build check that compared recorded reasons against page contents is removed.

### Requirement: The record covers what is published, not only what is HTML
**Reason**: The coverage scope rule governs a record that no longer exists.
**Migration**: No replacement.
