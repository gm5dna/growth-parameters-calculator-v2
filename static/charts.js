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
