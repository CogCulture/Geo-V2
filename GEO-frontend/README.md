# GEO Analyzer

A modern React TypeScript web application for analyzing brand visibility across major language models (LLMs). Built with a beautiful, responsive UI and real-time progress tracking.

## Features

### Input Form
- **Brand Name** (required): Enter the brand you want to analyze
- **Product Description / Industry** (optional): Provide additional context
- **Website URL** (optional): Add your website for reference
- **LLM Selection** (required): Choose from 6 major LLMs:
  - Claude
  - Mistral
  - Google AI Overview
  - ChatGPT
  - Perplexity
  - Gemini

### Real-Time Progress Tracking
- Live progress bar showing 0-100% completion
- Current step description
- Automatic polling every 2 seconds
- Elegant error handling with retry functionality

### Results Dashboard

#### Summary Metrics (4 Cards)
- **Analyzed Prompts**: Total number of prompts analyzed
- **Brand Mentions**: Count of brand mentions across responses
- **Average Position**: Mean position of brand mentions
- **Average Visibility**: Overall visibility score as percentage

#### Visualizations
- **Visibility Over Time**: Line chart showing visibility trends across prompt sequences
- **Share of Voice**: Pie chart displaying brand percentage distribution
- **Analyzed Prompts Table**: Paginated table with search functionality
  - Columns: Prompt, Source (LLM), Citation, Visibility
  - 10 items per page with navigation
  - Real-time search across prompts and LLMs
- **Top Cited Domains**: Sorted table of domain citations with counts and percentages

## Technology Stack

### Frontend
- **React 18** with TypeScript
- **Tailwind CSS** for styling
- **Shadcn UI** for component library
- **TanStack Query** (React Query v5) for data fetching and caching
- **Recharts** for data visualizations
- **React Hook Form** with Zod validation
- **Wouter** for routing

### Backend
- **Express.js** for API proxy server
- **Axios** for FastAPI backend communication
- **TypeScript** for type safety

## Prerequisites

You need a FastAPI backend running that provides the following endpoints:

- `POST /api/analysis/run` - Start analysis
- `GET /api/analysis/status/{session_id}` - Check progress
- `GET /api/results/{session_id}` - Get results

By default, the application expects the FastAPI backend at `http://localhost:8000`. You can configure this with the `FASTAPI_BASE_URL` environment variable.

## Getting Started

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Start the FastAPI backend** (on port 8000 by default)

3. **Run the application**:
   ```bash
   npm run dev
   ```

4. **Open your browser** to `http://localhost:5000`

## Configuration

### Environment Variables

- `FASTAPI_BASE_URL`: Base URL for the FastAPI backend (default: `http://localhost:8000`)

## Usage Flow

1. **Enter Brand Information**: Fill in the brand name (required) and optional details
2. **Select LLMs**: Choose at least one LLM to analyze (up to all 6)
3. **Start Analysis**: Click "Start Analysis" to begin
4. **Monitor Progress**: Watch the real-time progress bar and status updates
5. **View Results**: Explore the comprehensive dashboard with metrics, charts, and tables
6. **New Analysis**: Click "New Analysis" to start over

## Error Handling

The application includes robust error handling:

- **Connection Failures**: If the FastAPI backend is unavailable, you'll see a clear error message with a retry button
- **Network Issues**: Automatic retries (3 attempts) before showing error
- **User-Friendly Messages**: All errors display helpful guidance
- **Recovery**: Retry button re-establishes connection without page reload

## Design Philosophy

- **Data First**: Clean, legible presentation of analytics data
- **Progressive Disclosure**: Show complexity only when needed (form → loading → results)
- **Responsive**: Fully mobile-responsive with adaptive layouts
- **Accessible**: WCAG AA color contrast, proper ARIA labels, keyboard navigation
- **Professional**: Material Design principles with subtle shadows and consistent spacing

## Project Structure

```
├── client/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/              # Shadcn UI components
│   │   │   ├── analysis-form.tsx
│   │   │   ├── analysis-progress.tsx
│   │   │   ├── analysis-results.tsx
│   │   │   ├── summary-metrics.tsx
│   │   │   ├── prompts-table.tsx
│   │   │   ├── visibility-chart.tsx
│   │   │   ├── share-of-voice-chart.tsx
│   │   │   └── domain-citations-table.tsx
│   │   ├── pages/
│   │   │   └── home.tsx
│   │   ├── lib/
│   │   │   ├── queryClient.ts   # TanStack Query setup
│   │   │   └── utils.ts
│   │   └── App.tsx
│   └── index.html
├── server/
│   ├── routes.ts                # API proxy routes
│   └── index.ts
├── shared/
│   └── schema.ts                # TypeScript types and Zod schemas
└── README.md
```

## API Integration

The application communicates with your FastAPI backend through proxy routes:

### Start Analysis
```typescript
POST /api/analysis/run
Body: {
  brand_name: string,
  product_name?: string,
  website_url?: string,
  num_prompts: number,
  selected_llms: string[]
}
Response: { session_id: string }
```

### Check Status
```typescript
GET /api/analysis/status/{session_id}
Response: {
  progress: number,      // 0-100
  current_step: string,
  status: string         // "running" | "completed"
}
```

### Get Results
```typescript
GET /api/results/{session_id}
Response: {
  session_id: string,
  llm_responses: Array<{
    prompt: string,
    source: string,
    citation?: string,
    visibility_score?: number
  }>,
  brand_scores: Array<{
    mention_count: number,
    average_position: number,
    visibility_score: number
  }>,
  share_of_voice: Array<{
    brand_name: string,
    percentage: number
  }>,
  domain_citations: Array<{
    domain: string,
    count: number,
    percentage: number
  }>,
  metrics: {
    total_prompts: number
  }
}
```

## Testing

The application includes comprehensive `data-testid` attributes for end-to-end testing:

- Form inputs: `input-brand-name`, `input-product-name`, `input-website-url`
- LLM checkboxes: `checkbox-llm-{llm-name}`
- Progress tracking: `progress-bar`, `text-progress-percentage`, `text-current-step`
- Results: `metric-total-prompts`, `metric-mention-count`, etc.
- Tables: `row-prompt-{index}`, `row-domain-{index}`
- Pagination: `button-previous-page`, `button-next-page`

## Contributing

This is a production-ready MVP. Future enhancements could include:

- Export functionality (PDF reports, CSV downloads)
- Analysis history and comparison
- Advanced filtering and sorting
- Competitor analysis visualization
- Result sharing with shareable links

## License

MIT
