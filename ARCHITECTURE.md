# Architecture

This project is a stateless Flask single-page application for paediatric growth
calculations. It is designed for privacy: requests are processed in memory and
the application does not use a database or retain patient-identifiable health
information.

## Request Flow

The browser collects input, provides client-side validation for usability, and
displays results. Clinical validation and calculations are authoritative only on
the Flask server.

The main calculation path is shared:

- `/calculate` parses JSON input and calls `perform_calculation()` in `app.py`.
- `/export-pdf` also calls `perform_calculation()` before rendering the report.
- `validation.py` owns server-side input validation and rejects unsafe payloads.
- `models.py` wraps the mandatory `rcpchgrowth` library for growth reference
  calculations, SDS, centiles, and supported measurement checks.
- `calculations.py` contains derived calculations such as age, BSA, gestation
  correction, height velocity, and growth hormone dose helpers.

PDF export deliberately recalculates from the submitted measurement inputs and
ignores any client-supplied result objects.

## Frontend

The frontend is vanilla JavaScript using ES modules. `templates/index.html`
loads self-hosted Chart.js vendor scripts from `static/vendor/` and then loads
`static/main.mjs` as the module entrypoint.

Important frontend modules include:

- `static/script.mjs` for form orchestration and UI updates.
- `static/charts.mjs` for Chart.js setup and chart rendering.
- `static/state.mjs` for shared browser-side state.
- `static/validation.mjs` for client-side validation messages.
- `static/clipboard.mjs` for copy-to-clipboard formatting.

## Clinical Safety Rules

- Server-side validation is authoritative; client-side validation is for user
  experience only.
- Do not persist PHI in localStorage, logs, databases, or any other durable
  storage.
- Do not manually implement growth references. All reference calculations must
  go through `rcpchgrowth`.
- Do not display clinical results that have not passed server validation.
- PDF export must continue to recalculate server-side and must not trust
  client-supplied calculation results.
