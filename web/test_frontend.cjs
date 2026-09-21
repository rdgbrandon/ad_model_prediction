// Execute the actual frontend with a minimal DOM and the live local API.
// This tests rendering logic and interactions; it is not a browser layout test.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const elements=new Map();
class Element{constructor(id){this.id=id;this.value='';this.innerHTML='';this.textContent='';this.listeners={};this.dataset={};}
 addEventListener(event,fn){this.listeners[event]=fn;}
 replaceChildren(...children){this.children=children;this.value=children[0]?.value||'';}}
for(const [,id] of fs.readFileSync(__dirname+'/index.html','utf8').matchAll(/id="([^"]+)"/g))elements.set(id,new Element(id));
elements.get('ceiling').value='192';elements.get('model').value='mlp8';elements.get('seed').value='0';elements.get('radius-slider').value='100';
const buttons=['audit','rebuild','full'].map(kind=>{const e=new Element(kind);e.dataset.run=kind;return e;});
const context=vm.createContext({document:{getElementById:id=>elements.get(id),createElement:()=>new Element(),querySelectorAll:()=>buttons},
 fetch:(path,options)=>fetch('http://127.0.0.1:8765'+path,options),setInterval:()=>0,console});
vm.runInContext(fs.readFileSync(__dirname+'/app.js','utf8'),context);
(async()=>{
 await vm.runInContext('load()',context);
 const snap=await (await fetch('http://127.0.0.1:8765/data/snapshot.json')).json();
 const head=snap.consensus.summary['canonical_192|mlp8|0'];
 assert.equal(elements.get('metric-score').textContent,(head.mean_S_over_e*100).toFixed(2)+'%');
 assert.equal(elements.get('metric-old').textContent,(head.baseline_mean_S_over_e*100).toFixed(2)+'%');
 // The caveats must be filled from the data, never left as placeholders.
 for(const id of ['blend-note','subset-note','premise-note','margin-note','latest-finding']){
   const v=elements.get(id).textContent;assert(v&&v!=='—',`${id} not populated`);assert(!v.includes('NaN'),`${id} has NaN`);}
 assert.match(elements.get('subset-note').textContent,/exactly 1 eligible group/);
 // Combining candidates can never lower the score: the single rule is one of them.
 for(const row of snap.consensus.rows){assert(row.S>=row.baseline_S-1e-8);assert(row.S>=row.best_single_S-1e-8);}
 for(const ceiling of ['146','192'])for(const model of ['mlp8','mlp16x16','linear'])for(const seed of ['0','1','2']){
   elements.get('ceiling').value=ceiling;elements.get('model').value=model;elements.get('seed').value=seed;
   vm.runInContext('update()',context);
   for(const child of elements.get('trial').children){elements.get('trial').value=child.value;vm.runInContext('render()',context);
     for(const id of ['comparison','spectrum','geometry','corpus-chart']){assert.match(elements.get(id).innerHTML,/<svg/);assert(!elements.get(id).innerHTML.includes('NaN'));}
     assert(Number(elements.get('score').textContent)<=Number(elements.get('error-value').textContent)+.011);
   }
 }
 elements.get('ceiling').value='146';vm.runInContext('update()',context);
 assert.match(elements.get('model-results').innerHTML,/only one group/);
 elements.get('ceiling').value='192';vm.runInContext('update()',context);
 assert.match(elements.get('model-results').innerHTML,/pts/);
 for(const scale of ['0','100','300']){elements.get('radius-slider').value=scale;vm.runInContext('geometry()',context);assert(!elements.get('geometry').innerHTML.includes('NaN'));}
 console.log('Frontend data rendering, all model/ceiling/seed/trial selections, and radius slider passed.');
})().catch(e=>{console.error(e);process.exitCode=1;});
