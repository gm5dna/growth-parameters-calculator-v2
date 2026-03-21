# PRD 01: Product Overview - Pediatric Growth Parameters Calculator

## Document Information
- **Version:** 1.0
- **Last Updated:** January 2026
- **Status:** Reference Implementation Complete

---

## 1. Executive Summary

### 1.1 Product Vision
Build a web-based clinical tool that calculates pediatric growth parameters using validated medical reference data, enabling healthcare professionals to assess child growth accurately and efficiently.

### 1.2 Problem Statement
Healthcare professionals need a reliable, accessible tool to:
- Calculate growth percentiles and standard deviation scores (SDS) for children
- Visualize growth trajectories on reference charts
- Account for special populations (preterm infants, genetic syndromes)
- Generate professional reports for medical records

### 1.3 Solution
A stateless web application that provides instant growth calculations using clinically validated reference data from the Royal College of Paediatrics and Child Health (RCPCH).

---

## 2. Target Users

### 2.1 Primary Users
- **Pediatricians** - Routine growth assessment
- **Pediatric Endocrinologists** - Growth hormone therapy monitoring
- **General Practitioners** - Well-child visits
- **Pediatric Nurses** - Clinic measurements

### 2.2 Secondary Users
- **Medical Students** - Learning growth assessment
- **Researchers** - Reference data exploration

### 2.3 User Environment
- Clinical settings (hospitals, clinics)
- Mobile devices at point of care
- Desktop computers in consultation rooms

---

## 3. Core Value Propositions

| Value | Description |
|-------|-------------|
| **Clinical Accuracy** | Uses RCPCH-validated growth references |
| **Privacy by Design** | No data storage, stateless architecture |
| **Accessibility** | Mobile-responsive, works offline (PWA) |
| **Professional Output** | PDF reports suitable for medical records |
| **Multiple References** | Supports UK-WHO, Turner, Trisomy-21, CDC |

---

## 4. Success Metrics

### 4.1 Functional Metrics
- Calculation accuracy: 100% match with RCPCH library output
- Page load time: < 3 seconds on 3G connection
- API response time: < 500ms for calculations

### 4.2 Usability Metrics
- Task completion rate: > 95% for basic calculations
- Mobile usability score: > 90 (Google Lighthouse)
- Accessibility compliance: WCAG 2.1 AA

---

## 5. High-Level Feature Map

```
┌─────────────────────────────────────────────────────────────────┐
│                    GROWTH CALCULATOR                              │
├─────────────────────────────────────────────────────────────────┤
│  CORE FEATURES                    │  ADVANCED FEATURES           │
│  ─────────────────                │  ─────────────────           │
│  • Age calculation                │  • Height velocity           │
│  • Weight centiles/SDS            │  • Bone age plotting         │
│  • Height centiles/SDS            │  • GH dose calculator        │
│  • BMI centiles/SDS               │  • BSA calculation           │
│  • OFC centiles/SDS               │  • Previous measurements     │
│  • Mid-parental height            │  • CSV import/export         │
│  • Preterm correction             │  • BMI % median              │
├─────────────────────────────────────────────────────────────────┤
│  VISUALIZATION                    │  OUTPUT                      │
│  ─────────────────                │  ─────────────────           │
│  • Interactive growth charts      │  • PDF reports with charts   │
│  • Multiple age ranges            │  • Clipboard copy            │
│  • Centile bands (0.4-99.6th)     │  • Chart PNG download        │
│  • Previous measurements plot     │  • Clinical text formatting  │
├─────────────────────────────────────────────────────────────────┤
│  GROWTH REFERENCES                                               │
│  ─────────────────                                               │
│  • UK-WHO (0-20 years) - Default                                 │
│  • Turner Syndrome (1-20 years)                                  │
│  • Trisomy 21 / Down Syndrome (0-18 years)                       │
│  • CDC (US reference)                                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Design Principles

### 6.1 Clinical Safety
- Display clear warnings for extreme values
- Hard rejection of physiologically impossible values
- Prominent disclaimer about tool limitations
- All calculations use validated medical library

### 6.2 Privacy
- **Stateless architecture** - no database
- **No PHI retention** - data exists only during request
- **No cookies for tracking** - only preferences
- **Local storage** - form state only, user-controlled

### 6.3 Accessibility
- Mobile-first responsive design
- High contrast text and UI elements
- Keyboard navigation support
- Screen reader compatible (ARIA labels)

### 6.4 Performance
- Minimal dependencies
- No heavy frameworks
- Server-side PDF generation
- PWA for offline capability

---

## 7. Technical Constraints

| Constraint | Requirement |
|------------|-------------|
| **Growth Library** | Must use `rcpchgrowth` Python library |
| **Python Version** | 3.12.x (greenlet compatibility) |
| **No Database** | Stateless by design |
| **Single Page App** | No page navigation required |
| **Browser Support** | Modern browsers (Chrome, Firefox, Safari, Edge) |

---

## 8. Out of Scope (v1.0)

- User accounts / authentication
- Historical data storage
- FHIR/HL7 integration (planned for future)
- Multi-language support
- Syndrome-specific charts beyond Turner/T21
- Voice input

---

## 9. Related PRDs

| PRD | Title |
|-----|-------|
| PRD-02 | Core Calculator Functionality |
| PRD-03 | Growth Charts & Visualization |
| PRD-04 | Advanced Clinical Features |
| PRD-05 | User Experience & Interface |
| PRD-06 | Technical Architecture |
| PRD-07 | Export & Reporting |

---

## 10. Glossary

| Term | Definition |
|------|------------|
| **SDS** | Standard Deviation Score (Z-score) - how many standard deviations from mean |
| **Centile** | Percentile - position relative to reference population |
| **OFC** | Occipitofrontal Circumference (head circumference) |
| **BMI** | Body Mass Index = weight(kg) / height(m)² |
| **MPH** | Mid-Parental Height - predicted adult height from parental heights |
| **BSA** | Body Surface Area - used for medication dosing |
| **UK-WHO** | Combined WHO Child Growth Standards (0-4y) + UK 1990 data (4-20y) |
| **RCPCH** | Royal College of Paediatrics and Child Health |
| **PWA** | Progressive Web App - works offline |
