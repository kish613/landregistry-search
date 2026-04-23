/* global React */

// Option C — Document-as-hero.
// Treats the landing page like the cover of an official ledger:
// heavy rule lines, stamped seal, monospace metadata, inline search.
function LRDocumentHero({ headline = 'Who owns this?', sub = 'Follow the title, not the façade.' }) {
  const [mode, setMode] = React.useState('company');
  const [val,  setVal]  = React.useState('');
  const [focus,setFocus]= React.useState(false);

  const modes = [
    { k:'company',  label:'COMPANY',  placeholder:'BARRATT DEVELOPMENTS PLC' },
    { k:'address',  label:'ADDRESS',  placeholder:'SW7 2AX' },
    { k:'director', label:'DIRECTOR', placeholder:'JONATHAN M. SMITH' },
  ];
  const m = modes.find(x=>x.k===mode);

  // Today's date — shown in archival format
  const today = '03 APRIL 2026';

  return (
    <header style={dH.wrap}>
      {/* Top double-rule — ledger cover */}
      <div style={dH.doubleRule}/>

      {/* Masthead strip — "official document" metadata */}
      <div style={dH.masthead}>
        <div style={dH.mastLeft}>
          <span style={dH.mastSmall}>VOL. XXIV</span>
          <span style={dH.mastPipe}/>
          <span style={dH.mastSmall}>CCOD · v2026.04</span>
          <span style={dH.mastPipe}/>
          <span style={dH.mastSmall}>{today}</span>
        </div>
        <div style={dH.mastCentre}>
          THE CORPORATE LAND REGISTER
          <span style={dH.mastCentreSub}>— of England &amp; Wales —</span>
        </div>
        <div style={dH.mastRight}>
          <span style={dH.mastSmall}>SHEET EW·144</span>
          <span style={dH.mastPipe}/>
          <span style={dH.mastSmall}>FOLIO 00001</span>
        </div>
      </div>

      {/* Thin rule between masthead and body */}
      <div style={dH.hairline}/>

      {/* Body — two-column editorial: headline + stamped seal */}
      <div style={dH.body}>
        <div style={dH.bodyInner}>

          {/* LEFT — dropcap headline, inline search sentence */}
          <div style={dH.leftCol}>

            {/* Case file number — like a docket */}
            <div style={dH.caseLine}>
              <span style={dH.caseNo}>No. 3,814,226</span>
              <span style={dH.caseLabel}>titles on record — indexed this morning</span>
            </div>

            {/* Editorial headline with dropcap */}
            <h1 style={dH.headline}>
              <span style={dH.dropcap}>W</span>
              <span>{headline.replace(/^W/, '')}</span>
              <br/>
              <span style={dH.headlineItalic}>{sub}</span>
            </h1>

            {/* Inline search — reads like a sentence in a ledger */}
            <div style={dH.searchBlock}>
              <div style={dH.searchEyebrow}>
                <span style={dH.searchEyebrowNum}>§ 01</span>
                <span style={dH.searchEyebrowLabel}>SEARCH THE REGISTER</span>
              </div>

              <div style={dH.sentence}>
                <span style={dH.sentenceWord}>Show me the titles held by</span>

                {/* mode selector — rendered as a dropdown-style token */}
                <div style={dH.modeToken}>
                  {modes.map(x => (
                    <button
                      key={x.k}
                      onClick={()=>setMode(x.k)}
                      style={{
                        ...dH.modeBtn,
                        ...(mode===x.k ? dH.modeBtnActive : {}),
                      }}
                    >
                      {x.label}
                    </button>
                  ))}
                </div>

                <span style={dH.sentenceWord}>named</span>

                {/* Inline input — underlined, no box */}
                <span style={{
                  ...dH.inputWrap,
                  borderBottomColor: focus ? 'var(--brand-700)' : 'var(--ink)',
                  borderBottomWidth: focus ? 2 : 1,
                }}>
                  <input
                    value={val}
                    onChange={e=>setVal(e.target.value)}
                    onFocus={()=>setFocus(true)}
                    onBlur={()=>setFocus(false)}
                    placeholder={m.placeholder}
                    style={dH.inputEl}
                    autoComplete="off"
                  />
                  {!val && !focus && <span style={dH.caret}>_</span>}
                </span>

                <span style={dH.sentenceWord}>.</span>
              </div>

              {/* Submit — single bold action */}
              <div style={dH.actionRow}>
                <button style={dH.submitBtn}>
                  <span>ISSUE SEARCH</span>
                  <i className="ph ph-arrow-right" style={{fontSize:14}}/>
                </button>
                <span style={dH.priceLine}>
                  <i className="ph-fill ph-seal-check" style={{color:'var(--gold-500)', fontSize:12, verticalAlign:-1}}/>
                  &nbsp;£1.00 per title · £3.00 per director search
                </span>
              </div>

              {/* Sample queries — as archival "see also" */}
              <div style={dH.seeAlso}>
                <span style={dH.seeAlsoLabel}>See also —</span>
                {[
                  'Barratt Developments PLC',
                  'Tesco Stores Limited',
                  'SW7 2AX',
                  '00048839',
                ].map((q, i) => (
                  <a key={i} href="#" style={dH.seeAlsoLink}>{q}</a>
                ))}
              </div>
            </div>
          </div>

          {/* RIGHT — stamped seal + metadata column */}
          <aside style={dH.rightCol}>
            <LRSeal/>

            <div style={dH.metaGrid}>
              <div style={dH.metaRow}>
                <span style={dH.metaKey}>Source</span>
                <span style={dH.metaVal}>HM Land Registry (CCOD)</span>
              </div>
              <div style={dH.metaRow}>
                <span style={dH.metaKey}>Cross-ref.</span>
                <span style={dH.metaVal}>Companies House</span>
              </div>
              <div style={dH.metaRow}>
                <span style={dH.metaKey}>Coverage</span>
                <span style={dH.metaVal}>England &amp; Wales</span>
              </div>
              <div style={dH.metaRow}>
                <span style={dH.metaKey}>Refreshed</span>
                <span style={dH.metaVal}>{today}</span>
              </div>
              <div style={dH.metaRow}>
                <span style={dH.metaKey}>Median query</span>
                <span style={dH.metaVal}>180 ms</span>
              </div>
              <div style={dH.metaRow}>
                <span style={dH.metaKey}>Schema</span>
                <span style={dH.metaVal}>OSGB36 · EPSG:27700</span>
              </div>
            </div>

            <div style={dH.footnote}>
              <sup style={dH.footSup}>†</sup>&nbsp;Records drawn from the public register under Land Registration Act 2002 § 66. Cross-reference via Companies House open index.
            </div>
          </aside>

        </div>
      </div>

      {/* Bottom double-rule — closes the ledger page */}
      <div style={dH.hairline}/>
      <div style={dH.doubleRule}/>
    </header>
  );
}

// ---- Stamped seal ----------------------------------------------------
function LRSeal() {
  return (
    <div style={dH.sealWrap}>
      <svg viewBox="0 0 200 200" width="180" height="180" style={dH.sealSvg}>
        <defs>
          <path id="seal-top" d="M 100 100 m -76 0 a 76 76 0 1 1 152 0"/>
          <path id="seal-bot" d="M 100 100 m -76 0 a 76 76 0 1 0 152 0"/>
        </defs>

        {/* Outer ring */}
        <circle cx="100" cy="100" r="88" fill="none" stroke="currentColor" strokeWidth="1.5"/>
        <circle cx="100" cy="100" r="82" fill="none" stroke="currentColor" strokeWidth="0.6"/>

        {/* Text along the top arc */}
        <text fontFamily="IBM Plex Mono, monospace" fontSize="10" fontWeight="600"
              fill="currentColor" letterSpacing="3">
          <textPath href="#seal-top" startOffset="50%" textAnchor="middle">
            REGISTERED · VERIFIED · INDEXED
          </textPath>
        </text>
        <text fontFamily="IBM Plex Mono, monospace" fontSize="10" fontWeight="600"
              fill="currentColor" letterSpacing="3">
          <textPath href="#seal-bot" startOffset="50%" textAnchor="middle">
            · CORPORATE LAND REGISTER · EST. 2026 ·
          </textPath>
        </text>

        {/* Inner ring */}
        <circle cx="100" cy="100" r="56" fill="none" stroke="currentColor" strokeWidth="0.6"/>

        {/* Cross-hatched crest — stylised title deed */}
        <g transform="translate(100 100)" stroke="currentColor" strokeWidth="1" fill="none">
          <path d="M -24 -30 L 24 -30 L 24 22 L 0 34 L -24 22 Z"/>
          <line x1="-18" y1="-20" x2="18" y2="-20"/>
          <line x1="-18" y1="-10" x2="18" y2="-10"/>
          <line x1="-18" y1="0"   x2="18" y2="0"/>
          <line x1="-18" y1="10"  x2="18" y2="10"/>
        </g>

        {/* Date band */}
        <text x="100" y="168" textAnchor="middle"
              fontFamily="IBM Plex Mono, monospace" fontSize="9" fontWeight="600"
              fill="currentColor" letterSpacing="2">
          MMXXVI
        </text>
      </svg>
      <span style={dH.sealCaption}>Verified against HM Land Registry</span>
    </div>
  );
}

// ---- Styles ----------------------------------------------------------
const dH = {
  wrap: {
    position:'relative',
    background:'var(--paper)',
    borderBottom:'1px solid var(--line)',
    color:'var(--ink)',
  },

  /* Heavy top rule — two-line, like a legal document */
  doubleRule: {
    height:4,
    background:'linear-gradient(to bottom, var(--ink) 0, var(--ink) 1px, transparent 1px, transparent 3px, var(--ink) 3px, var(--ink) 4px)',
  },
  hairline: { height:1, background:'var(--line-strong)' },

  /* Masthead */
  masthead: {
    display:'grid',
    gridTemplateColumns:'1fr auto 1fr',
    alignItems:'center',
    gap:16,
    padding:'12px 32px',
    background:'var(--paper)',
  },
  mastLeft: {
    display:'flex', alignItems:'center', gap:10,
    font:'500 11px/1 var(--font-mono)',
    color:'var(--ink-3)', letterSpacing:'0.06em',
  },
  mastRight: {
    display:'flex', alignItems:'center', gap:10, justifyContent:'flex-end',
    font:'500 11px/1 var(--font-mono)',
    color:'var(--ink-3)', letterSpacing:'0.06em',
  },
  mastSmall: { whiteSpace:'nowrap' },
  mastPipe: { width:1, height:10, background:'var(--line-strong)' },

  mastCentre: {
    textAlign:'center',
    font:'600 12px/1 var(--font-body)',
    textTransform:'uppercase',
    letterSpacing:'0.36em',
    color:'var(--ink)',
    whiteSpace:'nowrap',
  },
  mastCentreSub: {
    display:'block',
    marginTop:6,
    font:'400 italic 13px/1 var(--font-display)',
    letterSpacing:'0.02em',
    textTransform:'none',
    color:'var(--ink-3)',
  },

  /* Body */
  body: { padding:'0 32px' },
  bodyInner: {
    maxWidth:1200, margin:'0 auto',
    padding:'64px 0 80px',
    display:'grid',
    gridTemplateColumns:'minmax(0, 1.55fr) minmax(0, 1fr)',
    columnGap:80,
    alignItems:'start',
  },

  leftCol: { minWidth:0 },

  caseLine: {
    display:'flex', alignItems:'baseline', gap:12,
    marginBottom:28,
  },
  caseNo: {
    font:'600 14px/1 var(--font-mono)',
    color:'var(--ink)',
    padding:'5px 10px',
    border:'1px solid var(--ink)',
    letterSpacing:'0.02em',
  },
  caseLabel: {
    font:'400 italic 14px/1.4 var(--font-display)',
    color:'var(--ink-3)',
  },

  headline: {
    font:'400 clamp(3rem, 1.4rem + 4.5vw, 5rem)/0.98 var(--font-display)',
    letterSpacing:'-0.025em',
    color:'var(--ink)',
    margin:'0 0 40px',
    textWrap:'balance',
  },
  dropcap: {
    float:'left',
    font:'700 clamp(5rem, 2rem + 8vw, 9rem)/0.82 var(--font-display)',
    color:'var(--brand-700)',
    paddingRight:14,
    paddingTop:4,
    letterSpacing:'-0.04em',
  },
  headlineItalic: {
    display:'block',
    marginTop:8,
    fontStyle:'italic',
    fontWeight:400,
    color:'var(--ink-3)',
    font:'400 italic clamp(1.6rem, 0.8rem + 1.8vw, 2.4rem)/1.15 var(--font-display)',
    letterSpacing:'-0.01em',
  },

  /* Search section — numbered like a ledger clause */
  searchBlock: {
    paddingTop:28,
    borderTop:'2px solid var(--ink)',
  },
  searchEyebrow: {
    display:'flex', alignItems:'center', gap:10,
    marginBottom:18,
  },
  searchEyebrowNum: {
    font:'600 11px/1 var(--font-mono)',
    color:'var(--brand-700)',
    letterSpacing:'0.04em',
  },
  searchEyebrowLabel: {
    font:'600 11px/1 var(--font-body)',
    textTransform:'uppercase',
    letterSpacing:'0.2em',
    color:'var(--ink-3)',
  },

  sentence: {
    display:'flex', flexWrap:'wrap', alignItems:'center',
    gap:'6px 12px',
    font:'500 clamp(1.25rem, 0.8rem + 0.8vw, 1.6rem)/1.5 var(--font-display)',
    color:'var(--ink)',
    marginBottom:28,
  },
  sentenceWord: {
    color:'var(--ink-2)',
    fontStyle:'italic',
    fontWeight:400,
  },

  modeToken: {
    display:'inline-flex',
    border:'1px solid var(--ink)',
    background:'var(--paper)',
    overflow:'hidden',
  },
  modeBtn: {
    padding:'8px 14px',
    border:0,
    background:'transparent',
    color:'var(--ink-3)',
    font:'600 11px/1 var(--font-mono)',
    letterSpacing:'0.12em',
    cursor:'pointer',
    borderRight:'1px solid var(--line-strong)',
    transition:'background 120ms var(--ease), color 120ms var(--ease)',
  },
  modeBtnActive: {
    background:'var(--ink)',
    color:'var(--paper)',
  },

  inputWrap: {
    position:'relative',
    display:'inline-flex', alignItems:'baseline',
    minWidth:280, flex:'1 1 280px',
    borderBottom:'1px solid var(--ink)',
    paddingBottom:2,
  },
  inputEl: {
    flex:1,
    border:0, outline:0, background:'transparent',
    padding:'4px 0',
    font:'500 clamp(1.25rem, 0.8rem + 0.8vw, 1.6rem)/1.5 var(--font-display)',
    color:'var(--ink)',
    letterSpacing:'-0.005em',
    minWidth:0,
  },
  caret: {
    position:'absolute', right:0, bottom:2,
    font:'500 20px/1 var(--font-mono)',
    color:'var(--ink-4)',
    animation:'lrPulse 1.1s ease-in-out infinite',
  },

  actionRow: {
    display:'flex', alignItems:'center', gap:20, flexWrap:'wrap',
    paddingTop:8, paddingBottom:20,
    borderBottom:'1px solid var(--line)',
  },
  submitBtn: {
    display:'inline-flex', alignItems:'center', gap:10,
    padding:'14px 24px',
    border:0, borderRadius:0,
    background:'var(--ink)', color:'var(--paper)',
    font:'700 12px/1 var(--font-body)',
    letterSpacing:'0.22em',
    cursor:'pointer',
    transition:'background 120ms var(--ease)',
  },
  priceLine: {
    font:'500 12px/1.4 var(--font-mono)',
    color:'var(--ink-3)',
    letterSpacing:'0.02em',
  },

  seeAlso: {
    display:'flex', alignItems:'center', gap:10,
    marginTop:18, flexWrap:'wrap',
  },
  seeAlsoLabel: {
    font:'600 italic 13px/1 var(--font-display)',
    color:'var(--ink-4)',
  },
  seeAlsoLink: {
    font:'500 12px/1 var(--font-mono)',
    color:'var(--ink-2)',
    textDecoration:'underline',
    textDecorationThickness:'1px',
    textUnderlineOffset:3,
    textDecorationColor:'var(--line-strong)',
    padding:'2px 0',
  },

  /* Right column — seal + metadata */
  rightCol: {
    minWidth:0,
    display:'flex', flexDirection:'column', gap:28,
    borderLeft:'1px solid var(--line)',
    paddingLeft:40,
  },

  sealWrap: {
    display:'flex', flexDirection:'column', alignItems:'center',
    color:'var(--brand-700)',
    padding:'12px 0 16px',
    borderBottom:'1px dashed var(--line-strong)',
  },
  sealSvg: {
    transform:'rotate(-6deg)',
    opacity:0.88,
    filter:'drop-shadow(0 1px 0 rgba(15,20,12,0.04))',
  },
  sealCaption: {
    marginTop:12,
    font:'500 11px/1 var(--font-mono)',
    color:'var(--ink-3)',
    textAlign:'center',
    letterSpacing:'0.04em',
  },

  metaGrid: {
    display:'flex', flexDirection:'column',
    borderTop:'1px solid var(--line)',
    borderBottom:'1px solid var(--line)',
  },
  metaRow: {
    display:'grid', gridTemplateColumns:'110px 1fr', gap:14,
    padding:'10px 0',
    borderBottom:'1px dotted var(--line-strong)',
    alignItems:'baseline',
  },
  metaKey: {
    font:'600 10px/1.4 var(--font-body)',
    textTransform:'uppercase', letterSpacing:'0.18em',
    color:'var(--ink-4)',
  },
  metaVal: {
    font:'500 13px/1.4 var(--font-mono)',
    color:'var(--ink)',
  },

  footnote: {
    font:'400 italic 12px/1.5 var(--font-display)',
    color:'var(--ink-3)',
    paddingTop:4,
  },
  footSup: {
    color:'var(--brand-700)',
    fontStyle:'normal',
    fontFamily:'var(--font-mono)',
    fontWeight:600,
  },
};

/* ——— Remove last metaRow border for tidiness ——— */
// applied via CSS below
const css = `
  .lr-docmeta > div:last-child { border-bottom: 0 !important; }
`;

window.LRDocumentHero = LRDocumentHero;
