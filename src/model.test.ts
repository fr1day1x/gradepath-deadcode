import { describe, expect, it } from 'vitest';
import { calculate, courses } from './model';
const scenario={course:courses[0], finalScore:85, target:90,replaceLowest:true,dropLowest:true};
describe('demo projection',()=>{
 it('weights the grade and applies both course rules',()=>{const r=calculate(scenario);expect(r.projected).toBeCloseTo(87.7,2);expect(r.current).toBeCloseTo(86.2857142857);});
 it('never replaces a better midterm with a lower final',()=>{const s={...scenario,finalScore:50,dropLowest:false};expect(calculate(s).projected).toEqual(calculate({...s,replaceLowest:false}).projected)});
 it('drops exactly one lowest quiz',()=>{const a=calculate(scenario),b=calculate({...scenario,dropLowest:false});expect(a.projected-b.projected).toBeCloseTo(.45)});
 it('finds the minimum final to reach the target',()=>{const r=calculate(scenario);expect(r.required).not.toBeNull();expect(calculate({...scenario,finalScore:r.required!}).projected).toBeGreaterThanOrEqual(90);expect(calculate({...scenario,finalScore:r.required!-.1}).projected).toBeLessThan(90)});
 it('reports unreachable targets',()=>{const course={...courses[0],categories:courses[0].categories.map(c=>({...c,scores:c.scores.map(()=>0)}))};expect(calculate({...scenario,course,replaceLowest:false}).required).toBeNull()});
 it('rejects invalid weight totals',()=>{expect(()=>calculate({...scenario,course:{...courses[0],categories:courses[0].categories.map(c=>({...c,weight:10}))}})).toThrow('100%')});
});
