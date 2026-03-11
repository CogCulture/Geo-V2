# GEO Analyzer Design Guidelines

## Design Approach
**System-Based Approach**: Material Design principles adapted for data-heavy analytics interface
- Focus on clarity, hierarchy, and data legibility
- Card-based architecture for component organization
- Emphasis on functional design over decorative elements

## Core Design Principles
1. **Data First**: All design decisions prioritize data readability and comprehension
2. **Progressive Disclosure**: Show complexity only when needed (form → loading → results)
3. **Consistent Elevation**: Use shadow hierarchy to indicate component importance and state

## Typography System

**Font Family**: Inter via Google Fonts (excellent for data displays)
- Primary: Inter (400, 500, 600, 700)

**Hierarchy**:
- Hero Title (GEO Analyzer): text-5xl font-bold
- Section Headings: text-2xl font-semibold
- Card Titles: text-lg font-semibold
- Metric Values: text-3xl font-bold (for dashboard numbers)
- Body Text: text-base font-normal
- Labels/Captions: text-sm font-medium
- Table Headers: text-xs font-semibold uppercase tracking-wide

## Layout System

**Spacing Units**: Tailwind units of 2, 4, 6, 8, 12, 16
- Component padding: p-6 or p-8
- Section gaps: gap-6 or gap-8
- Card spacing: space-y-6
- Form field spacing: space-y-4

**Container Strategy**:
- Max width: max-w-7xl (1280px)
- Page padding: px-4 sm:px-6 lg:px-8
- Responsive breakpoints: sm (640px), md (768px), lg (1024px), xl (1280px)

## Color Palette

**Primary**: Blue #3B82F6 (bg-blue-500)
- Buttons, active states, links, progress bars

**Neutrals**:
- Background: bg-gray-50
- Cards: bg-white
- Borders: border-gray-200
- Text Primary: text-gray-900
- Text Secondary: text-gray-600
- Text Muted: text-gray-500

**Semantic**:
- Success: bg-green-500 (for completed status)
- Warning: bg-yellow-500 (for in-progress)
- Error: bg-red-500 (for error states)

## Component Library

### Header
- Full-width white background with subtle bottom border
- Centered content with max-w-7xl
- Title + subtitle stack vertically on mobile, horizontal on desktop

### Input Form Card
- White card with shadow-md, rounded-lg borders
- Grid layout: 2 columns on desktop (md:grid-cols-2), single column mobile
- Input fields with border-gray-300, focus:border-blue-500, focus:ring-2 focus:ring-blue-200
- Labels with text-sm font-medium text-gray-700 above inputs

### LLM Selection
- Grid of 6 checkboxes: 2 columns mobile, 3 columns tablet, 6 columns desktop
- Each checkbox as a clickable card with border, hover state with border-blue-500
- Active state with bg-blue-50 and border-blue-500

### Progress Section
- Centered card during loading state
- Progress bar with bg-blue-500 fill on bg-gray-200 track, rounded-full
- Current step text below progress bar in text-gray-600

### Results Dashboard
**Summary Metrics**: 4-column grid (grid-cols-1 sm:grid-cols-2 lg:grid-cols-4)
- Each metric card with icon (from Heroicons), large number, and label
- Icon in blue circle background (bg-blue-100, text-blue-600)

**Data Tables**:
- Striped rows (even:bg-gray-50)
- Sticky header with bg-gray-100
- Borders: border-gray-200
- Pagination controls below table

**Charts**:
- White card containers with p-6
- Chart titles with text-lg font-semibold mb-4
- Recharts with blue color scheme matching primary color
- Tooltips with white background and shadow

### Buttons
- Primary: bg-blue-500 hover:bg-blue-600 text-white px-6 py-3 rounded-lg font-medium
- Disabled: bg-gray-300 cursor-not-allowed
- Secondary: border border-gray-300 hover:border-gray-400 bg-white px-6 py-3

### Cards
- Base: bg-white rounded-lg shadow-md p-6
- Hover (clickable): hover:shadow-lg transition-shadow
- Spacing between cards: space-y-6

## Responsive Behavior
- Stack all multi-column layouts to single column below md breakpoint
- Hide non-essential table columns on mobile, show expand button
- Collapse chart legends below charts on mobile
- Form fields full-width on mobile with larger touch targets (min-h-12)

## Visual Refinements
- Subtle shadows for depth: shadow-sm, shadow-md, shadow-lg
- Rounded corners consistently: rounded-lg for cards, rounded-md for inputs
- Smooth transitions on interactive elements: transition-colors duration-200
- No decorative animations - focus on data clarity
- Empty states: centered icon + message for "No data" scenarios

## Accessibility
- Form labels properly associated with inputs
- Sufficient color contrast (WCAG AA minimum)
- Focus indicators visible on all interactive elements
- ARIA labels for charts and complex data displays