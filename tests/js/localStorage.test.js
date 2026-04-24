/**
 * Confirms that localStorage persistence never writes patient-identifiable
 * data. The README promises "no patient data retention"; if a future change
 * re-adds DOB or measurement values to the persisted state, this test fails.
 */

let saveFormState;

beforeAll(async () => {
  ({ saveFormState } = await import('../../static/script.mjs'));
});

const PERMITTED_KEYS = new Set(['sex', 'reference', 'ghTreatment', 'advancedMode']);
const PHI_LIKE_NAMES = [
  'birthDate', 'birth_date', 'measurementDate', 'measurement_date',
  'weight', 'height', 'ofc', 'maternalHeight', 'paternalHeight',
  'maternal_height', 'paternal_height', 'previousMeasurements',
  'boneAgeAssessments', 'bone_age', 'gestationWeeks', 'gestationDays',
];

function buildFormHtml() {
  document.body.innerHTML = `
    <form id="growthForm">
      <input type="radio" name="sex" id="sexMale" value="male" checked />
      <input type="radio" name="sex" id="sexFemale" value="female" />
      <input type="date" id="birthDate" value="2020-06-15" />
      <input type="date" id="measurementDate" value="2023-06-15" />
      <input type="number" id="weight" value="14.5" />
      <input type="number" id="height" value="96.0" />
      <input type="number" id="ofc" value="48.0" />
      <input type="number" id="maternalHeight" value="165" />
      <input type="number" id="paternalHeight" value="178" />
      <input type="number" id="gestationWeeks" value="38" />
      <input type="number" id="gestationDays" value="2" />
      <select id="reference">
        <option value="uk-who" selected>uk-who</option>
      </select>
      <input type="checkbox" id="ghTreatment" checked />
      <input type="checkbox" id="modeToggle" checked />
    </form>
  `;
}

describe('saveFormState', () => {
  beforeEach(() => {
    buildFormHtml();
    localStorage.clear();
  });

  test('only persists non-identifying preferences', () => {
    saveFormState();
    const raw = localStorage.getItem('growthCalculatorFormState');
    expect(raw).toBeTruthy();
    const state = JSON.parse(raw);

    // Every key in persisted state must be on the allow-list.
    Object.keys(state).forEach((key) => {
      expect(PERMITTED_KEYS.has(key)).toBe(true);
    });

    // None of the PHI-like names should appear.
    PHI_LIKE_NAMES.forEach((name) => {
      expect(state).not.toHaveProperty(name);
    });
  });

  test('persists sex and reference', () => {
    saveFormState();
    const state = JSON.parse(localStorage.getItem('growthCalculatorFormState'));
    expect(state.sex).toBe('male');
    expect(state.reference).toBe('uk-who');
  });

  test('persists non-identifying toggle state', () => {
    saveFormState();
    const state = JSON.parse(localStorage.getItem('growthCalculatorFormState'));
    expect(state.ghTreatment).toBe(true);
    expect(state.advancedMode).toBe(true);
  });
});
