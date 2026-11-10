import type {Signal} from './main';

export const emptyRadarFilters = {return_1d:'',return_5d:'',return_21d:'',return_63d:'',relative_volume:'',revenue_growth:'',operating_margin:'',completeness:'',risk_flag:'ANY'};
export type RadarFilters = typeof emptyRadarFilters;
export type RadarSort = 'score'|'return_1d'|'return_5d'|'return_21d'|'return_63d'|'relative_volume'|'dollar_volume_20d'|'completeness'|'revenue_growth'|'operating_margin';
type NumericKey = Exclude<keyof RadarFilters,'risk_flag'>;
const definitions:Record<NumericKey,{label:string;scale:number;min:number;max:number}> = {
  return_1d:{label:'Minimum 1D return (%)',scale:100,min:-100,max:1e6},
  return_5d:{label:'Minimum 1W return (%)',scale:100,min:-100,max:1e6},
  return_21d:{label:'Minimum 1M return (%)',scale:100,min:-100,max:1e6},
  return_63d:{label:'Minimum 3M return (%)',scale:100,min:-100,max:1e6},
  relative_volume:{label:'Minimum relative volume',scale:1,min:0,max:1e6},
  revenue_growth:{label:'Minimum reported revenue growth (%)',scale:100,min:-1e6,max:1e6},
  operating_margin:{label:'Minimum reported operating margin (%)',scale:100,min:-1e6,max:1e6},
  completeness:{label:'Minimum factor coverage (%)',scale:100,min:0,max:100},
};
const numericKeys = Object.keys(definitions) as NumericKey[];
const value = (signal:Signal,key:RadarSort) => key === 'revenue_growth' || key === 'operating_margin' ? signal.financials?.[key] : signal[key];

export function parseRadarFilters(filters:RadarFilters):Partial<Record<NumericKey,number>> {
  const parsed:Partial<Record<NumericKey,number>>={};
  for(const key of numericKeys) {
    const raw=filters[key], rule=definitions[key];
    if(raw==='') continue;
    if(raw.length>100 || !/^[+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?$/i.test(raw) || !Number.isFinite(Number(raw)) || Number(raw)<rule.min || Number(raw)>rule.max) throw new Error(`${rule.label}: enter a finite value from ${rule.min} to ${rule.max}, or leave blank.`);
    parsed[key]=Number(raw)/rule.scale;
  }
  return parsed;
}

export function matchesRadar(signal:Signal,filters:RadarFilters):boolean {
  const parsed=parseRadarFilters(filters);
  if(Object.entries(parsed).some(([key,minimum]) => {const actual=value(signal,key as NumericKey);return typeof actual!=='number' || !Number.isFinite(actual) || actual<minimum;})) return false;
  if(filters.risk_flag==='NONE') return Array.isArray(signal.risk_flags) && signal.risk_flags.length===0;
  return filters.risk_flag==='ANY' || (Array.isArray(signal.risk_flags) && signal.risk_flags.includes(filters.risk_flag));
}

export function compareRadar(left:Signal,right:Signal,key:RadarSort):number {
  const a=value(left,key), b=value(right,key), knownA=typeof a==='number' && Number.isFinite(a), knownB=typeof b==='number' && Number.isFinite(b);
  if(knownA && knownB && a!==b) return b-a;
  if(knownA!==knownB) return knownA ? -1 : 1;
  return left.security_id<right.security_id ? -1 : left.security_id>right.security_id ? 1 : 0;
}

export function RadarFilterControls({filters,onChange,signals}:{filters:RadarFilters;onChange:(next:RadarFilters)=>void;signals:Signal[]}) {
  const input = (key:NumericKey) => <label key={key}>{definitions[key].label}<input inputMode="decimal" value={filters[key]} maxLength={100} onChange={e=>onChange({...filters,[key]:e.target.value})}/></label>;
  const active=numericKeys.filter(key=>filters[key]!=='').length+(filters.risk_flag==='ANY'?0:1);
  return <><div className="filters">{input('return_63d')}{input('relative_volume')}<button className="secondary" onClick={()=>onChange({...emptyRadarFilters})}>Reset research thresholds</button></div><details className="radar-filters"><summary>Additional horizon, financial, risk and coverage filters · {active} active thresholds</summary><div className="filters">{numericKeys.filter(key=>!['return_63d','relative_volume'].includes(key)).map(input)}<label>Required risk flag<select aria-label="Required risk flag" value={filters.risk_flag} onChange={e=>onChange({...filters,risk_flag:e.target.value})}><option value="ANY">Any recorded risk status</option><option value="NONE">No recorded flags (unknown excluded)</option>{[...new Set(signals.flatMap(signal=>signal.risk_flags ?? []))].sort().map(flag=><option key={flag}>{flag}</option>)}</select></label></div><p>Blank thresholds are disabled; zero is an explicit threshold. A required financial value or risk status that is missing stays excluded. These display filters do not change the saved run, stage rules, strategy policy or backtest.</p></details></>;
}
