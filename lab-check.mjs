import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
const browser=await chromium.launch({channel:'chrome'});
try{
 const page=await browser.newPage({baseURL:'http://127.0.0.1:5001',viewport:{width:1440,height:1000}});
 page.setDefaultTimeout(15000);
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const session=await(await page.request.get('/api/auth/session')).json();
 const user=await(await page.request.post('/api/auth/register',{headers:{'X-CSRF-Token':session.csrfToken},data:{name:'Lab QA',email:`lab-${Date.now()}@example.com`,password:'testing-only-pass'}})).json();
 const sample=await(await page.request.get('/api/sample')).json();
 const policy=sample.policy||sample;
 const created=await(await page.request.post('/api/auth/policies',{headers:{'X-CSRF-Token':user.csrfToken},data:{name:'Contest sample',policy}})).json();assert.ok(created.id);
 await page.goto('/');await page.getByRole('heading',{name:'The what-if lab',exact:true}).waitFor();
 await page.getByLabel('Hypothetical final score',{exact:true}).fill('95');
 await page.locator('.lab-result>strong').filter({hasText:'93.10%'}).waitFor();
 await page.getByRole('img',{name:/Projected grade by final exam score/}).waitFor();
 await page.getByRole('button',{name:'Save scenario snapshot',exact:true}).click();
 await page.getByRole('checkbox',{name:'Use final replacement',exact:true}).uncheck();
 await page.locator('.lab-result>strong').filter({hasText:'89.70%'}).waitFor();
 await page.getByRole('button',{name:'Calendar',exact:true}).click();await page.getByRole('button',{name:'Overview',exact:true}).click();
 await page.getByRole('button',{name:/Restore final 95/}).click();await page.locator('.lab-result>strong').filter({hasText:'93.10%'}).waitFor();
 await page.getByLabel('Target grade',{exact:true}).selectOption('B');
 const download=page.waitForEvent('download');await page.getByRole('button',{name:'Export scenario',exact:true}).click();assert.equal((await download).suggestedFilename(),'gradepath-scenario.json');
 const record=await(await page.request.get(`/api/auth/policies/${created.id}`)).json();assert.equal(record.history.length,1);assert.deepEqual(record.policy,policy);
 await page.screenshot({path:'space-account-lab-desktop.png'});
 await page.setViewportSize({width:390,height:844});await page.locator('.account-lab').scrollIntoViewIfNeeded();assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:'space-account-lab-mobile.png'});
 await page.getByRole('button',{name:'Gradebook',exact:true}).click();await page.getByRole('dialog').waitFor();await page.getByRole('button',{name:'Close policy editor',exact:true}).click();
 assert.deepEqual(errors,[]);console.log('PASS: saved-policy graph, exact replacement comparison, target selection, snapshots across tabs, export, unchanged records, mobile fit and gradebook access');
}finally{await browser.close()}
