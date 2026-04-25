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

import { appState } from './state.mjs';

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
/*  Theme-aware chart colours                                         */
/* ------------------------------------------------------------------ */

/**
 * Convert a hex colour string to comma-separated RGB components.
 *
 * @param {string} hex - Hex colour, e.g. "#6b7280".
 * @returns {string}   - "r, g, b" string for use in rgba().
 */
function hexToRgb(hex) {
    var r = parseInt(hex.slice(1, 3), 16);
    var g = parseInt(hex.slice(3, 5), 16);
    var b = parseInt(hex.slice(5, 7), 16);
    return r + ', ' + g + ', ' + b;
}

/**
 * Return chart colour palette appropriate for the current theme.
 *
 * @returns {Object} - Colour values keyed by role.
 */
function getChartColors() {
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    var sex = (typeof appState.lastPayload !== 'undefined' && appState.lastPayload) ? appState.lastPayload.sex : 'male';
    var isFemale = sex === 'female';

    return {
        centileLine: isFemale
            ? (isDark ? '#c88a9e' : '#b0466a')
            : (isDark ? '#8a9cac' : '#5a7080'),
        median: isFemale
            ? (isDark ? '#d87aa0' : '#8e3060')
            : (isDark ? '#5aadcc' : '#1a5c7a'),
        currentMarker: isFemale
            ? (isDark ? '#d86a94' : '#c24070')
            : (isDark ? '#38b0cc' : '#1a7a96'),
        previousMarker: isDark ? '#6b7280' : '#9ca3af',
        gridColor: isDark ? '#2d3b4d' : '#dce1e8',
        textColor: isDark ? '#e8ecf1' : '#1a2332',
        labelColor: isFemale
            ? (isDark ? '#c88a9e' : '#8e3060')
            : (isDark ? '#8a9cac' : '#5a7080'),
        bgColor: isDark ? '#1c2733' : '#ffffff',
    };
}

/* ------------------------------------------------------------------ */
/*  Chart data cache                                                  */
/* ------------------------------------------------------------------ */

/** Cache keyed by "reference|method|sex", stores centile arrays. */
var chartDataCache = {};
var chartPluginsRegistered = false;
var activeChartRequestId = 0;

/* ------------------------------------------------------------------ */
/*  Age range configuration                                           */
/* ------------------------------------------------------------------ */

var AGE_RANGES = {
  height: [
    { label: '0\u20132 years', min: 0, max: 2 },
    { label: '0\u20134 years', min: 0, max: 4 },
    { label: '0\u201318 years', min: 0, max: 18 },
    { label: '2\u201318 years', min: 2, max: 18 },
    { label: '8\u201320 years', min: 8, max: 20 },
  ],
  weight: [
    { label: '0\u20132 years', min: 0, max: 2 },
    { label: '0\u20134 years', min: 0, max: 4 },
    { label: '0\u201318 years', min: 0, max: 18 },
    { label: '8\u201320 years', min: 8, max: 20 },
  ],
  bmi: [
    { label: '0\u20134 years', min: 0, max: 4 },
    { label: '2\u201318 years', min: 2, max: 18 },
    { label: '0\u201318 years', min: 0, max: 18 },
  ],
  ofc: [
    { label: '0\u20132 years', min: 0, max: 2 },
    { label: '0\u201318 years', min: 0, max: 18 },
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
export function switchChartType(chartType) {
  currentChartType = chartType;

  syncChartTabs(chartType);

  // Build age range selector
  renderAgeRangeSelector(chartType);

  // Fetch and render
  loadAndRenderChart();
}

function syncChartTabs(chartType) {
  var panel = document.getElementById('growthChartPanel');
  document.querySelectorAll('.chart-tab').forEach(function(tab) {
    var isActive = tab.getAttribute('data-chart') === chartType;
    tab.classList.toggle('active', isActive);
    tab.setAttribute('aria-selected', isActive ? 'true' : 'false');
    tab.setAttribute('tabindex', isActive ? '0' : '-1');
    if (isActive && panel && tab.id) {
      panel.setAttribute('aria-labelledby', tab.id);
    }
  });
}

function handleChartTabKeydown(event) {
  var keys = ['ArrowLeft', 'ArrowRight', 'Home', 'End'];
  if (keys.indexOf(event.key) === -1) return;
  var tabs = Array.from(document.querySelectorAll('.chart-tab'));
  if (!tabs.length) return;
  var currentIndex = tabs.indexOf(event.currentTarget);
  if (currentIndex === -1) return;

  event.preventDefault();
  var nextIndex = currentIndex;
  if (event.key === 'ArrowRight') nextIndex = (currentIndex + 1) % tabs.length;
  if (event.key === 'ArrowLeft') nextIndex = (currentIndex - 1 + tabs.length) % tabs.length;
  if (event.key === 'Home') nextIndex = 0;
  if (event.key === 'End') nextIndex = tabs.length - 1;

  var nextTab = tabs[nextIndex];
  if (!nextTab) return;
  nextTab.focus();
  switchChartType(nextTab.getAttribute('data-chart'));
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
  var ageYears = (typeof appState.lastResults !== 'undefined' && appState.lastResults) ? appState.lastResults.age_years || 0 : 0;
  var hasParentalHeights = (typeof appState.lastResults !== 'undefined' && appState.lastResults) ? !!appState.lastResults.mid_parental_height : false;
  var defaultIndex = getDefaultAgeRange(chartType, ageYears, hasParentalHeights);
  currentAgeRangeIndex = defaultIndex;

  ranges.forEach(function(range, index) {
    var label = document.createElement('label');
    var radio = document.createElement('input');
    radio.type = 'radio';
    radio.name = 'ageRange';
    radio.value = index;
    radio.className = 'visually-hidden-control';
    radio.setAttribute('aria-label', range.label.replace(/–/g, '-'));
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
 * appState.lastPayload (set by script.mjs after a successful calculation).
 */
export async function loadAndRenderChart() {
  var requestId = ++activeChartRequestId;
  var reference = (typeof appState.lastPayload !== 'undefined' && appState.lastPayload) ? appState.lastPayload.reference || 'uk-who' : 'uk-who';
  var sex = (typeof appState.lastPayload !== 'undefined' && appState.lastPayload) ? appState.lastPayload.sex : 'male';
  var ranges = AGE_RANGES[currentChartType] || [];
  var ageRange = ranges[currentAgeRangeIndex] || ranges[0];
  var chartTypeForRequest = currentChartType;

  try {
    var centiles = await fetchChartData(reference, chartTypeForRequest, sex, requestId);
    if (requestId !== activeChartRequestId || chartTypeForRequest !== currentChartType) return;
    renderChart(centiles, ageRange, chartTypeForRequest);
  } catch (err) {
    if (requestId === activeChartRequestId) {
      console.error('Chart render failed:', err);
    }
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
function fetchChartData(reference, method, sex, requestId) {
  var cacheKey = reference + '|' + method + '|' + sex;
  var loadingEl = document.getElementById('chartLoading');

  if (chartDataCache[cacheKey]) {
    if (loadingEl && requestId === activeChartRequestId) loadingEl.hidden = true;
    return Promise.resolve(chartDataCache[cacheKey]);
  }

  if (loadingEl && requestId === activeChartRequestId) loadingEl.hidden = false;

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
      if (loadingEl && requestId === activeChartRequestId) loadingEl.hidden = true;
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
export function destroyChart() {
  if (appState.currentChart) {
    appState.currentChart.destroy();
    appState.currentChart = null;
  }
}

/* ------------------------------------------------------------------ */
/*  Centile label plugin                                              */
/* ------------------------------------------------------------------ */

/**
 * Chart.js plugin that draws centile value labels at the rightmost
 * visible point of each centile curve.
 */
var centileLabelPlugin = {
  id: 'centileLabels',
  afterDatasetsDraw: function(chart) {
    var colors = getChartColors();
    var ctx = chart.ctx;
    ctx.save();
    chart.data.datasets.forEach(function(dataset, i) {
      if (dataset.type === 'scatter' || !dataset.centileLabel) return;
      if (chart.width < 500 && ['0.4', '50', '99.6'].indexOf(dataset.centileLabel) === -1) return;
      var meta = chart.getDatasetMeta(i);
      if (!meta.visible) return;
      var lastPoint = meta.data[meta.data.length - 1];
      if (!lastPoint) return;
      ctx.fillStyle = colors.labelColor;
      var fontSize = chart.width < 500 ? 8 : 10;
      ctx.font = fontSize + 'px -apple-system, sans-serif';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      ctx.fillText(dataset.centileLabel, lastPoint.x + 4, lastPoint.y);
    });
    ctx.restore();
  },
};

var chartBgPlugin = {
  id: 'customCanvasBackground',
  beforeDraw: function(chart) {
    var bgColor = chart.config.options.plugins.customCanvasBackground?.color;
    if (bgColor) {
      var ctx = chart.ctx;
      ctx.save();
      ctx.globalCompositeOperation = 'destination-over';
      ctx.fillStyle = bgColor;
      ctx.fillRect(0, 0, chart.width, chart.height);
      ctx.restore();
    }
  },
};

function ensureChartPluginsRegistered() {
  if (chartPluginsRegistered) return true;
  if (!window.Chart) return false;
  window.Chart.register(centileLabelPlugin);
  window.Chart.register(chartBgPlugin);
  chartPluginsRegistered = true;
  return true;
}

/* ------------------------------------------------------------------ */
/*  Measurement point helper                                          */
/* ------------------------------------------------------------------ */

/**
 * Return the current measurement as a {x, y} point for plotting on
 * the given chart type, or null if no data is available.
 *
 * @param {string} chartType - "height"|"weight"|"bmi"|"ofc".
 * @returns {Object|null}    - { x: ageYears, y: measurementValue } or null.
 */
function getMeasurementPoint(chartType) {
  if (typeof appState.lastResults === 'undefined' || !appState.lastResults) return null;
  var measurement = appState.lastResults[chartType];
  if (!measurement || measurement.value === undefined) return null;

  // Per RCPCH guidance: plot at chronological age, then draw arrow back
  // to corrected age to show gestational correction
  return { x: appState.lastResults.age_years, y: measurement.value };
}

function getCorrectedMeasurementPoint(chartType) {
  if (typeof appState.lastResults === 'undefined' || !appState.lastResults) return null;
  if (!appState.lastResults.gestation_correction_applied) return null;
  if (appState.lastResults.corrected_age_years === undefined) return null;
  var measurement = appState.lastResults[chartType];
  if (!measurement || measurement.value === undefined) return null;

  return { x: appState.lastResults.corrected_age_years, y: measurement.value };
}

/* ------------------------------------------------------------------ */
/*  MPH annotations helper                                            */
/* ------------------------------------------------------------------ */

/**
 * Return Chart.js annotation plugin config for the mid-parental height
 * line and target range shading. Only applies to the height chart when
 * MPH data exists and the age range extends to adult heights (>= 18).
 *
 * @param {string} chartType - "height"|"weight"|"bmi"|"ofc".
 * @param {Object} ageRange  - { min: number, max: number } in years.
 * @returns {Object}         - Annotation definitions, or empty object.
 */
function getMphAnnotations(chartType, ageRange) {
  if (chartType !== 'height') return {};
  if (typeof appState.lastResults === 'undefined' || !appState.lastResults) return {};
  var mph = appState.lastResults.mid_parental_height;
  if (!mph) return {};
  if (ageRange.max < 18) return {};
  var isDark = document.documentElement.getAttribute('data-theme') === 'dark';

  // MPH represents predicted adult height — draw it at the right end of
  // the chart where the centile curves reach adult values. The line extends
  // to the chart edge; the label sits to the left of the centile labels.
  var ageSpan = ageRange.max - ageRange.min;
  var mphXStart = ageRange.max - ageSpan * 0.2; // start at 80% of x-axis
  var mphXEnd = ageRange.max;                    // extend to right edge

  return {
    mphLine: {
      type: 'line',
      yMin: mph.mid_parental_height,
      yMax: mph.mid_parental_height,
      xMin: mphXStart,
      xMax: mphXEnd,
      borderColor: 'rgba(100, 80, 140, 0.8)',
      borderWidth: 2,
      borderDash: [6, 4],
      label: {
        display: true,
        content: 'MPH: ' + mph.mid_parental_height + ' cm',
        position: 'start',
        font: { size: 10, weight: 'bold' },
        backgroundColor: isDark ? 'rgba(28, 39, 51, 0.85)' : 'rgba(255, 255, 255, 0.85)',
        color: '#6b5090',
        padding: { top: 2, bottom: 2, left: 4, right: 4 },
        yAdjust: -14,
      },
    },
    mphRange: {
      type: 'box',
      xMin: mphXStart,
      xMax: mphXEnd,
      yMin: mph.target_range_lower,
      yMax: mph.target_range_upper,
      backgroundColor: 'rgba(100, 80, 140, 0.06)',
      borderWidth: 0,
    },
    mphUpper: {
      type: 'line',
      yMin: mph.target_range_upper,
      yMax: mph.target_range_upper,
      xMin: mphXStart,
      xMax: mphXEnd,
      borderColor: 'rgba(100, 80, 140, 0.25)',
      borderWidth: 1,
      borderDash: [3, 3],
    },
    mphLower: {
      type: 'line',
      yMin: mph.target_range_lower,
      yMax: mph.target_range_lower,
      xMin: mphXStart,
      xMax: mphXEnd,
      borderColor: 'rgba(100, 80, 140, 0.25)',
      borderWidth: 1,
      borderDash: [3, 3],
    },
  };
}

/* ------------------------------------------------------------------ */
/*  Previous measurements and bone age helpers                       */
/* ------------------------------------------------------------------ */

/**
 * Return previous measurement points for the given chart type as an
 * array of {x, y} objects, sourced from appState.lastResults.previous_measurements.
 *
 * @param {string} chartType - "height"|"weight"|"bmi"|"ofc".
 * @returns {Array}          - Array of {x: ageYears, y: value} points.
 */
function getPreviousMeasurementPoints(chartType) {
  if (typeof appState.lastResults === 'undefined' || !appState.lastResults || !appState.lastResults.previous_measurements) return [];
  return appState.lastResults.previous_measurements
    .filter(function(pm) { return pm[chartType] && pm[chartType].value !== undefined; })
    .map(function(pm) {
      var point = { x: pm.age, y: pm[chartType].value };
      if (pm.corrected_age !== undefined) {
        point.correctedX = pm.corrected_age;
      }
      return point;
    });
}

/**
 * Return the bone age scatter point for the height chart, or null if
 * unavailable or outside the valid window.
 *
 * @returns {Object|null} - { x: boneAgeYears, y: heightCm } or null.
 */
function getBoneAgePoint() {
  if (typeof appState.lastResults === 'undefined' || !appState.lastResults || !appState.lastResults.bone_age_height) return null;
  var ba = appState.lastResults.bone_age_height;
  if (!ba.within_window || !ba.height) return null;
  return { x: ba.bone_age, y: ba.height };
}

/* ------------------------------------------------------------------ */
/*  Chart rendering                                                   */
/* ------------------------------------------------------------------ */

/**
 * Build datasets from centile data, applying the graduated styling
 * defined in CENTILE_STYLES and theme-aware colours.
 *
 * @param {Array}  centiles - Filtered centile array.
 * @param {Object} colors   - Chart colour palette from getChartColors().
 * @returns {Array}          - Chart.js dataset objects.
 */
function buildCentileDatasets(centiles, colors) {
  return centiles.map(function (centile) {
    var style = CENTILE_STYLES[centile.centile] || { width: 1, opacity: 0.3 };
    var borderColor =
      centile.centile === 50
        ? colors.median
        : 'rgba(' + hexToRgb(colors.centileLine) + ', ' + style.opacity + ')';

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
  if (!ensureChartPluginsRegistered()) {
    throw new Error('Chart.js is not loaded.');
  }
  destroyChart();

  var canvas = document.getElementById('growthChart');
  if (!canvas) return;

  var colors = getChartColors();
  var filtered = filterDataToRange(centiles, ageRange.min, ageRange.max);
  var datasets = buildCentileDatasets(filtered, colors);

  // Add the child's current measurement as a scatter point
  // Per RCPCH Fact Sheet 5: plot at chronological age, draw arrow back to corrected age
  var measurementPoint = getMeasurementPoint(chartType);
  var correctedPoint = getCorrectedMeasurementPoint(chartType);

  if (measurementPoint) {
    // If preterm with correction: show arrow from chronological → corrected age
    if (correctedPoint) {
      // Arrow line from chronological age to corrected age
      datasets.push({
        type: 'line',
        label: 'Gestation correction',
        data: [measurementPoint, correctedPoint],
        borderColor: colors.currentMarker,
        borderWidth: 1.5,
        borderDash: [4, 3],
        pointRadius: [0, 5],  // no dot at chronological end, arrow tip at corrected
        pointBackgroundColor: colors.currentMarker,
        pointBorderColor: colors.bgColor,
        pointBorderWidth: 2,
        pointStyle: ['circle', 'triangle'],
        fill: false,
        tension: 0,
      });
      // Open circle at chronological age (actual age plot)
      datasets.push({
        type: 'scatter',
        label: 'Current measurement',
        data: [measurementPoint],
        pointRadius: 5,
        pointBackgroundColor: colors.bgColor,
        pointBorderColor: colors.currentMarker,
        pointBorderWidth: 2,
        pointHoverRadius: 7,
      });
    } else {
      // Term baby — simple filled dot
      datasets.push({
        type: 'scatter',
        label: 'Current measurement',
        data: [measurementPoint],
        pointRadius: 5,
        pointBackgroundColor: colors.currentMarker,
        pointBorderColor: colors.bgColor,
        pointBorderWidth: 2,
        pointHoverRadius: 7,
      });
    }
  }

  // Add previous measurements — with correction arrows for preterm
  var prevPoints = getPreviousMeasurementPoints(chartType);
  if (prevPoints.length > 0) {
    // Separate corrected and uncorrected points
    var uncorrectedPrev = prevPoints.filter(function(p) { return p.correctedX === undefined; });
    var correctedPrev = prevPoints.filter(function(p) { return p.correctedX !== undefined; });

    // Uncorrected previous measurements: simple dots
    if (uncorrectedPrev.length > 0) {
      datasets.push({
        type: 'scatter',
        label: 'Previous measurements',
        data: uncorrectedPrev,
        pointRadius: 4,
        pointBackgroundColor: colors.previousMarker,
        pointBorderColor: colors.bgColor,
        pointBorderWidth: 1,
        pointHoverRadius: 6,
      });
    }

    // Corrected previous measurements: arrow from chronological to corrected age
    correctedPrev.forEach(function(p) {
      // Arrow line
      datasets.push({
        type: 'line',
        label: 'Gestation correction (previous)',
        data: [{ x: p.x, y: p.y }, { x: p.correctedX, y: p.y }],
        borderColor: colors.previousMarker,
        borderWidth: 1,
        borderDash: [3, 2],
        pointRadius: [0, 3],
        pointBackgroundColor: colors.previousMarker,
        pointBorderColor: colors.bgColor,
        pointBorderWidth: 1,
        pointStyle: ['circle', 'triangle'],
        fill: false,
        tension: 0,
      });
      // Open circle at chronological age
      datasets.push({
        type: 'scatter',
        label: 'Previous measurements',
        data: [{ x: p.x, y: p.y }],
        pointRadius: 4,
        pointBackgroundColor: colors.bgColor,
        pointBorderColor: colors.previousMarker,
        pointBorderWidth: 1.5,
        pointHoverRadius: 6,
      });
    });
  }

  // Add bone age diamond marker (height chart only, when within_window)
  if (chartType === 'height') {
    var baPoint = getBoneAgePoint();
    if (baPoint) {
      datasets.push({
        type: 'scatter',
        label: 'Bone age',
        data: [baPoint],
        pointRadius: 5,
        pointBackgroundColor: '#d97706',
        pointBorderColor: colors.bgColor,
        pointBorderWidth: 2,
        pointStyle: 'rectRot',
        pointHoverRadius: 7,
      });
    }
  }

  // MPH annotations (height chart only, adult range)
  var annotations = getMphAnnotations(chartType, ageRange);

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
          title: { display: true, text: 'Age (years)', color: colors.textColor },
          min: ageRange.min,
          max: ageRange.max,
          grid: { color: colors.gridColor },
          ticks: { color: colors.textColor },
        },
        y: {
          type: 'linear',
          title: { display: true, text: Y_AXIS_LABELS[chartType] || '', color: colors.textColor },
          grid: { color: colors.gridColor },
          ticks: { color: colors.textColor },
        },
      },
      plugins: {
        customCanvasBackground: { color: colors.bgColor },
        legend: { display: false },
        tooltip: {
          enabled: true,
          filter: function(tooltipItem) {
            // Allow scatter points and the corrected-age end of correction arrows
            if (tooltipItem.dataset.type === 'scatter') return true;
            var lbl = tooltipItem.dataset.label || '';
            if (lbl.indexOf('Gestation correction') === 0 && tooltipItem.dataIndex === 1) return true;
            return false;
          },
          callbacks: {
            title: function() { return ''; },
            label: function(context) {
              var point = context.raw;
              var datasetLabel = context.dataset.label || '';

              // Gestation correction arrow tip (corrected age)
              if (datasetLabel.indexOf('Gestation correction') === 0) {
                var chronPoint = context.dataset.data[0];
                var measurement = appState.lastResults[currentChartType];
                var name = CHART_DISPLAY_NAMES[currentChartType] || currentChartType;
                var unit = CHART_UNITS[currentChartType] || '';
                var lines = [
                  'Corrected age: ' + point.x.toFixed(2) + ' years',
                  'Chronological age: ' + chronPoint.x.toFixed(2) + ' years',
                  name + ': ' + point.y + ' ' + unit,
                ];
                if (measurement && measurement.centile !== null) {
                  lines.push('Centile (corrected): ' + measurement.centile.toFixed(1) + '%');
                }
                if (measurement && measurement.sds !== null) {
                  lines.push('SDS (corrected): ' + (measurement.sds >= 0 ? '+' : '') + measurement.sds.toFixed(2));
                }
                return lines;
              }

              // Bone age tooltip
              if (datasetLabel === 'Bone age') {
                var ba = appState.lastResults.bone_age_height;
                return [
                  'Bone Age: ' + point.x.toFixed(1) + ' years',
                  'Height: ' + point.y + ' cm',
                  'Centile: ' + (ba && ba.centile !== null ? ba.centile.toFixed(1) + '%' : 'N/A'),
                  'SDS: ' + (ba && ba.sds !== null ? (ba.sds >= 0 ? '+' : '') + ba.sds.toFixed(2) : 'N/A'),
                ];
              }

              // Previous measurement tooltip
              if (datasetLabel === 'Previous measurements') {
                return [
                  'Age: ' + point.x.toFixed(2) + ' years',
                  CHART_DISPLAY_NAMES[currentChartType] + ': ' + point.y + ' ' + CHART_UNITS[currentChartType],
                ];
              }

              // Current measurement tooltip (existing)
              var currentMeasurement = appState.lastResults[currentChartType];
              var currentName = CHART_DISPLAY_NAMES[currentChartType] || currentChartType;
              var currentUnit = CHART_UNITS[currentChartType] || '';
              return [
                'Age: ' + point.x.toFixed(2) + ' years',
                currentName + ': ' + point.y + ' ' + currentUnit,
                'Centile: ' + (currentMeasurement && currentMeasurement.centile !== null ? currentMeasurement.centile.toFixed(1) + '%' : 'N/A'),
                'SDS: ' + (currentMeasurement && currentMeasurement.sds !== null ? (currentMeasurement.sds >= 0 ? '+' : '') + currentMeasurement.sds.toFixed(2) : 'N/A'),
              ];
            },
          },
        },
        annotation: Object.keys(annotations).length > 0
          ? { annotations: annotations }
          : undefined,
      },
      elements: {
        point: { radius: 0 },
      },
      layout: {
        padding: { right: 40 },
      },
    },
  };

  appState.currentChart = new window.Chart(canvas.getContext('2d'), config);

  // Update screen reader description
  var descEl = document.getElementById('chartDescription');
  if (descEl && measurementPoint) {
    var meas = appState.lastResults[chartType];
    descEl.textContent = CHART_DISPLAY_NAMES[chartType] + ' chart. ' +
      'Current measurement: ' + measurementPoint.y + ' ' + CHART_UNITS[chartType] +
      ' at age ' + measurementPoint.x.toFixed(2) + ' years.' +
      (meas ? ' Centile: ' + (meas.centile !== null ? meas.centile.toFixed(1) + '%' : 'N/A') +
      ', SDS: ' + (meas.sds !== null ? (meas.sds >= 0 ? '+' : '') + meas.sds.toFixed(2) : 'N/A') : '');
  }
}

/* ------------------------------------------------------------------ */
/*  Chart download and capture                                        */
/* ------------------------------------------------------------------ */

export function downloadChart() {
    ensureChartPluginsRegistered();
    if (!appState.currentChart) return;

    // Force light mode for export. The try/finally is load-bearing — without
    // it, any canvas failure between the theme switch and the restore block
    // leaves the page stuck in light mode.
    var savedTheme = document.documentElement.getAttribute('data-theme');
    document.documentElement.setAttribute('data-theme', 'light');

    var ranges = AGE_RANGES[currentChartType] || [];
    var ageRange = ranges[currentAgeRangeIndex] || ranges[0];
    var cacheKey = (typeof appState.lastPayload !== 'undefined' && appState.lastPayload ? appState.lastPayload.reference || 'uk-who' : 'uk-who') + '|' + currentChartType + '|' + (typeof appState.lastPayload !== 'undefined' && appState.lastPayload ? appState.lastPayload.sex : 'male');
    var centiles = chartDataCache[cacheKey];
    if (centiles) renderChart(centiles, ageRange, currentChartType);

    try {
        var canvas = document.getElementById('growthChart');
        if (!canvas) return;

        var chartType = currentChartType || 'chart';
        var date = new Date().toISOString().split('T')[0];
        var filename = 'growth-chart-' + chartType + '-' + date + '.png';

        // Create high-res export canvas (2x for Retina)
        var scale = 2;
        var exportCanvas = document.createElement('canvas');
        exportCanvas.width = canvas.width * scale;
        exportCanvas.height = canvas.height * scale;

        var ctx = exportCanvas.getContext('2d');
        ctx.scale(scale, scale);
        ctx.drawImage(canvas, 0, 0);

        var link = document.createElement('a');
        link.download = filename;
        link.href = exportCanvas.toDataURL('image/png');
        link.click();
    } finally {
        if (savedTheme) {
            document.documentElement.setAttribute('data-theme', savedTheme);
        } else {
            document.documentElement.removeAttribute('data-theme');
        }
        if (centiles) renderChart(centiles, ageRange, currentChartType);
    }
}

export async function captureChartImages() {
    ensureChartPluginsRegistered();
    var images = {};
    var reference = (typeof appState.lastPayload !== 'undefined' && appState.lastPayload) ? appState.lastPayload.reference || 'uk-who' : 'uk-who';
    var sex = (typeof appState.lastPayload !== 'undefined' && appState.lastPayload) ? appState.lastPayload.sex : 'male';
    var savedType = currentChartType;

    // Temporarily show charts section so the canvas has dimensions
    var chartsSection = document.getElementById('chartsSection');
    var wasHidden = chartsSection && chartsSection.hidden;
    if (wasHidden) chartsSection.hidden = false;

    // Force light mode for PDF export
    var savedTheme = document.documentElement.getAttribute('data-theme');
    document.documentElement.setAttribute('data-theme', 'light');

    var types = ['height', 'weight', 'bmi', 'ofc'];
    for (var i = 0; i < types.length; i++) {
        var type = types[i];
        try {
            var centiles = await fetchChartData(reference, type, sex);
            var ranges = AGE_RANGES[type] || [];
            var ageYears = (typeof appState.lastResults !== 'undefined' && appState.lastResults) ? appState.lastResults.age_years || 0 : 0;
            var hasParentalHeights = (typeof appState.lastResults !== 'undefined' && appState.lastResults) ? !!appState.lastResults.mid_parental_height : false;
            var defaultIdx = getDefaultAgeRange(type, ageYears, hasParentalHeights);
            var ageRange = ranges[defaultIdx] || ranges[0];

            renderChart(centiles, ageRange, type);
            var canvas = document.getElementById('growthChart');
            if (canvas) {
                images[type] = canvas.toDataURL('image/png');
            }
        } catch (e) {
            // Skip failed charts
        }
    }

    // Restore original theme
    if (savedTheme) {
        document.documentElement.setAttribute('data-theme', savedTheme);
    } else {
        document.documentElement.removeAttribute('data-theme');
    }

    // Restore the chart that was showing before capture
    if (savedType) {
        switchChartType(savedType);
    }

    // Re-hide charts section if it was hidden before
    if (wasHidden) {
        chartsSection.hidden = true;
        destroyChart();
    }

    return images;
}

/* ------------------------------------------------------------------ */
/*  Event listeners                                                   */
/* ------------------------------------------------------------------ */

export function initCharts() {
  ensureChartPluginsRegistered();

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
    tab.addEventListener('keydown', handleChartTabKeydown);
  });
}

export const __chartTestHooks = {
  renderAgeRangeSelectorForTest: renderAgeRangeSelector,
  syncChartTabsForTest: syncChartTabs,
  handleChartTabKeydownForTest: handleChartTabKeydown,
  loadAndRenderChartForTest: loadAndRenderChart,
  resetChartRequestStateForTest: function () {
    activeChartRequestId = 0;
    chartDataCache = {};
  },
};
