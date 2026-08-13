import { expect, afterEach, beforeEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
import * as matchers from '@testing-library/jest-dom/matchers';

// Extend Vitest's expect with jest-dom matchers
expect.extend(matchers);

if (typeof globalThis.localStorage === 'undefined') {
  const values = new Map<string, string>();
  const localStorageShim: Storage = {
    get length() { return values.size; },
    clear: () => values.clear(),
    getItem: (key) => values.get(key) ?? null,
    key: (index) => [...values.keys()][index] ?? null,
    removeItem: (key) => values.delete(key),
    setItem: (key, value) => values.set(key, String(value)),
  };
  Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: localStorageShim });
}

// A few legacy suites were authored for Jest. Keep their spy surface working
// while the suite is migrated to Vitest, without adding a second test runner.
(globalThis as typeof globalThis & { jest: typeof vi }).jest = vi;

// Cleanup after each test
afterEach(() => {
  cleanup();
});

// Keep browser-backed caches and jsdom-only APIs deterministic across suites.
beforeEach(() => {
  localStorage.clear();
  window.scrollTo = vi.fn() as typeof window.scrollTo;
  Element.prototype.scrollIntoView = vi.fn();
});
