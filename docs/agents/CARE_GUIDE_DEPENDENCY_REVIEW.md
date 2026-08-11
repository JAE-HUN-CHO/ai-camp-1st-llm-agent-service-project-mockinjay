# CareGuide dependency review

Date: 2026-08-12

The canonical frontend was confirmed before this review. No dependency was
changed without a lock and regression run.

## Backend resolution

`backend/requirements.lock` pins the exact transitive graph used by the
passing local application environment. It is generated from the union of
`backend/requirements.txt` and the legacy root `requirements.txt`, so imports
from route adapters and research scripts (including `parlant`, LangChain
community adapters, and `toon-format`) are not silently omitted. The source
files remain human-maintained compatibility contracts; neither uses an
unbounded `latest` specifier.

## Stable-version review

The current PyPI metadata was checked for the highest relevant releases:

| Package | Tested/pinned in this change | Latest observed | Decision |
|---|---:|---:|---|
| FastAPI | 0.120.4 | 0.141.1 | defer; latest metadata is a new compatibility line and the current route contract is green |
| PyMongo | 4.6.0 | 4.17.0 | defer; Mongo/Vector smoke is green with the pinned driver |
| Motor | 3.3.2 | 3.7.1 | defer with PyMongo pair; upgrade requires a separate driver contract run |
| pydantic-settings | 2.12.0 | 2.14.2 | defer; current settings/auth tests are green |
| OpenAI | 1.109.1 | current release line is newer | opt-in provider only; no default-path upgrade |
| dnspython | 2.7.0 | 2.x compatibility line | promoted from the stale 1.16.0 environment pin because `email-validator` requires `>=2`; lock and installed environment agree |

This is a deliberate compatibility gate, not an assertion that older pins are
the newest releases. A future upgrade must update the lock, run the complete
backend/frontend/integration suite, and re-check Atlas Local vector behavior.

## Remaining environment note

The active development environment now satisfies the `email-validator` /
`dnspython` contract (`dnspython==2.7.0`). A clean environment created only
from the lock remains the preferred upgrade verification path.
