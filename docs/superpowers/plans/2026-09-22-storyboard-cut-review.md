# Storyboard cut review integration

User approved connecting the existing storyboard to the completed Midea review.

- [x] Add an optional read-only loader joining canonical scene cutIds, cut_plan and review by cutId; reject cross-scene/missing records and mark changed narration stale.
- [x] Show original narration, shot/continuity, candidate image and decision/reason inside existing scene cards, with status filter and summary. Preserve selection and render state. Ordinary projects unchanged.
- [x] Copy external supplied image references into project assets without deleting or overwriting originals, and use safe project-local URLs.
- [x] Test missing data, joins, stale narration, path containment, escaping and template integration. Verify 131 scenes / 227 cuts against real project, then inspect running app.

No new dashboard, image generation, automatic asset selection, or render pipeline change.

Validation: 12 focused tests passed; live browser showed 131 scenes / 227 cuts, remake filter 69 cuts in 48 scenes, all 97 unique image URLs HTTP 200, no JavaScript errors.

User correction: promoted all 227 cuts into independent scene_specs records; v3 remains historical. Current source is scene_analysis_v4 and scene_specs.json. No nested cut cards for this project. Migration backs up canonical specs, direction plan and registry; DB scene count synchronized.
