---
name: franceska-compare
description: >-
  Measures how far the product is from the reference app: a weighted feature coverage
  score with the gaps in build order, a layout comparison of screenshots that
  ignores colour, and a behaviour comparison, ending in a shippable or not
  verdict. Use for requests like "how near are we", "what is still absent",
  "coverage", "compare screens", "is it ready to ship", or after franceska-test.
---

# franceska-compare

**Stage:** Compare · **Role:** Product Evaluator.

```bash
FR=<path to this skill>/scripts/fr.py
python3 $FR start compare
python3 $FR feature_coverage
python3 $FR visual_compare franceska/screens/S07.png franceska/app-screens/S07.png --out franceska/diffs/S07.png
python3 $FR visual_compare franceska/screens/S07.png franceska/app-screens/S07.png --json > franceska/diffs/S07.json
python3 $FR feature_coverage --visual franceska/diffs/*.json --markdown > franceska/coverage.md
```

## Coverage means equal capability, not equal looks

Two questions matter. Can a user still do everything they used to (the feature
score)? Is information roughly where a switching user expects it (the layout
score)? Colour is excluded on purpose, since the brand stage replaces all of
it. Do not chase pixel sameness: the reference app's precise look is its trade
dress.

## Feature score

Update `features.csv` so each `yours` cell reads `yes`, `partial` (note what
is missing), `no` or `skip` (give a reason). Scoring weights are must 3, should
2, could 1, with partial worth half; skipped rows and anything you added beyond
the reference app stay out of the score. Gaps are sorted by priority, then effort. Any missing must-have
means not shippable.

## Layout score

Capture both sides at one viewport (1440x900 or 390x844) in the same state.
Originals are in `franceska/screens/`, yours in `franceska/app-screens/`. The
default mode compares edge maps on a grid and reports a score (90+ matches,
75+ close, 50+ partly, otherwise different), the regions that differ in the
the reference app's pixel coordinates, and a note when page heights diverge. In the
diff image red marks edges only in the reference app and blue only in yours.
`--mode pixel` is for comparing your own builds over time. PNG only,
non-interlaced; big retina files take a few seconds.

## Behaviour check

Walk each flow in both products and compare what scores cannot see: clicks to
finish, error handling, what is remembered, which emails arrive. Record
`flow | reference app | yours | fix or keep`. Fewer clicks is a win.

## Write the verdict

`franceska/coverage.md` carries the overall, feature and per-screen scores, the
gaps, the behaviour differences and one verdict:
- **not shippable**: a required feature is absent, or a severe bug (S1 or S2) is unresolved;
- **shippable**: every must-have done, feature score at least 80, no S1 or S2;
- **better than the reference app**: shippable and carrying the fixes from the
  validate stage, which is the goal.

Give honest numbers. Publish a Dashboard artifact of them if available.

## Exit gate

```bash
python3 $FR gate compare
```

Needs `coverage.md`, every must-have `yes`, feature score 80+, no open S1/S2.
On failure list the top five builds and `python3 $FR reopen build`.

## Hand off

`franceska-validate`.
