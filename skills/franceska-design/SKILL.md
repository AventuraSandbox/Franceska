---
name: franceska-design
description: >-
  Builds the product's design system as tokens and component specs: colour
  roles, type scale, spacing, radii, shadows and layout, light and dark, with
  open icons and fonts and original assets, plus a WCAG contrast checker. Use
  when the user says "design system", "design tokens", "colours and fonts",
  "match the look of X", "component specs", or after franceska-plan.
---

# franceska-design

**Stage:** Design · **Role:** Product Designer.

```bash
FR=<path to this skill>/scripts/fr.py
python3 $FR start design
python3 $FR contrast_check            # reads franceska/design/tokens.json
```

Inputs: `explore.md`, `screens/`. Outputs: `design/tokens.json` (starter in
`templates/`), `design/tokens.css`, a Tailwind mapping and
`design/components.md`.

## What is yours to rebuild

Systems and patterns are free to reuse: the idea of a colour role, a type
scale, how a modal behaves. Specific expressions are not. Leave these behind:

- logos, icons, illustrations, photos and sounds (use open icon sets such as
  Lucide, Phosphor, Heroicons or Tabler; make your own artwork);
- fonts that need a licence (choose an open font that does the same job, for
  example Inter, Geist, IBM Plex, Manrope or Source Serif);
- the reference app's wording;
- its brand colour plus signature layout, which together are trade dress. Keep
  the accent as a neutral placeholder; the brand stage supplies the real one.

Record every added asset in `franceska/assets.csv` (`path,source,license`).

## Method

1. **Measure.** Work from the captures, zooming in, or ask the user for sampled
   values. Record the colour roles (bg, surface, border, border-input, text,
   text-muted, accent, on-accent, danger, success, warning), the type scale,
   the spacing unit (typically 4 or 8), a few radii, shadows and motion, and
   layout limits like content width and breakpoints.
2. **Write tokens for both modes.** Populate `colors` and `colors_dark` with
   stable role names, and list each text-on-background pairing under `pairs`
   with the ratio it must reach. Run `python3 $FR contrast_check`. WCAG AA sets the
   minimum: 4.5 for body text, 3 for large text, input borders and focus rings.
   The checker covers both modes and returns non-zero on any miss; correct the
   tokens, not single components. Output `tokens.css` as custom properties and
   feed them to the Tailwind theme so components use names like `bg-surface`
   instead of hex values.
3. **Spec the components.** One block each in `components.md`: variants,
   sizes, every state (default, hover, active, focus-visible, disabled,
   loading, error, empty), tokens used, accessibility behaviour, and the
   screens using it.
4. **Build the primitives** in isolation first (a `/design` route or
   Storybook), on an accessible foundation such as Radix, shadcn/ui or React
   Aria. A screenshot of that page proves the system works.

## Exit gate

```bash
python3 $FR gate design
```

Needs every colour role, zero failing contrast pairs, and `components.md`.
Warns if dark tokens are absent.

## Hand off

Next is `franceska-build`; confirm the go with the user first.
