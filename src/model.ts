export type Category = { id: string; name: string; weight: number; scores: number[]; color: string; bonus?: boolean };
export type Course = { id: string; name: string; code: string; categories: Category[] };
export type Scenario = { course: Course; finalScore: number; target: number; replaceLowest: boolean; dropLowest: boolean };
export type Projection = { curve?: {score:number;grade:number}[]; source?: string; current: number; projected: number; required: number | null; contributions: { name: string; average: number; contribution: number }[] };
// Sample data is for the guest workspace only; signed-in courses come from the account API.
export const courses: Course[] = [
 { id: 'cs', name: 'Data Structures', code: 'CS 241', categories: [
  { id: 'homework', name: 'Assignments', weight: 25, scores: [94, 88, 96, 92, 85], color: '#753347' },
  { id: 'quiz', name: 'Quizzes', weight: 15, scores: [85, 90, 78, 95], color: '#b87687' },
  { id: 'exam', name: 'Midterms', weight: 30, scores: [76, 88], color: '#9d6a71' },
  { id: 'final', name: 'Final exam', weight: 30, scores: [], color: '#c5a080' } ] },
 { id: 'math', name: 'Linear Algebra', code: 'MATH 220', categories: [
  { id: 'homework', name: 'Assignments', weight: 25, scores: [95, 98, 92], color: '#753347' },
  { id: 'quiz', name: 'Quizzes', weight: 15, scores: [90, 94, 88], color: '#b87687' },
  { id: 'exam', name: 'Midterms', weight: 30, scores: [85, 91], color: '#9d6a71' },
  { id: 'final', name: 'Final exam', weight: 30, scores: [], color: '#c5a080' } ] }
];
export const letter = (n: number) => n >= 90 ? 'A' : n >= 80 ? 'B' : n >= 70 ? 'C' : n >= 60 ? 'D' : 'F';
const mean = (a: number[]) => a.reduce((s, n) => s + n, 0) / (a.length || 1);
export const scoreMaximum=(category:Category)=>category.bonus&&['homework','exam','final'].includes(category.id)?199.99:100;
export function calculate(s: Scenario): Projection {
 const finalMax=scoreMaximum(s.course.categories.find(c=>c.id==='final')!);
 if(!Number.isFinite(s.finalScore)||s.finalScore<0||s.finalScore>finalMax)throw new Error('Final score is outside the allowed range.');
 for(const c of s.course.categories){if(!Number.isFinite(c.weight)||c.weight<0||c.weight>100||c.scores.some(n=>!Number.isFinite(n)||n<0||n>scoreMaximum(c)))throw new Error('Scores and weights must be within their allowed ranges.');}
 const total = s.course.categories.reduce((n,c)=>n+c.weight,0);
 if (Math.abs(total-100) > .01) throw new Error('Category weights must total 100%.');
 const contributionsAt = (final: number) => s.course.categories.map(c => {
  let scores = [...c.scores];
  if(c.id === 'quiz' && s.dropLowest && scores.length > 1) scores.splice(scores.indexOf(Math.min(...scores)),1);
  if(c.id === 'exam' && s.replaceLowest && scores.length) { const i=scores.indexOf(Math.min(...scores)); scores[i]=Math.max(scores[i],final); }
  const average = c.id === 'final' ? final : mean(scores);
  return { name:c.name, average, contribution: average*c.weight/100 };
 });
 const gradeAt = (f:number) => contributionsAt(f).reduce((n,c)=>n+c.contribution,0);
 const completed = s.course.categories.filter(c=>c.id !== 'final');
 const completedWeight = completed.reduce((n,c)=>n+c.weight,0);
 const current = completedWeight ? completed.reduce((n,c)=>n+mean(c.scores)*c.weight,0)/completedWeight : 0;
 let required: number|null = null;
 for(let f=0; f<=Math.ceil(finalMax*10); f++) if(gradeAt(Math.min(finalMax,f/10))>=s.target) {required=Math.min(finalMax,f/10);break;}
 return {current, projected:gradeAt(s.finalScore), required, contributions:contributionsAt(s.finalScore)};
}
