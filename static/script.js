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

/* ------------------------------------------------------------------ */
/*  Constants                                                         */
/* ------------------------------------------------------------------ */

const STORAGE_KEY = 'growthCalculatorFormState';

var lastResults = null;
var lastPayload = null;

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
  debouncedSave();
}

/* ------------------------------------------------------------------ */
/*  Previous Measurements — table row management                      */
/* ------------------------------------------------------------------ */

function addPrevMeasurementRow(dateVal, heightVal, weightVal, ofcVal) {
  var tbody = document.getElementById('prevMeasurementsBody');
  if (!tbody) return;
  var tr = document.createElement('tr');
  tr.innerHTML =
    '<td><input type="date" class="prev-date" value="' + (dateVal || '') + '"></td>' +
    '<td><input type="number" class="prev-height" step="0.1" min="10" max="250" value="' + (heightVal || '') + '"></td>' +
    '<td><input type="number" class="prev-weight" step="0.01" min="0.1" max="300" value="' + (weightVal || '') + '"></td>' +
    '<td><input type="number" class="prev-ofc" step="0.1" min="10" max="100" value="' + (ofcVal || '') + '"></td>' +
    '<td><button type="button" class="btn-delete" aria-label="Delete row"><span class="material-symbols-outlined">delete</span></button></td>';
  // Wire up delete button
  tr.querySelector('.btn-delete').addEventListener('click', function() { tr.remove(); debouncedSave(); });
  // Wire up change events for auto-save
  tr.querySelectorAll('input').forEach(function(input) { input.addEventListener('change', debouncedSave); });
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

function importCsv(file) {
  var reader = new FileReader();
  reader.onload = function(e) {
    var lines = e.target.result.trim().split('\n');
    if (lines.length < 2) return; // Need header + at least 1 row
    // Skip header line
    for (var i = 1; i < lines.length; i++) {
      var cols = lines[i].split(',').map(function(c) { return c.trim(); });
      if (cols.length < 1) continue;
      addPrevMeasurementRow(cols[0] || '', cols[1] || '', cols[2] || '', cols[3] || '');
    }
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
    tr.innerHTML =
        '<td><input type="date" class="ba-date" value="' + (dateVal || '') + '"></td>' +
        '<td><input type="number" class="ba-age" step="0.1" min="0" max="20" value="' + (ageVal || '') + '"></td>' +
        '<td><select class="ba-standard"><option value="gp"' + (standardVal === 'gp' || !standardVal ? ' selected' : '') + '>Greulich-Pyle</option><option value="tw3"' + (standardVal === 'tw3' ? ' selected' : '') + '>TW3</option></select></td>' +
        '<td><button type="button" class="btn-delete" aria-label="Delete row"><span class="material-symbols-outlined">delete</span></button></td>';
    tr.querySelector('.btn-delete').addEventListener('click', function() { tr.remove(); debouncedSave(); });
    tr.querySelectorAll('input, select').forEach(function(el) { el.addEventListener('change', debouncedSave); });
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

function displayResults(results) {
  resultsGrid.innerHTML = '';

  // Hide errors
  clearError();

  // --- Age card ---
  if (results.age_calendar !== undefined) {
    const ageText = formatCalendarAge(results.age_calendar);
    const subs = [];
    if (results.age_years !== undefined) {
      subs.push(results.age_years.toFixed(4) + ' decimal years');
    }
    resultsGrid.appendChild(createResultCard('AGE', ageText, subs));
  }

  // --- Corrected age card (preterm) ---
  if (results.corrected_age_calendar !== undefined) {
    const correctedText = formatCalendarAge(results.corrected_age_calendar);
    const subs = [];
    if (results.corrected_age_years !== undefined) {
      subs.push(results.corrected_age_years.toFixed(4) + ' corrected decimal years');
    }
    subs.push('Gestation correction applied');
    resultsGrid.appendChild(createResultCard('CORRECTED AGE', correctedText, subs));
  }

  // --- Measurement cards: weight, height, ofc, bmi ---
  ['weight', 'height', 'ofc', 'bmi'].forEach(function (method) {
    const meas = results[method];
    if (!meas) return;

    const label = MEASUREMENT_LABELS[method] || method.toUpperCase();
    const unit = MEASUREMENT_UNITS[method] || '';
    const value = meas.value + ' ' + unit;
    const subs = [];

    if (meas.centile !== null && meas.centile !== undefined) {
      subs.push('Centile: ' + formatCentile(meas.centile));
    }
    if (meas.sds !== null && meas.sds !== undefined) {
      subs.push('SDS: ' + formatSds(meas.sds));
    }

    resultsGrid.appendChild(createResultCard(label, value, subs));
  });

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

  // Scroll results into view
  resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
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
/*  Disclaimer                                                        */
/* ------------------------------------------------------------------ */

function dismissDisclaimer() {
  if (disclaimer) disclaimer.setAttribute('hidden', '');
}

/* ------------------------------------------------------------------ */
/*  localStorage persistence                                          */
/* ------------------------------------------------------------------ */

function saveFormState() {
  const state = {
    sex: document.querySelector('input[name="sex"]:checked')?.value || '',
  };

  FIELD_IDS.forEach(function (id) {
    const el = document.getElementById(id);
    if (el) state[id] = el.value;
  });

  var ghCheck = document.getElementById('ghTreatment');
  if (ghCheck) state.ghTreatment = ghCheck.checked;

  var modeCheck = document.getElementById('modeToggle');
  if (modeCheck) state.advancedMode = modeCheck.checked;

  state.previousMeasurements = getPreviousMeasurements();
  state.boneAgeAssessments = getBoneAgeAssessments();

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

  // Restore sex radio
  if (state.sex === 'male') {
    const el = document.getElementById('sexMale');
    if (el) el.checked = true;
  } else if (state.sex === 'female') {
    const el = document.getElementById('sexFemale');
    if (el) el.checked = true;
  }

  // Restore text/date/number fields
  FIELD_IDS.forEach(function (id) {
    if (state[id] !== undefined && state[id] !== '') {
      const el = document.getElementById(id);
      if (el) el.value = state[id];
    }
  });

  // Restore GH treatment checkbox
  if (state.ghTreatment) {
    var ghEl = document.getElementById('ghTreatment');
    if (ghEl) ghEl.checked = true;
  }

  // Restore advanced mode toggle
  if (state.advancedMode) {
    var modeEl = document.getElementById('modeToggle');
    if (modeEl) { modeEl.checked = true; handleModeToggle(); }
  }

  // Restore previous measurements
  if (state.previousMeasurements && state.previousMeasurements.length > 0) {
    state.previousMeasurements.forEach(function(m) {
      addPrevMeasurementRow(m.date || '', m.height || '', m.weight || '', m.ofc || '');
    });
    // Expand the section
    var prevContent = document.getElementById('prevMeasurementsContent');
    var prevToggle = document.getElementById('prevMeasurementsToggle');
    if (prevContent) prevContent.hidden = false;
    if (prevToggle) prevToggle.querySelector('.material-symbols-outlined').textContent = 'remove';
  }

  // Restore bone age assessments
  if (state.boneAgeAssessments && state.boneAgeAssessments.length > 0) {
    state.boneAgeAssessments.forEach(function(ba) {
      addBoneAgeRow(ba.date || '', ba.bone_age || '', ba.standard || 'gp');
    });
    var baContent = document.getElementById('boneAgeContent');
    var baToggle = document.getElementById('boneAgeToggle');
    if (baContent) baContent.hidden = false;
    if (baToggle) baToggle.querySelector('.material-symbols-outlined').textContent = 'remove';
  }
}

const debouncedSave = debounce(saveFormState, 500);

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

  // Reset advanced mode toggle
  document.body.classList.remove('advanced-mode');
  var modeToggle = document.getElementById('modeToggle');
  if (modeToggle) modeToggle.checked = false;

  // Reset GH treatment checkbox
  var ghCheck = document.getElementById('ghTreatment');
  if (ghCheck) ghCheck.checked = false;

  // Hide GH calculator if visible
  var ghCalc = document.getElementById('ghCalculator');
  if (ghCalc) ghCalc.hidden = true;

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
  resultsGrid = document.getElementById('resultsGrid');
  warningsDisplay = document.getElementById('warningsDisplay');
  warningsList = document.getElementById('warningsList');
  disclaimer = document.getElementById('disclaimer');
  dismissDisclaimerBtn = document.getElementById('dismissDisclaimer');
  toast = document.getElementById('toast');

  // Event listeners
  if (form) {
    form.addEventListener('submit', handleSubmit);
    form.addEventListener('input', debouncedSave);
    form.addEventListener('change', debouncedSave);
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

  document.addEventListener('keydown', handleKeyboardShortcuts);

  // Restore saved form state
  restoreFormState();
});

// Export for Node.js (Jest) -- no-op in browser
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    debounce,
    formatCentile,
    formatSds,
    formatCalendarAge,
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
    exportCsv,
    toggleCollapsible,
    addBoneAgeRow,
    getBoneAgeAssessments,
  };
}
