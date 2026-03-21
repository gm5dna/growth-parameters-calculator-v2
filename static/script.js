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

const FIELD_IDS = [
  'birthDate',
  'measurementDate',
  'weight',
  'height',
  'ofc',
  'maternalHeight',
  'paternalHeight',
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
  };
}
