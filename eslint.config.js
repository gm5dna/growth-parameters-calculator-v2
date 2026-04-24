// ESLint flat config — conservative rule set. This is a safety net for
// obvious bugs (syntax errors, undefined globals, typos), not a style
// enforcer. Tighten over time as the JS modules get split up.

const js = require("@eslint/js");

module.exports = [
  {
    ignores: ["static/vendor/**", "node_modules/**", "coverage/**"],
  },
  js.configs.recommended,
  {
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "script",
      globals: {
        // Browser globals used in static/*.js
        window: "readonly",
        document: "readonly",
        localStorage: "readonly",
        sessionStorage: "readonly",
        fetch: "readonly",
        navigator: "readonly",
        console: "readonly",
        alert: "readonly",
        confirm: "readonly",
        prompt: "readonly",
        setTimeout: "readonly",
        clearTimeout: "readonly",
        setInterval: "readonly",
        clearInterval: "readonly",
        requestAnimationFrame: "readonly",
        FileReader: "readonly",
        Blob: "readonly",
        URL: "readonly",
        Image: "readonly",
        HTMLElement: "readonly",
        Event: "readonly",
        CustomEvent: "readonly",
        DOMParser: "readonly",
        MutationObserver: "readonly",
        ResizeObserver: "readonly",
        getComputedStyle: "readonly",
        matchMedia: "readonly",
        // Third-party globals
        Chart: "readonly",
        // Test globals (Jest)
        jest: "readonly",
        describe: "readonly",
        test: "readonly",
        it: "readonly",
        expect: "readonly",
        beforeEach: "readonly",
        afterEach: "readonly",
        beforeAll: "readonly",
        afterAll: "readonly",
        // CommonJS for Jest tests
        module: "readonly",
        require: "readonly",
        // Cross-file symbols shared via the browser window scope. The review
        // flags the script.js/charts.js module split as a future item — until
        // then, allow these names to be resolved across files.
        lastResults: "writable",
        lastPayload: "writable",
        currentChart: "writable",
        loadAndRenderChart: "readonly",
        downloadChart: "readonly",
        captureChartImages: "readonly",
        copyResultsToClipboard: "readonly",
        validateSex: "readonly",
        validateDate: "readonly",
        validateWeight: "readonly",
        validateHeight: "readonly",
        validateOfc: "readonly",
        validateAtLeastOneMeasurement: "readonly",
      },
    },
    rules: {
      // Existing codebase is tolerant of unused args / intentional fall-through.
      // Flag outright bugs only.
      "no-unused-vars": "off",
      "no-empty": "off",
      "no-prototype-builtins": "off",
      "no-inner-declarations": "off",
      "no-useless-escape": "off",
      "no-redeclare": "warn",
      "no-undef": "error",
    },
  },
];
