# Product Requirements Documents Index

## Growth Parameters Calculator - Complete PRD Suite

**Last Updated:** January 2026
**Application:** Pediatric Growth Parameters Calculator
**Reference Implementation:** https://growth-parameters-calculator.onrender.com

---

## Document Overview

This PRD suite provides comprehensive specifications for recreating the Growth Parameters Calculator from scratch. The documents are organized by functional area and can be implemented in phases.

---

## PRD List

| Document | Title | Description |
|----------|-------|-------------|
| [PRD-01](PRD_01_PRODUCT_OVERVIEW.md) | **Product Overview** | Vision, target users, design principles, feature map |
| [PRD-02](PRD_02_CORE_CALCULATOR.md) | **Core Calculator** | Age calculations, measurements, SDS/centiles, MPH |
| [PRD-03](PRD_03_GROWTH_CHARTS.md) | **Growth Charts** | Interactive charts, centile curves, measurement plotting |
| [PRD-04](PRD_04_ADVANCED_FEATURES.md) | **Advanced Features** | Height velocity, bone age, BSA, GH dosing, previous measurements |
| [PRD-05](PRD_05_USER_EXPERIENCE.md) | **User Experience** | UI design, themes, accessibility, responsive design |
| [PRD-06](PRD_06_TECHNICAL_ARCHITECTURE.md) | **Technical Architecture** | Tech stack, API design, code structure, deployment |
| [PRD-07](PRD_07_EXPORT_REPORTING.md) | **Export & Reporting** | PDF generation, clipboard copy, chart download |

---

## Implementation Phases

### Phase 1: Foundation
**Goal:** Basic working calculator

1. Set up project structure (PRD-06)
2. Implement core calculations (PRD-02)
3. Create basic UI (PRD-05, simplified)
4. Deploy MVP

**Deliverables:**
- Calculate endpoint working
- Age, weight, height, BMI, OFC with SDS/centiles
- Basic responsive form
- Results display

### Phase 2: Visualization
**Goal:** Add growth charts

1. Implement chart-data endpoint (PRD-03)
2. Integrate Chart.js
3. Add chart controls (tabs, age ranges)
4. Plot measurements on charts

**Deliverables:**
- All four chart types
- Centile curves rendered
- Current measurement plotted
- Age range selection

### Phase 3: Advanced Features
**Goal:** Full clinical functionality

1. Add previous measurements (PRD-04)
2. Implement height velocity
3. Add bone age assessment
4. Implement BSA and GH calculator
5. Add preterm correction

**Deliverables:**
- Previous measurements table with CSV
- Height velocity calculation
- Bone age plotting
- BSA and GH dose calculator
- Gestation correction

### Phase 4: Export & Polish
**Goal:** Production-ready application

1. Implement PDF export (PRD-07)
2. Add clipboard copy
3. Implement chart download
4. Add dark mode (PRD-05)
5. PWA capabilities
6. Comprehensive testing

**Deliverables:**
- PDF report generation
- Clipboard copy functionality
- Chart PNG download
- Dark/light theme toggle
- Offline capability
- Full test coverage

---

## Key Dependencies

### External Libraries

| Library | Purpose | Critical? |
|---------|---------|-----------|
| rcpchgrowth | Growth calculations | **Yes** |
| Flask | Web framework | Yes |
| Chart.js | Charting | Yes |
| ReportLab | PDF generation | For export |
| python-dateutil | Date handling | Yes |

### The rcpchgrowth Library

The entire application depends on the `rcpchgrowth` library from RCPCH. This library provides:
- Validated growth reference data
- Measurement SDS/centile calculations
- Mid-parental height calculations
- Centile curve generation

**Documentation:** https://growth.rcpch.ac.uk/developer/rcpchgrowth/

**Critical note:** Do not attempt to implement growth calculations manually. Always use the validated library.

---

## Reference Data

### Growth References

| Reference | Age Range | Use Case |
|-----------|-----------|----------|
| UK-WHO | 0-20 years | General UK population |
| Turner Syndrome | 1-20 years | 45,X females |
| Trisomy 21 | 0-18 years | Down syndrome |
| CDC | 0-20 years | US population |

### Centile Bands

Standard centile lines displayed: 0.4, 2, 9, 25, 50, 75, 91, 98, 99.6

### Validation Thresholds

| Measurement | Warning | Reject |
|-------------|---------|--------|
| Weight/Height/OFC | ±4 SDS | ±8 SDS |
| BMI | ±4 SDS | ±15 SDS |

---

## Design Decisions Summary

| Decision | Rationale |
|----------|-----------|
| No database | Privacy by design, simplicity |
| Vanilla JS | Performance, no framework overhead |
| Server-side PDF | Quality control, consistent output |
| rcpchgrowth library | Clinical validation essential |
| Single page app | Simple navigation, form state |
| localStorage for state | No server storage, user control |

---

## Quality Requirements

### Performance
- Page load: < 3 seconds on 3G
- Calculation response: < 500ms
- Lighthouse score: > 90

### Accessibility
- WCAG 2.1 AA compliance
- Keyboard navigable
- Screen reader compatible

### Testing
- Backend: > 80% coverage
- Frontend: > 70% coverage
- All critical paths tested

---

## Getting Started

1. **Read PRD-01** - Understand the product vision and scope
2. **Review PRD-06** - Set up the technical foundation
3. **Implement PRD-02** - Build core calculator functionality
4. **Follow phases** - Add features incrementally
5. **Refer to PRD-05** - Ensure UX quality throughout

---

## Glossary

| Term | Definition |
|------|------------|
| SDS | Standard Deviation Score (Z-score) |
| Centile | Percentile rank in reference population |
| OFC | Occipitofrontal Circumference (head circumference) |
| BMI | Body Mass Index |
| MPH | Mid-Parental Height |
| BSA | Body Surface Area |
| GH | Growth Hormone |
| RCPCH | Royal College of Paediatrics and Child Health |
| UK-WHO | Combined UK/WHO growth reference |

---

## Contact & Resources

- **RCPCH Growth Charts:** https://growth.rcpch.ac.uk/
- **rcpchgrowth Library:** https://pypi.org/project/rcpchgrowth/
- **Chart.js Documentation:** https://www.chartjs.org/docs/
- **Flask Documentation:** https://flask.palletsprojects.com/
