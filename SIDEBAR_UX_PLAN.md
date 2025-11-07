# MANTRIX AXIS.AI - Sidebar Navigation UX Plan

## Overview
This document outlines the visual and structural design for reorganizing the left sidebar navigation following the STOX.AI pattern of "Store Level View / 4 Modules" - showing clear hierarchy, module counts, and expandable sections.

---

## Design Pattern Reference: STOX.AI Style

### Visual Pattern
```
┌─────────────────────────────────┐
│  [Icon]  Store Level            │  ← Main Category
│          Store Level View       │  ← Sub-category name
│          4 Modules           ▼  │  ← Module count + Expand icon
└─────────────────────────────────┘
         │ (when expanded)
         ▼
    ┌─────────────────────────────┐
    │    [Icon] Module 1          │  ← Individual modules
    │    [Icon] Module 2          │
    │    [Icon] Module 3          │
    │    [Icon] Module 4          │
    └─────────────────────────────┘
```

### Key Visual Elements
1. **Main Category Title** (Bold, larger font)
2. **Sub-category/Description** (Secondary text, smaller font)
3. **Module Count** (Chip/badge showing "X Modules")
4. **Expand/Collapse Icon** (Chevron up/down)
5. **Indented Sub-items** (When expanded)

---

## Proposed Sidebar Structure

### TIER 1: Featured Standalone Modules (Non-expandable)
These are primary modules that don't have sub-sections.

```
┌─────────────────────────────────────────────┐
│  [🏠]  Home                                 │
│         Dashboard Overview                  │
├─────────────────────────────────────────────┤
│  [🎯]  AXIS.AI                              │
│         Natural Language Intelligence       │
├─────────────────────────────────────────────┤
│  [🌐]  CONTROL TOWER                        │
│         Process Mining & Analytics          │
├─────────────────────────────────────────────┤
│  [🔐]  COMMAND CENTER                       │
│         Task Management & Audit Trail       │
└─────────────────────────────────────────────┘
```

**Design Specs:**
- Height: 56px per item
- Icon size: 32px (colored with brand colors)
- Primary text: 14px bold
- Secondary text: 11px, 60% opacity
- Background: Gradient highlight on hover/selection
- No expand icon (not expandable)

---

### TIER 2: Expandable Module Categories
These sections contain multiple related sub-modules.

#### 1. Search & Explore
```
┌─────────────────────────────────────────────┐
│  [🔍]  Search & Explore                     │
│          Advanced Search Tools              │
│          3 Modules                       ▼  │
└─────────────────────────────────────────────┘
         │ (expanded)
         ▼
    ┌─────────────────────────────────────────┐
    │    [🔎] Natural Language Search         │
    │    [🧭] Data Explorer                   │
    │    [📑] Saved Searches                  │
    └─────────────────────────────────────────┘
```

**Modules:**
- Natural Language Search (ID: 1)
- Data Explorer (ID: 2)
- Saved Searches (ID: 3)

**Color Theme:** #4CAF50 (Green)

---

#### 2. Insights & Analytics
```
┌─────────────────────────────────────────────┐
│  [💡]  Insights & Analytics                 │
│          AI-Powered Intelligence            │
│          3 Modules                       ▼  │
└─────────────────────────────────────────────┘
         │ (expanded)
         ▼
    ┌─────────────────────────────────────────┐
    │    [✨] Automated Insights              │
    │    [🔔] Anomalies & Alerts              │
    │    [👁️] Watchlist                       │
    └─────────────────────────────────────────┘
```

**Modules:**
- Automated Insights (ID: 4)
- Anomalies & Alerts (ID: 5)
- Watchlist (ID: 6)

**Color Theme:** #00BCD4 (Cyan)

---

#### 3. Dashboards
```
┌─────────────────────────────────────────────┐
│  [📊]  Dashboards                           │
│          Custom Visualization Boards        │
│          3 Modules                       ▼  │
└─────────────────────────────────────────────┘
         │ (expanded)
         ▼
    ┌─────────────────────────────────────────┐
    │    [📈] My Dashboards                   │
    │    [🔗] Shared with Me                  │
    │    [⭐] Favorites                        │
    └─────────────────────────────────────────┘
```

**Modules:**
- My Dashboards (ID: 7)
- Shared with Me (ID: 8)
- Favorites (ID: 9)

**Color Theme:** #3F51B5 (Indigo)

---

#### 4. Data Management
```
┌─────────────────────────────────────────────┐
│  [🗄️]  Data Management                      │
│          Sources, Catalog & Business Views  │
│          3 Modules                       ▼  │
└─────────────────────────────────────────────┘
         │ (expanded)
         ▼
    ┌─────────────────────────────────────────┐
    │    [💾] Data Sources                    │
    │    [🌳] Business Views                  │
    │    [📁] Data Catalog                    │
    └─────────────────────────────────────────┘
```

**Modules:**
- Data Sources (ID: 10)
- Business Views (ID: 11)
- Data Catalog (ID: 12)

**Color Theme:** #607D8B (Blue Grey)

---

#### 5. AI & ML
```
┌─────────────────────────────────────────────┐
│  [🤖]  AI & Machine Learning                │
│          Automated Model Training           │
│          3 Modules                       ▼  │
└─────────────────────────────────────────────┘
         │ (expanded)
         ▼
    ┌─────────────────────────────────────────┐
    │    [⚡] AutoML                           │
    │    [🧠] Predictive Models               │
    │    [📊] Model Performance               │
    └─────────────────────────────────────────┘
```

**Modules:**
- AutoML (ID: 13)
- Predictive Models (ID: 14)
- Model Performance (ID: 15)

**Color Theme:** #E91E63 (Pink)

---

#### 6. Reports
```
┌─────────────────────────────────────────────┐
│  [📋]  Reports                              │
│          Scheduled & Historical Reports     │
│          2 Modules                       ▼  │
└─────────────────────────────────────────────┘
         │ (expanded)
         ▼
    ┌─────────────────────────────────────────┐
    │    [⏰] Scheduled Reports               │
    │    [📜] Report History                  │
    └─────────────────────────────────────────┘
```

**Modules:**
- Scheduled Reports (ID: 16)
- Report History (ID: 17)

**Color Theme:** #00BCD4 (Cyan)

---

#### 7. Collaboration
```
┌─────────────────────────────────────────────┐
│  [👥]  Collaboration                        │
│          Team Spaces & Communication        │
│          2 Modules                       ▼  │
└─────────────────────────────────────────────┘
         │ (expanded)
         ▼
    ┌─────────────────────────────────────────┐
    │    [🏢] Team Spaces                     │
    │    [💬] Comments                        │
    └─────────────────────────────────────────┘
```

**Modules:**
- Team Spaces (ID: 18)
- Comments (ID: 19)

**Color Theme:** #4CAF50 (Green)

---

#### 8. Administration
```
┌─────────────────────────────────────────────┐
│  [⚙️]  Administration                       │
│          System, Users & Security           │
│          3 Modules                       ▼  │
└─────────────────────────────────────────────┘
         │ (expanded)
         ▼
    ┌─────────────────────────────────────────┐
    │    [👤] User Management                 │
    │    [🔒] Security & Audit                │
    │    [⚙️] System Settings                 │
    └─────────────────────────────────────────┘
```

**Modules:**
- User Management (ID: 20)
- Security & Audit (ID: 21)
- System Settings (ID: 22)

**Color Theme:** #F44336 (Red)

---

## Complete Sidebar Hierarchy

### Final Structure (12 Total Sections)
```
MANTRIX AXIS.AI SIDEBAR
├── 🏠 Home
├── 🎯 AXIS.AI
├── 🌐 CONTROL TOWER
├── 🔐 COMMAND CENTER
├── 🔍 Search & Explore (3 modules)
│   ├── Natural Language Search
│   ├── Data Explorer
│   └── Saved Searches
├── 💡 Insights & Analytics (3 modules)
│   ├── Automated Insights
│   ├── Anomalies & Alerts
│   └── Watchlist
├── 📊 Dashboards (3 modules)
│   ├── My Dashboards
│   ├── Shared with Me
│   └── Favorites
├── 🗄️ Data Management (3 modules)
│   ├── Data Sources
│   ├── Business Views
│   └── Data Catalog
├── 🤖 AI & ML (3 modules)
│   ├── AutoML
│   ├── Predictive Models
│   └── Model Performance
├── 📋 Reports (2 modules)
│   ├── Scheduled Reports
│   └── Report History
├── 👥 Collaboration (2 modules)
│   ├── Team Spaces
│   └── Comments
└── ⚙️ Administration (3 modules)
    ├── User Management
    ├── Security & Audit
    └── System Settings
```

**Total Items:**
- 4 standalone tiles (Tier 1)
- 8 expandable categories (Tier 2)
- 22 sub-modules

---

## Design Specifications

### Typography
```
Main Category Title:
  Font: Inter/Roboto
  Size: 14px
  Weight: 600 (Semi-bold)
  Color: Primary text color

Sub-category Description:
  Font: Inter/Roboto
  Size: 11px
  Weight: 400 (Regular)
  Color: Secondary text (60% opacity)
  Line Height: 1.2

Module Count Badge:
  Font: Inter/Roboto
  Size: 10px
  Weight: 500 (Medium)
  Background: Category color (15% opacity)
  Border: 1px solid category color
  Border Radius: 12px
  Padding: 2px 8px

Sub-module Text:
  Font: Inter/Roboto
  Size: 13px
  Weight: 400
  Color: Primary text
```

### Spacing
```
Main Category Item:
  Height: 56px
  Padding: 12px 16px
  Margin Bottom: 4px

Expandable Category Item:
  Height: 64px (taller to fit 3 lines)
  Padding: 10px 16px
  Margin Bottom: 4px

Sub-module Item:
  Height: 40px
  Padding: 8px 16px 8px 48px (48px left for indentation)
  Margin Bottom: 2px

Section Divider:
  Height: 1px
  Margin: 16px 8px
  Color: Divider color (12% opacity)
```

### Colors & Theming

#### Light Theme (SAP/Professional)
```
Background: #FFFFFF
Text Primary: #1A1A1A
Text Secondary: rgba(26, 26, 26, 0.6)
Divider: rgba(0, 0, 0, 0.12)
Hover: rgba(0, 0, 0, 0.04)
Selected: Category color at 15% opacity
```

#### Dark Theme (Current)
```
Background: #0f0f23
Text Primary: #E0E0E0
Text Secondary: rgba(224, 224, 224, 0.6)
Divider: rgba(255, 255, 255, 0.1)
Hover: rgba(255, 255, 255, 0.08)
Selected: Category color at 20% opacity
```

### Interactive States

#### Main Category / Expandable Section
```
Default:
  Background: transparent
  Border Left: 0px

Hover:
  Background: theme.hover
  Border Left: 3px solid category color
  Transform: translateX(4px) [only when sidebar is open]
  Transition: all 0.2s ease

Selected:
  Background: category color (15-20% opacity)
  Border Left: 3px solid category color
  Icon: Highlighted with category color

Active (Clicking):
  Transform: scale(0.98)
  Transition: transform 0.1s
```

#### Sub-modules
```
Default:
  Background: transparent
  Opacity: 0.8

Hover:
  Background: category color (10% opacity)
  Opacity: 1

Selected:
  Background: category color (15% opacity)
  Opacity: 1
  Font Weight: 500
```

### Animations

#### Expand/Collapse
```
Duration: 300ms
Easing: cubic-bezier(0.4, 0.0, 0.2, 1)
Property: height, opacity

Chevron Rotation:
  From: 0deg (collapsed - pointing down)
  To: 180deg (expanded - pointing up)
  Duration: 200ms
  Easing: ease-in-out
```

#### Sidebar Open/Close
```
Duration: 300ms
Easing: cubic-bezier(0.4, 0.0, 0.2, 1)
Property: width

Width States:
  Open: 260px (increased from 240px to fit module count)
  Closed: 64px

Content Behavior:
  Fade Out: opacity 0 → hidden at 100ms (when closing)
  Fade In: opacity 0 → 1 at 200ms delay (when opening)
```

### Icons

#### Sizing
```
Main Category Icon: 24px × 24px
Sub-module Icon: 20px × 20px
Expand/Collapse Icon: 20px × 20px
```

#### Style
```
Type: Material Icons (Outlined style)
Color:
  - Standalone modules: Icon inherits category color
  - Expandable categories: Icon colored with category color
  - Sub-modules: Icon at 70% opacity
```

---

## Collapsed Sidebar Behavior

When sidebar is collapsed (64px width):

```
┌──────┐
│ [🏠] │  ← Show only icon, tooltip on hover
├──────┤
│ [🎯] │
├──────┤
│ [🌐] │
├──────┤
│ [🔐] │
├──────┤
│ [🔍] │  ← Expandable sections show icon only
├──────┤    Click opens a popover menu to the right
│ [💡] │    (or can auto-expand sidebar on click)
├──────┤
│ [📊] │
└──────┘
```

**Collapsed State Rules:**
1. Show only icon (24px)
2. Hide all text, badges, descriptions
3. Center icon vertically and horizontally
4. Show tooltip on hover with full category name
5. On click: Either expand sidebar OR show popover menu with sub-items
6. Badge indicator: Small dot on top-right corner if category has notifications

---

## Module Count Display Options

### Option 1: Badge Style (Recommended)
```
┌─────────────────────────────────────────────┐
│  [🔍]  Search & Explore              [3] ▼ │
│          Advanced Search Tools              │
└─────────────────────────────────────────────┘
```
- Compact
- Clean
- Easy to scan

### Option 2: Text Style (STOX.AI Pattern)
```
┌─────────────────────────────────────────────┐
│  [🔍]  Search & Explore                     │
│          Advanced Search Tools              │
│          3 Modules                       ▼  │
└─────────────────────────────────────────────┘
```
- More descriptive
- Matches STOX.AI exactly
- Takes more vertical space

### Option 3: Inline Badge
```
┌─────────────────────────────────────────────┐
│  [🔍]  Search & Explore  [3 modules]     ▼ │
│          Advanced Search Tools              │
└─────────────────────────────────────────────┘
```
- Balanced approach
- Less vertical space than Option 2
- Still descriptive

**Recommendation:** Use **Option 2** (STOX.AI Pattern) for consistency with the reference design.

---

## Responsive Behavior

### Sidebar States
```
Desktop (>1280px):
  Default: Open (260px)
  Collapsible: Yes

Tablet (768px - 1280px):
  Default: Closed (64px)
  Expandable on hover or click

Mobile (<768px):
  Default: Hidden
  Toggle: Overlay drawer from left
  Width: 280px (full width on small screens)
```

---

## Accessibility

### Keyboard Navigation
```
Tab: Navigate through main categories
Enter/Space: Expand/collapse or activate
Arrow Up/Down: Navigate within expanded sections
Arrow Right: Expand category (if collapsed)
Arrow Left: Collapse category (if expanded)
Escape: Collapse all or close sidebar (on mobile)
```

### ARIA Labels
```
Expandable Category:
  role="button"
  aria-expanded="true/false"
  aria-controls="submenu-{section-key}"
  aria-label="{Category Name} - {Module Count} modules"

Sub-module:
  role="link"
  aria-current="page" (if selected)

Collapse/Expand Icon:
  aria-hidden="true" (decorative)
```

### Focus Indicators
```
Focus Ring:
  Outline: 2px solid primary color
  Offset: 2px
  Border Radius: 8px
```

---

## Implementation Notes

### State Management
```javascript
const [expandedSections, setExpandedSections] = useState({
  search: false,
  insights: false,
  dashboards: false,
  data: false,
  ai: false,
  reports: false,
  collab: false,
  admin: false,
});

// Toggle function
const toggleSection = (sectionKey) => {
  setExpandedSections(prev => ({
    ...prev,
    [sectionKey]: !prev[sectionKey]
  }));
};
```

### Menu Items Data Structure
```javascript
const menuItems = [
  // Tier 1: Standalone
  {
    id: 0,
    icon: <HomeIcon />,
    primary: 'Home',
    secondary: 'Dashboard Overview',
    color: '#2196F3',
    standalone: true,
  },

  // Tier 2: Expandable
  {
    id: 'search',
    icon: <SearchIcon />,
    primary: 'Search & Explore',
    secondary: 'Advanced Search Tools',
    color: '#4CAF50',
    isExpandable: true,
    sectionKey: 'search',
    moduleCount: 3,
    subItems: [
      { id: 1, icon: <SearchIcon />, primary: 'Natural Language Search' },
      { id: 2, icon: <DataExplorerIcon />, primary: 'Data Explorer' },
      { id: 3, icon: <BookmarkIcon />, primary: 'Saved Searches' },
    ],
  },
];
```

---

## Visual Mockup Comparison

### BEFORE (Current)
```
Simple list with expand icons, no descriptions or module counts:

[🏠] Home
[🌐] CONTROL TOWER
[🔐] COMMAND CENTER
[🔍] Search & Explore          ▼
[💡] Insights & Analytics      ▼
[📊] Dashboards                ▼
```

### AFTER (Proposed)
```
Rich cards with descriptions and module counts:

┌─────────────────────────────────────────┐
│ [🏠]  Home                              │
│        Dashboard Overview               │
├─────────────────────────────────────────┤
│ [🌐]  CONTROL TOWER                     │
│        Process Mining & Analytics       │
├─────────────────────────────────────────┤
│ [🔍]  Search & Explore                  │
│        Advanced Search Tools            │
│        3 Modules                     ▼  │
└─────────────────────────────────────────┘
```

---

## Success Criteria

✅ Module counts are clearly visible for all expandable sections
✅ Hierarchy is obvious (Main → Sub-modules)
✅ Visual design matches STOX.AI pattern
✅ Smooth animations on expand/collapse
✅ Accessible via keyboard
✅ Responsive across all screen sizes
✅ Consistent color theming per category
✅ Clear visual feedback on hover/select
✅ Sidebar collapse/expand works smoothly
✅ All 22 modules are properly organized

---

## Next Steps

1. ✅ **Planning Phase** (This document)
2. [ ] **Implementation Phase**
   - Update EnhancedSidebar.jsx with new structure
   - Add secondary text and module counts
   - Enhance styling to match mockups
   - Add smooth animations
3. [ ] **Testing Phase**
   - Test all expand/collapse interactions
   - Verify keyboard navigation
   - Test responsive behavior
   - Accessibility audit
4. [ ] **Polish Phase**
   - Fine-tune animations
   - Adjust colors and spacing
   - Add loading states
   - User testing feedback

---

**Document Version:** 1.0.0
**Last Updated:** 2025-11-01
**Status:** Ready for Implementation
**Estimated Implementation Time:** 4-6 hours
