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
npm run docs:build      # outputs to .vitepress/dist
npm run docs:preview    # preview the production build locally
```

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
