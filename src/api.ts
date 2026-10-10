import { calculate, scoreMaximum, type Scenario, type Projection } from './model';
const base = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');
export const isDemo = import.meta.env.VITE_DEMO_MODE === 'true';
export async function getProjection(scenario: Scenario, signal?: AbortSignal): Promise<Projection> {
 if (isDemo) return calculate(scenario);
 const response = await fetch(`${base}/predict`, {method:'POST', credentials:'include', headers:{'Content-Type':'application/json'}, body:JSON.stringify(scenario), signal});
 if (!response.ok) { const body = await response.json().catch(()=>null); throw new Error(body?.error || `Grade service unavailable (${response.status}). Start the Python backend and try again.`); }
 const data = await response.json();
 if (!Number.isFinite(data.current) || !Number.isFinite(data.projected) || !(data.required === null || Number.isFinite(data.required)) || !Array.isArray(data.contributions) || !data.contributions.every((c: Record<string, unknown>)=>typeof c.name==='string' && Number.isFinite(c.average) && Number.isFinite(c.contribution))) throw new Error('The prediction service returned an invalid result.');
 const max=scoreMaximum(scenario.course.categories.find(c=>c.id==='final')!);
 if (!Array.isArray(data.curve) || data.curve.length!==21 || !data.curve.every((p: Record<string,unknown>,i:number)=>Math.abs(Number(p.score)-i*max/20)<.001 && Number.isFinite(p.grade))) throw new Error('The prediction service returned an invalid chart.');
 return data;
}
