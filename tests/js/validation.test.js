let validateDate,
  validateWeight,
  validateHeight,
  validateOfc,
  validateSex,
  validateAtLeastOneMeasurement,
  validateNumericRange;

beforeAll(async () => {
  ({
    validateDate,
    validateWeight,
    validateHeight,
    validateOfc,
    validateSex,
    validateAtLeastOneMeasurement,
    validateNumericRange,
  } = await import('../../static/validation.mjs'));
});

// Shared shape across these tables: valid input -> null, invalid input -> truthy error.
function expectValidity(result, isValid) {
  if (isValid) {
    expect(result).toBeNull();
  } else {
    expect(result).toBeTruthy();
  }
}

describe('validateDate', () => {
  test.each([
    ['accepts valid YYYY-MM-DD', '2023-06-15', true],
    ['rejects empty string', '', false],
    ['rejects invalid format', '15/06/2023', false],
    ['rejects future date', '2099-01-01', false],
  ])('%s', (_name, input, isValid) => {
    expectValidity(validateDate(input), isValid);
  });
});

describe('validateWeight', () => {
  // Includes the non-finite / trailing-garbage cases: parseFloat would
  // silently accept "12abc", the switch to Number() makes the client
  // validator match the server.
  test.each([
    ['accepts valid weight', '12.5', true],
    ['accepts empty (optional)', '', true],
    ['rejects below minimum', '0.05', false],
    ['rejects above maximum', '301', false],
    ['rejects non-numeric', 'abc', false],
    ['rejects trailing garbage', '12abc', false],
    ['rejects Infinity', 'Infinity', false],
    ['rejects NaN', 'NaN', false],
    ['accepts scientific notation (1.2e1 = 12)', '1.2e1', true],
  ])('%s', (_name, input, isValid) => {
    expectValidity(validateWeight(input), isValid);
  });
});

describe('validateHeight', () => {
  test.each([
    ['accepts valid height', '95.0', true],
    ['accepts empty', '', true],
    ['rejects below minimum', '5', false],
    ['rejects trailing garbage', '90x', false],
  ])('%s', (_name, input, isValid) => {
    expectValidity(validateHeight(input), isValid);
  });
});

describe('validateOfc', () => {
  test.each([
    ['accepts valid ofc', '48.2', true],
    ['rejects above maximum', '110', false],
  ])('%s', (_name, input, isValid) => {
    expectValidity(validateOfc(input), isValid);
  });
});

describe('validateSex', () => {
  test.each([
    ['accepts male', 'male', true],
    ['accepts female', 'female', true],
    ['rejects empty', '', false],
  ])('%s', (_name, input, isValid) => {
    expectValidity(validateSex(input), isValid);
  });
});

describe('validateAtLeastOneMeasurement', () => {
  test.each([
    ['passes with weight', ['12', '', ''], true],
    ['fails with no measurements', ['', '', ''], false],
  ])('%s', (_name, args, isValid) => {
    expectValidity(validateAtLeastOneMeasurement(...args), isValid);
  });
});

describe('validateNumericRange (parental heights, limits from input min/max)', () => {
  test.each([
    ['accepts value at minimum', '115.4', true],
    ['accepts value at maximum', '211.9', true],
    ['accepts empty (optional)', '', true],
    ['rejects below minimum', '105', false],
    ['rejects above maximum', '212', false],
    ['rejects non-numeric', '1.6m', false],
  ])('%s', (_name, input, isValid) => {
    expectValidity(validateNumericRange(input, 115.4, 211.9, 'Maternal height'), isValid);
  });
});
