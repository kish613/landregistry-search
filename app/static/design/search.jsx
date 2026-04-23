/* global React */

// Mock suggestion data
const MOCK_SUGGESTIONS = {
  company: [
    { name: 'Barratt Developments PLC',  no: '00604574', titles: 2418 },
    { name: 'Barratt Homes Limited',     no: '00606411', titles:  184 },
    { name: 'Barratt London Limited',    no: '04944391', titles:  312 },
    { name: 'Barratt Bristol Limited',   no: '08473922', titles:   46 },
  ],
  address: [
    { name: 'SW7 2AX — Kensington Gore, London', no: 'Postcode', titles: 14 },
    { name: '12 Kensington Gore, London',        no: 'NGL-123456', titles: 1 },
    { name: 'Royal Albert Hall, Kensington Gore',no: 'NGL-445112', titles: 1 },
  ],
  director: [
    { name: 'Jonathan M. Smith',   no: 'DIR-09188471', titles: 12 },
    { name: 'Jonathan P. Smith',   no: 'DIR-02471099', titles:  4 },
    { name: 'Jon M. Smith',        no: 'DIR-10099182', titles:  1 },
  ],
};

function LRSearch({ densityMode = 'roomy' }) {
  const [mode, setMode] = React.useState('company');
  const [val,  setVal]  = React.useState('');
  const [focus,setFocus]= React.useState(false);

  const modes = [
    { k:'company',  label:'Company',  icon:'ph-buildings',
      placeholder:'e.g. Barratt Developments PLC  —  or  00604574',
      eyebrow:'Company name or registration number',
      price:'£1.00 per title search' },
    { k:'address',  label:'Address',  icon:'ph-map-pin',
      placeholder:'e.g. SW7 2AX  —  or  12 Kensington Gore',
      eyebrow:'Address or postcode — reverse lookup',
      price:'£1.00 per title search' },
    { k:'director', label:'Director', icon:'ph-user',
      placeholder:'e.g. Jonathan M. Smith',
      eyebrow:'Director or linked person',
      price:'£3.00 · premium tier' },
  ];
  const m = modes.find(x=>x.k===mode);

  // Live-filtered suggestions
  const suggestions = React.useMemo(() => {
    const pool = MOCK_SUGGESTIONS[mode] || [];
    if (!val.trim()) return pool.slice(0, 3);
    const v = val.toLowerCase();
    return pool.filter(s => s.name.toLowerCase().includes(v) || s.no.toLowerCase().includes(v));
  }, [mode, val]);

  const showSuggest = focus && val.length > 0;

  return (
    <div style={{...lrSearchStyles.panel, padding: densityMode==='compact' ? '16px 18px 14px' : '22px 22px 18px'}}>
      {/* tab row */}
      <div style={lrSearchStyles.tabs}>
        {modes.map(x => (
          <button
            key={x.k}
            onClick={()=>setMode(x.k)}
            style={{...lrSearchStyles.tab, ...(mode===x.k?lrSearchStyles.tabActive:{})}}
          >
            <i className={`ph ${x.icon}`} style={{fontSize:14}}></i>
            {x.label}
            {mode===x.k && <span style={lrSearchStyles.tabMark}/>}
          </button>
        ))}
        <span style={{flex:1}}/>
        <span style={lrSearchStyles.priceTag}>
          <i className="ph-fill ph-seal-check" style={{color:'var(--gold-500)', fontSize:13}}></i>
          {m.price}
        </span>
      </div>

      <div style={lrSearchStyles.eyebrow}>{m.eyebrow}</div>

      {/* Input + submit */}
      <form
        onSubmit={(e)=>{ e.preventDefault(); }}
        style={lrSearchStyles.row}
      >
        <div style={{
          ...lrSearchStyles.field,
          borderColor: focus ? 'var(--brand-700)' : 'var(--line-strong)',
          boxShadow: focus
            ? '0 0 0 3px rgba(31,81,48,0.12), inset 0 1px 0 rgba(15,20,12,0.04)'
            : 'var(--shadow-inset)',
        }}>
          <i className="ph ph-magnifying-glass" style={lrSearchStyles.fieldIcon}></i>
          <input
            style={lrSearchStyles.input}
            placeholder={m.placeholder}
            value={val}
            onChange={e=>setVal(e.target.value)}
            onFocus={()=>setFocus(true)}
            onBlur={()=>setTimeout(()=>setFocus(false), 150)}
            autoComplete="off"
          />
          {mode==='company' && (
            <span style={lrSearchStyles.suffix}>
              <span style={lrSearchStyles.kbd}>⌘K</span>
              <span style={lrSearchStyles.suffixLabel}>fuzzy match</span>
            </span>
          )}
        </div>

        <button type="submit" style={lrSearchStyles.btn}>
          Search the register
          <i className="ph ph-arrow-right" style={{fontSize:14}}></i>
        </button>
      </form>

      {/* Suggestions dropdown */}
      {showSuggest && suggestions.length > 0 && (
        <div style={lrSearchStyles.suggest}>
          <div style={lrSearchStyles.suggestHead}>
            <span>Matches</span>
            <span>{suggestions.length} suggestion{suggestions.length===1?'':'s'}</span>
          </div>
          {suggestions.map((s, i) => (
            <button
              key={i}
              type="button"
              onMouseDown={(e)=>{ e.preventDefault(); setVal(s.name); }}
              style={lrSearchStyles.suggestRow}
              className="lr-suggest-row"
            >
              <div style={lrSearchStyles.suggestBody}>
                <div style={lrSearchStyles.suggestName}>{s.name}</div>
                <div style={lrSearchStyles.suggestMeta}>
                  <span className="mono" style={{color:'var(--ink-3)'}}>{s.no}</span>
                  <span style={lrSearchStyles.dot}/>
                  <span>
                    <span className="tabular" style={{color:'var(--ink)', fontWeight:500}}>
                      {s.titles.toLocaleString()}
                    </span>{' '}
                    <span style={{color:'var(--ink-3)'}}>titles</span>
                  </span>
                </div>
              </div>
              <i className="ph ph-arrow-up-right" style={{color:'var(--ink-4)',fontSize:14}}></i>
            </button>
          ))}
        </div>
      )}

      {/* Footer */}
      <div style={lrSearchStyles.foot}>
        <span>
          <i className="ph ph-database" style={{marginRight:6, verticalAlign:-2}}></i>
          HM Land Registry · CCOD
        </span>
        <span style={lrSearchStyles.pipe}/>
        <span>Last refresh: <span className="tabular">3 April 2026</span></span>
        <span style={lrSearchStyles.pipe}/>
        <span>Median query: <span className="tabular">180&nbsp;ms</span></span>
        <span style={lrSearchStyles.pipe}/>
        <span><a href="#" style={{color:'var(--brand-700)', fontWeight:500}}>10 free searches for new accounts</a></span>
      </div>
    </div>
  );
}

const lrSearchStyles = {
  panel: {
    background:'#FFFFFF',
    border:'1px solid var(--line-strong)',
    borderRadius:6,
    boxShadow:'0 1px 0 rgba(15,20,12,0.04), 0 8px 24px rgba(15,20,12,0.08)',
    position:'relative',
  },
  tabs: { display:'flex', alignItems:'center', gap:4, marginBottom:14 },
  tab: {
    position:'relative',
    display:'inline-flex', alignItems:'center', gap:6,
    padding:'8px 14px',
    border:0, borderRadius:4, background:'transparent',
    color:'var(--ink-3)',
    font:'600 12px/1 var(--font-body)',
    cursor:'pointer',
    transition:'color 120ms var(--ease), background 120ms var(--ease)',
  },
  tabActive: { color:'var(--ink)' },
  tabMark: {
    position:'absolute', left:10, right:10, bottom:-4, height:2,
    background:'var(--brand-700)',
  },
  priceTag: {
    display:'inline-flex', alignItems:'center', gap:6,
    padding:'4px 10px',
    background:'var(--paper-soft)',
    border:'1px solid var(--line)',
    borderRadius:2,
    font:'500 11px/1.3 var(--font-mono)',
    color:'var(--ink-2)',
  },
  eyebrow: {
    font:'600 11px/1.3 var(--font-body)',
    textTransform:'uppercase', letterSpacing:'0.14em',
    color:'var(--ink-3)', marginBottom:6,
    paddingTop:12, borderTop:'1px solid var(--line)',
  },
  row: { display:'flex', gap:8 },
  field: {
    flex:1, display:'flex', alignItems:'center',
    background:'var(--paper-soft)',
    border:'1px solid var(--line-strong)',
    borderRadius:4, padding:'0 12px',
    transition:'border-color 120ms var(--ease), box-shadow 120ms var(--ease)',
  },
  fieldIcon: { color:'var(--ink-3)', fontSize:16 },
  input: {
    flex:1, border:0, outline:0, background:'transparent',
    padding:'14px 10px',
    font:'500 16px/1.4 var(--font-body)', color:'var(--ink)',
    letterSpacing:'-0.005em',
  },
  suffix: { display:'inline-flex', alignItems:'center', gap:8, color:'var(--ink-4)' },
  suffixLabel: { font:'var(--t-mono-sm)' },
  kbd: {
    font:'500 10px/1 var(--font-mono)',
    padding:'4px 6px',
    border:'1px solid var(--line-strong)',
    borderRadius:3,
    background:'#fff', color:'var(--ink-3)',
    boxShadow:'0 1px 0 rgba(15,20,12,0.06)',
  },
  btn: {
    display:'inline-flex', alignItems:'center', gap:10,
    padding:'0 22px',
    border:0, borderRadius:4,
    background:'var(--brand-700)', color:'#fff',
    font:'600 13px/1 var(--font-body)',
    letterSpacing:'0.02em',
    cursor:'pointer',
    transition:'background 120ms var(--ease)',
  },
  suggest: {
    position:'absolute', left:-1, right:-1, top:'calc(100% - 56px)',
    marginTop:8,
    background:'#fff',
    border:'1px solid var(--line-strong)',
    borderRadius:4,
    boxShadow:'var(--shadow-3)',
    padding:'6px 0',
    zIndex:10,
  },
  suggestHead: {
    display:'flex', justifyContent:'space-between',
    padding:'6px 14px 8px',
    borderBottom:'1px solid var(--line)',
    font:'600 10px/1.3 var(--font-body)',
    textTransform:'uppercase', letterSpacing:'0.14em',
    color:'var(--ink-4)',
  },
  suggestRow: {
    width:'100%',
    display:'flex', alignItems:'center', justifyContent:'space-between',
    padding:'10px 14px', gap:12,
    border:0, background:'transparent',
    textAlign:'left', cursor:'pointer',
    transition:'background 120ms var(--ease)',
  },
  suggestBody: { display:'flex', flexDirection:'column', gap:2 },
  suggestName: { font:'500 14px/1.3 var(--font-body)', color:'var(--ink)' },
  suggestMeta: {
    display:'flex', alignItems:'center', gap:10,
    font:'var(--t-body-sm)', color:'var(--ink-3)',
  },
  dot: { width:3, height:3, borderRadius:'50%', background:'var(--ink-5)' },
  foot: {
    marginTop:14, paddingTop:12,
    borderTop:'1px solid var(--line)',
    display:'flex', alignItems:'center', gap:10,
    font:'var(--t-body-sm)', color:'var(--ink-3)',
    flexWrap:'wrap',
  },
  pipe: { width:1, height:11, background:'var(--line-strong)' },
};

window.LRSearch = LRSearch;
