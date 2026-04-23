/* global React */
function LRNav({ credits = 42, signedIn = false }) {
  return (
    <nav style={lrNavStyles.bar}>
      <div style={lrNavStyles.inner}>
        {/* Brand — tighter, drops the .company tagline once the wordmark is set */}
        <a href="/" style={lrNavStyles.brand}>
          <img src={(window.LR_ASSETS && window.LR_ASSETS.logoMark) || '/static/design/assets/logo-mark.svg'}
               style={{width:30,height:30}} alt="" />
          <span style={lrNavStyles.word}>
            landregistry<span style={lrNavStyles.dom}>.company</span>
          </span>
        </a>

        {/* Centre — three concise links, sentence-case (matches guide) */}
        <div style={lrNavStyles.links}>
          <a href="/search"  style={lrNavStyles.link}>Search</a>
          <a href="/how-to-search-land-registry" style={lrNavStyles.link}>How to</a>
          <a href="#data"    style={lrNavStyles.link}>Data source</a>
        </div>

        {/* Right — sign in as a plain text link, single compact CTA */}
        <div style={lrNavStyles.right}>
          {signedIn ? (
            <span style={lrNavStyles.credits}>
              <i className="ph ph-coins" style={{fontSize:13}}></i>
              <span className="tabular">{credits}</span>
            </span>
          ) : (
            <a href="/auth" style={lrNavStyles.signin}>Sign in</a>
          )}
          <a href="/search" style={lrNavStyles.cta} data-btn="primary">
            Run a search
          </a>
        </div>
      </div>
      <div style={lrNavStyles.rule}/>
    </nav>
  );
}

const lrNavStyles = {
  bar: {
    position:'sticky', top:0, zIndex:40,
    background:'rgba(250,250,245,0.92)',
    backdropFilter:'blur(12px)',
    WebkitBackdropFilter:'blur(12px)',
  },
  inner: {
    maxWidth:1200, margin:'0 auto', padding:'0 32px', height:60,
    display:'grid', gridTemplateColumns:'auto 1fr auto', alignItems:'center',
    columnGap:32,
  },
  brand: {
    display:'inline-flex', alignItems:'center', gap:10,
    textDecoration:'none', color:'var(--ink)',
  },
  word: { font:'600 15px/1 var(--font-display)', letterSpacing:'-0.01em' },
  dom:  { color:'var(--brand-700)', fontWeight:400 },
  links:{ display:'flex', gap:28, justifyContent:'center' },
  link: {
    font:'500 13px/1 var(--font-body)',
    color:'var(--ink-3)', textDecoration:'none',
    whiteSpace:'nowrap',
    transition:'color 120ms var(--ease)',
  },
  right:{ display:'flex', alignItems:'center', gap:18, justifySelf:'end' },
  credits: {
    display:'inline-flex', alignItems:'center', gap:6,
    padding:'5px 9px', background:'var(--paper-soft)',
    border:'1px solid var(--line)', borderRadius:4,
    font:'500 12px/1 var(--font-mono)', color:'var(--ink-2)',
  },
  signin: {
    font:'500 13px/1 var(--font-body)', color:'var(--ink-2)',
    textDecoration:'none',
  },
  cta: {
    display:'inline-flex', alignItems:'center', gap:6,
    padding:'8px 14px', borderRadius:4,
    background:'var(--brand-700)', color:'#fff',
    font:'600 12px/1 var(--font-body)',
    letterSpacing:'0.01em',
    textDecoration:'none',
    transition:'background 120ms var(--ease)',
  },
  rule: { height:1, background:'var(--line)' },
};

window.LRNav = LRNav;
