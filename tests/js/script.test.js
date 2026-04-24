let buildMeasurementSummaryRows,
  showChartFromSummary,
  resetForm,
  __testHooks,
  appState;

beforeAll(async () => {
  ({
    buildMeasurementSummaryRows,
    showChartFromSummary,
    resetForm,
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
