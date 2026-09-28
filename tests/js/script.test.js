let buildMeasurementSummaryRows,
  buildExportPdfPayload,
  resetForm,
  initApp,
  __testHooks,
  appState,
  showCharts,
  gatherFormData,
  handleSubmit;

beforeAll(async () => {
  ({
    buildMeasurementSummaryRows,
    buildExportPdfPayload,
    resetForm,
    initApp,
    __testHooks,
    gatherFormData,
    handleSubmit,
  } = await import('../../static/script.mjs'));
  ({ appState } = await import('../../static/state.mjs'));
  ({ showCharts } = await import('../../static/charts.mjs'));
});

describe('buildMeasurementSummaryRows', () => {
  test('can be imported without a Chart.js browser global', () => {
    expect(buildMeasurementSummaryRows).toEqual(expect.any(Function));
  });

  test('returns compact measurement rows with formatted centile and SDS', () => {
    const rows = buildMeasurementSummaryRows({
      weight: { value: 18.2, centile: 16.7, sds: -0.97 },
      height: { value: 110.4, centile: 16.6, sds: -0.97 },
      bmi: { value: 14.9, centile: 31.1, sds: -0.49, percentage_median: 96.1 },
      ofc: { value: 51.2, centile: 10.6, sds: -1.25 },
    });

    expect(rows).toEqual([
      { key: 'weight', label: 'Weight', value: '18.2 kg', centile: '16.7%', sds: '-0.97', extra: '', band: '' },
      { key: 'height', label: 'Height', value: '110.4 cm', centile: '16.6%', sds: '-0.97', extra: '', band: '' },
      { key: 'bmi', label: 'BMI', value: '14.9 kg/m²', centile: '31.1%', sds: '-0.49', extra: '96.1% median', band: '' },
      { key: 'ofc', label: 'OFC', value: '51.2 cm', centile: '10.6%', sds: '-1.25', extra: '', band: '' },
    ]);
  });

  test('carries the RCPCH centile band sentence when present', () => {
    const rows = buildMeasurementSummaryRows({
      height: { value: 110.4, centile: 16.6, sds: -0.97, centile_band: 'This height measurement is on or near the 9th centile.' },
    });
    expect(rows[0].band).toBe('This height measurement is on or near the 9th centile.');
  });

  test('band is empty when the server gives none', () => {
    const rows = buildMeasurementSummaryRows({ weight: { value: 12, centile: null, sds: null } });
    expect(rows[0].band).toBe('');
  });

  test('omits missing measurements and preserves chart keys', () => {
    const rows = buildMeasurementSummaryRows({
      weight: { value: 12, centile: null, sds: null },
    });

    expect(rows).toEqual([
      { key: 'weight', label: 'Weight', value: '12 kg', centile: 'N/A', sds: 'N/A', extra: '', band: '' },
    ]);
  });
});

describe('showCharts', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <section id="chartsSection" hidden></section>
      <button id="showChartsBtn"></button>
      <div class="chart-tabs">
        <button type="button" class="chart-tab active" data-chart="height" aria-selected="true">Height</button>
        <button type="button" class="chart-tab" data-chart="weight" aria-selected="false">Weight</button>
      </div>
      <div id="ageRangeSelector"></div>
    `;
    window.Chart = jest.fn(() => ({ destroy: jest.fn() }));
    window.Chart.register = jest.fn();
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, centiles: [] }),
    });
    // jsdom does not implement scrollIntoView.
    Element.prototype.scrollIntoView = jest.fn();
  });

  afterEach(() => {
    delete window.Chart;
    delete global.fetch;
  });

  test('reveals charts section, hides launch button, and switches chart type', () => {
    showCharts('weight');

    const section = document.getElementById('chartsSection');
    const btn = document.getElementById('showChartsBtn');

    expect(section.hidden).toBe(false);
    expect(btn.hidden).toBe(true);
    expect(document.querySelector('[data-chart="weight"]').classList.contains('active')).toBe(true);
    expect(document.querySelector('[data-chart="weight"]').getAttribute('aria-selected')).toBe('true');
    expect(global.fetch).toHaveBeenCalledWith('/chart-data', expect.objectContaining({
      body: expect.stringContaining('"measurement_method":"weight"'),
    }));
    expect(Element.prototype.scrollIntoView).toHaveBeenCalledWith({
      behavior: 'smooth',
      block: 'nearest',
    });
  });

  test('tolerates missing DOM elements', () => {
    document.body.innerHTML = '';
    expect(() => showCharts('bmi')).not.toThrow();
  });
});

describe('resetForm chart lifecycle', () => {
  test('destroys the live Chart.js instance before clearing shared state', () => {
    document.body.innerHTML = `
      <form id="growthForm"></form>
      <section id="chartsSection"></section>
      <button id="showChartsBtn"></button>
    `;
    const destroy = jest.fn();
    appState.currentChart = { destroy };
    appState.lastResults = { age_years: 10 };
    appState.lastPayload = { sex: 'female' };

    resetForm();

    expect(destroy).toHaveBeenCalledTimes(1);
    expect(appState.currentChart).toBeNull();
    expect(appState.lastResults).toBeNull();
    expect(appState.lastPayload).toBeNull();
  });
});

describe('buildExportPdfPayload', () => {
  afterEach(() => {
    appState.lastPayload = null;
  });

  test('sends calculate inputs at top level for server-side PDF recalculation', () => {
    appState.lastPayload = {
      sex: 'female',
      birth_date: '2020-06-15',
      measurement_date: '2023-06-15',
      reference: 'uk-who',
      weight: 14.5,
      height: 96,
    };

    const payload = buildExportPdfPayload({ height: 'data:image/png;base64,abc' });

    expect(payload).toMatchObject({
      sex: 'female',
      birth_date: '2020-06-15',
      measurement_date: '2023-06-15',
      reference: 'uk-who',
      weight: 14.5,
      height: 96,
      chart_images: { height: 'data:image/png;base64,abc' },
    });
    expect(payload).not.toHaveProperty('results');
    expect(payload.patient_info).toEqual({});
  });
});

describe('updateGhDisplay', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <output id="ghDoseValue"></output>
      <div id="ghResults"></div>
      <div id="ghPenInfo"></div>
      <select id="ghPenDevice">
        <option value="norditropin" selected>Norditropin</option>
      </select>
    `;
  });

  test('renders GH dose result lines as text nodes in child elements', () => {
    const resultsDiv = document.getElementById('ghResults');
    Object.defineProperty(resultsDiv, 'innerHTML', {
      configurable: true,
      get() {
        return '';
      },
      set() {
        throw new Error('updateGhDisplay must render result lines without innerHTML');
      },
    });

    __testHooks.setGhState({ dose: 0.7, bsa: 1.2, weightKg: 20 });
    __testHooks.updateGhDisplay();

    const resultLines = Array.from(document.querySelectorAll('#ghResults div'));
    expect(resultLines.map((line) => line.textContent)).toEqual([
      '= 4.1 mg/m²/week',
      '= 35.0 mcg/kg/day',
    ]);
    expect(resultLines).toHaveLength(2);
    resultLines.forEach((line) => {
      expect(line.tagName).toBe('DIV');
      expect(line.children).toHaveLength(0);
    });
  });
});

describe('debounce', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  test('cancel prevents a pending call from firing', () => {
    const fn = jest.fn();
    const debounced = __testHooks.createDebounced(fn, 500);

    debounced('first');
    debounced.cancel();
    jest.advanceTimersByTime(500);

    expect(fn).not.toHaveBeenCalled();
  });
});

describe('calculate request sequencing', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    document.body.innerHTML = `
      <form id="growthForm">
        <input type="radio" name="sex" id="sexMale" value="male" checked />
        <input type="radio" name="sex" id="sexFemale" value="female" />
        <input type="date" id="birthDate" value="2018-04-25" />
        <input type="date" id="measurementDate" value="2024-04-25" />
        <input type="number" id="weight" value="20.5" />
        <input type="number" id="height" value="114.2" />
        <input type="number" id="ofc" value="" />
        <input type="number" id="maternalHeight" value="" />
        <input type="number" id="paternalHeight" value="" />
        <input type="number" id="gestationWeeks" value="" />
        <input type="number" id="gestationDays" value="" />
        <select id="reference"><option value="uk-who" selected>UK-WHO</option></select>
        <input type="checkbox" id="ghTreatment" />
        <button type="submit" id="calculateBtn">Calculate</button>
        <button type="button" id="resetBtn">Reset</button>
      </form>
      <div id="errorDisplay" hidden><p id="errorMessage"></p></div>
      <section id="resultsSection" hidden></section>
      <div id="measurementSummary" hidden></div>
      <div id="resultsGrid"></div>
      <div id="warningsDisplay" hidden><ul id="warningsList"></ul></div>
      <button id="showChartsBtn" hidden>Show Growth Charts</button>
      <section id="chartsSection" hidden></section>
      <div id="ghCalculator" hidden></div>
      <div id="toast" hidden></div>
      <div id="disclaimer"></div>
      <button id="dismissDisclaimer"></button>
      <button id="themeToggle"></button>
    `;
    Element.prototype.scrollIntoView = jest.fn();
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        results: {
          age_years: 6,
          age_calendar: { years: 6, months: 0, days: 0 },
          weight: { value: 20.5, centile: 45.9, sds: -0.1 },
        },
      }),
    });
    initApp();
  });

  afterEach(() => {
    jest.useRealTimers();
    delete global.fetch;
  });

  test('H1: switching mode recalculates (toggle is outside the form)', async () => {
    const { handleModeToggle } = await import('../../static/script.mjs');
    const toggle = document.createElement('input');
    toggle.type = 'checkbox';
    toggle.id = 'modeToggle';
    document.body.appendChild(toggle);

    handleModeToggle();
    jest.advanceTimersByTime(900);
    await Promise.resolve();

    expect(global.fetch).toHaveBeenCalledTimes(1);
    toggle.remove();
    localStorage.clear(); // handleModeToggle's debounced save would leak into later restores
  });

  test('manual submit cancels a pending auto-calculate', async () => {
    __testHooks.resetCalculateState();
    __testHooks.scheduleAutoCalculate();

    document.getElementById('growthForm').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    await Promise.resolve();
    jest.advanceTimersByTime(900);
    await Promise.resolve();

    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

  test('does not reveal Show Growth Charts while charts are already open', () => {
    const charts = document.getElementById('chartsSection');
    const button = document.getElementById('showChartsBtn');
    charts.hidden = false;
    button.hidden = true;

    __testHooks.renderResultsForTest({
      age_years: 6,
      age_calendar: { years: 6, months: 0, days: 0 },
      weight: { value: 20.5, centile: 45.9, sds: -0.1 },
    });

    expect(charts.hidden).toBe(false);
    expect(button.hidden).toBe(true);
  });
});

describe('collapsible sections', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <button type="button" class="collapsible-header" id="prevMeasurementsToggle" aria-expanded="false" aria-controls="prevMeasurementsContent">
        <span class="material-symbols-outlined" aria-hidden="true">add</span>
        <span>Add Previous Measurement</span>
      </button>
      <div id="prevMeasurementsContent" hidden>
        <table><tbody id="prevMeasurementsBody"></tbody></table>
      </div>
    `;
  });

  test('opening and closing keeps aria-expanded and icon in sync', () => {
    const toggle = document.getElementById('prevMeasurementsToggle');
    const content = document.getElementById('prevMeasurementsContent');

    __testHooks.toggleCollapsibleForTest(toggle, content);
    expect(content.hidden).toBe(false);
    expect(toggle.getAttribute('aria-expanded')).toBe('true');
    expect(toggle.querySelector('.material-symbols-outlined').textContent).toBe('remove');

    __testHooks.toggleCollapsibleForTest(toggle, content);
    expect(content.hidden).toBe(true);
    expect(toggle.getAttribute('aria-expanded')).toBe('false');
    expect(toggle.querySelector('.material-symbols-outlined').textContent).toBe('add');
  });
});

describe('advanced table row labels', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <table><tbody id="prevMeasurementsBody"></tbody></table>
      <table><tbody id="boneAgeBody"></tbody></table>
    `;
  });

  test('previous measurement cells include mobile data labels and input aria labels', () => {
    __testHooks.addPreviousMeasurementRowForTest('2024-01-01', '100', '16', '50');

    const cells = Array.from(document.querySelectorAll('#prevMeasurementsBody td'));
    expect(cells.map((cell) => cell.getAttribute('data-label'))).toEqual([
      'Date',
      'Height (cm)',
      'Weight (kg)',
      'OFC (cm)',
      'Remove',
    ]);
    expect(document.querySelector('.prev-height').getAttribute('aria-label')).toBe('Height (cm)');
  });

  test('bone age cells include mobile data labels and select aria label', () => {
    __testHooks.addBoneAgeRowForTest('2024-01-01', '6.5', 'gp');

    const cells = Array.from(document.querySelectorAll('#boneAgeBody td'));
    expect(cells.map((cell) => cell.getAttribute('data-label'))).toEqual([
      'Assessment date',
      'Bone age (years)',
      'Standard',
      'Remove',
    ]);
    expect(document.querySelector('.ba-standard').getAttribute('aria-label')).toBe('Bone age standard');
  });
});

describe('localDateString (review #4 — local, not UTC)', () => {
  let localDateString;
  beforeAll(async () => {
    ({ localDateString } = await import('../../static/script.mjs'));
  });

  test('formats a local date as YYYY-MM-DD with zero padding', () => {
    // 3 July 2026, 00:30 local time
    const d = new Date(2026, 6, 3, 0, 30, 0);
    expect(localDateString(d)).toBe('2026-07-03');
  });

  test('defaults to now when called with no argument', () => {
    const now = new Date();
    const expected = now.getFullYear() + '-' +
      String(now.getMonth() + 1).padStart(2, '0') + '-' +
      String(now.getDate()).padStart(2, '0');
    expect(localDateString()).toBe(expected);
  });

  test('pads single-digit months and days', () => {
    expect(localDateString(new Date(2026, 0, 5))).toBe('2026-01-05');
  });
});

describe('review fixes: basic mode, reset, gestation, Escape, PDF dose', () => {
  const html = `
    <form id="growthForm">
      <input type="radio" name="sex" id="sexMale" value="male" checked />
      <input type="date" id="birthDate" value="2018-04-25" />
      <input type="date" id="measurementDate" value="2024-04-25" />
      <input type="number" id="weight" value="20.5" />
      <input type="number" id="height" value="114.2" />
      <input type="number" id="ofc" value="" />
      <input type="number" id="maternalHeight" value="170" min="120" max="220" />
      <input type="number" id="paternalHeight" value="180" min="120" max="220" />
      <input type="number" id="gestationWeeks" value="30" />
      <input type="number" id="gestationDays" value="" />
      <span id="gestationError"></span>
      <select id="reference"><option value="turner" selected>Turner</option></select>
      <input type="checkbox" id="ghTreatment" checked />
      <select id="ghPenDevice"><option value="surepal-10" selected>SurePal 10</option></select>
      <button type="submit" id="calculateBtn">Calculate</button>
      <button type="button" id="resetBtn">Reset</button>
    </form>
    <div id="errorDisplay" hidden><p id="errorMessage"></p></div>
    <section id="resultsSection" hidden></section>
    <div id="measurementSummary" hidden></div>
    <div id="resultsGrid"></div>
    <div id="warningsDisplay" hidden><ul id="warningsList"></ul></div>
    <button id="showChartsBtn" hidden></button>
    <section id="chartsSection" hidden></section>
    <div id="ghCalculator" hidden></div>
    <div id="toast" hidden></div>
    <div id="disclaimer"></div>
    <button id="dismissDisclaimer"></button>
    <button id="themeToggle"></button>
  `;

  beforeEach(() => {
    document.body.className = '';
    document.body.innerHTML = html;
    Element.prototype.scrollIntoView = jest.fn();
    global.fetch = jest.fn();
    __testHooks.resetCalculateState();
    initApp();
  });

  afterEach(() => {
    delete global.fetch;
    appState.lastPayload = null;
  });

  test('H1: basic mode omits advanced-only fields from the payload', () => {
    const p = gatherFormData();
    ['reference', 'gestation_weeks', 'gh_treatment', 'maternal_height', 'paternal_height']
      .forEach((k) => expect(p).not.toHaveProperty(k));
    expect(p.weight).toBe(20.5);
    // values are kept, not cleared
    expect(document.getElementById('gestationWeeks').value).toBe('30');
  });

  test('H1: advanced mode includes them', () => {
    document.body.classList.add('advanced-mode');
    const p = gatherFormData();
    expect(p).toMatchObject({ reference: 'turner', gestation_weeks: 30, gh_treatment: true, maternal_height: 170 });
  });

  test('M6: basic mode ignores (does not validate) hidden gestation', async () => {
    document.getElementById('gestationWeeks').value = '36.5';
    await handleSubmit(new Event('submit', { cancelable: true }));
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

  test('M6: 36.5 weeks rejected client-side in advanced mode', async () => {
    document.body.classList.add('advanced-mode');
    document.getElementById('gestationWeeks').value = '36.5';
    await handleSubmit(new Event('submit', { cancelable: true }));
    expect(global.fetch).not.toHaveBeenCalled();
    expect(document.getElementById('gestationError').textContent).toMatch(/whole number/);
    expect(document.getElementById('gestationWeeks').getAttribute('aria-invalid')).toBe('true');
  });

  test('M6: sends gestation as Number', () => {
    document.body.classList.add('advanced-mode');
    expect(typeof gatherFormData().gestation_weeks).toBe('number');
  });

  test('H4: a response arriving after reset is ignored', async () => {
    let resolve;
    global.fetch.mockReturnValue(new Promise((r) => { resolve = r; }));
    const pending = handleSubmit(new Event('submit', { cancelable: true }));
    resetForm();
    resolve({
      ok: true,
      status: 200,
      json: async () => ({ success: true, results: { age_years: 6, age_calendar: { years: 6, months: 0, days: 0 } } }),
    });
    await pending;
    expect(document.getElementById('resultsSection').hidden).toBe(true);
    expect(appState.lastResults).toBeNull();
    expect(document.getElementById('calculateBtn').disabled).toBe(false);
  });

  test('L8: non-JSON error response reports the status', async () => {
    global.fetch.mockResolvedValue({ ok: false, status: 429, json: async () => { throw new Error('html'); } });
    await handleSubmit(new Event('submit', { cancelable: true }));
    expect(document.getElementById('errorMessage').textContent).toMatch(/429/);
  });

  test('M7: server failure hides stale results and clears state', async () => {
    document.getElementById('resultsSection').hidden = false;
    appState.lastResults = { age_years: 1 };
    global.fetch.mockResolvedValue({ ok: false, status: 400, json: async () => ({ success: false, error: 'bad' }) });
    await handleSubmit(new Event('submit', { cancelable: true }));
    expect(document.getElementById('resultsSection').hidden).toBe(true);
    expect(appState.lastResults).toBeNull();
  });

  test('M10: Escape in an input does not reset; outside inputs it does', () => {
    const weight = document.getElementById('weight');
    weight.value = '99';
    weight.focus();
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    expect(weight.value).toBe('99');
    weight.blur();
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    expect(document.getElementById('weight').value).toBe('20.5'); // form.reset() to defaults
  });

  test('M5: PDF payload carries the on-screen GH dose only when calculator is visible', () => {
    appState.lastPayload = { sex: 'male' };
    __testHooks.setGhState({ dose: 0.9, bsa: 1, weightKg: 20 });
    expect(buildExportPdfPayload({})).not.toHaveProperty('gh_selected_daily_dose_mg');
    document.getElementById('ghCalculator').hidden = false;
    expect(buildExportPdfPayload({}).gh_selected_daily_dose_mg).toBe(0.9);
  });
});

