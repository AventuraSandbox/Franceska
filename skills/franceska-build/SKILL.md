---
name: franceska-build
description: >-
  Builds the product screen by screen from the explore map: the app shell, then
  the core loop as a thin working slice, then every remaining screen in all of
  its states, updating the feature sheet and saving a screenshot as it goes.
  Everything is written fresh. Use for requests like "start coding it",
  "build screen S07", "implement this flow", or once franceska-design is done.
---

# franceska-build

**Stage:** Build · **Role:** Frontend Engineer.

```bash
FR=<path to this skill>/scripts/fr.py
python3 $FR start build
```

Inputs: `explore.md`, `architecture.md`, `design/`. Outputs: the app itself,
`build-log.md` (starter in `templates/`), screenshots in `app-screens/`, and
the `yours` column of `features.csv`.

## Working rules

- **Author everything.** Code is derived from the explore map and design specs.
  Do not paste the reference app's HTML, CSS, JavaScript, SVG or images, do not
  reference its domain or CDN, and do not copy from its page source.
- **Use your own words.** Matching a button's function is coverage; matching its
  label is copying. Compare each new string with `original-strings.txt` and
  rephrase anything that matches.
- **Tokens, not literals.** Components reference design tokens; add a token if
  one is missing.

## Sequence

1. **Shell.** Routes for every screen (stubs are fine), layout, tokens wired in,
   primitives in place, believable fake seed data. Commit.
2. **Thin slice.** The core loop, start to finish, before anything else. Ugly
   is acceptable; working is what counts. With no backend yet, put fake data
   behind the same function signatures the real layer will have.
3. **Each screen**, in the order `architecture.md` gives:
   - re-read its explore row (purpose, components, states, flows);
   - use the capture for layout and hierarchy, not pixels;
   - build every state: empty, loading, filled, error, no permission, very long
     content, narrow screens;
   - keep the basics: semantic markup, labelled inputs, keyboard access,
     visible focus, alt text;
   - set the matching `features.csv` rows to `yes` or `partial` with a note;
   - screenshot at the capture's viewport (1440x900 or 390x844) into
     `franceska/app-screens/S07.png`;
   - add a line to `build-log.md` and commit (`build: S07 <name>`).

A screen is finished when all states work at 390 and 1440 pixels wide, the
flow can be completed by keyboard alone, the console is clean, no wording was
borrowed, and the sheet and screenshot are updated.

If a feature proves bigger than estimated, record that in the log and tell the
user instead of quietly delivering half of it.

When the reference app's behaviour is unclear, study it as a customer would (its
help pages, public videos, the user's own account), never through its code or
traffic, and then design the behaviour yourself.

## Exit gate

```bash
python3 $FR gate build
```

Needs a build log with screen lines, at least half the must-haves started, and
at least one app screenshots. The compare stage later demands all of them.

## Hand off

Report screens done of total and must-haves done of total. Then
`franceska-connect`, or for a purely static product
`python3 $FR skip connect --reason "..."`.
