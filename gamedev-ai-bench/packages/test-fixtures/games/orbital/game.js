"use strict";
(() => {
 const $ = s => document.querySelector(s), canvas=$('canvas'), ctx=canvas.getContext('2d');
 const fr=new URLSearchParams(location.search).get('lang')==='fr';
 const t=(en,frText)=>fr?frText:en;
 document.documentElement.lang=fr?'fr':'en';
 $('#title').textContent=t('ORBITAL COLLECTOR','COLLECTEUR ORBITAL');
 $('#score-label').textContent=t('CELLS','CELLULES'); $('#hint').textContent=t('WASD / arrow keys or touch controls','WASD / flèches ou commandes tactiles');
 const state={mode:'ready',x:240,y:160,score:0,lives:3,invincible:0,elapsed:0};
 const keys=new Set();let pointerDirection=null,last=0;
 const cells=[{x:55,y:60},{x:155,y:50},{x:365,y:60},{x:425,y:130},{x:60,y:220},{x:160,y:270},{x:360,y:265},{x:430,y:280},{x:245,y:55}];
 const stars=Array.from({length:55},(_,i)=>({x:(i*173+37)%480,y:(i*101+21)%320,r:i%3?0.7:1.4}));
 const variant=document.body.dataset.variant;const accent=variant==='orbital'?'#bdff81':'#84dcff';
 function sync(){ $('[data-testid=score]').textContent=String(state.score);$('[data-testid=state]').textContent=state.mode;$('[data-testid=player]').dataset.x=state.x.toFixed(2);$('#lives').textContent=state.lives+' / 3';$('#pause').disabled=!['running','paused'].includes(state.mode);$('#pause').textContent=state.mode==='paused'?t('Resume','Reprendre'):t('Pause','Pause');$('#restart').textContent=t('Restart','Rejouer');}
 function overlay(show,title,subtitle){$('.overlay').hidden=!show;$('#headline').textContent=title;$('#instructions').textContent=subtitle;$('#eyebrow').textContent=t('FLIGHT SYSTEMS READY','SYSTÈMES DE VOL PRÊTS');$('[data-testid=start]').textContent=t('Launch mission ↗','Lancer la mission ↗');}
 function reset(){Object.assign(state,{mode:'ready',x:240,y:160,score:0,lives:3,elapsed:0,invincible:0});keys.clear();pointerDirection=null;cells.forEach(c=>c.collected=false);overlay(true,t('Find your orbit.','Trouvez votre orbite.'),t('Collect nine energy cells. Avoid the sentinels.','Récoltez neuf cellules. Évitez les sentinelles.'));sync();}
 $('[data-testid=start]').addEventListener('click',()=>{if(state.mode==='finished')reset();state.mode='running';overlay(false,'','');canvas.focus();sync();});
 $('[data-testid=restart]').addEventListener('click',reset);
 $('#pause').addEventListener('click',()=>{state.mode=state.mode==='running'?'paused':'running';sync();});
 const directions={ArrowLeft:[-1,0],a:[-1,0],ArrowRight:[1,0],d:[1,0],ArrowUp:[0,-1],w:[0,-1],ArrowDown:[0,1],s:[0,1]};
 window.addEventListener('keydown',e=>{if(directions[e.key]){keys.add(e.key);e.preventDefault();}});window.addEventListener('keyup',e=>keys.delete(e.key));window.addEventListener('blur',()=>{keys.clear();pointerDirection=null;});
 for(const [name,dir] of Object.entries({left:[-1,0],right:[1,0],up:[0,-1],down:[0,1]})){const button=$('[data-testid=touch-'+name+']');button.addEventListener('pointerdown',e=>{pointerDirection=dir;button.setPointerCapture(e.pointerId);e.preventDefault();});button.addEventListener('pointerup',()=>pointerDirection=null);button.addEventListener('pointercancel',()=>pointerDirection=null);button.addEventListener('click',()=>{if(state.mode==='running'){state.x=Math.max(12,Math.min(468,state.x+dir[0]*12));state.y=Math.max(12,Math.min(308,state.y+dir[1]*12));sync();}});}
 function draw(ts){const dt=Math.min((ts-last)/1000||0,0.04);last=ts;const rect=canvas.getBoundingClientRect(),dpr=Math.min(devicePixelRatio||1,2);if(canvas.width!==Math.round(rect.width*dpr)||canvas.height!==Math.round(rect.height*dpr)){canvas.width=Math.round(rect.width*dpr);canvas.height=Math.round(rect.height*dpr);}ctx.setTransform(canvas.width/480,0,0,canvas.height/320,0,0);ctx.fillStyle=variant==='orbital'?'#0b141e':'#10221f';ctx.fillRect(0,0,480,320);
  ctx.strokeStyle='#263742';ctx.lineWidth=.4;for(let i=0;i<480;i+=40){ctx.beginPath();ctx.moveTo(i,0);ctx.lineTo(i,320);ctx.stroke();}for(let i=0;i<320;i+=40){ctx.beginPath();ctx.moveTo(0,i);ctx.lineTo(480,i);ctx.stroke();}
  for(const p of stars){ctx.fillStyle='#47616d';ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,Math.PI*2);ctx.fill();}
  ctx.strokeStyle='#294542';ctx.lineWidth=1;for(let r=55;r<170;r+=45){ctx.beginPath();ctx.ellipse(240,160,r,r*.68,-.35,0,Math.PI*2);ctx.stroke();}
  if(state.mode==='running'){state.elapsed+=dt;state.invincible=Math.max(0,state.invincible-dt);let dx=pointerDirection?.[0]||0,dy=pointerDirection?.[1]||0;for(const key of keys){dx+=directions[key][0];dy+=directions[key][1];}const len=Math.max(1,Math.hypot(dx,dy));state.x=Math.max(12,Math.min(468,state.x+dx/len*125*dt));state.y=Math.max(12,Math.min(308,state.y+dy/len*125*dt));}
  for(const c of cells){if(c.collected)continue;ctx.save();ctx.translate(c.x,c.y);ctx.rotate(Math.PI/4);ctx.shadowColor=accent;ctx.shadowBlur=12;ctx.fillStyle=accent;ctx.fillRect(-4,-4,8,8);ctx.restore();if(state.mode==='running'&&Math.hypot(c.x-state.x,c.y-state.y)<15){c.collected=true;state.score++;}}
  for(let i=0;i<3;i++){const a=state.elapsed*.5+i*Math.PI*.67,r=85+i*22,h={x:240+Math.cos(a)*r,y:160+Math.sin(a)*r*.65};ctx.fillStyle='#fd8b81';ctx.beginPath();ctx.arc(h.x,h.y,6,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#964c4c';ctx.beginPath();ctx.arc(h.x,h.y,12,0,Math.PI*2);ctx.stroke();if(state.mode==='running'&&state.invincible===0&&Math.hypot(h.x-state.x,h.y-state.y)<15){state.lives--;state.invincible=1.5;}}
  if(state.mode==='running'&&(state.score===9||state.lives<=0)){state.mode='finished';overlay(true,state.score===9?t('Orbit complete.','Orbite terminée.'):t('Signal lost.','Signal perdu.'),t('Restart to fly again.','Rejouez pour repartir.'));$('[data-testid=start]').textContent=t('Explore again','Explorer encore');}
  ctx.save();ctx.translate(state.x,state.y);ctx.fillStyle=state.invincible>0?'#fd8b81':'#f0fbf6';ctx.shadowColor=accent;ctx.shadowBlur=14;ctx.beginPath();ctx.moveTo(0,-10);ctx.lineTo(8,8);ctx.lineTo(0,4);ctx.lineTo(-8,8);ctx.closePath();ctx.fill();ctx.restore();sync();requestAnimationFrame(draw);}
 reset();requestAnimationFrame(draw);
})();