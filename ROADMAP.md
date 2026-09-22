# Roadmap

Planned work not yet scheduled. Specifications live in `spec/`.

## Features

### Add Sogroya (somapacitan) to the GH calculator
Sogroya is a once-weekly, long-acting growth hormone. The calculator currently
models daily GH only: initial dose = 7 mg/m²/week ÷ 7, rounded to the step of
a daily pen (`GH_PEN_DEVICES` in `static/script.mjs`). Supporting Sogroya needs:

- a weekly dosing mode (dose per week, not per day) in the backend
  (`calculate_gh_dose` in `calculations.py`), UI, clipboard text and PDF;
- its pen devices, strengths and dial increments;
- the licensed paediatric dosing basis and starting dose.

**Open questions — confirm from primary sources before building:** the
paediatric starting dose and its basis (e.g. per kg vs per m²), dose
adjustment rules, and pen strengths/increments. Sources: Sogroya SmPC, BNF for
Children, and the local NHS Highland endocrine protocol.

## UX

### Native `<details>` for the collapsible form sections
Replace the hand-rolled toggles for "Previous measurements" and "Bone age"
(`setCollapsibleState` / `toggleCollapsible` in `static/script.mjs`) with
`<details>`/`<summary>`. Changes UI behaviour, so re-check reset and form
restore, and test in the browser.

## Operations

- **Uptime monitoring:** an external check on `https://growth.gm5dna.com/health`
  (also catches Watchtower not picking up a new image — the response includes
  the rcpchgrowth version).
- **Deploy downtime:** Watchtower recreates the container, so each deploy has
  about 20 seconds of Cloudflare 1033 errors. Only worth fixing (e.g. a
  second container behind the tunnel) if the tool is used in live clinics.
