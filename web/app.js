'use strict';
const $=id=>document.getElementById(id);
let data,selectedRows=[],selected,lastJob=null,polling=false;
const modelName={mlp8:'Small neural network',mlp16x16:'Larger neural network',linear:'Straight-line model'};
function combined(r){return data.consensus.rows.find(x=>x.config===r.config&&x.model===r.model&&x.seed===r.seed&&x.trial===r.trial);}
const C={old:'#a2acaa',labelled:'#b8c88c',new:'#087f75',pred:'#ce703e',truth:'#173335',grid:'#e1e5dc'};
const f=(x,n=2)=>Number(x).toFixed(n);
const pct=x=>`${f(x*100,1)}%`;
const norm=v=>Math.sqrt(v.reduce((s,x)=>s+x*x,0));
function svg(content,w=460,h=245){return `<svg viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg">${content}</svg>`;}
function line(x1,y1,x2,y2,color=C.grid,dash=''){return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${color}" ${dash?'stroke-dasharray="'+dash+'"':''}/>`;}
function text(x,y,value,anchor='start',extra=''){return `<text x="${x}" y="${y}" text-anchor="${anchor}" ${extra}>${value}</text>`;}
function showError(message){$('error').textContent=message;$('error').hidden=!message;}
async function request(url,options){const res=await fetch(url,options);if(!res.ok){let msg=`Request failed (${res.status})`;try{msg=(await res.json()).error||msg;}catch{}throw new Error(msg);}return res.json();}
async function load(){data=await request('/data/snapshot.json');$('freshness').textContent='Published '+new Date(data.generated_at).toLocaleString();
 const s=data.consensus.summary['canonical_192|mlp8|0'];$('metric-score').textContent=f(s.mean_S_over_e*100,2)+'%';$('metric-old').textContent=f(s.baseline_mean_S_over_e*100,2)+'%';$('metric-cover').textContent=`${s.all_configurations_covered_trials} / ${s.unique_test_trials}`;
 const linear=data.consensus.summary['canonical_192|linear|0'];$('latest-finding').textContent=`For the straight-line model, the fraction of error we can account for rose from ${pct(linear.baseline_mean_S_over_e)} to ${pct(linear.mean_S_over_e)}. One run of the larger neural network rose from ${pct(data.consensus.summary['canonical_192|mlp16x16|1'].baseline_mean_S_over_e)} to ${pct(data.consensus.summary['canonical_192|mlp16x16|1'].mean_S_over_e)}. The small model changed very little. Open “Compare all models and training runs” to see every result.`;
 const ab=data.mechanism.ablations.sweep,labels={boundary_only:'Boundary only',fitted_plus_boundary:'Fitted slope + boundary',theory_slope:'Theory slope only',theory_plus_boundary:'Theory + boundary'};
 $('ablations').innerHTML=Object.entries(labels).map(([key,label])=>`<tr><td>${label}</td><td>${pct(ab[key].pooled_coverage)}</td><td>${f(ab[key].mean_S_over_e,3)}</td></tr>`).join('');
 $('growth-ratio').textContent=f(data.mechanism.growth.sweep.max_interval_ratio,3);update();}
const median=a=>{const s=[...a].sort((x,y)=>x-y);return s[s.length>>1];};
function caveats(){const rows=data.consensus.rows;
 const blend=Math.max(...rows.map(r=>r.S-r.best_single_S));
 $('blend-note').textContent=`Across all ${rows.length} checked cases, the weighted blend of regions beat the single strongest region by at most ${f(blend,4)} distance units—indistinguishable from zero next to measured errors of about ${f(median(rows.map(r=>r.e)),0)}.`;
 const balls=c=>{const r=rows.find(x=>x.config===c);return r?r.ball_count:0;};
 $('subset-note').textContent=`The 192 mW setting has four calibration experiments, which give ${balls('canonical_192')} eligible groups to choose from. The 146 mW setting has only three, so there is exactly ${balls('canonical_146')} eligible group and the result is unchanged by definition—not by measurement.`;
 const n=balls('canonical_'+$('ceiling').value);
 $('premise-note').textContent=`all ${n} region${n===1?'':'s'}`;
 const margin=Math.min(...rows.map(r=>Math.min(...r.all_ball_radii.map((v,i)=>v-r.all_ball_residuals[i]))));
 $('margin-note').textContent=`and the tightest region cleared the true answer by ${f(margin)} distance units,`;}
function update(){const model=$('model').value;if(model==='linear')$('seed').value='0';$('seed').disabled=model==='linear';
 selectedRows=data.ceiling.rows.filter(r=>r.config==='canonical_'+$('ceiling').value&&r.model===model&&r.seed===Number($('seed').value));
 const old=$('trial').value;$('trial').replaceChildren(...selectedRows.map(r=>{const o=document.createElement('option');o.value=r.trial;o.textContent=r.P+' mW';return o;}));
 if(selectedRows.some(r=>r.trial===old))$('trial').value=old;
 caveats();$('model-results').innerHTML=Object.entries(data.consensus.summary).filter(([k])=>k.startsWith('canonical_'+$('ceiling').value+'|')).map(([k,s])=>{const [,m,seed]=k.split('|');const g=(s.mean_S_over_e-s.baseline_mean_S_over_e)*100,only=(data.consensus.rows.find(x=>x.config==='canonical_'+$('ceiling').value)||{}).ball_count===1;return `<tr><td>${modelName[m]} / ${seed}</td><td>${pct(s.baseline_mean_S_over_e)}</td><td>${pct(s.mean_S_over_e)}</td><td>${only?'<span class="na">only one group—no choice</span>':'+'+f(g,2)+' pts'}</td></tr>`;}).join('');render();}
function render(){selected=selectedRows.find(r=>r.trial===$('trial').value)||selectedRows[0];comparison();spectrum();geometry();corpus();
 $('distance').textContent=f(norm(selected.prediction.map((v,i)=>v-selected.centre[i])));$('radius').textContent=f(selected.radius);$('score').textContent=f(selected.S);$('error-value').textContent=f(selected.e);
 const improved=combined(selected);$('example-sentence').textContent=improved.S>0?`If all the checking rules hold, this prediction is wrong by at least ${f(improved.S)} distance units. When we checked the real measurement afterwards, the error was ${f(improved.e)}. The warning accounts for ${pct(improved.S/improved.e)} of that measured mistake.`:`The checker cannot prove a mistake in this example: its minimum-error estimate is zero. The real error, measured afterwards, was ${f(improved.e)}. A silent warning does not mean the guess is right.`;}
function comparison(){const w=460,h=245,left=40,right=15,top=20,bottom=35,plotH=h-top-bottom;
 let s='';for(let v=0;v<=1.001;v+=.25){const y=top+(1-v)*plotH;s+=line(left,y,w-right,y)+text(left-8,y+4,`${Math.round(v*100)}%`,'end');}
 const step=(w-left-right)/selectedRows.length;
 selectedRows.forEach((r,i)=>{const x=left+step*(i+.5),bars=[r.S/r.e,combined(r).S/r.e];
 if(r.trial===selected.trial)s+=`<rect x="${x-step*.43}" y="${top-8}" width="${step*.86}" height="${plotH+12}" fill="#edf2e3" rx="5"/>`;
 bars.forEach((v,j)=>{const bw=Math.min(30,step*.25),xx=x+(j-.5)*bw-bw/2,hh=v*plotH;s+=`<rect x="${xx}" y="${top+plotH-hh}" width="${bw-3}" height="${hh}" rx="2" fill="${[C.labelled,C.new][j]}"><title>${r.P} mW: ${pct(v)}</title></rect>`;});
 s+=text(x,h-13,`${r.P} mW`,'middle');});$('comparison').innerHTML=svg(s,w,h);}
function spectrum(){const arrays=[selected.prediction,selected.truth,selected.centre],freq=data.ceiling.frequency_hz;
 const lo=Math.floor(Math.min(...arrays.flat())-1),hi=Math.ceil(Math.max(...arrays.flat())+1),x=v=>45+(Math.log(v)-Math.log(freq[0]))/(Math.log(freq.at(-1))-Math.log(freq[0]))*395,y=v=>205-(v-lo)/(hi-lo)*175;
 let s='';for(let i=0;i<=4;i++){const v=lo+(hi-lo)*i/4;s+=line(45,y(v),440,y(v))+text(35,y(v)+4,f(v,0),'end');}
 arrays.forEach((a,j)=>{s+=`<polyline points="${a.map((v,i)=>x(freq[i])+','+y(v)).join(' ')}" fill="none" stroke="${[C.pred,C.truth,C.new][j]}" stroke-width="2" ${j===2?'stroke-dasharray="5 4"':''}/>`;});
 [0,4,8,11].forEach(i=>s+=text(x(freq[i]),225,f(freq[i]/1000,1)+'k','middle'));s+=text(45,14,'Wave strength (log scale)')+text(440,242,'Cycles each second / Hz','end');$('spectrum').innerHTML=svg(s);}
function geometry(){const scale=Number($('radius-slider').value)/100,dist=norm(selected.prediction.map((v,i)=>v-selected.centre[i])),r=selected.radius*scale;
 const unit=Math.min(85/Math.max(selected.radius*3,1),255/Math.max(dist,1)),cx=125,cy=110,rr=r*unit,px=cx+dist*unit,edge=Math.min(px,cx+rr),bound=Math.max(dist-r,0);
 let s=`<circle cx="${cx}" cy="${cy}" r="${rr}" fill="#e7efdb" stroke="#799c76" stroke-width="1.5"/>`;
 s+=line(cx,cy,px,cy,'#a7b4a5','4 4')+`<circle cx="${cx}" cy="${cy}" r="4" fill="${C.new}"/><circle cx="${px}" cy="${cy}" r="6" fill="${C.pred}"/>`;
 s+=text(cx,cy+24,'Starting estimate','middle')+text(px,cy-16,'Model’s guess','middle');
 s+=`<line x1="${edge}" y1="160" x2="${px}" y2="160" stroke="${C.new}" stroke-width="4"/>`+text((edge+px)/2,185,'Minimum mistake: '+f(bound),'middle')+text(cx,15,'Possible answers','middle');
 $('geometry').innerHTML=svg(s,460,230);$('radius-scale').textContent=f(scale)+'×';$('geometry-caption').textContent=bound>0?`With this much uncertainty, the guess is at least ${f(bound)} distance units outside the circle. Make the circle bigger and the minimum mistake gets smaller.`:'The guess is inside the circle. This check cannot prove it is wrong—but it also cannot prove it is right.';}
function corpus(){const ceiling=Number($('ceiling').value),trials=data.dataset.trials,w=950,x=p=>35+(Math.log(p)-Math.log(7))/(Math.log(350)-Math.log(7))*880;
 let s=line(35,58,915,58,'#bac9bb');[7,12,54,106,146,192,250,350].forEach(p=>s+=line(x(p),64,x(p),70)+text(x(p),90,p,'middle'));
 trials.forEach((t,i)=>{let color=t.power<12?C.old:t.power<=54?C.truth:t.power<=ceiling?C.new:C.pred;const yy=t.id==='_45_1'?40:58;
 s+=`<circle cx="${x(t.power)}" cy="${yy}" r="7" fill="${color}" stroke="#fffef9" stroke-width="2"><title>${t.id}: ${t.power} mW, ${t.windows} windows</title></circle>`;});
 s+=text(35,18,'20 powered trials')+text(915,112,'Drive power / mW · log axis','end');$('corpus-chart').innerHTML=svg(s,w,120);}
async function startRun(kind){showError('');try{await request('/api/run',{method:'POST',headers:{'Content-Type':'application/json','X-Lab-Request':'1'},body:JSON.stringify({kind})});await poll();}catch(e){showError(e.message);}}
async function poll(){if(polling)return;polling=true;try{const j=await request('/api/status'),active=j.state==='running';document.querySelectorAll('[data-run]').forEach(b=>b.disabled=active);
 $('run-status').textContent={idle:'Ready',running:'Running',complete:'Complete',failed:'Failed'}[j.state]||j.state;
 const stages={'build_dataset.py':'Reading the wave recordings and building the data table','ceiling_audit.py':'Training models and checking the one-rule method','consensus_audit.py':'Combining several rules and checking the results','mechanism_audit.py':'Testing the assumptions behind the rules','export_data.py':'Updating the charts'};
 $('run-summary').textContent=j.state==='running'?(stages[(j.label||'').split('/').pop()]||'Running the full research comparison')+'…':j.state==='complete'?'Finished. The charts now show the newly calculated results.':j.state==='failed'?'The run stopped before it finished. Your last completed charts are still available. Open the progress log for details.':'Ready. You can explore the saved results without running anything.';
 if(j.id){$('run-label').textContent=j.label||'Starting pipeline';$('run-time').textContent=`Step ${j.step} of ${j.total} · ${Math.round(((j.finished||Date.now()/1000)-j.started))}s`;$('progress').max=j.total;$('progress').value=j.state==='complete'?j.total:Math.max(0,j.step-1);$('logs').textContent=j.logs.join('\n')||'Starting…';$('logs').scrollTop=$('logs').scrollHeight;}
 if(j.state==='failed')showError(j.error||'Run failed. See experiment log.');
 if(j.state==='complete'&&lastJob!==j.id){lastJob=j.id;await load();}
 }catch(e){showError('Cannot reach the local runner. '+e.message);}finally{polling=false;}}
['ceiling','model','seed'].forEach(id=>$(id).addEventListener('change',update));$('trial').addEventListener('change',render);$('radius-slider').addEventListener('input',geometry);
document.querySelectorAll('[data-run]').forEach(b=>b.addEventListener('click',()=>startRun(b.dataset.run)));
load().catch(e=>showError('Unable to load published results. '+e.message));poll();setInterval(poll,2000);
