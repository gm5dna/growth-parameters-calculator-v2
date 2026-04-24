// ESLint flat config — conservative rule set. This is a safety net for
// obvious bugs (syntax errors, undefined globals, typos), not a style
// enforcer.

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
        // Browser globals used in static app modules and Jest/jsdom tests.
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
        global: "readonly",
        Element: "readonly",
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
      "no-redeclare": ["warn", { builtinGlobals: false }],
      "no-undef": "error",
    },
  },
  {
    files: ["static/**/*.mjs"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
    },
  },
];
