let switchChartType, initCharts, __chartTestHooks, appState;

beforeAll(async () => {
  ({ switchChartType, initCharts, __chartTestHooks } = await import('../../static/charts.mjs'));
  ({ appState } = await import('../../static/state.mjs'));
});

describe('chart tab accessibility', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div class="chart-tabs" role="tablist" aria-label="Chart type">
        <button type="button" class="chart-tab active" role="tab" id="chartTab-height" data-chart="height" aria-selected="true" aria-controls="growthChartPanel">Height</button>
        <button type="button" class="chart-tab" role="tab" id="chartTab-weight" data-chart="weight" aria-selected="false" aria-controls="growthChartPanel">Weight</button>
        <button type="button" class="chart-tab" role="tab" id="chartTab-bmi" data-chart="bmi" aria-selected="false" aria-controls="growthChartPanel">BMI</button>
      </div>
      <div id="ageRangeSelector"></div>
      <div id="chartLoading" hidden></div>
      <div id="chartDescription"></div>
      <div id="growthChartPanel" role="tabpanel" aria-labelledby="chartTab-height">
        <canvas id="growthChart"></canvas>
      </div>
    `;
    appState.lastResults = { age_years: 6, height: { value: 114.2, centile: 36, sds: -0.36 } };
    appState.lastPayload = { sex: 'male', reference: 'uk-who' };
    window.Chart = jest.fn(() => ({ destroy: jest.fn() }));
    window.Chart.register = jest.fn();
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, centiles: [] }),
    });
  });

  afterEach(() => {
    appState.lastResults = null;
    appState.lastPayload = null;
    delete window.Chart;
    delete global.fetch;
  });

  test('switching chart type updates selected tab and roving tabindex', () => {
    switchChartType('weight');

    expect(document.getElementById('chartTab-height').getAttribute('aria-selected')).toBe('false');
    expect(document.getElementById('chartTab-height').getAttribute('tabindex')).toBe('-1');
    expect(document.getElementById('chartTab-weight').getAttribute('aria-selected')).toBe('true');
    expect(document.getElementById('chartTab-weight').getAttribute('tabindex')).toBe('0');
    expect(document.getElementById('growthChartPanel').getAttribute('aria-labelledby')).toBe('chartTab-weight');
  });

  test('arrow key moves from active tab to next tab', () => {
    initCharts();
    __chartTestHooks.syncChartTabsForTest('height');
    const heightTab = document.getElementById('chartTab-height');
    heightTab.focus();
    heightTab.dispatchEvent(new KeyboardEvent('keydown', {
      key: 'ArrowRight',
      bubbles: true,
    }));

    expect(document.getElementById('chartTab-weight').getAttribute('aria-selected')).toBe('true');
  });
});

describe('age range radios', () => {
  beforeEach(() => {
    document.body.innerHTML = `<div id="ageRangeSelector" role="radiogroup" aria-label="Age range"></div>`;
    appState.lastResults = { age_years: 6 };
  });

  afterEach(() => {
    appState.lastResults = null;
  });

  test('rendered age ranges have accessible labels', () => {
    __chartTestHooks.renderAgeRangeSelectorForTest('height');

    const radios = Array.from(document.querySelectorAll('#ageRangeSelector input[type="radio"]'));
    expect(radios.length).toBeGreaterThan(0);
    expect(radios[0].classList.contains('visually-hidden-control')).toBe(true);
    expect(radios[0].getAttribute('aria-label')).toBe('0-2 years');
  });
});
