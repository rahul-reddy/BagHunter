import {canonicalContext, emptyWorkspace, validateWorkspace, type ResearchWorkspace} from './researchEvidence';

export const initialThesisInputs = {revenue:'100000000',shares:'10000000',net_debt:'0',reference_price:'10',years:'3',dilution:'.02',growth:'.1',margin:'.15',multiple:'15'};
export type ThesisInputs = typeof initialThesisInputs;
export type ThesisNotes = {thesis:string; catalyst:string; breaker:string; bear:string; monitorDate:string};
export type ThesisContext = {mode:string; run_id:string; security_id:string; source_sha256s:string[]};
const keys = Object.keys(initialThesisInputs) as (keyof ThesisInputs)[];
export function parseThesisInputs(value: unknown): Record<keyof ThesisInputs,number> {
  const data = value as ThesisInputs | null;
  if (!data || Object.keys(data).length !== keys.length) throw new Error('Enter every scenario assumption explicitly.');
  const result = {} as Record<keyof ThesisInputs,number>;
  for (const key of keys) {
    const raw = data[key];
    if (typeof raw !== 'string' || raw.length > 100 || !/^[+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?$/i.test(raw) || !Number.isFinite(Number(raw))) throw new Error('Enter every scenario assumption explicitly; blanks are not zero.');
    result[key] = Number(raw);
  }
  const p = result;
  if (!(p.revenue > 0 && p.revenue <= 1e15 && p.shares >= 1 && p.shares <= 1e15 && Math.abs(p.net_debt) <= 1e15 && p.reference_price >= 1e-9 && p.reference_price <= 1e9 && Number.isInteger(p.years) && p.years >= 1 && p.years <= 10 && p.dilution >= 0 && p.dilution <= 1 && p.growth >= -.99 && p.growth <= 2 && Math.abs(p.margin) <= 1 && p.multiple >= 0 && p.multiple <= 200)) throw new Error('Scenario inputs are outside supported bounds.');
  return result;
}
export function validateThesisNotes(value: unknown): ThesisNotes {
  const data = value as ThesisNotes | null;
  const fields = ['thesis','catalyst','breaker','bear','monitorDate'] as const;
  if (!data || Object.keys(data).length !== fields.length || fields.some(key => typeof data[key] !== 'string' || data[key].length > 5000)) throw new Error('Invalid thesis notes.');
  if (data.monitorDate && (!/^\d{4}-\d{2}-\d{2}$/.test(data.monitorDate) || !Number.isFinite(Date.parse(data.monitorDate)) || new Date(data.monitorDate).toISOString().slice(0,10) !== data.monitorDate)) throw new Error('Invalid thesis review date.');
  return data;
}
export function restoreThesisDraft(value: unknown, context: ThesisContext, minimumClock: string): {inputs:ThesisInputs; notes:ThesisNotes; workspace:ResearchWorkspace; legacy:boolean} {
  const data = value as Record<string,unknown> | null;
  if (!data || typeof data !== 'object' || Array.isArray(data)) throw new Error('Invalid thesis draft.');
  if (data.schema === 'fixture-thesis-draft-v2') {
    if (canonicalContext(data.source_context) !== canonicalContext(context)) throw new Error('Draft belongs to another run or source.');
    parseThesisInputs(data.inputs);
    return {inputs:data.inputs as ThesisInputs, notes:validateThesisNotes(data.notes),workspace:validateWorkspace(data.research_workspace,minimumClock),legacy:false};
  }
  if (Object.hasOwn(data,'schema')) throw new Error('Unsupported thesis draft version.');
  const old = data.inputs as Record<string,unknown> | null;
  if (!old || Object.keys(old).length !== keys.length || keys.some(key => typeof old[key] !== 'number' || !Number.isFinite(old[key]))) throw new Error('Invalid legacy assumptions.');
  const inputs = Object.fromEntries(keys.map(key => [key,String(old[key])])) as ThesisInputs;
  parseThesisInputs(inputs);
  const notes = validateThesisNotes(Object.fromEntries(['thesis','catalyst','breaker','bear','monitorDate'].map(key => [key,data[key]])));
  return {inputs,notes,workspace:emptyWorkspace(new Date().toISOString()),legacy:true};
}
