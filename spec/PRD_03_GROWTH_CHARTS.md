# PRD 03: Growth Charts & Visualization

## Document Information
- **Version:** 1.0
- **Last Updated:** January 2026
- **Related PRD:** PRD-01 Product Overview, PRD-02 Core Calculator

---

## 1. Overview

This PRD defines the interactive growth chart visualization features, including centile curve display, measurement plotting, and chart customization options.

---

## 2. Chart Types

### 2.1 Available Charts

| Chart | Description | Age Ranges |
|-------|-------------|------------|
| Height | Height/length vs age | 0-2, 0-4, 0-18, 8-20 years |
| Weight | Weight vs age | 0-2, 0-4, 0-18, 8-20 years |
| BMI | Body mass index vs age | 0-4, 2-18 years |
| OFC | Head circumference vs age | 0-2, 0-18 years |

### 2.2 Chart Selection
- User selects chart type via tab interface
- Active chart highlighted
- Only one chart visible at a time

---

## 3. Centile Curves

### 3.1 Displayed Centiles

| Centile | Approximate SDS | Color (Light Mode) |
|---------|-----------------|-------------------|
| 0.4th | -2.67 | Light grey |
| 2nd | -2.05 | Grey |
| 9th | -1.34 | Blue-grey |
| 25th | -0.67 | Light blue |
| 50th | 0 | Blue (primary) |
| 75th | +0.67 | Light blue |
| 91st | +1.34 | Blue-grey |
| 98th | +2.05 | Grey |
| 99.6th | +2.67 | Light grey |

### 3.2 Curve Styling
```
Outer curves (0.4th, 99.6th): 1px, 20% opacity
Middle curves (2nd, 9th, 91st, 98th): 1px, 40% opacity
Inner curves (25th, 75th): 1.5px, 60% opacity
Median (50th): 2px, 100% opacity, bold
```

### 3.3 Curve Labels
- Display centile value on right side of chart
- Label positioned at end of each curve
- Format: "0.4", "2", "9", "25", "50", "75", "91", "98", "99.6"

---

## 4. Age Range Selection

### 4.1 Intelligent Default Selection

The system should automatically select the optimal age range based on:
- Child's current age
- Whether parental heights are provided
- Clinical relevance

#### Height Chart Defaults
| Child's Age | With Parental Heights | Without Parental Heights |
|-------------|----------------------|--------------------------|
| < 2 years | 0-2 years | 0-2 years |
| 2-4 years | 0-4 years | 0-4 years |
| ≥ 4 years | 2-18 years | 0-18 years |

#### Weight Chart Defaults
| Child's Age | Default Range |
|-------------|---------------|
| < 2 years | 0-2 years |
| 2-4 years | 0-4 years |
| ≥ 4 years | 0-18 years |

#### BMI Chart Defaults
| Child's Age | Default Range |
|-------------|---------------|
| < 4 years | 0-4 years |
| 4-10 years | 2-18 years |
| ≥ 10 years | 0-18 years |

#### OFC Chart Defaults
| Child's Age | Default Range |
|-------------|---------------|
| < 2 years | 0-2 years |
| ≥ 2 years | 0-18 years |

### 4.2 Manual Override
- User can override automatic selection
- Radio button interface for age range options
- Selection persists while viewing that chart type

---

## 5. Measurement Plotting

### 5.1 Current Measurement

| Property | Specification |
|----------|---------------|
| Marker | Filled circle |
| Size | 8px diameter |
| Color | Accent color (blue primary) |
| Border | 2px white stroke |
| Position | (age, measurement_value) |

### 5.2 Previous Measurements

| Property | Specification |
|----------|---------------|
| Marker | Smaller filled circle |
| Size | 6px diameter |
| Color | Secondary color (muted) |
| Border | 1px white stroke |
| Connection | Optional line connecting chronological points |

### 5.3 Corrected Age Indication
When gestation correction is applied:
- Show measurement at CORRECTED age position
- Optional: Show faded marker at chronological position with connecting line

---

## 6. Mid-Parental Height Display

### 6.1 When to Display
- Only on height chart
- Only when both parental heights provided
- Only for age ranges including adult height (0-18, 8-20)

### 6.2 Display Elements

| Element | Description |
|---------|-------------|
| MPH Line | Horizontal line at MPH value at age 18/20 |
| Target Range | Shaded band showing ±8.5cm range |
| Label | "MPH: XXX cm" positioned near line |

### 6.3 Styling
```
MPH Line: 2px dashed, purple/accent color
Target Range: Semi-transparent fill (10% opacity)
Label: Small text, positioned to avoid overlap
```

---

## 7. Bone Age Plotting

### 7.1 When to Display
- Only on height chart
- Only when bone age assessment provided
- Assessment date must be within ±1 month of measurement date

### 7.2 Display Elements

| Element | Description |
|---------|-------------|
| Bone Age Marker | Diamond or triangle marker |
| Position | X = bone age (years), Y = current height |
| Color | Distinct from chronological marker (e.g., orange) |
| Label | "BA: X.X years" |

### 7.3 Interpretation Aid
The bone age marker shows where the child's height falls when plotted against skeletal maturity rather than chronological age.

---

## 8. Chart Interaction

### 8.1 Hover/Touch Behavior
- Display tooltip on marker hover
- Tooltip content:
  ```
  Age: X.XX years
  [Measurement]: XX.X [unit]
  Centile: XX.X%
  SDS: X.XX
  ```

### 8.2 Zoom/Pan (Optional Enhancement)
- Pinch to zoom on mobile
- Drag to pan
- Reset button to return to default view

### 8.3 Responsive Behavior
- Chart resizes with container
- Maintain aspect ratio
- Minimum readable size enforced

---

## 9. Theme Support

### 9.1 Light Mode Colors
```css
--chart-background: #ffffff
--chart-grid: #e5e7eb
--chart-text: #374151
--chart-centile-line: #6b7280
--chart-median: #1e40af
--chart-current-marker: #2563eb
--chart-previous-marker: #9ca3af
```

### 9.2 Dark Mode Colors
```css
--chart-background: #1f2937
--chart-grid: #374151
--chart-text: #e5e7eb
--chart-centile-line: #9ca3af
--chart-median: #60a5fa
--chart-current-marker: #3b82f6
--chart-previous-marker: #6b7280
```

### 9.3 Theme Switching
- Charts must update colors when theme changes
- No page reload required
- Smooth transition (optional)

---

## 10. Chart Data API

### 10.1 Endpoint

**POST /chart-data**

#### Request Body
```json
{
  "reference": "uk-who",
  "measurement_method": "height",
  "sex": "male"
}
```

#### Response
```json
{
  "success": true,
  "centiles": [
    {
      "centile": 0.4,
      "data": [
        {"x": 0, "y": 46.1},
        {"x": 0.0833, "y": 51.2},
        ...
      ]
    },
    {
      "centile": 2,
      "data": [...]
    },
    ...
  ]
}
```

### 10.2 Data Format
- X values: Age in decimal years
- Y values: Measurement values in standard units
- Data points at regular intervals (typically monthly or weekly for infants)

---

## 11. Chart Library Requirements

### 11.1 Recommended: Chart.js

| Feature | Requirement |
|---------|-------------|
| Line Charts | Multiple datasets on single chart |
| Scatter Overlay | Point markers on line chart |
| Responsive | Auto-resize with container |
| Tooltips | Custom tooltip formatting |
| Annotations | Lines and regions (for MPH display) |
| Theming | Dynamic color updates |

### 11.2 Alternative Libraries
- D3.js (more flexibility, higher complexity)
- Plotly (heavier, more features)
- Lightweight alternatives (uPlot, etc.)

---

## 12. Chart Download

### 12.1 PNG Export
- Download button for each chart
- High resolution (2x scale for Retina displays)
- Include chart title and reference in image
- Filename format: `growth-chart-[type]-[date].png`

### 12.2 Export Contents
```
┌─────────────────────────────────────────────┐
│  Height Chart - UK-WHO Reference            │
│  ─────────────────────────────────────────  │
│                                             │
│            [Chart Canvas]                   │
│                                             │
│  ─────────────────────────────────────────  │
│  Generated: 2026-01-29                      │
└─────────────────────────────────────────────┘
```

---

## 13. Performance Considerations

### 13.1 Data Loading
- Cache chart data after first load
- Preload data for other chart types after initial display
- Show loading indicator during data fetch

### 13.2 Rendering
- Use canvas rendering (not SVG) for performance
- Limit animation complexity
- Debounce resize handlers

### 13.3 Memory
- Destroy chart instance when switching types
- Clear canvas before redrawing
- Avoid memory leaks in event listeners

---

## 14. Accessibility

### 14.1 Screen Reader Support
- Provide text description of current measurement position
- Announce centile and SDS values
- Describe trend if previous measurements exist

### 14.2 Keyboard Navigation
- Tab through chart controls
- Enter to select chart type
- Arrow keys for age range selection

### 14.3 Color Considerations
- Don't rely solely on color to convey information
- Sufficient contrast for centile labels
- Marker shapes distinguish measurement types

---

## 15. Acceptance Criteria

### 15.1 Chart Display
- [ ] All four chart types render correctly
- [ ] Centile curves display accurately
- [ ] Age range selector works
- [ ] Intelligent default selection implemented

### 15.2 Measurement Plotting
- [ ] Current measurement plotted correctly
- [ ] Previous measurements displayed
- [ ] Correct position (chronological vs corrected age)

### 15.3 Additional Features
- [ ] MPH displayed on height chart when applicable
- [ ] Bone age plotting works when assessment provided
- [ ] Tooltips show correct information

### 15.4 Responsiveness
- [ ] Charts resize appropriately
- [ ] Mobile touch interaction works
- [ ] Dark mode colors apply correctly

### 15.5 Export
- [ ] PNG download works
- [ ] Image quality acceptable
- [ ] Filename generated correctly
