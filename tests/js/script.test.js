let buildMeasurementSummaryRows,
  buildExportPdfPayload,
  showChartFromSummary,
  resetForm,
  initApp,
  __testHooks,
  appState;

beforeAll(async () => {
  ({
    buildMeasurementSummaryRows,
    buildExportPdfPayload,
    showChartFromSummary,
    resetForm,
    initApp,
    __testHooks,
  } = await import('../../static/script.mjs'));
  ({ appState } = await import('../../static/state.mjs'));
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
      { key: 'weight', label: 'Weight', value: '18.2 kg', centile: '16.7%', sds: '-0.97', extra: '' },
      { key: 'height', label: 'Height', value: '110.4 cm', centile: '16.6%', sds: '-0.97', extra: '' },
      { key: 'bmi', label: 'BMI', value: '14.9 kg/m²', centile: '31.1%', sds: '-0.49', extra: '96.1% median' },
      { key: 'ofc', label: 'OFC', value: '51.2 cm', centile: '10.6%', sds: '-1.25', extra: '' },
    ]);
  });

  test('omits missing measurements and preserves chart keys', () => {
    const rows = buildMeasurementSummaryRows({
      weight: { value: 12, centile: null, sds: null },
    });

    expect(rows).toEqual([
      { key: 'weight', label: 'Weight', value: '12 kg', centile: 'N/A', sds: 'N/A', extra: '' },
    ]);
  });
});

describe('showChartFromSummary', () => {
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
    showChartFromSummary('weight');

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
    expect(() => showChartFromSummary('bmi')).not.toThrow();
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

  test('flush runs the pending call immediately once', () => {
    const fn = jest.fn();
    const debounced = __testHooks.createDebounced(fn, 500);

    debounced('first', 'second');
    debounced.flush();
    jest.advanceTimersByTime(500);

    expect(fn).toHaveBeenCalledTimes(1);
    expect(fn).toHaveBeenCalledWith('first', 'second');
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
