/* global React */

function LRSection({ id, eyebrow, title, sub, children, tone = 'paper', narrow = false }) {
  const bg = tone === 'paper-soft' ? 'var(--paper-soft)' : 'var(--paper)';
  return (
    <section id={id} style={{
      background: bg,
      borderTop: tone === 'paper-soft' ? '1px solid var(--line)' : '0',
      borderBottom: tone === 'paper-soft' ? '1px solid var(--line)' : '0',
    }}>
      <div style={{
        maxWidth: narrow ? 820 : 1200,
        margin: '0 auto',
        padding: '88px 32px',
      }}>
        {eyebrow && <div className="eyebrow" style={{marginBottom: 14}}>{eyebrow}</div>}
        {title && <h2 style={{font:'var(--t-h1)', letterSpacing:'-0.015em', maxWidth: 720, marginBottom: sub ? 16 : 40}}>{title}</h2>}
        {sub && <p style={{font:'var(--t-body-lg)', color:'var(--ink-3)', maxWidth: 640, marginBottom: 48}}>{sub}</p>}
        {children}
      </div>
    </section>
  );
}

// Search methods — hairline cards, no glass, no big-icon-in-square.
function LRMethods() {
  const items = [
    { k:'Company search',
      body:'Locate every title registered to a corporate proprietor. Matches on exact name, fuzzy name, or 8-digit Companies House number.',
      fields:['Fuzzy name match','CRN lookup','Group / subsidiary trace'],
      price:'£1.00 per search',
      icon:'ph-buildings' },
    { k:'Address lookup',
      body:'Reverse lookup. Enter a postcode or site address to identify the registered corporate proprietor — freehold or leasehold.',
      fields:['Postcode (full or partial)','USRN / UPRN','Street-level match'],
      price:'£1.00 per search',
      icon:'ph-map-pin' },
    { k:'Director search',
      body:'Cross-references director appointment history with CCOD — surfaces titles held by companies where a named person is (or was) a director.',
      fields:['Resigned appointments','Associated entities','Date-bounded search'],
      price:'£3.00 · premium',
      icon:'ph-user' },
  ];
  return (
    <div style={lrMeth.grid}>
      {items.map((it, i) => (
        <article key={i} style={lrMeth.card} className="lr-method">
          <header style={lrMeth.head}>
            <i className={`ph ${it.icon}`} style={{fontSize:20, color:'var(--brand-700)'}}></i>
            <h3 style={lrMeth.name}>{it.k}</h3>
          </header>
          <p style={lrMeth.body}>{it.body}</p>
          <ul style={lrMeth.list}>
            {it.fields.map((f, j) => (
              <li key={j} style={lrMeth.li}>
                <i className="ph ph-caret-right" style={{fontSize:11, color:'var(--brand-700)'}}></i>
                {f}
              </li>
            ))}
          </ul>
          <footer style={lrMeth.foot}>
            <span style={lrMeth.price}>{it.price}</span>
            <a href="/search" style={lrMeth.link}>
              Try it <i className="ph ph-arrow-right" style={{fontSize:11}}></i>
            </a>
          </footer>
        </article>
      ))}
    </div>
  );
}

const lrMeth = {
  grid: { display:'grid', gridTemplateColumns:'repeat(3, 1fr)', gap:0,
          borderTop:'1px solid var(--line)', borderLeft:'1px solid var(--line)' },
  card: { padding:'28px 28px 24px',
          borderRight:'1px solid var(--line)', borderBottom:'1px solid var(--line)',
          background:'var(--paper)', display:'flex', flexDirection:'column', gap:12,
          transition:'background 120ms var(--ease)' },
  head: { display:'flex', alignItems:'center', gap:10, marginBottom:4 },
  name: { font:'var(--t-h4)', color:'var(--ink)' },
  body: { font:'var(--t-body)', color:'var(--ink-3)', margin:0 },
  list: { listStyle:'none', padding:0, margin:'4px 0 8px', display:'flex', flexDirection:'column', gap:6 },
  li:   { display:'flex', alignItems:'center', gap:8, font:'var(--t-body-sm)', color:'var(--ink-2)' },
  foot: { display:'flex', justifyContent:'space-between', alignItems:'center',
          paddingTop:14, borderTop:'1px solid var(--line)', marginTop:'auto' },
  price:{ font:'500 12px/1 var(--font-mono)', color:'var(--ink-2)' },
  link: { font:'600 11px/1 var(--font-body)', textTransform:'uppercase', letterSpacing:'0.14em',
          color:'var(--brand-700)', textDecoration:'none',
          display:'inline-flex', alignItems:'center', gap:6 },
};

// Stats strip — hairline table, tabular numerics
function LRStats() {
  const cells = [
    { v:'3.8 M',  k:'Corporate titles',   sub:'Freehold + leasehold' },
    { v:'1.2 M',  k:'Registered proprietors', sub:'UK + overseas' },
    { v:'180 ms', k:'Median query time',  sub:'p95 · 420 ms' },
    { v:'Monthly',k:'Data refresh',       sub:'Last: 3 Apr 2026' },
  ];
  return (
    <div style={lrStats.wrap}>
      {cells.map((c, i) => (
        <div key={i} style={{...lrStats.cell, borderLeft: i ? '1px solid var(--line)' : '0'}}>
          <div style={lrStats.v} className="tabular">{c.v}</div>
          <div style={lrStats.k}>{c.k}</div>
          <div style={lrStats.sub}>{c.sub}</div>
        </div>
      ))}
    </div>
  );
}

const lrStats = {
  wrap: { display:'grid', gridTemplateColumns:'repeat(4, 1fr)',
          borderTop:'1px solid var(--line)', borderBottom:'1px solid var(--line)' },
  cell: { padding:'22px 24px', display:'flex', flexDirection:'column', gap:4 },
  v:    { font:'600 32px/1.05 var(--font-display)', letterSpacing:'-0.015em', color:'var(--ink)' },
  k:    { font:'600 11px/1.3 var(--font-body)', textTransform:'uppercase',
          letterSpacing:'0.14em', color:'var(--ink-3)', marginTop:6 },
  sub:  { font:'var(--t-body-sm)', color:'var(--ink-4)' },
};

// Audience — who uses this
function LRAudience() {
  const rows = [
    { role:'Investigative journalists', icon:'ph-newspaper',
      use:'Follow money, trace ownership chains, expose opaque structures behind overseas entities.' },
    { role:'Property dealers & auctioneers', icon:'ph-gavel',
      use:'Source deals; verify registered proprietor before bidding on lots or submitting offers.' },
    { role:'Insolvency practitioners', icon:'ph-scales',
      use:'Identify titles held by distressed companies and track charges registered over them.' },
    { role:'Solicitors & paralegals', icon:'ph-books',
      use:'Conveyancing due diligence; confirm proprietor details against CCOD on file.' },
  ];
  return (
    <div style={lrAud.list}>
      {rows.map((r, i) => (
        <div key={i} style={{...lrAud.row, borderTop: i ? '1px solid var(--line)' : '1px solid var(--line-strong)'}}>
          <div style={lrAud.side}>
            <i className={`ph ${r.icon}`} style={{fontSize:18, color:'var(--brand-700)'}}></i>
            <div style={lrAud.role}>{r.role}</div>
          </div>
          <div style={lrAud.use}>{r.use}</div>
        </div>
      ))}
      <div style={{borderTop:'1px solid var(--line-strong)'}}/>
    </div>
  );
}

const lrAud = {
  list: { display:'flex', flexDirection:'column' },
  row:  { display:'grid', gridTemplateColumns:'320px 1fr', gap:40, padding:'22px 4px' },
  side: { display:'flex', alignItems:'center', gap:12 },
  role: { font:'600 16px/1.3 var(--font-body)', color:'var(--ink)' },
  use:  { font:'var(--t-body-lg)', color:'var(--ink-3)', maxWidth:640 },
};

// Data source callout — split
function LRData() {
  return (
    <div style={lrDataS.grid}>
      <div style={lrDataS.left}>
        <h2 style={{font:'var(--t-h2)', letterSpacing:'-0.01em', marginBottom:18}}>
          The register, indexed and searchable.
        </h2>
        <p style={{font:'var(--t-body-lg)', color:'var(--ink-3)', marginBottom:28, maxWidth:520}}>
          The dataset covers every freehold and leasehold interest registered to a corporate
          proprietor in England and Wales. We mirror HM Land Registry's Commercial and
          Corporate Ownership Data (CCOD), refreshed monthly, and layer a fast search index
          plus Companies House cross-reference on top.
        </p>
        <div style={lrDataS.sources}>
          <div style={lrDataS.src}>
            <div style={lrDataS.srcHead}>
              <i className="ph ph-database" style={{fontSize:18, color:'var(--brand-700)'}}></i>
              <span style={lrDataS.srcName}>HM Land Registry</span>
              <i className="ph-fill ph-seal-check" style={{color:'var(--gold-500)', fontSize:14, marginLeft:'auto'}}></i>
            </div>
            <div style={lrDataS.srcDesc}>CCOD — all registered titles owned by a UK or overseas company.</div>
          </div>
          <div style={lrDataS.src}>
            <div style={lrDataS.srcHead}>
              <i className="ph ph-identification-card" style={{fontSize:18, color:'var(--brand-700)'}}></i>
              <span style={lrDataS.srcName}>Companies House</span>
              <i className="ph-fill ph-seal-check" style={{color:'var(--gold-500)', fontSize:14, marginLeft:'auto'}}></i>
            </div>
            <div style={lrDataS.srcDesc}>Appointments + corporate filings, mapped by CRN to title numbers.</div>
          </div>
        </div>
      </div>

      <div style={lrDataS.card}>
        <div style={lrDataS.cardHead}>
          <span className="eyebrow">Registry status</span>
          <span style={lrDataS.live}>
            <span style={lrDataS.dot}/>Online
          </span>
        </div>
        <table style={lrDataS.table} className="tabular">
          <tbody>
            <tr><td style={lrDataS.k}>Dataset</td><td style={lrDataS.v}>CCOD · v2026.04</td></tr>
            <tr><td style={lrDataS.k}>Last refresh</td><td style={lrDataS.v}>3 April 2026</td></tr>
            <tr><td style={lrDataS.k}>Next refresh</td><td style={lrDataS.v}>6 May 2026</td></tr>
            <tr><td style={lrDataS.k}>Titles indexed</td><td style={lrDataS.v}>3,814,226</td></tr>
            <tr><td style={lrDataS.k}>Proprietors</td><td style={lrDataS.v}>1,187,094</td></tr>
            <tr><td style={lrDataS.k}>Overseas entities</td><td style={lrDataS.v}>98,412</td></tr>
            <tr><td style={lrDataS.k}>Coverage</td><td style={lrDataS.v}>England & Wales</td></tr>
            <tr><td style={lrDataS.k}>Licence</td><td style={lrDataS.v}>Open Government</td></tr>
          </tbody>
        </table>
        <a href="/search" style={lrDataS.cta}>
          <i className="ph ph-magnifying-glass" style={{fontSize:14}}></i>
          Run a search
        </a>
      </div>
    </div>
  );
}

const lrDataS = {
  grid: { display:'grid', gridTemplateColumns:'1fr 420px', gap:56, alignItems:'start' },
  left: {},
  sources: { display:'flex', flexDirection:'column', gap:12 },
  src:  { padding:'14px 16px', border:'1px solid var(--line)', borderRadius:6,
          background:'var(--paper-soft)' },
  srcHead: { display:'flex', alignItems:'center', gap:10, marginBottom:4 },
  srcName: { font:'600 14px/1.3 var(--font-body)', color:'var(--ink)', flex:1, minWidth:0 },
  srcDesc: { font:'var(--t-body-sm)', color:'var(--ink-3)' },
  card: { background:'#fff', border:'1px solid var(--line-strong)', borderRadius:6,
          padding:'24px', boxShadow:'var(--shadow-1)' },
  cardHead: { display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:16 },
  live: { display:'inline-flex', alignItems:'center', gap:6,
          font:'600 10px/1 var(--font-body)', textTransform:'uppercase',
          letterSpacing:'0.14em', color:'var(--ok)' },
  dot:  { width:6, height:6, borderRadius:'50%', background:'var(--ok)' },
  table:{ width:'100%', borderCollapse:'collapse', margin:'0 0 18px' },
  k:    { padding:'8px 0', borderBottom:'1px solid var(--line)',
          font:'var(--t-body-sm)', color:'var(--ink-3)', textAlign:'left', width:'45%' },
  v:    { padding:'8px 0', borderBottom:'1px solid var(--line)',
          font:'500 13px/1.4 var(--font-mono)', color:'var(--ink)', textAlign:'right' },
  cta:  { display:'flex', alignItems:'center', justifyContent:'center', gap:8,
          padding:'12px 18px', background:'var(--brand-700)', color:'#fff',
          font:'600 12px/1 var(--font-body)', textTransform:'uppercase', letterSpacing:'0.14em',
          borderRadius:4, textDecoration:'none' },
};

// Pricing / final CTA
function LRPricing() {
  return (
    <div style={lrPri.grid}>
      <div style={lrPri.tier}>
        <div className="eyebrow" style={{marginBottom:10}}>Standard</div>
        <div style={lrPri.amount}>
          £<span className="tabular">1.00</span>
          <span style={lrPri.unit}>per title search</span>
        </div>
        <ul style={lrPri.list}>
          <li>Company, CRN, or address search</li>
          <li>Full title detail — proprietor, charges, tenure</li>
          <li>CSV + JSON export</li>
          <li>10 free searches on sign-up</li>
        </ul>
      </div>
      <div style={{...lrPri.tier, ...lrPri.tierPrem}}>
        <div className="eyebrow" style={{marginBottom:10, color:'var(--gold-700)'}}>
          <i className="ph-fill ph-seal-check" style={{color:'var(--gold-500)', marginRight:6, verticalAlign:-2}}></i>
          Premium
        </div>
        <div style={lrPri.amount}>
          £<span className="tabular">3.00</span>
          <span style={lrPri.unit}>per director search</span>
        </div>
        <ul style={lrPri.list}>
          <li>Cross-referenced with Companies House appointments</li>
          <li>Includes resigned &amp; historic directorships</li>
          <li>Linked-entity trace (up to 3 hops)</li>
          <li>Priority support + bulk export</li>
        </ul>
      </div>
    </div>
  );
}

const lrPri = {
  grid: { display:'grid', gridTemplateColumns:'1fr 1fr', gap:20 },
  tier: { padding:'28px 28px 24px', background:'var(--paper)',
          border:'1px solid var(--line-strong)', borderRadius:6 },
  tierPrem: { borderColor:'var(--gold-500)', background:'#fff' },
  amount: { font:'600 36px/1.05 var(--font-display)', letterSpacing:'-0.015em', color:'var(--ink)',
            display:'flex', alignItems:'baseline', gap:14, marginBottom:18,
            paddingBottom:14, borderBottom:'1px solid var(--line)' },
  unit: { font:'400 13px/1.3 var(--font-body)', color:'var(--ink-3)',
          position:'relative', top:-4 },
  list: { listStyle:'none', padding:0, margin:0, display:'flex', flexDirection:'column', gap:8,
          font:'var(--t-body)', color:'var(--ink-2)' },
};

// Footer — hairline, institutional
function LRFooter() {
  return (
    <footer style={lrFoot.wrap}>
      <div style={lrFoot.inner}>
        <div style={lrFoot.top}>
          <div>
            <div style={lrFoot.brand}>
              <img src={(window.LR_ASSETS && window.LR_ASSETS.logoMark) || '/static/design/assets/logo-mark.svg'}
                   style={{width:30,height:30}} alt=""/>
              <span style={lrFoot.word}>landregistry<span style={{color:'var(--brand-700)',fontWeight:400}}>.company</span></span>
            </div>
            <p style={lrFoot.desc}>
              Corporate land ownership for England and Wales. Data under Open Government Licence v3.0.
            </p>
          </div>
          <div style={lrFoot.colset}>
            <div style={lrFoot.col}>
              <div style={lrFoot.h}>Product</div>
              <a style={lrFoot.l} href="/search">Run a search</a>
              <a style={lrFoot.l} href="/how-to-search-land-registry">How to use</a>
              <a style={lrFoot.l} href="#pricing">Pricing</a>
              <a style={lrFoot.l} href="/resources">Resources</a>
            </div>
            <div style={lrFoot.col}>
              <div style={lrFoot.h}>Data</div>
              <a style={lrFoot.l} href="https://www.gov.uk/government/organisations/land-registry" target="_blank" rel="noopener">HM Land Registry</a>
              <a style={lrFoot.l} href="https://use-land-property-data.service.gov.uk/datasets/ccod" target="_blank" rel="noopener">CCOD dataset</a>
              <a style={lrFoot.l} href="https://find-and-update.company-information.service.gov.uk/" target="_blank" rel="noopener">Companies House</a>
              <a style={lrFoot.l} href="#data">Refresh schedule</a>
            </div>
            <div style={lrFoot.col}>
              <div style={lrFoot.h}>Company</div>
              <a style={lrFoot.l} href="/about">About</a>
              <a style={lrFoot.l} href="/faq">FAQ</a>
              <a style={lrFoot.l} href="/blog">Blog</a>
              <a style={lrFoot.l} href="mailto:hello@landregistry.company">Contact</a>
            </div>
          </div>
        </div>
        <div style={lrFoot.meta}>
          <span>© 2026 IntelTree Ltd — landregistry.company</span>
          <span>Data © Crown copyright &amp; database right 2026 · HM Land Registry</span>
          <span style={{display:'inline-flex',alignItems:'center',gap:8}}>
            <span style={{width:6,height:6,borderRadius:'50%',background:'var(--ok)'}}></span>
            All systems online
          </span>
        </div>
      </div>
    </footer>
  );
}

const lrFoot = {
  wrap:  { borderTop:'1px solid var(--line-strong)', background:'var(--paper-soft)' },
  inner: { maxWidth:1200, margin:'0 auto', padding:'56px 32px 32px' },
  top:   { display:'grid', gridTemplateColumns:'1.3fr 2fr', gap:56 },
  brand: { display:'flex', alignItems:'center', gap:10, marginBottom:14 },
  word:  { font:'600 16px/1 var(--font-display)', letterSpacing:'-0.01em' },
  desc:  { font:'var(--t-body-sm)', color:'var(--ink-3)', maxWidth:320 },
  colset:{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:32 },
  col:   { display:'flex', flexDirection:'column', gap:10 },
  h:     { font:'600 11px/1 var(--font-body)', textTransform:'uppercase', letterSpacing:'0.14em',
           color:'var(--ink-4)', marginBottom:6 },
  l:     { font:'var(--t-body-sm)', color:'var(--ink-2)', textDecoration:'none' },
  meta:  { marginTop:40, paddingTop:20, borderTop:'1px solid var(--line)',
           display:'flex', justifyContent:'space-between', gap:20,
           font:'500 11px/1.3 var(--font-body)', textTransform:'uppercase',
           letterSpacing:'0.14em', color:'var(--ink-4)', flexWrap:'wrap' },
};

window.LRSection = LRSection;
window.LRMethods = LRMethods;
window.LRStats   = LRStats;
window.LRAudience= LRAudience;
window.LRData    = LRData;
window.LRPricing = LRPricing;
window.LRFooter  = LRFooter;
