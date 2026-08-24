## ADDED Requirements

### Requirement: Hover-Only Content Is Also Reachable By Keyboard
Any information a chart reveals only on pointer hover SHALL be reachable by keyboard focus as well. A tooltip that appears on `pointerenter` and disappears on `pointerleave` SHALL appear on `focus` and disappear on `blur` using the same content and the same trigger element, not a separate keyboard-only implementation.

#### Scenario: A chart data point is tabbed to
- **WHEN** a keyboard user tabs to a chart's hit target
- **THEN** the same tooltip content that pointer hover would show SHALL appear, and it SHALL disappear on blur

#### Scenario: Keyboard and pointer paths diverge
- **WHEN** a tooltip's content or trigger condition is implemented separately for keyboard than for pointer
- **THEN** that duplication SHALL be treated as a defect, because a rule implemented twice drifts

### Requirement: A Chart Point Representing A Term And Category May Link To Its Detail Page
Where a page presents an aggregate figure for one (term, election type) pair, and another page on the site presents the record-level detail for that same pair, the aggregate's chart SHALL let a reader navigate from the point to that detail — reachable by pointer click, keyboard activation, and touch alike — using a native link element rather than a script-driven redirect.

This linking SHALL NOT be added where no corresponding detail page exists for the dataset being charted.

#### Scenario: A turnout or seat chart point is activated
- **WHEN** a reader clicks, taps, or presses Enter on a chart point for a given term and election type
- **THEN** navigation SHALL go to the detail page filtered to that same term and election type, using the page's existing addressing scheme rather than a new one

#### Scenario: A dataset has no detail page
- **WHEN** a chart presents a dataset for which the site has no record-level detail page
- **THEN** its points SHALL remain keyboard- and pointer-accessible for their tooltip content, but SHALL NOT be turned into links to an unrelated or non-existent page

#### Scenario: The link target is native, not scripted
- **WHEN** a chart point becomes navigable
- **THEN** it SHALL be implemented as an anchor element a browser handles natively — opening in a new tab, copying the link, and screen-reader link semantics SHALL all work without additional script
