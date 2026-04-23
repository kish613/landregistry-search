/* global React */

// Mock "latest in the register" events
const FEED_EVENTS = [
  { t:'New charge',     co:'TESCO STORES LIMITED',           crn:'00519500', pc:'AL7 1GA', tenure:'Freehold',  when:'2m ago' },
  { t:'Proprietor',     co:'BARRATT DEVELOPMENTS PLC',       crn:'00604574', pc:'NW1 4RY', tenure:'Freehold',  when:'4m ago' },
  { t:'Title updated',  co:'OCADO GROUP PLC',                crn:'07098618', pc:'WD3 7GX', tenure:'Leasehold', when:'7m ago' },
  { t:'Overseas',       co:'KIRKWOOD HOLDINGS SARL',         crn:'OE029114', pc:'W1K 3BF', tenure:'Freehold',  when:'11m ago' },
  { t:'Charge removed', co:'SEGRO (GREATER LONDON) LIMITED', crn:'09381011', pc:'UB11 1FE',tenure:'Leasehold', when:'14m ago' },
  { t:'Proprietor',     co:'GROSVENOR ESTATE HOLDINGS LTD',  crn:'03219178', pc:'SW1X 7JJ',tenure:'Freehold',  when:'18m ago' },
  { t:'New charge',     co:'BRITISH LAND COMPANY PLC',       crn:'00621920', pc:'EC3M 3BD',tenure:'Leasehold', when:'22m ago' },
  { t:'Title updated',  co:'ROYAL MAIL GROUP LIMITED',       crn:'04138203', pc:'EC1A 1BB',tenure:'Freehold',  when:'26m ago' },
  { t:'Overseas',       co:'MARINA BAY INVEST PTE LTD',      crn:'OE117822', pc:'E14 5AB', tenure:'Leasehold', when:'31m ago' },
  { t:'Proprietor',     co:'JOHN LAID BOOTS PROPERTIES LTD', crn:'00229230', pc:'NG1 2FE', tenure:'Freehold',  when:'37m ago' },
];

function LRRegisterFeed() {
  const [tick, setTick] = React.useState(0);
  React.useEffect(() => {
    const id = setInterval(() => setTick(t => t + 1), 2600);
    return () => clearInterval(id);
  }, []);

  // Rotate the array so the "newest" moves to the top
  const n = FEED_EVENTS.length;
  const rows = React.useMemo(() => {
    const offset = tick % n;
    return [...FEED_EVENTS.slice(offset), ...FEED_EVENTS.slice(0, offset)];
  }, [tick]);

  const tagColor = (t) => {
    if (t === 'New charge' || t === 'Overseas')     return 'var(--danger)';
    if (t === 'Charge removed')                     return 'var(--ok)';
    if (t === 'Proprietor')                         return 'var(--brand-700)';
    return 'var(--ink-3)';
  };
  const tagBg = (t) => {
    if (t === 'New charge' || t === 'Overseas')     return 'var(--danger-bg)';
    if (t === 'Charge removed')                     return 'var(--ok-bg)';
    if (t === 'Proprietor')                         return 'var(--brand-50)';
    return 'var(--paper-soft)';
  };

  return (
    <div style={feedS.wrap}>
      <header style={feedS.head}>
        <div>
          <div style={feedS.eyebrow}>Latest in the register</div>
          <div style={feedS.sub}>Title-level events indexed in the last hour</div>
        </div>
        <span style={feedS.live}>
          <span style={feedS.dot}/>
          Live
        </span>
      </header>

      <div style={feedS.table}>
        <div style={feedS.headRow}>
          <span>Event</span>
          <span>Proprietor</span>
          <span style={{textAlign:'right'}}>Time</span>
        </div>
        <div style={feedS.scroll}>
          {rows.slice(0, 4).map((r, i) => (
            <div
              key={`${tick}-${i}`}
              style={{
                ...feedS.row,
                opacity: 1 - i * 0.07,
                animation: i === 0 ? 'lrFeedIn 480ms var(--ease)' : 'none',
              }}
            >
              <span style={{...feedS.tag, color: tagColor(r.t), background: tagBg(r.t)}}>
                {r.t}
              </span>
              <div style={feedS.who}>
                <div style={feedS.co}>{r.co}</div>
                <div style={feedS.meta} className="mono tabular">
                  <span>{r.crn}</span>
                  <span style={feedS.pipe}/>
                  <span>{r.pc}</span>
                  <span style={feedS.pipe}/>
                  <span>{r.tenure}</span>
                </div>
              </div>
              <span style={feedS.when} className="tabular">{r.when}</span>
            </div>
          ))}
        </div>
      </div>

      <footer style={feedS.foot}>
        <span>
          <i className="ph ph-activity" style={{fontSize:12, marginRight:6, verticalAlign:-1}}></i>
          <span className="tabular">128</span> events today
        </span>
        <span style={feedS.pipe}/>
        <a href="#search" style={feedS.link}>
          Open stream
          <i className="ph ph-arrow-right" style={{fontSize:11}}></i>
        </a>
      </footer>
    </div>
  );
}

const feedS = {
  wrap: {
    background:'#FFFFFF',
    border:'1px solid var(--line-strong)',
    borderRadius:6,
    boxShadow:'0 1px 0 rgba(15,20,12,0.04), 0 8px 24px rgba(15,20,12,0.08)',
    overflow:'hidden',
    display:'flex', flexDirection:'column',
  },
  head: {
    padding:'14px 16px',
    borderBottom:'1px solid var(--line)',
    display:'flex', justifyContent:'space-between', alignItems:'center',
    background:'var(--paper-soft)',
  },
  eyebrow: {
    font:'600 11px/1.2 var(--font-body)',
    textTransform:'uppercase', letterSpacing:'0.14em',
    color:'var(--ink-2)',
  },
  sub: { font:'var(--t-caption)', color:'var(--ink-3)', marginTop:2 },
  live: {
    display:'inline-flex', alignItems:'center', gap:6,
    padding:'3px 8px', borderRadius:999,
    border:'1px solid var(--ok)', background:'var(--ok-bg)',
    font:'600 10px/1 var(--font-body)',
    textTransform:'uppercase', letterSpacing:'0.14em',
    color:'var(--ok)',
  },
  dot: { width:6, height:6, borderRadius:'50%', background:'var(--ok)',
         animation:'lrPulse 1.6s ease-in-out infinite' },
  table: { flex:1, display:'flex', flexDirection:'column' },
  headRow: {
    display:'grid', gridTemplateColumns:'90px 1fr 70px', gap:12,
    padding:'10px 16px', borderBottom:'1px solid var(--line)',
    font:'600 10px/1.2 var(--font-body)', textTransform:'uppercase',
    letterSpacing:'0.14em', color:'var(--ink-4)',
  },
  scroll: { flex:1 },
  row: {
    display:'grid', gridTemplateColumns:'90px 1fr 70px', gap:12,
    padding:'10px 16px', alignItems:'center',
    borderBottom:'1px solid var(--line)',
  },
  tag: {
    display:'inline-flex', alignItems:'center', justifyContent:'center',
    padding:'3px 8px', borderRadius:2,
    font:'500 11px/1.2 var(--font-body)',
    whiteSpace:'nowrap',
    width:'fit-content',
  },
  who: { minWidth:0 },
  co: {
    font:'500 13px/1.3 var(--font-body)', color:'var(--ink)',
    whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis',
  },
  meta: {
    font:'500 11px/1.3 var(--font-mono)', color:'var(--ink-3)',
    display:'flex', alignItems:'center', gap:8, marginTop:3,
  },
  pipe: { width:1, height:10, background:'var(--line-strong)' },
  when: {
    font:'500 11px/1.3 var(--font-mono)', color:'var(--ink-3)',
    textAlign:'right',
  },
  foot: {
    padding:'10px 16px',
    borderTop:'1px solid var(--line)',
    background:'var(--paper-soft)',
    display:'flex', alignItems:'center', justifyContent:'space-between',
    font:'var(--t-body-sm)', color:'var(--ink-3)',
  },
  link: {
    font:'600 11px/1 var(--font-body)',
    textTransform:'uppercase', letterSpacing:'0.14em',
    color:'var(--brand-700)', textDecoration:'none',
    display:'inline-flex', alignItems:'center', gap:6,
  },
};

window.LRRegisterFeed = LRRegisterFeed;
