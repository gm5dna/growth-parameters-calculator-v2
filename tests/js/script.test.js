const {
  buildMeasurementSummaryRows,
  showChartFromSummary,
  __testHooks,
} = require('../../static/script');

describe('buildMeasurementSummaryRows', () => {
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
  // Regression: an earlier commit added this function without a test and
  // relied on `switchChartType` being defined in charts.js (loaded as a
  // sibling script at runtime). ESLint caught the cross-file reference once
  // `switchChartType` was added to its globals list; this test pins the
  // contract so any future rename fails fast.

  beforeEach(() => {
    document.body.innerHTML = `
      <section id="chartsSection" hidden></section>
      <button id="showChartsBtn"></button>
    `;
    global.switchChartType = jest.fn();
    // jsdom does not implement scrollIntoView.
    Element.prototype.scrollIntoView = jest.fn();
  });

  afterEach(() => {
    delete global.switchChartType;
  });

  test('reveals charts section, hides launch button, and switches chart', () => {
    showChartFromSummary('height');

    const section = document.getElementById('chartsSection');
    const btn = document.getElementById('showChartsBtn');

    expect(section.hidden).toBe(false);
    expect(btn.hidden).toBe(true);
    expect(global.switchChartType).toHaveBeenCalledTimes(1);
    expect(global.switchChartType).toHaveBeenCalledWith('height');
    expect(Element.prototype.scrollIntoView).toHaveBeenCalledWith({
      behavior: 'smooth',
      block: 'nearest',
    });
  });

  test('is a no-op on switchChartType when that global is missing', () => {
    delete global.switchChartType;

    expect(() => showChartFromSummary('weight')).not.toThrow();
    const section = document.getElementById('chartsSection');
    expect(section.hidden).toBe(false);
  });

  test('tolerates missing DOM elements', () => {
    document.body.innerHTML = '';
    expect(() => showChartFromSummary('bmi')).not.toThrow();
    expect(global.switchChartType).toHaveBeenCalledWith('bmi');
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
