/**
 * Tests for the CSV parser used by the Previous Measurements Import flow.
 *
 * We only require the parser (a pure function) — this avoids the
 * DOMContentLoaded handler in script.js triggering real DOM initialisation.
 */

// Stub document.addEventListener and minimal DOM before requiring script.js
// so the top-level DOMContentLoaded registration doesn't throw.
require('../../static/validation.js');
require('../../static/clipboard.js');
const { parsePreviousMeasurementsCsv } = require('../../static/script.js');

describe('parsePreviousMeasurementsCsv', () => {
  test('accepts a valid single row', () => {
    const csv = 'date,height,weight,ofc\n2023-01-01,100,15,48';
    const result = parsePreviousMeasurementsCsv(csv);
    expect(result.errors).toEqual([]);
    expect(result.rows).toEqual([['2023-01-01', '100', '15', '48']]);
  });

  test('accepts blank measurements', () => {
    const csv = 'date,height,weight,ofc\n2023-01-01,100,,';
    const result = parsePreviousMeasurementsCsv(csv);
    expect(result.errors).toEqual([]);
    expect(result.rows).toEqual([['2023-01-01', '100', '', '']]);
  });

  test('rejects rows with wrong column count', () => {
    const csv = 'date,height,weight,ofc\n2023-01-01,100,15';
    const result = parsePreviousMeasurementsCsv(csv);
    expect(result.rows).toEqual([]);
    expect(result.errors[0]).toMatch(/expected 4 columns/i);
  });

  test('rejects malformed dates', () => {
    const csv = 'date,height,weight,ofc\n01/01/2023,100,15,48';
    const result = parsePreviousMeasurementsCsv(csv);
    expect(result.rows).toEqual([]);
    expect(result.errors[0]).toMatch(/YYYY-MM-DD/);
  });

  test('rejects non-numeric measurements', () => {
    const csv = 'date,height,weight,ofc\n2023-01-01,abc,15,48';
    const result = parsePreviousMeasurementsCsv(csv);
    expect(result.rows).toEqual([]);
    expect(result.errors[0]).toMatch(/numeric or blank/);
  });

  test('rejects non-finite numbers', () => {
    const csv = 'date,height,weight,ofc\n2023-01-01,Infinity,15,48';
    const result = parsePreviousMeasurementsCsv(csv);
    expect(result.rows).toEqual([]);
    expect(result.errors[0]).toMatch(/numeric or blank/);
  });

  test('accepts and rejects in the same file', () => {
    const csv = [
      'date,height,weight,ofc',
      '2023-01-01,100,15,48',
      'bad-row',
      '2023-06-01,110,17,49',
    ].join('\n');
    const result = parsePreviousMeasurementsCsv(csv);
    expect(result.rows).toHaveLength(2);
    expect(result.errors).toHaveLength(1);
  });

  test('handles CRLF line endings', () => {
    const csv = 'date,height,weight,ofc\r\n2023-01-01,100,15,48\r\n';
    const result = parsePreviousMeasurementsCsv(csv);
    expect(result.errors).toEqual([]);
    expect(result.rows).toHaveLength(1);
  });

  test('skips blank lines', () => {
    const csv = 'date,height,weight,ofc\n\n2023-01-01,100,15,48\n\n';
    const result = parsePreviousMeasurementsCsv(csv);
    expect(result.errors).toEqual([]);
    expect(result.rows).toHaveLength(1);
  });

  test('returns empty rows for empty input', () => {
    expect(parsePreviousMeasurementsCsv('')).toEqual({ rows: [], errors: [] });
    expect(parsePreviousMeasurementsCsv('   \n  \n')).toEqual({ rows: [], errors: [] });
  });

  test('accepts scientific notation and decimals', () => {
    const csv = 'date,height,weight,ofc\n2023-01-01,1.1e2,15.25,48.0';
    const result = parsePreviousMeasurementsCsv(csv);
    expect(result.errors).toEqual([]);
    expect(result.rows).toHaveLength(1);
  });

  test('strips leading UTF-8 BOM so Excel-exported files parse', () => {
    const csv = '﻿date,height,weight,ofc\n2023-01-01,100,15,48';
    const result = parsePreviousMeasurementsCsv(csv);
    expect(result.errors).toEqual([]);
    expect(result.rows).toEqual([['2023-01-01', '100', '15', '48']]);
  });
});
