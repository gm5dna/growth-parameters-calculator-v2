# PRD 05: User Experience & Interface Design

## Document Information
- **Version:** 1.0
- **Last Updated:** January 2026
- **Related PRD:** PRD-01 Product Overview

---

## 1. Overview

This PRD defines the user interface design, user experience patterns, responsive behavior, accessibility requirements, and visual design system for the Growth Parameters Calculator.

---

## 2. Design Philosophy

### 2.1 Core Principles

| Principle | Description |
|-----------|-------------|
| **Clinical Safety First** | Clear warnings, impossible to miss errors |
| **Mobile-First** | Designed for point-of-care on mobile devices |
| **Progressive Disclosure** | Basic mode default, advanced features available |
| **Immediate Feedback** | Real-time validation, instant results |
| **Minimal Distraction** | Clean interface, focused on task |

### 2.2 Target Experience
```
"Enter patient data, get accurate results, generate report - all in under 60 seconds"
```

---

## 3. Page Layout

### 3.1 Single Page Application Structure

```
┌─────────────────────────────────────────────────────────────┐
│  [Help Link]                    [Theme Toggle] [Mode Toggle] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│         GROWTH PARAMETERS CALCULATOR                         │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  [Dismissible Disclaimer Banner]                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  INPUT FORM                                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ • Sex selection (radio buttons)                      │   │
│  │ • Growth reference (advanced only)                   │   │
│  │ • Date inputs (DOB, measurement date)                │   │
│  │ • Measurements (weight, height, OFC)                 │   │
│  │ • Gestation (advanced only)                          │   │
│  │ • Previous measurements (collapsible)                │   │
│  │ • Bone age (collapsible)                             │   │
│  │ • GH treatment checkbox (advanced only)              │   │
│  │ • Parental heights                                   │   │
│  │ • [Calculate] [Reset] buttons                        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  ERROR DISPLAY (when present)                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  RESULTS (appears after calculation)                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Results Header + [Copy] [Export PDF]                 │   │
│  │ Warning messages (if any)                            │   │
│  │ Result cards grid                                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  [Show Growth Charts] button                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  CHARTS SECTION (expandable)                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Header + [Download] [Close]                          │   │
│  │ Chart type tabs                                      │   │
│  │ Age range selector                                   │   │
│  │ Chart canvas                                         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  FOOTER                                                     │
│  Open source on GitHub                                      │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Container Width
- Max width: 900px
- Centered on larger screens
- Full width with padding on mobile

---

## 4. Theme System

### 4.1 Light Mode (Default)

```css
:root {
  --bg-primary: #ffffff;
  --bg-secondary: #f9fafb;
  --text-primary: #1f2937;
  --text-secondary: #6b7280;
  --accent-primary: #2563eb;
  --accent-secondary: #1e40af;
  --border-color: #e5e7eb;
  --error-color: #dc2626;
  --warning-color: #f59e0b;
  --success-color: #10b981;
}
```

### 4.2 Dark Mode

```css
[data-theme="dark"] {
  --bg-primary: #1f2937;
  --bg-secondary: #111827;
  --text-primary: #f3f4f6;
  --text-secondary: #9ca3af;
  --accent-primary: #3b82f6;
  --accent-secondary: #60a5fa;
  --border-color: #374151;
  --error-color: #ef4444;
  --warning-color: #fbbf24;
  --success-color: #34d399;
}
```

### 4.3 Theme Detection & Toggle
1. Check localStorage for saved preference
2. If none, detect system preference (`prefers-color-scheme`)
3. Apply detected/saved theme
4. Toggle button switches theme and saves to localStorage

### 4.4 Theme Toggle Icon
- Light mode: Show sun icon (☀️)
- Dark mode: Show moon icon (🌙)
- Positioned in top-right corner

---

## 5. Form Design

### 5.1 Input Fields

#### Text/Number Inputs
```css
input {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  font-size: 16px; /* Prevents iOS zoom */
  background: var(--bg-primary);
  color: var(--text-primary);
}

input:focus {
  border-color: var(--accent-primary);
  outline: none;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

input:invalid {
  border-color: var(--error-color);
}
```

#### Date Inputs
- Native date picker on mobile
- Calendar icon indicator
- Format display: YYYY-MM-DD

#### Radio Buttons (Sex Selection)
```
┌─────────────┐ ┌─────────────┐
│ ○ Male      │ │ ● Female    │
└─────────────┘ └─────────────┘
```
- Large touch targets (44px minimum)
- Clear selected state
- Grouped with label

### 5.2 Form Grid
- 2-column grid on desktop
- Single column on mobile (< 768px)
- Gap: 16px between fields

### 5.3 Labels
- Above input field
- Font weight: 600
- Required fields: No asterisk (all core fields required)
- Optional fields: "(Optional)" suffix

### 5.4 Unit Indicators
- Positioned inside or beside input
- Muted color
- Examples: "kg", "cm", "weeks", "days"

---

## 6. Button Design

### 6.1 Primary Button (Calculate)
```css
.btn-submit {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  padding: 14px 32px;
  border-radius: 8px;
  font-weight: 600;
  font-size: 16px;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
}

.btn-submit:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-submit:disabled {
  opacity: 0.6;
  cursor: wait;
}
```

### 6.2 Secondary Button (Reset)
```css
.btn-reset {
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  padding: 14px 32px;
  border-radius: 8px;
}
```

### 6.3 Action Buttons (Copy, Export)
- Smaller than primary buttons
- Icon + text
- Hover effects

### 6.4 Button States
- Default
- Hover
- Active/Pressed
- Disabled
- Loading (spinner)

---

## 7. Results Display

### 7.1 Results Container
```css
.results {
  background: var(--bg-secondary);
  border-radius: 12px;
  padding: 24px;
  margin-top: 24px;
  display: none; /* Hidden until calculation */
}

.results.show {
  display: block;
  animation: slideDown 0.3s ease;
}
```

### 7.2 Result Cards Grid
```
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│     Age      │ │    Weight    │ │    Height    │
│   2.45 yrs   │ │   12.5 kg    │ │   85.3 cm    │
│              │ │ Centile: 50% │ │ Centile: 25% │
│              │ │ SDS: +0.03   │ │ SDS: -0.67   │
└──────────────┘ └──────────────┘ └──────────────┘
```

### 7.3 Result Card Styling
```css
.result-item {
  background: var(--bg-primary);
  border-radius: 8px;
  padding: 16px;
  border: 1px solid var(--border-color);
}

.result-label {
  font-size: 12px;
  text-transform: uppercase;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.result-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
}

.result-sub {
  font-size: 14px;
  color: var(--text-secondary);
}
```

### 7.4 Warning Display
```css
.validation-warnings {
  background: rgba(245, 158, 11, 0.1);
  border-left: 4px solid var(--warning-color);
  padding: 12px 16px;
  margin-bottom: 16px;
  border-radius: 0 8px 8px 0;
}
```

---

## 8. Error Handling

### 8.1 Error Display
```css
.error {
  background: rgba(220, 38, 38, 0.1);
  border: 1px solid var(--error-color);
  color: var(--error-color);
  padding: 16px;
  border-radius: 8px;
  margin-top: 16px;
  display: none;
}

.error.show {
  display: block;
}
```

### 8.2 Inline Validation
- Real-time validation on blur
- Red border for invalid fields
- Error message below field

### 8.3 Error Messages
- Clear, actionable language
- Specific about what's wrong
- Suggest how to fix

---

## 9. Responsive Design

### 9.1 Breakpoints

| Breakpoint | Width | Layout |
|------------|-------|--------|
| Mobile | < 480px | Single column, compact |
| Tablet | 480-768px | Single column, comfortable |
| Desktop | > 768px | Two column form, wider |

### 9.2 Mobile Adaptations
- Full-width inputs
- Larger touch targets (44px minimum)
- Sticky header (optional)
- Collapsible sections default collapsed
- Bottom action buttons

### 9.3 Touch Considerations
- No hover-dependent interactions
- Swipe gestures for charts (optional)
- Tap-friendly date pickers

---

## 10. Accessibility (WCAG 2.1 AA)

### 10.1 Color Contrast
- Text on background: Minimum 4.5:1 ratio
- Large text: Minimum 3:1 ratio
- Interactive elements: Minimum 3:1 ratio

### 10.2 Keyboard Navigation
- All interactive elements focusable
- Visible focus indicators
- Logical tab order
- Skip to main content link

### 10.3 ARIA Labels
```html
<input type="number"
       id="weight"
       aria-label="Weight in kilograms"
       aria-required="false">

<div role="radiogroup" aria-labelledby="sex-label">
  <label class="radio-label">
    <input type="radio" name="sex" value="male" aria-label="Male">
    <span>Male</span>
  </label>
</div>
```

### 10.4 Screen Reader Support
- Form labels properly associated
- Error messages announced
- Results announced on calculation
- Chart descriptions available

### 10.5 Motion Preferences
```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 11. Loading States

### 11.1 Calculate Button Loading
```html
<button class="btn-submit" disabled>
  <span class="spinner"></span>
  Calculating...
</button>
```

### 11.2 Chart Loading
```html
<div class="chart-loading">
  <div class="spinner"></div>
  <p>Loading chart data...</p>
</div>
```

### 11.3 Spinner Style
```css
.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
```

---

## 12. Toast Notifications

### 12.1 Purpose
Confirm non-destructive actions (copy, export).

### 12.2 Appearance
```
┌─────────────────────────────┐
│ ✓ Results copied to clipboard│
└─────────────────────────────┘
```

### 12.3 Behavior
- Appears at bottom center
- Auto-dismisses after 3 seconds
- Slide up animation

### 12.4 Styling
```css
.toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--text-primary);
  color: var(--bg-primary);
  padding: 12px 24px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  opacity: 0;
  transition: opacity 0.3s;
}

.toast.show {
  opacity: 1;
}
```

---

## 13. Disclaimer Banner

### 13.1 Content
```
⚠️ Disclaimer: This is an experimental web application and should NOT be
used for clinical decision-making. All calculations must be verified
independently before any clinical use. This tool is for educational and
research purposes only.
```

### 13.2 Behavior
- Displayed prominently at top
- Dismissible (user can click X)
- Dismissal saved to localStorage
- Returns on page refresh (safety feature)

### 13.3 Styling
```css
.disclaimer {
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid var(--warning-color);
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 24px;
}
```

---

## 14. Icons

### 14.1 Icon System
Use Material Symbols (variable icon font).

```html
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0" />

<span class="material-symbols-outlined">add</span>
```

### 14.2 Common Icons

| Usage | Icon Name |
|-------|-----------|
| Add | add |
| Delete | delete |
| Download | download |
| Upload | upload |
| Help | help |
| Light mode | light_mode |
| Dark mode | dark_mode |
| Close | close |
| Copy | content_copy |

---

## 15. Typography

### 15.1 Font Stack
```css
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
             Oxygen, Ubuntu, Cantarell, sans-serif;
```

### 15.2 Scale

| Element | Size | Weight |
|---------|------|--------|
| H1 (Page title) | 28px | 700 |
| H2 (Section) | 20px | 600 |
| Body | 16px | 400 |
| Small | 14px | 400 |
| Label | 14px | 600 |
| Caption | 12px | 400 |

---

## 16. PWA Requirements

### 16.1 Manifest
```json
{
  "name": "Growth Parameters Calculator",
  "short_name": "Growth Calc",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#667eea",
  "icons": [
    {
      "src": "/static/icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/static/icon-512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
```

### 16.2 Offline Support
- Service worker caches static assets
- Form works offline (calculation requires server)
- Show offline indicator when disconnected

### 16.3 Install Prompt
- Add to home screen on mobile
- Desktop PWA installation

---

## 17. Acceptance Criteria

### 17.1 Visual Design
- [ ] Light and dark modes implemented
- [ ] Theme toggle works correctly
- [ ] Colors meet contrast requirements
- [ ] Consistent spacing and typography

### 17.2 Responsiveness
- [ ] Works on 320px width screens
- [ ] Touch targets ≥ 44px
- [ ] No horizontal scrolling
- [ ] Charts readable on mobile

### 17.3 Accessibility
- [ ] Keyboard navigation works
- [ ] Screen reader tested
- [ ] Focus indicators visible
- [ ] Form labels correct

### 17.4 Performance
- [ ] Lighthouse score ≥ 90
- [ ] First contentful paint < 1.5s
- [ ] Time to interactive < 3s

### 17.5 PWA
- [ ] Manifest validates
- [ ] Installable on mobile
- [ ] Offline page shows appropriately
