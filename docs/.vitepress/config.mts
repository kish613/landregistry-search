import { defineConfig } from 'vitepress'

export default defineConfig({
  lang: 'en-GB',
  title: 'landregistry.company',
  titleTemplate: ':title · landregistry.company docs',
  description:
    'Documentation for landregistry.company — search the UK Land Registry CCOD dataset by company, address, or director.',

  cleanUrls: true,
  lastUpdated: true,

  head: [
    ['link', { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' }],
    ['link', { rel: 'icon', type: 'image/png', href: '/favicon.png' }],
    ['link', { rel: 'preconnect', href: 'https://fonts.googleapis.com' }],
    ['link', { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' }],
    [
      'link',
      {
        rel: 'stylesheet',
        href: 'https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,400;0,500;0,600;0,700;1,400&family=IBM+Plex+Sans:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap'
      }
    ],
    ['meta', { name: 'theme-color', content: '#1f5130' }],
    ['meta', { property: 'og:type', content: 'website' }],
    ['meta', { property: 'og:site_name', content: 'landregistry.company docs' }],
    ['meta', { property: 'og:image', content: 'https://landregistry.company/static/og-image.png' }],
    ['meta', { name: 'twitter:card', content: 'summary_large_image' }]
  ],

  themeConfig: {
    logo: '/logo-mark.svg',
    siteTitle: 'landregistry.company',

    nav: [
      { text: 'Guide', link: '/guide/introduction', activeMatch: '/guide/' },
      { text: 'Data', link: '/data/ccod', activeMatch: '/data/' },
      { text: 'API', link: '/api/overview', activeMatch: '/api/' },
      { text: 'FAQ', link: '/faq' },
      {
        text: 'Resources',
        items: [
          { text: 'About the project', link: '/about' },
          { text: 'Changelog', link: '/changelog' },
          {
            text: 'HM Land Registry',
            link: 'https://www.gov.uk/government/organisations/land-registry'
          },
          {
            text: 'CCOD dataset',
            link: 'https://use-land-property-data.service.gov.uk/'
          },
          {
            text: 'Companies House',
            link: 'https://www.gov.uk/government/organisations/companies-house'
          }
        ]
      },
      {
        text: 'Run a search',
        link: 'https://landregistry.company/search'
      }
    ],

    sidebar: {
      '/guide/': [
        {
          text: 'Getting started',
          collapsed: false,
          items: [
            { text: 'Introduction', link: '/guide/introduction' },
            { text: 'Quick start', link: '/guide/quick-start' },
            { text: 'Accounts & credits', link: '/guide/accounts' },
            { text: 'Pricing', link: '/guide/pricing' }
          ]
        },
        {
          text: 'Searching the register',
          collapsed: false,
          items: [
            { text: 'Search methods', link: '/guide/search-methods' },
            { text: 'Company search', link: '/guide/search-company' },
            { text: 'Address search', link: '/guide/search-address' },
            { text: 'Director search', link: '/guide/search-director' }
          ]
        },
        {
          text: 'Working with results',
          collapsed: false,
          items: [
            { text: 'Reading a result', link: '/guide/reading-results' },
            { text: 'Exporting data', link: '/guide/exporting' },
            { text: 'Tips & best practice', link: '/guide/tips' }
          ]
        }
      ],
      '/data/': [
        {
          text: 'Source data',
          collapsed: false,
          items: [
            { text: 'CCOD overview', link: '/data/ccod' },
            { text: 'OCOD (overseas)', link: '/data/ocod' },
            { text: 'Companies House cross-reference', link: '/data/companies-house' }
          ]
        },
        {
          text: 'How we use it',
          collapsed: false,
          items: [
            { text: 'Methodology', link: '/data/methodology' },
            { text: 'Refresh schedule', link: '/data/refresh-schedule' },
            { text: 'Coverage & limits', link: '/data/coverage' },
            { text: 'Schema reference', link: '/data/schema' },
            { text: 'Licensing', link: '/data/licensing' }
          ]
        }
      ],
      '/api/': [
        {
          text: 'API reference',
          collapsed: false,
          items: [
            { text: 'Overview', link: '/api/overview' },
            { text: 'Authentication & credits', link: '/api/authentication' },
            { text: 'Search endpoint', link: '/api/search' },
            { text: 'Director endpoints', link: '/api/directors' },
            { text: 'Export endpoints', link: '/api/export' },
            { text: 'Checkout & payments', link: '/api/checkout' },
            { text: 'Errors', link: '/api/errors' }
          ]
        }
      ]
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/kish613/landregistry-search' }
    ],

    footer: {
      message:
        'Data © Crown copyright &amp; database right · HM Land Registry, under the Open Government Licence v3.0.',
      copyright: '© IntelTree Ltd — landregistry.company'
    },

    search: {
      provider: 'local',
      options: {
        detailedView: true
      }
    },

    outline: {
      level: [2, 3],
      label: 'On this page'
    },

    docFooter: {
      prev: 'Previous',
      next: 'Next'
    },

    editLink: {
      pattern:
        'https://github.com/kish613/landregistry-search/edit/master/docs/:path',
      text: 'Suggest an edit on GitHub'
    },

    lastUpdated: {
      text: 'Last updated',
      formatOptions: { dateStyle: 'long' }
    }
  },

  sitemap: {
    hostname: 'https://landregistry.company/docs'
  }
})
