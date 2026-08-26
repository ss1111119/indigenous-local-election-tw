# site-navigation Specification

## Purpose

`docs/index.html` and `docs/legislative.html` are long pages that can only be
read by scrolling, and the navigation bar lists page links without saying what
each page covers. A reader has no way to jump to a section, and no way to learn
from the page they are on that other datasets exist elsewhere on the site. This
capability governs the in-page table of contents — whose entries must match the
page's actual sections — and the dataset map that every published page carries.

## Requirements

### Requirement: Multi-section pages provide an in-page table of contents whose entries match the page's actual sections
A page with more than one `<section>` SHALL give every `<section>` a stable `id` attribute and SHALL present, near its `<h1>`, a navigable table of contents whose entries link to those `id`s in the same order the sections appear on the page.

#### Scenario: A reader jumps to a section
- **WHEN** a reader activates a table-of-contents entry
- **THEN** the browser SHALL navigate to the `<section>` whose `id` matches that entry, using a plain anchor link with no script required

#### Scenario: A section is added without updating the table of contents
- **WHEN** a page's `<section>` elements do not have an `id` for every id referenced in that page's table of contents, or the table of contents omits an `id` present on the page, or the two orders disagree
- **THEN** the build SHALL abort, naming the page and the mismatch

#### Scenario: A single-section page is not required to have a table of contents
- **WHEN** a page has only one logical content section (for example a roster page listing candidates)
- **THEN** it SHALL NOT be required to carry a table of contents


<!-- @trace
source: page-toc-and-dataset-map
updated: 2026-08-26
code:
  - docs/index.html
  - scripts/mutate_build_site_data.py
  - README.md
  - docs/legislative.html
  - scripts/build_site_data.py
  - docs/en/legislative.html
  - data/reference/mountain-township-list.csv
  - docs/schema/山地鄉鄉長資料清點.md
  - docs/roster.html
  - data/sources.json
  - docs/en/index.html
tests:
  - scripts/test_build_site_data.py
-->

---
### Requirement: Every published page states where the site's other datasets can be found
Because the site presents multiple non-comparable datasets across separate pages (see the `site-multi-dataset` capability), every published page SHALL carry, near its navigation, a statement of what each dataset covers and that they are not comparable, and this statement SHALL be identical, word for word within a given language, across every page required to carry it.

#### Scenario: A reader arrives on any published page
- **WHEN** any published page under `docs/` loads
- **THEN** it SHALL contain, in the page's own language, the dataset-map statement naming the site's datasets and stating they are not comparable

#### Scenario: The statement is missing from one page
- **WHEN** a page required to carry the dataset-map statement does not contain it verbatim in its own language
- **THEN** the build SHALL abort, naming the page

#### Scenario: The statement is edited on one page but not the shared source
- **WHEN** the dataset-map text is edited directly in a page's HTML in a way that no longer matches the shared source text
- **THEN** the build SHALL abort, because a per-page edit is exactly how the qualifier text and its source drift apart over time

<!-- @trace
source: page-toc-and-dataset-map
updated: 2026-08-26
code:
  - docs/index.html
  - scripts/mutate_build_site_data.py
  - README.md
  - docs/legislative.html
  - scripts/build_site_data.py
  - docs/en/legislative.html
  - data/reference/mountain-township-list.csv
  - docs/schema/山地鄉鄉長資料清點.md
  - docs/roster.html
  - data/sources.json
  - docs/en/index.html
tests:
  - scripts/test_build_site_data.py
-->