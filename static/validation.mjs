/**
 * Client-side validation — for UX only. Server-side validation is authoritative.
 * Each function returns null if valid, or an error message string if invalid.
 */

export function validateDate(value) {
  if (!value || typeof value !== 'string') return 'Date is required.';
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return 'Date must be in YYYY-MM-DD format.';
  const parsed = new Date(value + 'T00:00:00');
  if (isNaN(parsed.getTime())) return 'Invalid date.';
  if (parsed > new Date()) return 'Date cannot be in the future.';
  return null;
}

function validateNumericRange(value, min, max, name) {
  if (value === '' || value === null || value === undefined) return null;
  // Number() rejects strings with trailing garbage like "12abc"; parseFloat
  // would silently accept them. Server-side validation catches this too, but
  // keep client-side consistent.
  const num = Number(value);
  if (!Number.isFinite(num)) return name + ' must be a number.';
  if (num < min || num > max) return name + ' must be between ' + min + ' and ' + max + '.';
  return null;
}

export function validateWeight(value) {
  return validateNumericRange(value, 0.1, 300, 'Weight');
}

export function validateHeight(value) {
  return validateNumericRange(value, 10, 250, 'Height');
}

export function validateOfc(value) {
  return validateNumericRange(value, 10, 100, 'Head circumference');
}

export function validateSex(value) {
  if (!value || (value !== 'male' && value !== 'female')) return 'Please select sex.';
  return null;
}

export function validateAtLeastOneMeasurement(weight, height, ofc) {
  if ((!weight || weight === '') && (!height || height === '') && (!ofc || ofc === '')) {
    return 'At least one measurement is required.';
  }
  return null;
}
