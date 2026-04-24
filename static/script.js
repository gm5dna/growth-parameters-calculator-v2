/**
 * Growth Parameters Calculator — main frontend script.
 *
 * Phase 1 scope: form submission via fetch, results display, error display,
 * disclaimer dismiss, form state persistence with localStorage, keyboard
 * shortcuts (Ctrl+Enter to submit, Escape to reset).
 */

/* ------------------------------------------------------------------ */
/*  Utility                                                           */
/* ------------------------------------------------------------------ */

function debounce(fn, delay) {
  let timer;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  };
}

function showToast(message) {
    var toastEl = document.getElementById('toast');
    if (!toastEl) return;
    toastEl.textContent = message;
    toastEl.hidden = false;
    toastEl.classList.add('show');
    setTimeout(function() {
        toastEl.classList.remove('show');
        setTimeout(function() { toastEl.hidden = true; }, 300);
    }, 3000);
}

/* ------------------------------------------------------------------ */
/*  Copy & PDF export handlers                                        */
/* ------------------------------------------------------------------ */

async function handleCopyResults() {
    if (!lastResults) return;
    var patientInfo = {
        sex: lastPayload ? lastPayload.sex : '',
        reference: lastPayload ? lastPayload.reference || 'uk-who' : 'uk-who',
        weight: lastPayload ? lastPayload.weight : null,
    };
    var success = await copyResultsToClipboard(lastResults, patientInfo);
    showToast(success ? 'Results copied to clipboard' : 'Copy failed \u2014 please copy manually');
}

async function handleExportPdf() {
    if (!lastResults || !lastPayload) return;
    var btn = document.getElementById('exportPdfBtn');
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner" aria-hidden="true"></span> Generating PDF\u2026'; }

    try {
        var chartImages = typeof captureChartImages === 'function' ? await captureChartImages() : {};
        var payload = {
            results: lastResults,
            patient_info: {
                sex: lastPayload.sex,
                birth_date: lastPayload.birth_date,
                measurement_date: lastPayload.measurement_date,
                reference: lastPayload.reference || 'uk-who',
            },
            chart_images: chartImages,
        };

        var response = await fetch('/export-pdf', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            var errData = await response.json().catch(function() { return {}; });
            showToast(errData.error || 'PDF generation failed.');
            return;
        }

        var blob = await response.blob();
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = 'growth-report-' + new Date().toISOString().split('T')[0] + '.pdf';
        a.click();
        URL.revokeObjectURL(url);
        showToast('PDF downloaded');
    } catch (err) {
        showToast('Network error. Please try again.');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<span class="material-symbols-outlined" aria-hidden="true">picture_as_pdf</span> Export PDF';
        }
    }
}

/* ------------------------------------------------------------------ */
/*  Constants                                                         */
/* ------------------------------------------------------------------ */

const STORAGE_KEY = 'growthCalculatorFormState';

var lastResults = null;
var lastPayload = null;
var autoCalcInProgress = false;
var currentGhDose = 0;
var currentBsa = null;
var currentWeightKg = null;

var GH_PEN_DEVICES = {
  'norditropin-5':  { step: 0.025, min: 0.025, max: 2.0 },
  'norditropin-10': { step: 0.05,  min: 0.05,  max: 4.0 },
  'norditropin-15': { step: 0.1,   min: 0.1,   max: 8.0 },
  'surepal-5':      { step: 0.1,   min: 0.1,   max: 2.4 },
  'surepal-10':     { step: 0.1,   min: 0.1,   max: 4.8 },
  'surepal-15':     { step: 0.1,   min: 0.1,   max: 7.2 },
};

function getSelectedPen() {
  var sel = document.getElementById('ghPenDevice');
  var id = sel ? sel.value : 'norditropin-5';
  return GH_PEN_DEVICES[id] || GH_PEN_DEVICES['norditropin-5'];
}

function roundToStep(value, step) {
  return Math.round(value / step) * step;
}

const FIELD_IDS = [
  'birthDate',
  'measurementDate',
  'weight',
  'height',
  'ofc',
  'maternalHeight',
  'paternalHeight',
  'gestationWeeks',
  'gestationDays',
  'reference',
];

const MEASUREMENT_UNITS = {
  weight: 'kg',
  height: 'cm',
  ofc: 'cm',
  bmi: 'kg/m\u00B2',
};

const MEASUREMENT_LABELS = {
  weight: 'WEIGHT',
  height: 'HEIGHT',
  ofc: 'HEAD CIRCUMFERENCE (OFC)',
  bmi: 'BMI',
};

/* ------------------------------------------------------------------ */
/*  DOM references (populated on DOMContentLoaded)                    */
/* ------------------------------------------------------------------ */

let form,
  calculateBtn,
  resetBtn,
  errorDisplay,
  errorMessage,
  resultsSection,
  measurementSummary,
  resultsGrid,
  warningsDisplay,
  warningsList,
  disclaimer,
  dismissDisclaimerBtn,
  toast;

/* ------------------------------------------------------------------ */
/*  Mode toggle                                                       */
/* ------------------------------------------------------------------ */

function handleModeToggle() {
  var toggle = document.getElementById('modeToggle');
  if (toggle && toggle.checked) {
    document.body.classList.add('advanced-mode');
  } else {
    document.body.classList.remove('advanced-mode');
  }
  // Highlight active mode label
  var labels = document.querySelectorAll('.mode-label');
  if (labels.length >= 2) {
    labels[0].classList.toggle('active-label', !toggle.checked);
    labels[1].classList.toggle('active-label', toggle.checked);
  }
  debouncedSave();
}

/* ------------------------------------------------------------------ */
/*  Theme toggle (dark mode)                                          */
/* ------------------------------------------------------------------ */

function initTheme() {
    var saved = null;
    try { saved = localStorage.getItem('growthCalcTheme'); } catch(e) {}
    if (saved) {
        document.documentElement.setAttribute('data-theme', saved);
    } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        document.documentElement.setAttribute('data-theme', 'dark');
    }
    updateThemeIcon();
}

function toggleTheme() {
    var current = document.documentElement.getAttribute('data-theme');
    var next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    try { localStorage.setItem('growthCalcTheme', next); } catch(e) {}
    updateThemeIcon();
    // Re-render chart if visible to pick up new colours
    if (typeof currentChart !== 'undefined' && currentChart && typeof loadAndRenderChart === 'function') {
        loadAndRenderChart();
    }
}

function updateThemeIcon() {
    var icon = document.getElementById('themeIcon');
    if (!icon) return;
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    icon.textContent = isDark ? 'light_mode' : 'dark_mode';
}

/* ------------------------------------------------------------------ */
/*  Previous Measurements — table row management                      */
/* ------------------------------------------------------------------ */

function _makeInputCell(attrs, value) {
  var td = document.createElement('td');
  var input = document.createElement('input');
  Object.keys(attrs).forEach(function(k) { input.setAttribute(k, attrs[k]); });
  if (value !== undefined && value !== null && value !== '') {
    input.value = String(value);
  }
  td.appendChild(input);
  return { td: td, input: input };
}

function _makeDeleteCell(onClick) {
  var td = document.createElement('td');
  var btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'btn-delete';
  btn.setAttribute('aria-label', 'Delete row');
  var icon = document.createElement('span');
  icon.className = 'material-symbols-outlined';
  icon.textContent = 'delete';
  btn.appendChild(icon);
  btn.addEventListener('click', onClick);
  td.appendChild(btn);
  return td;
}

function addPrevMeasurementRow(dateVal, heightVal, weightVal, ofcVal) {
  var tbody = document.getElementById('prevMeasurementsBody');
  if (!tbody) return;
  var tr = document.createElement('tr');
  var dateCell = _makeInputCell({ type: 'date', class: 'prev-date' }, dateVal);
  var heightCell = _makeInputCell({ type: 'number', class: 'prev-height', step: '0.1', min: '10', max: '250' }, heightVal);
  var weightCell = _makeInputCell({ type: 'number', class: 'prev-weight', step: '0.01', min: '0.1', max: '300' }, weightVal);
  var ofcCell = _makeInputCell({ type: 'number', class: 'prev-ofc', step: '0.1', min: '10', max: '100' }, ofcVal);
  tr.appendChild(dateCell.td);
  tr.appendChild(heightCell.td);
  tr.appendChild(weightCell.td);
  tr.appendChild(ofcCell.td);
  tr.appendChild(_makeDeleteCell(function() { tr.remove(); debouncedSave(); }));
  [dateCell.input, heightCell.input, weightCell.input, ofcCell.input].forEach(function(input) {
    input.addEventListener('change', debouncedSave);
  });
  tbody.appendChild(tr);
  debouncedSave();
}

function getPreviousMeasurements() {
  var rows = document.querySelectorAll('#prevMeasurementsBody tr');
  var measurements = [];
  rows.forEach(function(row) {
    var date = row.querySelector('.prev-date')?.value || '';
    var height = row.querySelector('.prev-height')?.value || '';
    var weight = row.querySelector('.prev-weight')?.value || '';
    var ofc = row.querySelector('.prev-ofc')?.value || '';
    if (!date && !height && !weight && !ofc) return; // Skip entirely empty rows
    var entry = {};
    if (date) entry.date = date;
    if (height) entry.height = parseFloat(height);
    if (weight) entry.weight = parseFloat(weight);
    if (ofc) entry.ofc = parseFloat(ofc);
    measurements.push(entry);
  });
  return measurements;
}

/* ------------------------------------------------------------------ */
/*  Previous Measurements — CSV import/export                         */
/* ------------------------------------------------------------------ */

// Strict CSV parser. The accepted format is:
//
//   date,height,weight,ofc
//   YYYY-MM-DD,<float|empty>,<float|empty>,<float|empty>
//
// Rows are rejected when they don't have exactly 4 comma-separated columns,
// when the date is not YYYY-MM-DD, or when a numeric column is not empty and
// not a finite number. Quoted values, CRLF edge cases, and escaped fields
// are deliberately not supported — anything more complex should be typed
// into the UI directly.
//
// Returned shape: `{ rows: Array<[date, height, weight, ofc]>, errors: string[] }`.
// The parser is a pure function so it can be unit-tested without DOM.
function parsePreviousMeasurementsCsv(text) {
  // Strip UTF-8 BOM (U+FEFF) so Excel-exported CSVs parse their first row.
  var safeText = String(text || '').replace(/^\uFEFF/, '').replace(/\r\n/g, '\n').trim();
  if (!safeText) return { rows: [], errors: [] };
  var lines = safeText.split('\n');
  var errors = [];
  var rows = [];
  for (var i = 1; i < lines.length; i++) {
    var line = lines[i].trim();
    if (!line) continue;
    var cols = line.split(',').map(function(c) { return c.trim(); });
    if (cols.length !== 4) {
      errors.push('Row ' + (i + 1) + ': expected 4 columns (date,height,weight,ofc)');
      continue;
    }
    var date = cols[0];
    if (date && !/^\d{4}-\d{2}-\d{2}$/.test(date)) {
      errors.push('Row ' + (i + 1) + ': date must be YYYY-MM-DD');
      continue;
    }
    var numericOk = [1, 2, 3].every(function(idx) {
      var value = cols[idx];
      if (value === '') return true;
      var parsed = Number(value);
      return Number.isFinite(parsed);
    });
    if (!numericOk) {
      errors.push('Row ' + (i + 1) + ': height/weight/ofc must be numeric or blank');
      continue;
    }
    rows.push(cols);
  }
  return { rows: rows, errors: errors };
}

function importCsv(file) {
  var reader = new FileReader();
  reader.onload = function(e) {
    var parsed = parsePreviousMeasurementsCsv(e.target.result);
    if (parsed.errors.length && typeof showError === 'function') {
      showError('CSV import: ' + parsed.errors.join('; '));
    }
    parsed.rows.forEach(function(cols) {
      addPrevMeasurementRow(cols[0] || '', cols[1] || '', cols[2] || '', cols[3] || '');
    });
  };
  reader.readAsText(file);
}


function exportCsv() {
  var measurements = getPreviousMeasurements();
  if (measurements.length === 0) return;
  var csv = 'date,height,weight,ofc\n';
  measurements.forEach(function(m) {
    csv += (m.date || '') + ',' + (m.height || '') + ',' + (m.weight || '') + ',' + (m.ofc || '') + '\n';
  });
  var blob = new Blob([csv], { type: 'text/csv' });
  var url = URL.createObjectURL(blob);
  var a = document.createElement('a');
  a.href = url;
  a.download = 'previous-measurements.csv';
  a.click();
  URL.revokeObjectURL(url);
}

/* ------------------------------------------------------------------ */
/*  Bone Age Assessments — table row management                       */
/* ------------------------------------------------------------------ */

function addBoneAgeRow(dateVal, ageVal, standardVal) {
    var tbody = document.getElementById('boneAgeBody');
    if (!tbody) return;
    var tr = document.createElement('tr');
    var dateCell = _makeInputCell({ type: 'date', class: 'ba-date' }, dateVal);
    var ageCell = _makeInputCell({ type: 'number', class: 'ba-age', step: '0.1', min: '0', max: '20' }, ageVal);

    var standardTd = document.createElement('td');
    var select = document.createElement('select');
    select.className = 'ba-standard';
    var resolvedStandard = standardVal === 'tw3' ? 'tw3' : 'gp';
    [['gp', 'Greulich-Pyle'], ['tw3', 'TW3']].forEach(function(opt) {
        var o = document.createElement('option');
        o.value = opt[0];
        o.textContent = opt[1];
        if (opt[0] === resolvedStandard) o.selected = true;
        select.appendChild(o);
    });
    standardTd.appendChild(select);

    tr.appendChild(dateCell.td);
    tr.appendChild(ageCell.td);
    tr.appendChild(standardTd);
    tr.appendChild(_makeDeleteCell(function() { tr.remove(); debouncedSave(); }));
    [dateCell.input, ageCell.input, select].forEach(function(el) {
        el.addEventListener('change', debouncedSave);
    });
    tbody.appendChild(tr);
    debouncedSave();
}

function getBoneAgeAssessments() {
    var rows = document.querySelectorAll('#boneAgeBody tr');
    var assessments = [];
    rows.forEach(function(row) {
        var date = row.querySelector('.ba-date')?.value || '';
        var age = row.querySelector('.ba-age')?.value || '';
        var standard = row.querySelector('.ba-standard')?.value || 'gp';
        if (!date && !age) return;
        var entry = { standard: standard };
        if (date) entry.date = date;
        if (age) entry.bone_age = parseFloat(age);
        assessments.push(entry);
    });
    return assessments;
}

/* ------------------------------------------------------------------ */
/*  Collapsible section toggle                                        */
/* ------------------------------------------------------------------ */

function toggleCollapsible(toggleEl, contentEl) {
  if (contentEl.hidden) {
    contentEl.hidden = false;
    toggleEl.querySelector('.material-symbols-outlined').textContent = 'remove';
    // Add first row if table is empty
    var tbody = contentEl.querySelector('tbody');
    if (tbody && tbody.children.length === 0) {
      addPrevMeasurementRow();
    }
  } else {
    contentEl.hidden = true;
    toggleEl.querySelector('.material-symbols-outlined').textContent = 'add';
  }
}

/* ------------------------------------------------------------------ */
/*  Form data gathering                                               */
/* ------------------------------------------------------------------ */

function gatherFormData() {
  const payload = {
    sex: document.querySelector('input[name="sex"]:checked')?.value || '',
    birth_date: document.getElementById('birthDate').value,
    measurement_date: document.getElementById('measurementDate').value,
  };

  const weight = document.getElementById('weight').value;
  if (weight) payload.weight = parseFloat(weight);

  const height = document.getElementById('height').value;
  if (height) payload.height = parseFloat(height);

  const ofc = document.getElementById('ofc').value;
  if (ofc) payload.ofc = parseFloat(ofc);

  const maternalHeight = document.getElementById('maternalHeight').value;
  if (maternalHeight) payload.maternal_height = parseFloat(maternalHeight);

  const paternalHeight = document.getElementById('paternalHeight').value;
  if (paternalHeight) payload.paternal_height = parseFloat(paternalHeight);

  const gestWeeks = document.getElementById('gestationWeeks')?.value;
  if (gestWeeks) payload.gestation_weeks = parseInt(gestWeeks);

  const gestDays = document.getElementById('gestationDays')?.value;
  if (gestDays) payload.gestation_days = parseInt(gestDays);

  const reference = document.getElementById('reference')?.value;
  if (reference) payload.reference = reference;

  const ghTreatment = document.getElementById('ghTreatment')?.checked;
  if (ghTreatment) payload.gh_treatment = true;

  var prevMeasurements = getPreviousMeasurements();
  if (prevMeasurements.length > 0) payload.previous_measurements = prevMeasurements;

  var boneAgeAssessments = getBoneAgeAssessments();
  if (boneAgeAssessments.length > 0) payload.bone_age_assessments = boneAgeAssessments;

  return payload;
}

/* ------------------------------------------------------------------ */
/*  Client-side validation (UX only — server is authoritative)        */
/* ------------------------------------------------------------------ */

function runClientValidation(payload) {
  let hasError = false;

  // Clear all field errors first
  clearFieldErrors();

  const sexErr = validateSex(payload.sex);
  if (sexErr) {
    showFieldError('sexError', sexErr);
    hasError = true;
  }

  const birthErr = validateDate(payload.birth_date);
  if (birthErr) {
    showFieldError('birthDateError', birthErr);
    hasError = true;
  }

  const measErr = validateDate(payload.measurement_date);
  if (measErr) {
    showFieldError('measurementDateError', measErr);
    hasError = true;
  }

  const weightErr = validateWeight(document.getElementById('weight').value);
  if (weightErr) {
    showFieldError('weightError', weightErr);
    hasError = true;
  }

  const heightErr = validateHeight(document.getElementById('height').value);
  if (heightErr) {
    showFieldError('heightError', heightErr);
    hasError = true;
  }

  const ofcErr = validateOfc(document.getElementById('ofc').value);
  if (ofcErr) {
    showFieldError('ofcError', ofcErr);
    hasError = true;
  }

  const atLeastOneErr = validateAtLeastOneMeasurement(
    document.getElementById('weight').value,
    document.getElementById('height').value,
    document.getElementById('ofc').value
  );
  if (atLeastOneErr) {
    // Show on the first measurement field
    showFieldError('weightError', atLeastOneErr);
    hasError = true;
  }

  return !hasError;
}

function showFieldError(id, message) {
  const el = document.getElementById(id);
  if (el) el.textContent = message;
}

function clearFieldErrors() {
  const errorIds = [
    'sexError',
    'birthDateError',
    'measurementDateError',
    'weightError',
    'heightError',
    'ofcError',
    'maternalHeightError',
    'paternalHeightError',
  ];
  errorIds.forEach(function (id) {
    const el = document.getElementById(id);
    if (el) el.textContent = '';
  });
}

/* ------------------------------------------------------------------ */
/*  Form submission                                                   */
/* ------------------------------------------------------------------ */

async function handleSubmit(event) {
  event.preventDefault();
  clearError();
  clearFieldErrors();

  const payload = gatherFormData();

  // Client-side validation (UX only)
  if (!runClientValidation(payload)) {
    return;
  }

  setLoadingState(true);

  try {
    const response = await fetch('/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const data = await response.json();

    if (!data.success) {
      showError(data.error || 'An unknown error occurred.');
      return;
    }

    displayResults(data.results);
  } catch (err) {
    showError('Network error: unable to reach the server. Please try again.');
  } finally {
    setLoadingState(false);
    // Clear the auto-calc flag once the submit fully resolves. The previous
    // 100 ms setTimeout could fire before a slow request came back, which
    // would cause the auto-triggered calculation to scroll the results
    // section into view even though the user hadn't requested it.
    autoCalcInProgress = false;
  }
}

/* ------------------------------------------------------------------ */
/*  Loading state                                                     */
/* ------------------------------------------------------------------ */

function setLoadingState(loading) {
  if (!calculateBtn) return;

  if (loading) {
    calculateBtn.disabled = true;
    calculateBtn.setAttribute('data-original-text', calculateBtn.innerHTML);
    calculateBtn.innerHTML =
      '<span class="spinner" aria-hidden="true"></span> Calculating\u2026';
  } else {
    calculateBtn.disabled = false;
    const original = calculateBtn.getAttribute('data-original-text');
    if (original) {
      calculateBtn.innerHTML = original;
      calculateBtn.removeAttribute('data-original-text');
    }
  }
}

/* ------------------------------------------------------------------ */
/*  Error display                                                     */
/* ------------------------------------------------------------------ */

function showError(message) {
  if (errorMessage) errorMessage.textContent = message;
  if (errorDisplay) errorDisplay.removeAttribute('hidden');
  if (resultsSection) resultsSection.setAttribute('hidden', '');
}

function clearError() {
  if (errorDisplay) errorDisplay.setAttribute('hidden', '');
  if (errorMessage) errorMessage.textContent = '';
}

/* ------------------------------------------------------------------ */
/*  Format helpers                                                    */
/* ------------------------------------------------------------------ */

function formatCentile(centile) {
  if (centile === null || centile === undefined) return 'N/A';
  return centile.toFixed(1) + '%';
}

function formatSds(sds) {
  if (sds === null || sds === undefined) return 'N/A';
  const sign = sds >= 0 ? '+' : '';
  return sign + sds.toFixed(2);
}

function formatCalendarAge(ageCal) {
  if (!ageCal) return '';
  const y = ageCal.years || 0;
  const m = ageCal.months || 0;
  const d = ageCal.days || 0;
  const parts = [];
  parts.push(y === 1 ? '1 year' : y + ' years');
  parts.push(m === 1 ? '1 month' : m + ' months');
  parts.push(d === 1 ? '1 day' : d + ' days');
  return parts.join(', ');
}

function formatMeasurementValue(value, unit) {
  if (value === null || value === undefined) return 'N/A';
  return unit ? value + ' ' + unit : String(value);
}

function buildMeasurementSummaryRows(results) {
  var summaryConfig = [
    { key: 'weight', label: 'Weight' },
    { key: 'height', label: 'Height' },
    { key: 'bmi', label: 'BMI' },
    { key: 'ofc', label: 'OFC' },
  ];

  return summaryConfig
    .filter(function (item) { return results[item.key]; })
    .map(function (item) {
      var measurement = results[item.key];
      var extra = '';
      if (item.key === 'bmi' && measurement.percentage_median !== null && measurement.percentage_median !== undefined) {
        extra = measurement.percentage_median.toFixed(1) + '% median';
      }
      return {
        key: item.key,
        label: item.label,
        value: formatMeasurementValue(measurement.value, MEASUREMENT_UNITS[item.key] || ''),
        centile: formatCentile(measurement.centile),
        sds: formatSds(measurement.sds),
        extra: extra,
      };
    });
}

/* ------------------------------------------------------------------ */
/*  Results display                                                   */
/* ------------------------------------------------------------------ */

function createResultCard(label, value, subs) {
  const card = document.createElement('div');
  card.className = 'result-item';

  const labelDiv = document.createElement('div');
  labelDiv.className = 'result-label';
  labelDiv.textContent = label;
  card.appendChild(labelDiv);

  const valueDiv = document.createElement('div');
  valueDiv.className = 'result-value';
  valueDiv.textContent = value;
  card.appendChild(valueDiv);

  if (subs && subs.length) {
    subs.forEach(function (text) {
      const subDiv = document.createElement('div');
      subDiv.className = 'result-sub';
      subDiv.textContent = text;
      card.appendChild(subDiv);
    });
  }

  return card;
}

function showChartFromSummary(chartType) {
  var chartsSection = document.getElementById('chartsSection');
  var showChartsBtn = document.getElementById('showChartsBtn');
  if (chartsSection) chartsSection.hidden = false;
  if (showChartsBtn) showChartsBtn.hidden = true;
  if (typeof switchChartType === 'function') {
    switchChartType(chartType);
  }
  if (chartsSection) chartsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function renderMeasurementSummary(rows) {
  if (!measurementSummary) return;
  measurementSummary.innerHTML = '';

  if (!rows.length) {
    measurementSummary.hidden = true;
    return;
  }

  var title = document.createElement('h3');
  title.textContent = 'Current Measurements';
  measurementSummary.appendChild(title);

  var tableWrap = document.createElement('div');
  tableWrap.className = 'measurement-summary-table-wrap';

  var table = document.createElement('table');
  table.className = 'measurement-summary-table';

  var thead = document.createElement('thead');
  var headRow = document.createElement('tr');
  ['Parameter', 'Value', 'Centile', 'SDS', ''].forEach(function (label) {
    var th = document.createElement('th');
    th.textContent = label;
    headRow.appendChild(th);
  });
  thead.appendChild(headRow);
  table.appendChild(thead);

  var tbody = document.createElement('tbody');
  function appendCell(tr, label, text) {
    var td = document.createElement('td');
    td.setAttribute('data-label', label);
    td.textContent = text;
    tr.appendChild(td);
    return td;
  }

  rows.forEach(function (row) {
    var tr = document.createElement('tr');

    appendCell(tr, 'Parameter', row.label);
    appendCell(tr, 'Value', row.extra ? row.value + ' (' + row.extra + ')' : row.value);
    appendCell(tr, 'Centile', row.centile);
    appendCell(tr, 'SDS', row.sds);

    var chartCell = document.createElement('td');
    chartCell.setAttribute('data-label', 'Chart');
    var chartBtn = document.createElement('button');
    chartBtn.type = 'button';
    chartBtn.className = 'btn-summary-chart';
    chartBtn.setAttribute('aria-label', 'View ' + row.label + ' chart');
    chartBtn.setAttribute('data-chart', row.key);
    chartBtn.textContent = 'Chart';
    chartBtn.addEventListener('click', function () {
      showChartFromSummary(row.key);
    });
    chartCell.appendChild(chartBtn);
    tr.appendChild(chartCell);

    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  tableWrap.appendChild(table);
  measurementSummary.appendChild(tableWrap);
  measurementSummary.hidden = false;
}

function displayResults(results) {
  resultsGrid.innerHTML = '';

  // Hide errors
  clearError();

  // --- Age card ---
  if (results.age_calendar !== undefined) {
    const ageText = formatCalendarAge(results.age_calendar);
    const subs = [];
    if (results.age_years !== undefined) {
      subs.push(results.age_years.toFixed(2) + ' decimal years');
    }
    resultsGrid.appendChild(createResultCard('AGE', ageText, subs));
  }

  // --- Corrected age card (preterm) ---
  if (results.corrected_age_calendar !== undefined) {
    const correctedText = formatCalendarAge(results.corrected_age_calendar);
    const subs = [];
    if (results.corrected_age_years !== undefined) {
      subs.push(results.corrected_age_years.toFixed(2) + ' corrected decimal years');
    }
    subs.push('Gestation correction applied');
    resultsGrid.appendChild(createResultCard('CORRECTED AGE', correctedText, subs));
  }

  // --- Measurement cards: weight, height, ofc, bmi ---
  renderMeasurementSummary(buildMeasurementSummaryRows(results));

  // --- Mid-parental height card ---
  if (results.mid_parental_height) {
    const mph = results.mid_parental_height;
    const value = mph.mid_parental_height + ' cm';
    const subs = [];

    if (mph.target_range_lower !== undefined && mph.target_range_upper !== undefined) {
      subs.push(
        'Target: ' + mph.target_range_lower.toFixed(1) + ' \u2013 ' +
        mph.target_range_upper.toFixed(1) + ' cm'
      );
    }
    if (mph.mid_parental_height_centile !== undefined) {
      subs.push('Centile: ' + formatCentile(mph.mid_parental_height_centile));
    }
    if (mph.mid_parental_height_sds !== undefined) {
      subs.push('SDS: ' + formatSds(mph.mid_parental_height_sds));
    }

    resultsGrid.appendChild(createResultCard('MID-PARENTAL HEIGHT', value, subs));
  }

  // --- BSA card ---
  if (results.bsa) {
    resultsGrid.appendChild(createResultCard(
      'BODY SURFACE AREA',
      results.bsa.value + ' m\u00B2',
      ['Method: ' + results.bsa.method]
    ));
  }

  // --- Height velocity card ---
  if (results.height_velocity && results.height_velocity.value !== null) {
    var velSubs = [];
    if (results.height_velocity.based_on_date) {
      velSubs.push('Based on measurement from ' + results.height_velocity.based_on_date);
    }
    resultsGrid.appendChild(createResultCard(
      'HEIGHT VELOCITY',
      results.height_velocity.value + ' cm/year',
      velSubs
    ));
  } else if (results.height_velocity && results.height_velocity.message) {
    resultsGrid.appendChild(createResultCard(
      'HEIGHT VELOCITY',
      'N/A',
      [results.height_velocity.message]
    ));
  }

  // --- Bone age card ---
  if (results.bone_age_height) {
    var ba = results.bone_age_height;
    var baSubs = [
      'Standard: ' + (ba.standard === 'gp' ? 'Greulich-Pyle' : 'TW3'),
      'Height for bone age centile: ' + formatCentile(ba.centile),
      'Height for bone age SDS: ' + formatSds(ba.sds),
    ];
    if (!ba.within_window) baSubs.push('Outside \u00b11 month window');
    resultsGrid.appendChild(createResultCard(
      'BONE AGE',
      ba.bone_age + ' years',
      baSubs
    ));
  }

  // --- GH dose calculator ---
  if (results.gh_dose && results.gh_dose.initial_daily_dose !== null) {
    var ghCalc = document.getElementById('ghCalculator');
    if (ghCalc) {
      ghCalc.hidden = false;
      if (results.bsa) currentBsa = results.bsa.value;
      // Read weight directly from the form (lastPayload may not be set yet)
      var weightVal = document.getElementById('weight')?.value;
      if (weightVal) currentWeightKg = parseFloat(weightVal);
      var pen = getSelectedPen();
      currentGhDose = roundToStep(results.gh_dose.initial_daily_dose, pen.step);
      currentGhDose = Math.min(currentGhDose, pen.max);
      currentGhDose = Math.max(currentGhDose, pen.min);
      updateGhDisplay();
    }
  } else {
    var ghCalculator = document.getElementById('ghCalculator');
    if (ghCalculator) ghCalculator.hidden = true;
  }

  // --- Warnings ---
  displayWarnings(results.validation_messages);

  // Store results for chart access
  lastResults = results;
  lastPayload = gatherFormData();

  // Show "Show Growth Charts" button
  var showChartsBtn = document.getElementById('showChartsBtn');
  if (showChartsBtn) showChartsBtn.hidden = false;

  // Show results section
  resultsSection.removeAttribute('hidden');

  // Re-render charts if already visible
  var chartsSection = document.getElementById('chartsSection');
  if (chartsSection && !chartsSection.hidden && typeof loadAndRenderChart === 'function') {
    loadAndRenderChart();
  }

  // Scroll results into view (only on manual submit, not auto-calc)
  if (!autoCalcInProgress) {
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}

function displayWarnings(warnings) {
  if (!warnings || !warnings.length) {
    warningsDisplay.setAttribute('hidden', '');
    warningsList.innerHTML = '';
    return;
  }

  warningsList.innerHTML = '';
  warnings.forEach(function (msg) {
    const li = document.createElement('li');
    li.textContent = msg;
    warningsList.appendChild(li);
  });
  warningsDisplay.removeAttribute('hidden');
}

/* ------------------------------------------------------------------ */
/*  GH Dose Display                                                   */
/* ------------------------------------------------------------------ */

function updateGhDisplay() {
  var valueEl = document.getElementById('ghDoseValue');
  if (valueEl) valueEl.textContent = currentGhDose.toFixed(3);
  var resultsDiv = document.getElementById('ghResults');
  if (!resultsDiv) return;
  var lines = [];
  if (currentBsa) {
    lines.push('= ' + ((currentGhDose * 7) / currentBsa).toFixed(1) + ' mg/m\u00B2/week');
  }
  if (currentWeightKg) {
    lines.push('= ' + ((currentGhDose * 1000) / currentWeightKg).toFixed(1) + ' mcg/kg/day');
  }
  resultsDiv.replaceChildren();
  lines.forEach(function (line) {
    var div = document.createElement('div');
    div.textContent = line;
    resultsDiv.appendChild(div);
  });
  // Show pen range info
  var pen = getSelectedPen();
  var infoEl = document.getElementById('ghPenInfo');
  if (infoEl) infoEl.textContent = 'Step: ' + pen.step + ' mg | Range: ' + pen.min.toFixed(3) + ' \u2013 ' + pen.max.toFixed(3) + ' mg';
}

/* ------------------------------------------------------------------ */
/*  Disclaimer                                                        */
/* ------------------------------------------------------------------ */

function dismissDisclaimer() {
  if (disclaimer) disclaimer.setAttribute('hidden', '');
}

/* ------------------------------------------------------------------ */
/*  localStorage persistence                                          */
/*                                                                    */
/*  Only non-identifying UI preferences are persisted. DOBs,          */
/*  measurement dates, measurement values, parental heights,          */
/*  previous measurements, and bone-age assessments are deliberately  */
/*  NOT written to localStorage — the app advertises no patient data  */
/*  retention and we honour that client-side too.                     */
/* ------------------------------------------------------------------ */

const PERSISTED_PREFERENCE_KEYS = ['reference'];

function saveFormState() {
  const state = {
    sex: document.querySelector('input[name="sex"]:checked')?.value || '',
  };

  PERSISTED_PREFERENCE_KEYS.forEach(function (id) {
    const el = document.getElementById(id);
    if (el && el.value) state[id] = el.value;
  });

  var ghCheck = document.getElementById('ghTreatment');
  if (ghCheck) state.ghTreatment = ghCheck.checked;

  var modeCheck = document.getElementById('modeToggle');
  if (modeCheck) state.advancedMode = modeCheck.checked;

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch (_) {
    // localStorage may be unavailable; silently ignore
  }
}

function restoreFormState() {
  let state;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    state = JSON.parse(raw);
  } catch (_) {
    return;
  }

  if (!state) return;

  if (state.sex === 'male') {
    const el = document.getElementById('sexMale');
    if (el) el.checked = true;
  } else if (state.sex === 'female') {
    const el = document.getElementById('sexFemale');
    if (el) el.checked = true;
  }

  PERSISTED_PREFERENCE_KEYS.forEach(function (id) {
    if (state[id]) {
      const el = document.getElementById(id);
      if (el) el.value = state[id];
    }
  });

  if (state.ghTreatment) {
    var ghEl = document.getElementById('ghTreatment');
    if (ghEl) ghEl.checked = true;
  }

  if (state.advancedMode) {
    var modeEl = document.getElementById('modeToggle');
    if (modeEl) { modeEl.checked = true; handleModeToggle(); }
  }
}

const debouncedSave = debounce(saveFormState, 500);

/* ------------------------------------------------------------------ */
/*  Auto-calculate on form change                                      */
/* ------------------------------------------------------------------ */

function autoCalculate() {
  // Only auto-calculate if minimum required fields are filled
  var sex = document.querySelector('input[name="sex"]:checked');
  var dob = document.getElementById('birthDate')?.value;
  var measDate = document.getElementById('measurementDate')?.value;
  var weight = document.getElementById('weight')?.value;
  var height = document.getElementById('height')?.value;
  var ofc = document.getElementById('ofc')?.value;

  if (!sex || !dob || !measDate) return;
  if (!weight && !height && !ofc) return;

  // Flag prevents the submit handler from scrolling the results into view
  // during an auto-calculation; handleSubmit() clears it in its finally.
  autoCalcInProgress = true;
  if (form) form.requestSubmit();
}

var debouncedAutoCalc = debounce(autoCalculate, 800);

/* ------------------------------------------------------------------ */
/*  Reset                                                             */
/* ------------------------------------------------------------------ */

function resetForm() {
  // Reset the HTML form (clears all inputs)
  if (form) form.reset();

  // Clear localStorage
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (_) {
    // ignore
  }

  // Hide results and errors
  clearError();
  clearFieldErrors();
  if (resultsSection) resultsSection.setAttribute('hidden', '');
  if (warningsDisplay) warningsDisplay.setAttribute('hidden', '');
  if (warningsList) warningsList.innerHTML = '';
  if (resultsGrid) resultsGrid.innerHTML = '';
  if (measurementSummary) {
    measurementSummary.innerHTML = '';
    measurementSummary.hidden = true;
  }

  // Reset advanced mode toggle
  document.body.classList.remove('advanced-mode');
  var modeToggle = document.getElementById('modeToggle');
  if (modeToggle) modeToggle.checked = false;

  // Reset GH treatment checkbox
  var ghCheck = document.getElementById('ghTreatment');
  if (ghCheck) ghCheck.checked = false;

  // Reset GH calculator state
  currentGhDose = 0;
  currentBsa = null;
  currentWeightKg = null;
  var ghCalcEl = document.getElementById('ghCalculator');
  if (ghCalcEl) ghCalcEl.hidden = true;

  // Clear previous measurements
  var prevBody = document.getElementById('prevMeasurementsBody');
  if (prevBody) prevBody.innerHTML = '';
  var prevContent = document.getElementById('prevMeasurementsContent');
  if (prevContent) prevContent.hidden = true;
  var prevToggle = document.getElementById('prevMeasurementsToggle');
  if (prevToggle) {
    var icon = prevToggle.querySelector('.material-symbols-outlined');
    if (icon) icon.textContent = 'add';
  }

  // Clear bone age assessments
  var baBody = document.getElementById('boneAgeBody');
  if (baBody) baBody.innerHTML = '';
  var baContent = document.getElementById('boneAgeContent');
  if (baContent) baContent.hidden = true;
  var baToggle = document.getElementById('boneAgeToggle');
  if (baToggle) {
    var baIcon = baToggle.querySelector('.material-symbols-outlined');
    if (baIcon) baIcon.textContent = 'add';
  }

  // Hide chart section
  lastResults = null;
  lastPayload = null;
  var chartsSection = document.getElementById('chartsSection');
  if (chartsSection) chartsSection.hidden = true;
  var showChartsBtn = document.getElementById('showChartsBtn');
  if (showChartsBtn) showChartsBtn.hidden = true;
}

/* ------------------------------------------------------------------ */
/*  Keyboard shortcuts                                                */
/* ------------------------------------------------------------------ */

function handleKeyboardShortcuts(event) {
  // Ctrl+C or Cmd+C: copy results (when results visible and not in an input)
  if (event.key === 'c' && (event.ctrlKey || event.metaKey)) {
    var activeTag = document.activeElement ? document.activeElement.tagName : '';
    var resultsVisible = resultsSection && !resultsSection.hidden;
    if (resultsVisible && activeTag !== 'INPUT' && activeTag !== 'TEXTAREA' && activeTag !== 'SELECT') {
        event.preventDefault();
        handleCopyResults();
        return;
    }
  }

  // Ctrl+Enter or Cmd+Enter: submit form
  if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
    event.preventDefault();
    if (form) form.requestSubmit();
    return;
  }

  // Escape: reset form
  if (event.key === 'Escape') {
    event.preventDefault();
    resetForm();
  }
}

/* ------------------------------------------------------------------ */
/*  Initialisation                                                    */
/* ------------------------------------------------------------------ */

document.addEventListener('DOMContentLoaded', function () {
  // Cache DOM references
  form = document.getElementById('growthForm');
  calculateBtn = document.getElementById('calculateBtn');
  resetBtn = document.getElementById('resetBtn');
  errorDisplay = document.getElementById('errorDisplay');
  errorMessage = document.getElementById('errorMessage');
  resultsSection = document.getElementById('resultsSection');
  measurementSummary = document.getElementById('measurementSummary');
  resultsGrid = document.getElementById('resultsGrid');
  warningsDisplay = document.getElementById('warningsDisplay');
  warningsList = document.getElementById('warningsList');
  disclaimer = document.getElementById('disclaimer');
  dismissDisclaimerBtn = document.getElementById('dismissDisclaimer');
  toast = document.getElementById('toast');

  // Initialise theme (before restoreFormState)
  initTheme();
  var themeBtn = document.getElementById('themeToggle');
  if (themeBtn) themeBtn.addEventListener('click', toggleTheme);

  // Event listeners
  if (form) {
    form.addEventListener('submit', handleSubmit);
    form.addEventListener('input', function() { debouncedSave(); debouncedAutoCalc(); });
    form.addEventListener('change', function() { debouncedSave(); debouncedAutoCalc(); });
  }

  if (resetBtn) {
    resetBtn.addEventListener('click', resetForm);
  }

  if (dismissDisclaimerBtn) {
    dismissDisclaimerBtn.addEventListener('click', dismissDisclaimer);
  }

  var modeToggle = document.getElementById('modeToggle');
  if (modeToggle) modeToggle.addEventListener('change', handleModeToggle);

  // Previous measurements toggle
  var prevToggle = document.getElementById('prevMeasurementsToggle');
  var prevContent = document.getElementById('prevMeasurementsContent');
  if (prevToggle && prevContent) {
    prevToggle.addEventListener('click', function() { toggleCollapsible(prevToggle, prevContent); });
    // Close button
    var closeBtn = prevContent.querySelector('.collapsible-close');
    if (closeBtn) closeBtn.addEventListener('click', function() {
      prevContent.hidden = true;
      prevToggle.querySelector('.material-symbols-outlined').textContent = 'add';
    });
  }
  // Add another row button
  var addPrevBtn = document.getElementById('addPrevMeasurement');
  if (addPrevBtn) addPrevBtn.addEventListener('click', function() { addPrevMeasurementRow(); });
  // CSV import
  var importBtn = document.getElementById('importCsvBtn');
  var csvInput = document.getElementById('csvFileInput');
  if (importBtn && csvInput) {
    importBtn.addEventListener('click', function() { csvInput.click(); });
    csvInput.addEventListener('change', function() {
      if (csvInput.files.length > 0) importCsv(csvInput.files[0]);
      csvInput.value = ''; // Reset for re-import
    });
  }
  // CSV export
  var exportBtn = document.getElementById('exportCsvBtn');
  if (exportBtn) exportBtn.addEventListener('click', exportCsv);

  // Bone age toggle
  var baToggle = document.getElementById('boneAgeToggle');
  var baContent = document.getElementById('boneAgeContent');
  if (baToggle && baContent) {
    baToggle.addEventListener('click', function() {
      if (baContent.hidden) {
        baContent.hidden = false;
        baToggle.querySelector('.material-symbols-outlined').textContent = 'remove';
        var tbody = document.getElementById('boneAgeBody');
        if (tbody && tbody.children.length === 0) addBoneAgeRow();
      } else {
        baContent.hidden = true;
        baToggle.querySelector('.material-symbols-outlined').textContent = 'add';
      }
    });
    var baCloseBtn = baContent.querySelector('.collapsible-close');
    if (baCloseBtn) baCloseBtn.addEventListener('click', function() {
      baContent.hidden = true;
      baToggle.querySelector('.material-symbols-outlined').textContent = 'add';
    });
  }
  var addBaBtn = document.getElementById('addBoneAge');
  if (addBaBtn) addBaBtn.addEventListener('click', function() { addBoneAgeRow(); });

  // GH dose adjuster buttons — pen-specific increments
  var ghIncBtn = document.getElementById('ghIncrease');
  var ghDecBtn = document.getElementById('ghDecrease');
  if (ghIncBtn) ghIncBtn.addEventListener('click', function() {
    var pen = getSelectedPen();
    var next = roundToStep(currentGhDose + pen.step, pen.step);
    currentGhDose = Math.min(next, pen.max);
    updateGhDisplay();
  });
  if (ghDecBtn) ghDecBtn.addEventListener('click', function() {
    var pen = getSelectedPen();
    var next = roundToStep(currentGhDose - pen.step, pen.step);
    currentGhDose = Math.max(next, 0);
    updateGhDisplay();
  });
  // Re-round dose when pen device changes
  var ghPenSel = document.getElementById('ghPenDevice');
  if (ghPenSel) ghPenSel.addEventListener('change', function() {
    var pen = getSelectedPen();
    currentGhDose = roundToStep(currentGhDose, pen.step);
    currentGhDose = Math.min(currentGhDose, pen.max);
    currentGhDose = Math.max(currentGhDose, pen.min);
    updateGhDisplay();
  });

  // Copy, PDF export, and chart download buttons
  var copyBtn = document.getElementById('copyResultsBtn');
  if (copyBtn) copyBtn.addEventListener('click', handleCopyResults);
  var pdfBtn = document.getElementById('exportPdfBtn');
  if (pdfBtn) pdfBtn.addEventListener('click', handleExportPdf);
  var dlChartBtn = document.getElementById('downloadChartBtn');
  if (dlChartBtn) dlChartBtn.addEventListener('click', function() { if (typeof downloadChart === 'function') downloadChart(); });

  document.addEventListener('keydown', handleKeyboardShortcuts);

  // Restore saved form state
  restoreFormState();

  // Default measurement date to today if not already set
  var measDateEl = document.getElementById('measurementDate');
  if (measDateEl && !measDateEl.value) {
    measDateEl.value = new Date().toISOString().split('T')[0];
  }

  // Set initial mode label active state
  var initLabels = document.querySelectorAll('.mode-label');
  if (initLabels.length >= 2) {
    var modeChecked = document.getElementById('modeToggle')?.checked;
    initLabels[0].classList.toggle('active-label', !modeChecked);
    initLabels[1].classList.toggle('active-label', !!modeChecked);
  }
});

// Export for Node.js (Jest) -- no-op in browser
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    debounce,
    formatCentile,
    formatSds,
    formatCalendarAge,
    buildMeasurementSummaryRows,
    showChartFromSummary,
    gatherFormData,
    saveFormState,
    restoreFormState,
    resetForm,
    showError,
    clearError,
    dismissDisclaimer,
    displayResults,
    handleSubmit,
    handleModeToggle,
    addPrevMeasurementRow,
    getPreviousMeasurements,
    importCsv,
    parsePreviousMeasurementsCsv,
    exportCsv,
    toggleCollapsible,
    addBoneAgeRow,
    getBoneAgeAssessments,
    updateGhDisplay,
    __testHooks: {
      setGhState: function (state) {
        currentGhDose = state.dose;
        currentBsa = state.bsa;
        currentWeightKg = state.weightKg;
      },
      updateGhDisplay,
    },
    showToast,
    handleCopyResults,
    handleExportPdf,
    initTheme,
    toggleTheme,
    updateThemeIcon,
  };
}
