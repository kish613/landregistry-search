# landregistry.company — docs

VitePress documentation for [landregistry.company](https://landregistry.company).

## Local development

```bash
cd docs
npm install
npm run docs:dev
```

The dev server runs at `http://localhost:5173` with hot reload.

## Build

```bash
npm run docs:build      # outputs to dist/docs/ (matches base: '/docs/')
npm run docs:preview    # preview the production build locally
```

The output is intentionally nested under `dist/docs/` so that when
`@vercel/static-build` uploads `dist/` to the deployment root, the
files end up at `/docs/...` — matching the `base: '/docs/'` URL prefix
the HTML is built with.

## Deployment

Vercel routing is set up in the repo's root `vercel.json`. A request
to `/docs` redirects to `/docs/`; `/docs/` serves the docs landing
page; clean URLs like `/docs/guide/introduction` are rewritten to
`/docs/guide/introduction.html`; anything that's not a docs path
falls through to the Flask app.

## Structure

```
docs/
├── .vitepress/
│   ├── config.mts        # Site config — nav, sidebar, head, theme
│   └── theme/
│       ├── index.ts      # Default theme + custom.css
│       └── custom.css    # Brand-matched palette (forest green + paper)
├── public/               # Static assets (favicons, logo mark)
├── guide/                # Search workflow walkthroughs
├── data/                 # CCOD / OCOD / Companies House background
├── api/                  # JSON API reference
├── index.md              # Landing page
├── faq.md
├── about.md
└── changelog.md
```

## Design tokens

The CSS in `.vitepress/theme/custom.css` mirrors
`app/static/css/tokens.css`. If the main site's palette changes there,
update the `--lr-*` variables in `custom.css` to keep the docs visually
in sync.
