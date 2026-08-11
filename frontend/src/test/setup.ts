import { expect, afterEach, beforeEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
import * as matchers from '@testing-library/jest-dom/matchers';

// Extend Vitest's expect with jest-dom matchers
expect.extend(matchers);

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
