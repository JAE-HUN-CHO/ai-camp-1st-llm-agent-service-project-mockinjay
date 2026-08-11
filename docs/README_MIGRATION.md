# CareGuide Frontend Migration - Quick Reference

## 📖 Documentation Index

1. **[PHASE_0_1_SUMMARY.md](./PHASE_0_1_SUMMARY.md)** - Start here! Quick overview of what was implemented
2. **[MIGRATION_PHASE_0_1.md](./MIGRATION_PHASE_0_1.md)** - Detailed implementation report
3. **[TYPESCRIPT_MIGRATION_GUIDE.md](./TYPESCRIPT_MIGRATION_GUIDE.md)** - How to fix TypeScript errors

---

## 🚀 Quick Start

### Development Server
```bash
cd frontend
npm install
npm run dev
```
Server runs on http://localhost:5173

### Build (Currently has TypeScript errors)
```bash
npm run build
```
See [TYPESCRIPT_MIGRATION_GUIDE.md](./TYPESCRIPT_MIGRATION_GUIDE.md) for fixes.

---

## 🎛️ Feature Flags

### Browser Console (Development Mode)
```javascript
// View all feature flags
window.__FEATURE_FLAGS__.log();

// Enable a feature
window.__FEATURE_FLAGS__.toggle('PHASE_2_UI_COMPONENTS', true);

// Enable entire phase
window.__FEATURE_FLAGS__.enablePhase(2);

// Disable entire phase
window.__FEATURE_FLAGS__.disablePhase(2);

// Clear all overrides
window.__FEATURE_FLAGS__.clearAll();
```

### In Code
```typescript
// Imperative check
import { isFeatureEnabled } from '@/config/featureFlags';

if (isFeatureEnabled('PHASE_1_DESIGN_SYSTEM')) {
  // Use new design system
}

// React Hook
import { useFeatureFlag } from '@/config/featureFlags';

function MyComponent() {
  const { enabled, toggle } = useFeatureFlag('PHASE_1_DESIGN_SYSTEM');

  return enabled ? <NewFeature /> : <OldFeature />;
}
```

---

## 🎨 Design Tokens

### Colors
```typescript
// Tailwind classes
className="bg-primary text-white"
className="text-text-secondary"
className="border-border-light"

// CSS variables
color: hsl(var(--primary));
background: hsl(var(--background));
```

### Typography
```typescript
className="text-h1"        // 40px heading
className="text-body"      // 16px body text
className="text-button"    // 14px button text
```

### Spacing
```typescript
className="p-card-padding"     // 24px padding
className="gap-section-gap"    // 32px gap
```

### Shadows
```typescript
className="shadow-card"        // Soft card shadow
className="shadow-elevated"    // Elevated shadow
```

---

## 📱 Responsive Design

### Breakpoints
```typescript
className="text-sm md:text-base lg:text-lg"
className="hidden md:block"
className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3"
```

Breakpoints:
- `xs`: 375px
- `sm`: 640px
- `md`: 768px
- `lg`: 1024px
- `xl`: 1280px
- `2xl`: 1536px

---

## ♿ Accessibility

### Built-in Classes
```typescript
className="sr-only"           // Screen reader only
className="touch-target"      // 44px touch target
className="focus-visible:ring-2"  // Focus indicator
```

### WCAG Compliance
All colors meet WCAG 2.2 AA standards (4.5:1 contrast minimum).

---

## 🔧 Path Aliases

```typescript
// Instead of: ../../../components/Button
// Use:
import { Button } from '@/components/Button';
```

---

## 📊 Current Status

### ✅ Completed
- Feature flag infrastructure
- WCAG AA design system
- TypeScript strict configuration
- Vite optimizations

### ⏸️ Pending
- Fix ~90 TypeScript errors
- Phase 2: UI Components
- Phase 3: Page migrations

---

## 🐛 Known Issues

**TypeScript Build Errors:** ~90 errors
- 60 unused imports (automated fix available)
- 24 undefined access (manual fix required)
- 3 type mismatches (easy fixes)

**Solution:** See [TYPESCRIPT_MIGRATION_GUIDE.md](./TYPESCRIPT_MIGRATION_GUIDE.md)

---

## 🆘 Need Help?

1. Build errors? → [TYPESCRIPT_MIGRATION_GUIDE.md](./TYPESCRIPT_MIGRATION_GUIDE.md)
2. Feature flags? → `src/config/featureFlags.ts` (800+ lines of docs)
3. Design tokens? → `tailwind.config.js` (697 lines with comments)
4. Styling? → `src/index.css` (743 lines with sections)

---

## 📞 Quick Commands

```bash
# Development
npm run dev          # Start dev server
npm run build        # Build for production
npm run lint         # Run ESLint
npm run preview      # Preview production build

# Feature Flag Testing
# (Use browser console with window.__FEATURE_FLAGS__)

# TypeScript Check
npx tsc --noEmit     # Type check without building
```

---

## 🎯 Next Phase

**Phase 2: Core UI Components** (Days 7-10)
- Install Shadcn/UI
- Migrate layout components
- Add Lucide icons
- Enable Phase 2 feature flags

---

**For full details, see [PHASE_0_1_SUMMARY.md](./PHASE_0_1_SUMMARY.md)**
