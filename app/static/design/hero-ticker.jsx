/* global React */

// Thin horizontal ticker — sits at the bottom edge of the hero.
// Fed by /api/ticker, which returns the most recent proprietor additions
// from the live CCOD/OCOD index. No mock data.
function LRRegisterTicker() {
  const [items, setItems] = React.useState([]);
  const [status, setStatus] = React.useState('loading');

  React.useEffect(() => {
    let cancelled = false;
    fetch('/api/ticker', { headers: { 'Accept': 'application/json' } })
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(data => {
        if (cancelled) return;
        const list = Array.isArray(data && data.items) ? data.items : [];
        setItems(list);
        setStatus(list.length ? 'ok' : 'empty');
      })
      .catch(() => { if (!cancelled) setStatus('error'); });
    return () => { cancelled = true; };
  }, []);

  const tagColor = (t) => {
    if (t === 'Overseas')   return { c:'var(--danger)',    bg:'var(--danger-bg)' };
    if (t === 'Proprietor') return { c:'var(--brand-700)', bg:'var(--brand-50)' };
    return { c:'var(--ink-3)', bg:'var(--paper-soft)' };
  };

  const loop = items.length ? [...items, ...items] : [];

  return (
    <div style={tS.rail}>
      <div style={tS.stamp}>
        <span style={tS.stampDot}/>
        <span style={tS.stampLabel}>Live feed</span>
        <span style={tS.stampSub}>
          {status === 'ok'      && 'Most recent proprietors'}
          {status === 'loading' && 'Fetching register…'}
          {status === 'empty'   && 'No recent entries'}
          {status === 'error'   && 'Feed unavailable'}
        </span>
      </div>

      <div style={tS.maskLeft}/>
      <div style={tS.viewport}>
        {loop.length === 0 ? (
          <div style={tS.placeholder}>
            {status === 'loading'
              ? '— Loading recent register entries —'
              : '— Register feed currently unavailable —'}
          </div>
        ) : (
          <div style={tS.track}>
            {loop.map((r, i) => {
              const { c, bg } = tagColor(r.tag);
              return (
                <div key={i} style={tS.item}>
                  <span style={{...tS.tag, color:c, background:bg}}>{r.tag}</span>
                  <span style={tS.co}>{r.company}</span>
                  <span style={tS.meta} className="mono tabular">{r.crn}</span>
                  <span style={tS.dot}/>
                  <span style={tS.meta} className="mono tabular">{r.postcode}</span>
                  <span style={tS.when} className="tabular">{formatWhen(r.date_added)}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>
      <div style={tS.maskRight}/>

      <a href="/search" style={tS.cta}>
        Open stream
        <i className="ph ph-arrow-right" style={{fontSize:12}}/>
      </a>
    </div>
  );
}

// HM Land Registry dates arrive mostly as DD-MM-YYYY but ISO YYYY-MM-DD
// is also common in our pipeline. Parse defensively, format coarsely.
function formatWhen(raw) {
  if (!raw) return '';
  const d = parseLandRegDate(raw);
  if (!d) return raw;

  const ms = Date.now() - d.getTime();
  if (ms < 0) return 'today';
  const days = Math.floor(ms / 86400000);
  if (days === 0) return 'today';
  if (days === 1) return 'yesterday';
  if (days < 7)   return days + 'd ago';
  if (days < 30)  return Math.floor(days / 7) + 'w ago';
  if (days < 365) return Math.floor(days / 30) + 'mo ago';
  return Math.floor(days / 365) + 'y ago';
}

function parseLandRegDate(s) {
  const t = String(s).trim();
  let m = /^(\d{4})-(\d{2})-(\d{2})/.exec(t);
  if (m) return new Date(+m[1], +m[2] - 1, +m[3]);
  m = /^(\d{2})-(\d{2})-(\d{4})/.exec(t);
  if (m) return new Date(+m[3], +m[2] - 1, +m[1]);
  m = /^(\d{2})\/(\d{2})\/(\d{4})/.exec(t);
  if (m) return new Date(+m[3], +m[2] - 1, +m[1]);
  return null;
}

const tS = {
  rail: {
    position:'relative',
    display:'flex', alignItems:'stretch',
    background:'rgba(255,255,255,0.82)',
    backdropFilter:'blur(10px)',
    border:'1px solid var(--line-strong)',
    borderLeft:0, borderRight:0,
    height:48,
    overflow:'hidden',
  },
  stamp: {
    display:'flex', alignItems:'center', gap:10,
    padding:'0 18px',
    borderRight:'1px solid var(--line-strong)',
    background:'var(--ink)',
    color:'#fff',
    flexShrink:0,
    zIndex:2,
  },
  stampDot: {
    width:7, height:7, borderRadius:'50%',
    background:'var(--gold-300)',
    boxShadow:'0 0 0 3px rgba(232,201,122,0.25)',
    animation:'lrPulse 1.6s ease-in-out infinite',
  },
  stampLabel: {
    font:'600 11px/1 var(--font-body)',
    textTransform:'uppercase', letterSpacing:'0.16em',
  },
  stampSub: {
    font:'500 11px/1 var(--font-mono)',
    color:'rgba(255,255,255,0.55)',
    paddingLeft:10,
    borderLeft:'1px solid rgba(255,255,255,0.15)',
  },
  viewport: {
    flex:1,
    position:'relative',
    overflow:'hidden',
    display:'flex', alignItems:'center',
  },
  track: {
    display:'flex', alignItems:'center', gap:0,
    animation:'lrTickerScroll 70s linear infinite',
    willChange:'transform',
  },
  placeholder: {
    padding:'0 18px',
    font:'500 11px/1 var(--font-mono)',
    color:'var(--ink-4)',
    letterSpacing:'0.04em',
  },
  item: {
    display:'inline-flex', alignItems:'center', gap:10,
    padding:'0 18px',
    borderRight:'1px solid var(--line)',
    whiteSpace:'nowrap',
    height:'100%',
  },
  tag: {
    padding:'3px 7px', borderRadius:2,
    font:'500 10px/1 var(--font-body)',
    textTransform:'uppercase', letterSpacing:'0.08em',
  },
  co: {
    font:'500 12px/1 var(--font-body)',
    color:'var(--ink)',
  },
  meta: {
    font:'500 11px/1 var(--font-mono)',
    color:'var(--ink-3)',
  },
  dot: { width:3, height:3, borderRadius:'50%', background:'var(--ink-5)' },
  when: {
    font:'500 11px/1 var(--font-mono)',
    color:'var(--ink-4)',
    marginLeft:4,
  },
  maskLeft: {
    position:'absolute', left:190, top:0, bottom:0, width:40,
    background:'linear-gradient(to right, rgba(255,255,255,0.95), transparent)',
    zIndex:1, pointerEvents:'none',
  },
  maskRight: {
    position:'absolute', right:140, top:0, bottom:0, width:60,
    background:'linear-gradient(to left, rgba(255,255,255,0.95), transparent)',
    zIndex:1, pointerEvents:'none',
  },
  cta: {
    display:'inline-flex', alignItems:'center', gap:6,
    padding:'0 18px',
    borderLeft:'1px solid var(--line-strong)',
    background:'var(--paper-soft)',
    color:'var(--brand-700)',
    font:'600 11px/1 var(--font-body)',
    textTransform:'uppercase', letterSpacing:'0.14em',
    textDecoration:'none',
    flexShrink:0,
    zIndex:2,
  },
};

window.LRRegisterTicker = LRRegisterTicker;
