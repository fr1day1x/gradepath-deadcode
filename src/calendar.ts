import type {Policy} from './policy';
export type CalendarEvent={id:string;title:string;description:string;start:string;end:string;allDay:boolean};
const compact=(value:string)=>value.replace(/[-:]/g,'').replace(/\.\d{3}/,'');
// iCalendar all-day DTEND is exclusive, including month/year boundaries.
export function tomorrow(day:string){const d=new Date(`${day}T12:00:00Z`);d.setUTCDate(d.getUTCDate()+1);return d.toISOString().slice(0,10)}
export function datedEvent(id:string,title:string,date:string):CalendarEvent{return {id,title,description:'Created with Gradepath. Review this event before saving. Calendar events do not record attendance.',start:date,end:tomorrow(date),allDay:true}}
export function deadlines(policy:Policy,courseId:number,today:string){return policy.categories.flatMap((c,i)=>c.items.flatMap((item,j)=>item.status==='pending'&&item.due_date&&item.due_date>=today?[datedEvent(`course-${courseId}-deadline-${i}-${j}`,`${policy.course_name}: ${item.name} due`,item.due_date)]:[]))}
export function timedEvent(id:string,title:string,local:string,minutes:number):CalendarEvent{
 const start=new Date(local);if(!Number.isFinite(start.getTime())||minutes<1||minutes>480)throw new Error('Choose a valid start time and duration.');
 return {id,title,description:'Study session planned in Gradepath. This does not change recorded scores.',start:start.toISOString(),end:new Date(start.getTime()+minutes*60000).toISOString(),allDay:false};
}
// Opening this URL prepares an event; Google still asks the student to save it.
export function googleLink(event:CalendarEvent){return 'https://calendar.google.com/calendar/render?'+new URLSearchParams({action:'TEMPLATE',text:event.title,dates:`${compact(event.start)}/${compact(event.end)}`,details:event.description}).toString()}
const escapeText=(s:string)=>s.replace(/\\/g,'\\\\').replace(/\r\n|\r|\n/g,'\\n').replace(/;/g,'\\;').replace(/,/g,'\\,');
// Fold at 75 UTF-8 octets without splitting a Unicode code point (RFC 5545).
function fold(line:string){let out='',size=0;for(const char of line){const bytes=new TextEncoder().encode(char).length;if(size+bytes>75){out+='\r\n ';size=1}out+=char;size+=bytes}return out}
export function calendarFile(events:CalendarEvent[],now=new Date()){
 const lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Gradepath//Student planner//EN','CALSCALE:GREGORIAN'];
 for(const e of events)lines.push('BEGIN:VEVENT',`UID:${e.id}@gradepath.local`,`DTSTAMP:${compact(now.toISOString())}`,`DTSTART${e.allDay?';VALUE=DATE':''}:${compact(e.start)}`,`DTEND${e.allDay?';VALUE=DATE':''}:${compact(e.end)}`,`SUMMARY:${escapeText(e.title)}`,`DESCRIPTION:${escapeText(e.description)}`,'END:VEVENT');
 return [...lines,'END:VCALENDAR'].map(fold).join('\r\n')+'\r\n';
}
export function downloadCalendar(events:CalendarEvent[],name:string){const url=URL.createObjectURL(new Blob([calendarFile(events)],{type:'text/calendar;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
