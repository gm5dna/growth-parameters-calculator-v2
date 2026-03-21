/**
 * Growth chart — data fetching, caching, and centile curve rendering.
 *
 * Depends on Chart.js 4.x (loaded from CDN before this script).
 * Canvas element: <canvas id="growthChart">.
 * Loading indicator: <div id="chartLoading" hidden>.
 *
 * This module is extended in Tasks 5 (tabs/age-range) and 6 (measurement
 * plotting, MPH display, tooltips).
 */

/* ------------------------------------------------------------------ */
/*  Configuration constants                                           */
/* ------------------------------------------------------------------ */

var CENTILE_STYLES = {
  0.4:  { width: 1,   opacity: 0.2 },
  2:    { width: 1,   opacity: 0.4 },
  9:    { width: 1,   opacity: 0.4 },
  25:   { width: 1.5, opacity: 0.6 },
  50:   { width: 2,   opacity: 1.0 },
  75:   { width: 1.5, opacity: 0.6 },
  91:   { width: 1,   opacity: 0.4 },
  98:   { width: 1,   opacity: 0.4 },
  99.6: { width: 1,   opacity: 0.2 },
};

var Y_AXIS_LABELS = {
  height: 'Height / Length (cm)',
  weight: 'Weight (kg)',
  bmi:    'BMI (kg/m\u00B2)',
  ofc:    'Head Circumference (cm)',
};

var CHART_UNITS = {
  height: 'cm',
  weight: 'kg',
  bmi:    'kg/m\u00B2',
  ofc:    'cm',
};

var CHART_DISPLAY_NAMES = {
  height: 'Height',
  weight: 'Weight',
  bmi:    'BMI',
  ofc:    'Head Circumference',
};

/* ------------------------------------------------------------------ */
/*  Chart data cache                                                  */
/* ------------------------------------------------------------------ */

/** Cache keyed by "reference|method|sex", stores centile arrays. */
var chartDataCache = {};

/* ------------------------------------------------------------------ */
/*  Current Chart.js instance                                         */
/* ------------------------------------------------------------------ */

/** The active Chart.js instance, or null if no chart is rendered. */
var currentChart = null;

/* ------------------------------------------------------------------ */
/*  Age range configuration                                           */
/* ------------------------------------------------------------------ */

var AGE_RANGES = {
  height: [
    { label: '0\u20132 years', min: -0.5, max: 2 },
    { label: '0\u20134 years', min: -0.5, max: 4 },
    { label: '0\u201318 years', min: -0.5, max: 18 },
    { label: '2\u201318 years', min: 2, max: 18 },
    { label: '8\u201320 years', min: 8, max: 20 },
  ],
  weight: [
    { label: '0\u20132 years', min: -0.5, max: 2 },
    { label: '0\u20134 years', min: -0.5, max: 4 },
    { label: '0\u201318 years', min: -0.5, max: 18 },
    { label: '8\u201320 years', min: 8, max: 20 },
  ],
  bmi: [
    { label: '0\u20134 years', min: -0.5, max: 4 },
    { label: '2\u201318 years', min: 2, max: 18 },
    { label: '0\u201318 years', min: -0.5, max: 18 },
  ],
  ofc: [
    { label: '0\u20132 years', min: -0.5, max: 2 },
    { label: '0\u201318 years', min: -0.5, max: 18 },
  ],
};

/* ------------------------------------------------------------------ */
/*  Current chart type and age range tracking                         */
/* ------------------------------------------------------------------ */

var currentChartType = 'height';
var currentAgeRangeIndex = 0;

/* ------------------------------------------------------------------ */
/*  Intelligent default age range selection                           */
/* ------------------------------------------------------------------ */

/**
 * Determine the best default age range index for the given chart type,
 * child's age, and whether parental heights are available.
 *
 * @param {string} chartType         - "height"|"weight"|"bmi"|"ofc".
 * @param {number} ageYears          - Child's age in decimal years.
 * @param {boolean} hasParentalHeights - True if MPH data is present.
 * @returns {number}                  - Index into AGE_RANGES[chartType].
 */
function getDefaultAgeRange(chartType, ageYears, hasParentalHeights) {
  switch (chartType) {
    case 'height':
      if (ageYears < 2) return 0;       // 0-2
      if (ageYears < 4) return 1;       // 0-4
      return hasParentalHeights ? 3 : 2; // 2-18 or 0-18
    case 'weight':
      if (ageYears < 2) return 0;
      if (ageYears < 4) return 1;
      return 2;                          // 0-18
    case 'bmi':
      if (ageYears < 4) return 0;       // 0-4
      if (ageYears < 10) return 1;      // 2-18
      return 2;                          // 0-18
    case 'ofc':
      if (ageYears < 2) return 0;       // 0-2
      return 1;                          // 0-18
    default:
      return 0;
  }
}

/* ------------------------------------------------------------------ */
/*  Tab switching                                                     */
/* ------------------------------------------------------------------ */

/**
 * Switch to the given chart type: update active tab, rebuild the
 * age range selector with intelligent defaults, and fetch/render.
 *
 * @param {string} chartType - "height"|"weight"|"bmi"|"ofc".
 */
function switchChartType(chartType) {
  currentChartType = chartType;

  // Update active tab
  document.querySelectorAll('.chart-tab').forEach(function(tab) {
    if (tab.getAttribute('data-chart') === chartType) {
      tab.classList.add('active');
      tab.setAttribute('aria-selected', 'true');
    } else {
      tab.classList.remove('active');
      tab.setAttribute('aria-selected', 'false');
    }
  });

  // Build age range selector
  renderAgeRangeSelector(chartType);

  // Fetch and render
  loadAndRenderChart();
}

/* ------------------------------------------------------------------ */
/*  Age range selector                                                */
/* ------------------------------------------------------------------ */

/**
 * Populate the #ageRangeSelector container with radio buttons for
 * the given chart type, pre-selecting the intelligent default.
 *
 * @param {string} chartType - "height"|"weight"|"bmi"|"ofc".
 */
function renderAgeRangeSelector(chartType) {
  var container = document.getElementById('ageRangeSelector');
  if (!container) return;
  container.innerHTML = '';

  var ranges = AGE_RANGES[chartType] || [];
  var ageYears = (typeof lastResults !== 'undefined' && lastResults) ? lastResults.age_years || 0 : 0;
  var hasParentalHeights = (typeof lastResults !== 'undefined' && lastResults) ? !!lastResults.mid_parental_height : false;
  var defaultIndex = getDefaultAgeRange(chartType, ageYears, hasParentalHeights);
  currentAgeRangeIndex = defaultIndex;

  ranges.forEach(function(range, index) {
    var label = document.createElement('label');
    var radio = document.createElement('input');
    radio.type = 'radio';
    radio.name = 'ageRange';
    radio.value = index;
    radio.checked = (index === defaultIndex);
    radio.addEventListener('change', function() {
      currentAgeRangeIndex = index;
      loadAndRenderChart();
    });
    label.appendChild(radio);
    label.appendChild(document.createTextNode(range.label));
    container.appendChild(label);
  });
}

/* ------------------------------------------------------------------ */
/*  Load and render orchestrator                                      */
/* ------------------------------------------------------------------ */

/**
 * Fetch centile data for the current chart type and render it with
 * the currently selected age range. Reads reference and sex from
 * lastPayload (set by script.js after a successful calculation).
 */
async function loadAndRenderChart() {
  var reference = (typeof lastPayload !== 'undefined' && lastPayload) ? lastPayload.reference || 'uk-who' : 'uk-who';
  var sex = (typeof lastPayload !== 'undefined' && lastPayload) ? lastPayload.sex : 'male';
  var ranges = AGE_RANGES[currentChartType] || [];
  var ageRange = ranges[currentAgeRangeIndex] || ranges[0];

  try {
    var centiles = await fetchChartData(reference, currentChartType, sex);
    renderChart(centiles, ageRange, currentChartType);
  } catch (err) {
    console.error('Chart render failed:', err);
  }
}

/* ------------------------------------------------------------------ */
/*  Show / close charts                                               */
/* ------------------------------------------------------------------ */

/**
 * Reveal the charts section, hide the "Show Growth Charts" button,
 * default to the height tab, and scroll to the chart.
 */
function showCharts() {
  var chartsSection = document.getElementById('chartsSection');
  var showChartsBtn = document.getElementById('showChartsBtn');
  if (chartsSection) chartsSection.hidden = false;
  if (showChartsBtn) showChartsBtn.hidden = true;

  switchChartType('height');
  if (chartsSection) chartsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/**
 * Hide the charts section, restore the "Show Growth Charts" button,
 * and destroy the active chart to free resources.
 */
function closeCharts() {
  var chartsSection = document.getElementById('chartsSection');
  var showChartsBtn = document.getElementById('showChartsBtn');
  if (chartsSection) chartsSection.hidden = true;
  if (showChartsBtn) showChartsBtn.hidden = false;
  destroyChart();
}

/* ------------------------------------------------------------------ */
/*  Data fetching                                                     */
/* ------------------------------------------------------------------ */

/**
 * Fetch centile curve data from /chart-data for the given parameters.
 * Returns the cached result if available; otherwise POSTs to the server.
 *
 * Shows #chartLoading while the fetch is in progress and hides it when
 * complete (whether the request succeeds or fails).
 *
 * @param {string} reference       - Growth reference (e.g. "uk-who").
 * @param {string} method          - Measurement method: height|weight|bmi|ofc.
 * @param {string} sex             - "male" or "female".
 * @returns {Promise<Array>}       - Array of centile objects [{centile, sds, data: [{x,y}]}].
 */
function fetchChartData(reference, method, sex) {
  var cacheKey = reference + '|' + method + '|' + sex;

  if (chartDataCache[cacheKey]) {
    return Promise.resolve(chartDataCache[cacheKey]);
  }

  var loadingEl = document.getElementById('chartLoading');
  if (loadingEl) loadingEl.hidden = false;

  return fetch('/chart-data', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      reference: reference,
      measurement_method: method,
      sex: sex,
    }),
  })
    .then(function (response) {
      if (!response.ok) {
        return response.json().then(function (body) {
          throw new Error(body.error || 'Failed to fetch chart data.');
        });
      }
      return response.json();
    })
    .then(function (data) {
      if (!data.success || !Array.isArray(data.centiles)) {
        throw new Error('Unexpected response from /chart-data.');
      }
      chartDataCache[cacheKey] = data.centiles;
      return data.centiles;
    })
    .finally(function () {
      if (loadingEl) loadingEl.hidden = true;
    });
}

/* ------------------------------------------------------------------ */
/*  Data filtering                                                    */
/* ------------------------------------------------------------------ */

/**
 * Return a new centile array with data points filtered to the given age
 * range (inclusive on both ends).
 *
 * @param {Array}  centiles - Array of centile objects from the cache.
 * @param {number} minAge   - Minimum age in years.
 * @param {number} maxAge   - Maximum age in years.
 * @returns {Array}         - Deep-ish copy with filtered data arrays.
 */
function filterDataToRange(centiles, minAge, maxAge) {
  return centiles.map(function (centile) {
    return {
      centile: centile.centile,
      sds: centile.sds,
      data: centile.data.filter(function (point) {
        return point.x >= minAge && point.x <= maxAge;
      }),
    };
  });
}

/* ------------------------------------------------------------------ */
/*  Chart destruction                                                 */
/* ------------------------------------------------------------------ */

/**
 * Destroy the current Chart.js instance to free resources and prevent
 * memory leaks. Safe to call even if no chart exists.
 */
function destroyChart() {
  if (currentChart) {
    currentChart.destroy();
    currentChart = null;
  }
}

/* ------------------------------------------------------------------ */
/*  Chart rendering                                                   */
/* ------------------------------------------------------------------ */

/**
 * Build datasets from centile data, applying the graduated styling
 * defined in CENTILE_STYLES.
 *
 * @param {Array} centiles - Filtered centile array.
 * @returns {Array}        - Chart.js dataset objects.
 */
function buildCentileDatasets(centiles) {
  return centiles.map(function (centile) {
    var style = CENTILE_STYLES[centile.centile] || { width: 1, opacity: 0.3 };
    var borderColor =
      centile.centile === 50
        ? '#1e40af'
        : 'rgba(107, 114, 128, ' + style.opacity + ')';

    return {
      label: 'Centile ' + centile.centile,
      data: centile.data,
      borderColor: borderColor,
      borderWidth: style.width,
      fill: false,
      tension: 0.4,
      pointRadius: 0,
      centileLabel: String(centile.centile),
    };
  });
}

/**
 * Create or replace the Chart.js instance on #growthChart with the
 * supplied centile data.
 *
 * @param {Array}  centiles  - Full centile array (will be filtered).
 * @param {Object} ageRange  - { min: number, max: number } in years.
 * @param {string} chartType - "height"|"weight"|"bmi"|"ofc".
 */
function renderChart(centiles, ageRange, chartType) {
  destroyChart();

  var canvas = document.getElementById('growthChart');
  if (!canvas) return;

  var filtered = filterDataToRange(centiles, ageRange.min, ageRange.max);
  var datasets = buildCentileDatasets(filtered);

  var config = {
    type: 'line',
    data: { datasets: datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      scales: {
        x: {
          type: 'linear',
          title: { display: true, text: 'Age (years)' },
          min: ageRange.min,
          max: ageRange.max,
        },
        y: {
          type: 'linear',
          title: { display: true, text: Y_AXIS_LABELS[chartType] || '' },
        },
      },
      plugins: {
        legend: { display: false },
        tooltip: { enabled: false },
      },
      elements: {
        point: { radius: 0 },
      },
      layout: {
        padding: { right: 40 },
      },
    },
  };

  currentChart = new Chart(canvas.getContext('2d'), config);
}

/* ------------------------------------------------------------------ */
/*  Event listeners                                                   */
/* ------------------------------------------------------------------ */

document.addEventListener('DOMContentLoaded', function() {
  // Show Charts button
  var showChartsBtn = document.getElementById('showChartsBtn');
  if (showChartsBtn) showChartsBtn.addEventListener('click', showCharts);

  // Close Charts button
  var closeChartsBtn = document.getElementById('closeChartsBtn');
  if (closeChartsBtn) closeChartsBtn.addEventListener('click', closeCharts);

  // Chart tabs
  document.querySelectorAll('.chart-tab').forEach(function(tab) {
    tab.addEventListener('click', function() {
      switchChartType(tab.getAttribute('data-chart'));
    });
  });
});
