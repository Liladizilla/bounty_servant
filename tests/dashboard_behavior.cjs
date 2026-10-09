const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const html = fs.readFileSync(path.join(__dirname, '..', 'docs', 'index.html'), 'utf8');
const match = html.match(/<script>([\s\S]*?)<\/script>/);
assert.ok(match, 'dashboard script exists');
const ids = ['connection','updated','refresh','export','loadError','total','verified','review','paid','trackedFoot','trend','scores','opportunities','showing','search','verificationFilter','statusFilter','opportunityRows','paginationSummary','loadMore','pipelineSummary','runCount','runSummary'];
const elements = new Map();
function element(id) {
  if (elements.has(id)) return elements.get(id);
  const listeners = {};
  const classes = new Set();
  const el = {id, value: id === 'verificationFilter' || id === 'statusFilter' ? 'all' : '', innerHTML:'', textContent:'', disabled:false, listeners, style:{},
    addEventListener(type, fn) { listeners[type] = fn; },
    click() { return listeners.click ? listeners.click() : undefined; },
    remove() {},
    classList: {add(c){classes.add(c);}, remove(c){classes.delete(c);}, toggle(c, force){const on=force===undefined?!classes.has(c):!!force; if(on)classes.add(c);else classes.delete(c);return on;}, contains(c){return classes.has(c);}}
  };
  elements.set(id, el); return el;
}
ids.forEach(element);
let ledgerRequests = 0;
const opportunities = {};
for (let i=0;i<35;i++) {
  const key = `issue-${i}`;
  opportunities[key] = {title:i===0?'=1+1':i===1?'NeedleUnique':`Issue ${i}`, repository:`org/repo-${i}`, issue_url:`https://github.com/org/repo/issues/${i}`, last_score:100-i, last_reward_evidence:'$50', verification:i%2===0?'verified_paid_candidate':'needs_manual_review', status:i===0?'accepted':i===1?'discovered':'investigating', first_seen:'2026-10-09', last_seen:'2026-10-09', pr_url:''};
}
const ledger = {updated_at:'2026-10-09T19:00:00Z', opportunities};
const history = {snapshots:[{date:'2026-10-09',tracked_opportunities:35,verification_counts:{verified_paid_candidate:18}}]};
const fakeFetch = async url => {
  if (String(url).includes('ledger.json')) { ledgerRequests++; return {ok:true,json:async()=>ledger}; }
  if (String(url).includes('metrics-history.json')) return {ok:true,json:async()=>history};
  if (String(url).includes('/actions/runs')) return {ok:true,json:async()=>({workflow_runs:[]})};
  throw new Error(`Unexpected fetch: ${url}`);
};
let downloaded = null;
class FakeBlob { constructor(parts, options){this.parts=parts;this.options=options;} }
const document = {getElementById:element, createElement:tag=>({tag,click(){if(tag==='a') downloaded=this;},remove(){}}), body:{appendChild(){}}};
const context = {document, fetch:fakeFetch, Blob:FakeBlob, URL:{createObjectURL:blob=>{context.URL.lastBlob=blob;return 'blob:test';}, revokeObjectURL(){}}, console, Intl};
vm.runInNewContext(match[1], context, {filename:'docs/index.html'});
const flush = async () => { for(let i=0;i<12;i++) await Promise.resolve(); await new Promise(resolve=>setImmediate(resolve)); };
(async()=>{
  await flush();
  assert.equal(element('total').textContent, '35', 'ledger loads into the dashboard');
  assert.ok(element('trend').innerHTML.includes('Oct 9'), 'snapshot keeps its calendar date in the chart');
  assert.ok(!element('trend').innerHTML.includes('Oct 8'), 'snapshot date is not shifted in western timezones');
  assert.equal((element('opportunityRows').innerHTML.match(/<tr>/g)||[]).length, 30, 'initial page renders 30 rows');
  assert.equal(element('paginationSummary').textContent, 'Showing 30 of 35 matches');
  await element('loadMore').click();
  assert.equal((element('opportunityRows').innerHTML.match(/<tr>/g)||[]).length, 35, 'load more reveals remaining rows');
  element('search').value='NeedleUnique'; element('search').listeners.input();
  assert.match(element('opportunityRows').innerHTML, /NeedleUnique/, 'search returns matching row');
  assert.doesNotMatch(element('opportunityRows').innerHTML, /Issue 2</, 'search hides non-matching rows');
  element('search').value=''; element('search').listeners.input();
  element('verificationFilter').value='verified_paid_candidate'; element('verificationFilter').listeners.change();
  assert.match(element('opportunityRows').innerHTML, /Issue 2|=1\+1/, 'verification filter keeps verified rows');
  assert.doesNotMatch(element('opportunityRows').innerHTML, /NeedleUnique/, 'verification filter excludes manual-review rows');
  element('verificationFilter').value='all'; element('verificationFilter').listeners.change();
  const before=ledgerRequests; await element('refresh').click(); await flush();
  assert.ok(ledgerRequests>before, 'refresh makes another ledger request');
  await element('export').click();
  assert.ok(downloaded, 'export triggers a download');
  assert.equal(downloaded.href, 'blob:test', 'download uses generated CSV blob URL');
  const csv=context.URL.lastBlob.parts.join('');
  assert.ok(csv.includes("'=1+1"), 'formula-leading issue title is neutralized in CSV');
  console.log(`dashboard behavior checks passed in ${process.env.TZ || 'default timezone'}`);
})().catch(error=>{console.error(error);process.exitCode=1;});
