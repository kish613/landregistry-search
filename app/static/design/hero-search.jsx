/* global React */

// Condensed hero search: mode chips on top, ONE confident input, one button.
// Designed to sit over the map backdrop — white surface with strong shadow.
function LRHeroSearch() {
  const [mode, setMode] = React.useState('company');
  const [val,  setVal]  = React.useState('');
  const [focus,setFocus]= React.useState(false);

  const modes = [
    { k:'company',  label:'Company',  icon:'ph-buildings',
      placeholder:'Barratt Developments PLC   ·   or   00604574',
      price:'£1.00' },
    { k:'address',  label:'Address',  icon:'ph-map-pin',
      placeholder:'SW7 2AX   ·   or   12 Kensington Gore, London',
      price:'£1.00' },
    { k:'director', label:'Director', icon:'ph-user',
      placeholder:'Jonathan M. Smith',
      price:'£3.00' },
  ];
  const m = modes.find(x=>x.k===mode);

  return (
    <div style={hS.wrap}>
      {/* Mode chips — live above the input, not inside */}
      <div style={hS.chipRow}>
        <span style={hS.chipLabel}>Search by</span>
        {modes.map(x => (
          <button
            key={x.k}
            onClick={()=>setMode(x.k)}
            style={{
              ...hS.chip,
              ...(mode===x.k ? hS.chipActive : {}),
            }}
          >
            <i className={`ph ${x.icon}`} style={{fontSize:13}}/>
            {x.label}
          </button>
        ))}
        <span style={{flex:1}}/>
        <span style={hS.priceChip}>
          <i className="ph-fill ph-seal-check" style={{color:'var(--gold-500)', fontSize:12}}/>
          {m.price} per title
        </span>
      </div>

      {/* The input bar — single, generous, confident */}
      <form
        action="/search"
        method="get"
        onSubmit={(e)=>{
          if (!val.trim()) { e.preventDefault(); return; }
        }}
        style={{
          ...hS.bar,
          borderColor: focus ? 'var(--brand-700)' : 'var(--line-strong)',
          boxShadow: focus
            ? '0 0 0 4px rgba(31,81,48,0.14), 0 8px 32px rgba(15,20,12,0.14)'
            : '0 8px 32px rgba(15,20,12,0.14)',
        }}
      >
        <i className="ph ph-magnifying-glass" style={hS.icon}/>
        <input
          name="q"
          style={hS.input}
          placeholder={m.placeholder}
          value={val}
          onChange={e=>setVal(e.target.value)}
          onFocus={()=>setFocus(true)}
          onBlur={()=>setFocus(false)}
          autoComplete="off"
        />
        <input type="hidden" name="type" value={mode}/>
        <span style={hS.kbd}>⌘K</span>
        <button type="submit" style={hS.btn}>
          Search
          <i className="ph ph-arrow-right" style={{fontSize:14}}/>
        </button>
      </form>

      {/* Sample queries — subtle, beneath the bar */}
      <div style={hS.trials}>
        <span style={hS.trialsLabel}>Try</span>
        {[
          { q:'Barratt Developments PLC', mono:false },
          { q:'Tesco Stores Limited',     mono:false },
          { q:'SW7 2AX',                  mono:true  },
          { q:'00048839',                 mono:true  },
        ].map((t, i) => (
          <a key={i} href={`/search?q=${encodeURIComponent(t.q)}`} style={{
            ...hS.trialChip,
            font: t.mono
              ? '500 12px/1 var(--font-mono)'
              : '500 12px/1 var(--font-body)',
          }}>{t.q}</a>
        ))}
      </div>
    </div>
  );
}

const hS = {
  wrap: { width:'100%' },

  chipRow: {
    display:'flex', alignItems:'center', gap:8,
    marginBottom:14, flexWrap:'wrap',
  },
  chipLabel: {
    font:'600 11px/1 var(--font-body)',
    textTransform:'uppercase', letterSpacing:'0.14em',
    color:'var(--ink-4)',
    marginRight:4,
  },
  chip: {
    display:'inline-flex', alignItems:'center', gap:6,
    padding:'7px 12px',
    border:'1px solid var(--line-strong)',
    borderRadius:999,
    background:'rgba(255,255,255,0.82)',
    backdropFilter:'blur(6px)',
    color:'var(--ink-2)',
    font:'600 12px/1 var(--font-body)',
    cursor:'pointer',
    transition:'background 120ms var(--ease), color 120ms var(--ease), border-color 120ms var(--ease)',
  },
  chipActive: {
    background:'var(--ink)',
    color:'#fff',
    borderColor:'var(--ink)',
  },
  priceChip: {
    display:'inline-flex', alignItems:'center', gap:6,
    padding:'6px 10px',
    border:'1px solid var(--line)',
    borderRadius:2,
    background:'rgba(255,255,255,0.7)',
    font:'500 11px/1.3 var(--font-mono)',
    color:'var(--ink-2)',
  },

  bar: {
    display:'flex', alignItems:'center',
    background:'#FFFFFF',
    border:'1px solid var(--line-strong)',
    borderRadius:6,
    padding:'6px 6px 6px 18px',
    transition:'border-color 120ms var(--ease), box-shadow 120ms var(--ease)',
  },
  icon: { color:'var(--ink-3)', fontSize:18, marginRight:10 },
  input: {
    flex:1, border:0, outline:0, background:'transparent',
    padding:'16px 4px',
    font:'500 17px/1.3 var(--font-body)',
    color:'var(--ink)', letterSpacing:'-0.005em',
    minWidth:0,
  },
  kbd: {
    font:'500 11px/1 var(--font-mono)',
    padding:'5px 7px',
    border:'1px solid var(--line-strong)',
    borderRadius:3,
    background:'var(--paper-soft)',
    color:'var(--ink-3)',
    marginRight:8,
  },
  btn: {
    display:'inline-flex', alignItems:'center', gap:8,
    padding:'14px 22px',
    border:0, borderRadius:4,
    background:'var(--brand-700)', color:'#fff',
    font:'600 13px/1 var(--font-body)',
    letterSpacing:'0.02em',
    cursor:'pointer',
    transition:'background 120ms var(--ease)',
  },

  trials: {
    display:'flex', alignItems:'center', gap:10,
    marginTop:16, flexWrap:'wrap',
  },
  trialsLabel: {
    font:'600 11px/1 var(--font-body)',
    textTransform:'uppercase', letterSpacing:'0.14em',
    color:'var(--ink-4)',
  },
  trialChip: {
    padding:'5px 10px',
    background:'rgba(255,255,255,0.65)',
    border:'1px solid var(--line)',
    borderRadius:999,
    color:'var(--ink-2)',
    textDecoration:'none',
  },
};

window.LRHeroSearch = LRHeroSearch;
