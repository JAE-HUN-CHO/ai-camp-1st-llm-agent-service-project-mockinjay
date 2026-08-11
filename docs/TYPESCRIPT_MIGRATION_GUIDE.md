# TypeScript Strict Mode Migration Guide

**Date:** 2025-11-28
**Version:** 1.0.0

## Overview

The Phase 1 migration includes stricter TypeScript configuration to catch potential bugs early. This guide documents the errors found and provides solutions for fixing them.

---

## Error Categories

### 1. Unused Imports and Variables (TS6133, TS6198)

**Error:** `'React' is declared but its value is never read`

**Cause:** In modern React (17+) with JSX transform, you don't need to import React unless you use it directly.

**Solution:**

```typescript
// Before
import React from 'react';

export function MyComponent() {
  return <div>Hello</div>;
}

// After (remove unused import)
export function MyComponent() {
  return <div>Hello</div>;
}

// Or keep if using React namespace
import React from 'react';

export function MyComponent() {
  const [state, setState] = React.useState(0);
  return <div>{state}</div>;
}
```

**Files Affected:**
- src/components/Drawer.tsx
- src/components/Header.tsx
- src/components/Logo.tsx
- src/components/MobileNav.tsx
- src/components/Sidebar.tsx
- src/components/ui/LoadingSpinner.tsx
- src/pages/*.tsx (multiple files)

### 2. Possibly Undefined Objects (TS2532, TS18048)

**Error:** `Object is possibly 'undefined'`

**Cause:** Stricter null checking with `noUncheckedIndexedAccess` enabled.

**Solution:**

```typescript
// Before
const question = quiz.questions[currentQuestionIndex];
const title = question.title; // Error: question might be undefined

// After - Option 1: Optional chaining
const title = quiz.questions[currentQuestionIndex]?.title;

// After - Option 2: Early return
const question = quiz.questions[currentQuestionIndex];
if (!question) return null;
const title = question.title;

// After - Option 3: Type guard
const question = quiz.questions[currentQuestionIndex];
if (typeof question === 'undefined') {
  throw new Error('Question not found');
}
const title = question.title;
```

**Files Affected:**
- src/pages/Quiz.tsx (7 instances)
- src/pages/QuizListPage.tsx (8 instances)
- src/pages/QuizPage.tsx (9 instances)
- src/pages/chat/utils.ts (3 instances)

### 3. Undefined Cannot be Used as Index Type (TS2538)

**Error:** `Type 'undefined' cannot be used as an index type`

**Cause:** Attempting to use a potentially undefined value as an object key.

**Solution:**

```typescript
// Before
const value = obj[possiblyUndefinedKey];

// After - Option 1: Null coalescing
const key = possiblyUndefinedKey ?? 'default';
const value = obj[key];

// After - Option 2: Conditional access
const value = possiblyUndefinedKey ? obj[possiblyUndefinedKey] : undefined;

// After - Option 3: Type guard
if (possiblyUndefinedKey !== undefined) {
  const value = obj[possiblyUndefinedKey];
}
```

**Files Affected:**
- src/pages/chat/utils.ts

### 4. Type Mismatch (TS2322)

**Error:** `Type 'boolean | undefined' is not assignable to type 'boolean'`

**Cause:** Component expecting strict boolean but receiving potentially undefined value.

**Solution:**

```typescript
// Before
<Component checked={formData.terms} />

// After - Option 1: Null coalescing
<Component checked={formData.terms ?? false} />

// After - Option 2: Double negation
<Component checked={!!formData.terms} />

// After - Option 3: Explicit boolean conversion
<Component checked={Boolean(formData.terms)} />
```

**Files Affected:**
- src/pages/SignupPage.tsx (3 instances)

### 5. Missing Module Declaration (TS2307)

**Error:** `Cannot find module 'vitest' or its corresponding type declarations`

**Cause:** Test file present but vitest not installed or types not configured.

**Solution:**

```bash
# Install vitest if needed for testing
npm install -D vitest @vitest/ui

# Or remove test file if not using vitest yet
```

**Files Affected:**
- src/config/featureFlags.test.ts

---

## Quick Fix Script

For a quick temporary fix to get the build working while you address errors properly:

### Option 1: Relax TypeScript Config (Not Recommended)

```json
// tsconfig.json - Temporary relaxation
{
  "compilerOptions": {
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noUncheckedIndexedAccess": false,
    // ... other options
  }
}
```

### Option 2: Add Type Assertions (Use Sparingly)

```typescript
// For quick fixes (not ideal for production)
const question = quiz.questions[currentQuestionIndex]!; // Non-null assertion
const value = obj[key as string]; // Type assertion
```

---

## Systematic Fix Approach

### Step 1: Fix Unused Variables (Easy)

```bash
# Remove unused imports automatically with ESLint
npx eslint --fix src/**/*.tsx
```

**Manual approach:**
1. Remove unused React imports
2. Remove or use unused variables
3. Comment out unused parameters with underscore prefix:

```typescript
// Before
function handleClick(event: MouseEvent, data: any) {
  console.log('clicked');
}

// After
function handleClick(_event: MouseEvent, _data: any) {
  console.log('clicked');
}
```

### Step 2: Fix Undefined Access (Medium)

For each file with undefined access errors:

1. **Quiz.tsx:**
```typescript
// Add guard at component top
const question = quiz.questions[currentQuestionIndex];
if (!question) {
  return <div>Question not found</div>;
}

// Now question is guaranteed to exist
return <div>{question.title}</div>;
```

2. **QuizListPage.tsx:**
```typescript
// Use optional chaining for rendering
<div>
  {quiz.questions[0]?.title || 'Untitled'}
</div>
```

3. **chat/utils.ts:**
```typescript
// Add type guards
if (key !== undefined && obj[key] !== undefined) {
  // Safe to access
}
```

### Step 3: Fix Type Mismatches (Medium)

For SignupPage.tsx:

```typescript
// Before
const [formData, setFormData] = useState({
  terms: undefined,
  privacy: undefined,
  marketing: undefined,
});

// After
const [formData, setFormData] = useState({
  terms: false,
  privacy: false,
  marketing: false,
});
```

### Step 4: Handle Test Files (Easy)

```bash
# Option A: Install vitest
npm install -D vitest @vitest/ui

# Option B: Move test file out of src
mv src/config/featureFlags.test.ts src/config/featureFlags.test.ts.backup

# Option C: Exclude from TypeScript compilation
# In tsconfig.json, already excluded via "exclude": ["**/*.test.ts"]
```

---

## Automated Fix Commands

```bash
# 1. Remove unused imports (requires eslint-plugin-unused-imports)
npm install -D eslint-plugin-unused-imports
npx eslint --fix src/

# 2. Run TypeScript to see remaining errors
npm run build

# 3. Fix specific file patterns
# Remove React imports from files that don't use React namespace
find src -name "*.tsx" -exec sed -i '' '/^import React from/d' {} +

# Note: Use with caution and test afterwards
```

---

## File-by-File Fix Priority

### High Priority (Blocking)
1. **src/pages/Quiz.tsx** - 7 errors (critical user flow)
2. **src/pages/QuizListPage.tsx** - 8 errors (critical user flow)
3. **src/pages/SignupPage.tsx** - 3 errors (critical user flow)

### Medium Priority (Important)
4. **src/pages/QuizPage.tsx** - 9 errors
5. **src/pages/chat/utils.ts** - 3 errors
6. **src/pages/CommunityPage.tsx** - Multiple errors

### Low Priority (Cleanup)
7. All files with unused React imports
8. All files with unused variables

---

## Testing After Fixes

```bash
# 1. TypeScript check
npm run build

# 2. Dev server check
npm run dev

# 3. Linting check
npm run lint

# 4. Runtime testing
# - Navigate to all affected pages
# - Test quiz functionality
# - Test signup flow
# - Test chat features
```

---

## Prevention

### 1. Use ESLint Auto-fix

Add to `package.json`:

```json
{
  "scripts": {
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
    "lint:fix": "eslint . --ext ts,tsx --fix"
  }
}
```

### 2. Pre-commit Hook

Install husky and lint-staged:

```bash
npm install -D husky lint-staged
npx husky install
```

Add to `package.json`:

```json
{
  "lint-staged": {
    "*.{ts,tsx}": [
      "eslint --fix",
      "prettier --write"
    ]
  }
}
```

### 3. VS Code Settings

Add to `.vscode/settings.json`:

```json
{
  "typescript.preferences.includePackageJsonAutoImports": "off",
  "typescript.suggest.autoImports": false,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true,
    "source.organizeImports": true
  }
}
```

---

## Summary

**Total Errors:** ~90

**Categories:**
- Unused imports/variables: ~60 (66%)
- Undefined access: ~24 (27%)
- Type mismatches: ~3 (3%)
- Module declarations: ~1 (1%)
- Other: ~2 (2%)

**Estimated Fix Time:**
- Automated fixes (unused imports): 1 hour
- Undefined access fixes: 3-4 hours
- Type mismatch fixes: 30 minutes
- Testing and verification: 1 hour
- **Total:** 5-6 hours

**Recommended Approach:**
1. Run automated cleanup for unused imports
2. Fix high-priority files manually (Quiz, Signup)
3. Fix medium-priority files (QuizPage, chat utils)
4. Clean up low-priority files
5. Test thoroughly
6. Set up prevention measures

---

## Questions?

If you encounter errors not covered in this guide:

1. Check the TypeScript error code (e.g., TS2532)
2. Search TypeScript documentation: https://www.typescriptlang.org/docs/
3. Use optional chaining (`?.`) and null coalescing (`??`) liberally
4. Add type guards where needed
5. Consider temporarily relaxing specific rules if blocked

**Remember:** These stricter checks help catch real bugs. Taking the time to fix them properly will improve code quality and prevent runtime errors.
