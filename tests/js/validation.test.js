const {
  validateDate,
  validateWeight,
  validateHeight,
  validateOfc,
  validateSex,
  validateAtLeastOneMeasurement,
} = require('../../static/validation');

describe('validateDate', () => {
  test('accepts valid YYYY-MM-DD', () => {
    expect(validateDate('2023-06-15')).toBeNull();
  });

  test('rejects empty string', () => {
    expect(validateDate('')).toBeTruthy();
  });

  test('rejects invalid format', () => {
    expect(validateDate('15/06/2023')).toBeTruthy();
  });

  test('rejects future date', () => {
    expect(validateDate('2099-01-01')).toBeTruthy();
  });
});

describe('validateWeight', () => {
  test('accepts valid weight', () => {
    expect(validateWeight('12.5')).toBeNull();
  });

  test('accepts empty (optional)', () => {
    expect(validateWeight('')).toBeNull();
  });

  test('rejects below minimum', () => {
    expect(validateWeight('0.05')).toBeTruthy();
  });

  test('rejects above maximum', () => {
    expect(validateWeight('301')).toBeTruthy();
  });

  test('rejects non-numeric', () => {
    expect(validateWeight('abc')).toBeTruthy();
  });
});

describe('validateHeight', () => {
  test('accepts valid height', () => {
    expect(validateHeight('95.0')).toBeNull();
  });

  test('accepts empty', () => {
    expect(validateHeight('')).toBeNull();
  });

  test('rejects below minimum', () => {
    expect(validateHeight('5')).toBeTruthy();
  });
});

describe('validateOfc', () => {
  test('accepts valid ofc', () => {
    expect(validateOfc('48.2')).toBeNull();
  });

  test('rejects above maximum', () => {
    expect(validateOfc('110')).toBeTruthy();
  });
});

describe('validateSex', () => {
  test('accepts male', () => {
    expect(validateSex('male')).toBeNull();
  });

  test('accepts female', () => {
    expect(validateSex('female')).toBeNull();
  });

  test('rejects empty', () => {
    expect(validateSex('')).toBeTruthy();
  });
});

describe('validateAtLeastOneMeasurement', () => {
  test('passes with weight', () => {
    expect(validateAtLeastOneMeasurement('12', '', '')).toBeNull();
  });

  test('fails with no measurements', () => {
    expect(validateAtLeastOneMeasurement('', '', '')).toBeTruthy();
  });
});

describe('non-finite and trailing-garbage inputs', () => {
  // parseFloat would silently accept "12abc"; the switch to Number() makes the
  // client validator match the server.
  test('rejects weight with trailing garbage', () => {
    expect(validateWeight('12abc')).toBeTruthy();
  });

  test('rejects height with trailing garbage', () => {
    expect(validateHeight('90x')).toBeTruthy();
  });

  test('rejects Infinity weight', () => {
    expect(validateWeight('Infinity')).toBeTruthy();
  });

  test('rejects NaN weight', () => {
    expect(validateWeight('NaN')).toBeTruthy();
  });

  test('accepts scientific notation', () => {
    expect(validateWeight('1.2e1')).toBeNull(); // 12
  });
});
