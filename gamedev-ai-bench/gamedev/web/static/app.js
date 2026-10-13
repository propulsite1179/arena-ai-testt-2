/* No trackers, no remote scripts, no provider keys. Untrusted output is never injected. */
'use strict';
(() => {
 const $=s=>document.querySelector(s), $$=s=>Array.from(document.querySelectorAll(s));
 const lang=document.documentElement.lang,base=$('meta[name="gdb-base"]')?.content||'';
 const isStatic=$('meta[name="gdb-static"]')?.content==='true';
 const t=k=>window.GDB_I18N?.[lang]?.[k]||window.GDB_I18N?.en?.[k]||k;
 const path=url=>url.startsWith('/')?base+url:url;
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 let toastTimer;
 function toast(message,error=false){const box=$('.toast');box.textContent=message;box.classList.toggle('is-error',error);box.hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>box.hidden=true,9000);}
 function errorText(error){return error instanceof Error?error.message:t('operation_failed');}
 async function api(url,options={}) {
  if(isStatic && options.method && options.method!=='GET')throw new Error(t('server_required'));
  const headers={'Accept':'application/json',...options.headers};
  if(options.body!==undefined){headers['Content-Type']='application/json';headers['X-CSRF-Token']=$('meta[name="csrf-token"]')?.content||'';}
  const response=await fetch(path(url),{credentials:'same-origin',...options,headers,body:options.body!==undefined?JSON.stringify(options.body):undefined});
  let value;try{value=await response.json();}catch{throw new Error(t('operation_failed'));}
  if(!response.ok){if(response.status===401)throw new Error(t('session_expired'));throw new Error(typeof value.detail==='string'?value.detail:t('operation_failed'));}
  return value;
 }
 async function busy(button,action){if(button)button.disabled=true;try{await action();}catch(error){toast(errorText(error),true);}finally{if(button)button.disabled=false;}}
 function message(form,text,error=false){const area=form.querySelector('.form-message');if(area){area.textContent=text;area.classList.toggle('is-error',error);}else toast(text,error);}
 const savedTheme=(()=>{try{return localStorage.getItem('gdb-theme');}catch{return null;}})();
 if(savedTheme==='light'||savedTheme==='dark')document.documentElement.dataset.theme=savedTheme;
 $('.theme-toggle')?.addEventListener('click',()=>{const theme=document.documentElement.dataset.theme==='light'?'dark':'light';document.documentElement.dataset.theme=theme;try{localStorage.setItem('gdb-theme',theme);}catch{/* Theme remains usable without storage. */}});
 const sidebar=$('#sidebar'),menu=$('.mobile-toggle'),backdrop=$('.nav-backdrop');
 function closeMenu(){sidebar.classList.remove('is-open');menu?.setAttribute('aria-expanded','false');backdrop.hidden=true;document.body.style.overflow='';}
 menu?.addEventListener('click',()=>{const open=!sidebar.classList.contains('is-open');sidebar.classList.toggle('is-open',open);menu.setAttribute('aria-expanded',String(open));backdrop.hidden=!open;document.body.style.overflow=open?'hidden':'';if(open)sidebar.querySelector('a')?.focus();});
 backdrop?.addEventListener('click',closeMenu);
 document.addEventListener('keydown',event=>{if(event.key==='Escape'){closeMenu();menu?.focus();}if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){event.preventDefault();($('.top-search input')||$('#model-search'))?.focus();}if(event.key==='Tab'&&sidebar.classList.contains('is-open')){const focusables=Array.from(sidebar.querySelectorAll('a,button'));if(event.shiftKey&&document.activeElement===focusables[0]){event.preventDefault();focusables.at(-1)?.focus();}else if(!event.shiftKey&&document.activeElement===focusables.at(-1)){event.preventDefault();focusables[0]?.focus();}}});
 $$('.nav-link').forEach(link=>link.addEventListener('click',closeMenu));
 const currentEnvironment=new URLSearchParams(location.search).get('environment')||'web';
 $$('.tab-bar .tab').forEach(tab=>tab.classList.toggle('active',new URLSearchParams((tab.getAttribute('href')||'').split('?')[1]||'').get('environment')===currentEnvironment));
 function filterModels(){const search=($('#model-search')?.value||'').trim().toLowerCase(),provider=$('#provider-filter')?.value||'';let count=0;
  $$('.model-row').forEach(row=>{row.hidden=!(row.dataset.name.includes(search)&&(!provider||row.dataset.provider===provider));if(!row.hidden)count++;});
  if($('#model-empty'))$('#model-empty').hidden=count>0;if($('#model-count'))$('#model-count').textContent=new Intl.NumberFormat(lang).format(count);
 }
 $('#model-search')?.addEventListener('input',filterModels);$('#provider-filter')?.addEventListener('change',filterModels);
 $('#model-sort')?.addEventListener('change',()=>{const sort=$('#model-sort').value;const rows=$$('.model-row');rows.sort((a,b)=>sort==='input'?Number(a.dataset.price)-Number(b.dataset.price):a.dataset[sort].localeCompare(b.dataset[sort],lang));rows.forEach(row=>$('#model-table-body').append(row));});
 $('#reset-filters')?.addEventListener('click',()=>{$('#model-search').value='';$('#provider-filter').value='';filterModels();});
 if($('#model-search'))filterModels();
 function filterTasks(){const search=($('#task-search')?.value||'').trim().toLowerCase(),category=$('#task-category')?.value||'';$$('.task-card').forEach(card=>card.hidden=!((!category||card.dataset.category===category)&&card.dataset.task.includes(search)));}
 $('#task-search')?.addEventListener('input',filterTasks);$('#task-category')?.addEventListener('change',filterTasks);
 $$('[data-copy]').forEach(button=>button.addEventListener('click',()=>busy(button,async()=>{await navigator.clipboard.writeText(button.dataset.copy);toast(t('copied'));})));
 $('#contact-form')?.addEventListener('submit',event=>{event.preventDefault();const form=event.currentTarget,fields=new FormData(form);busy(form.querySelector('button[type=submit]'),async()=>{const result=await api('/api/v1/contact',{method:'POST',body:{email:fields.get('email'),name:fields.get('name'),kind:fields.get('kind'),message:fields.get('message'),consent:fields.has('consent'),website:fields.get('website')||''}});message(form,t('contact_saved')+' '+result.reference);form.reset();});});
 $('#auth-form')?.addEventListener('submit',event=>{event.preventDefault();const form=event.currentTarget,fields=new FormData(form),action=form.dataset.action;
  const body={email:fields.get('email'),password:fields.get('password')};if(action==='register'){body.name=fields.get('name');body.locale=lang;}
  busy(form.querySelector('button[type=submit]'),async()=>{try{const result=await api('/api/v1/auth/'+action,{method:'POST',body});if(action==='register'){message(form,t('register_success'));form.reset();}else{location.assign(path('/'+lang+'/'+(['admin','reviewer'].includes(result.role)?'admin':'account')));}}catch(error){message(form,errorText(error),true);}});
 });
 $('#logout')?.addEventListener('click',event=>busy(event.currentTarget,async()=>{await api('/api/v1/auth/logout',{method:'POST',body:{}});location.assign(path('/'+lang+'/login'));}));
 $('#delete-account-form')?.addEventListener('submit',event=>{event.preventDefault();const form=event.currentTarget;busy(form.querySelector('button'),async()=>{await api('/api/v1/account/delete',{method:'POST',body:{password:new FormData(form).get('password')}});location.assign(path('/'+lang));});});
 $$('[data-follow]').forEach(button=>button.addEventListener('click',()=>busy(button,async()=>{const result=await api('/api/v1/account/follow/'+encodeURIComponent(button.dataset.follow),{method:'POST',body:{}});toast(result.following?t('following'):t('operation_saved'));})));
 async function showComparison(ids){
  const output=$('#comparison-output');if(!output)return;if(ids.length<2||ids.length>4)throw new Error(t('select_models'));
  const result=isStatic?await api('/static/catalog.json'):await api('/api/v1/compare?ids='+encodeURIComponent(ids.join(',')));
  const selected=(result.items||[]).filter(model=>ids.includes(model.id));if(selected.length!==ids.length)throw new Error(t('select_models'));
  const fields=[['provider',m=>m.provider],['api_id',m=>m.api_id],['input_price',m=>m.price?new Intl.NumberFormat(lang,{style:'currency',currency:'USD'}).format(Number(m.price.input)):t('not_recorded')],['output_price',m=>m.price?new Intl.NumberFormat(lang,{style:'currency',currency:'USD'}).format(Number(m.price.output)):t('not_recorded')],['reasoning',()=>t('default_reasoning')],['score',()=>t('insufficient')],['status',m=>t(m.status)]];
  output.innerHTML='<div class="table-scroll"><table class="comparison-table"><caption class="sr-only">'+esc(t('compare'))+'</caption><thead><tr><th>'+esc(t('configuration_label'))+'</th>'+selected.map(m=>'<th><a href="'+esc(path('/'+lang+'/models/'+m.id))+'"><strong>'+esc(m.name)+'</strong></a></th>').join('')+'</tr></thead><tbody>'+fields.map(([label,value])=>'<tr><td>'+esc(t(label))+'</td>'+selected.map(m=>'<td>'+esc(value(m))+'</td>').join('')+'</tr>').join('')+'</tbody></table></div><div class="form-actions"><button class="button" id="save-comparison">'+esc(t('save_comparison'))+'</button></div>';
  $('#save-comparison')?.addEventListener('click',event=>busy(event.currentTarget,async()=>{await api('/api/v1/account/comparisons',{method:'POST',body:{name:selected.map(m=>m.name).join(' / ').slice(0,100),model_ids:ids}});toast(t('operation_saved'));}));
  const url=new URL(location.href);url.searchParams.set('ids',ids.join(','));try{history.replaceState(null,'',url);}catch{/* Sandboxed component viewers may not allow history updates. */}
 }
 $('#compare-form')?.addEventListener('submit',event=>{event.preventDefault();const ids=new FormData(event.currentTarget).getAll('models');busy(event.currentTarget.querySelector('button'),()=>showComparison(ids));});
 if($('#compare-form')){const ids=new FormData($('#compare-form')).getAll('models');if(ids.length>=2&&ids.length<=4)showComparison(ids).catch(error=>toast(errorText(error),true));}
 let match=null,voteTimer;
 $('#new-match')?.addEventListener('click',event=>busy(event.currentTarget,async()=>{clearTimeout(voteTimer);$$('[data-vote]').forEach(button=>button.disabled=true);match=await api('/api/v1/arena/matches',{method:'POST',body:{mode:'fixture'}});
  for(const [side,url] of [['a',match.left],['b',match.right]]){if(!/^\/fixtures\/(orbital|meadow)\/index\.html$/.test(url))throw new Error(t('operation_failed'));$('#game-'+side).src=path(url)+'?lang='+lang;}
  $('#vote-status').textContent=t('vote_wait');voteTimer=setTimeout(()=>$$('[data-vote]').forEach(button=>button.disabled=false),match.minimum_seconds*1000+300);
 }));
 $$('[data-vote]').forEach(button=>button.addEventListener('click',()=>{if(!match)return;$$('[data-vote]').forEach(b=>b.disabled=true);api('/api/v1/arena/votes',{method:'POST',body:{match_id:match.id,choice:button.dataset.vote}}).then(result=>{$('#vote-status').textContent=t('vote_saved')+' A: '+result.left+' / B: '+result.right;match=null;}).catch(error=>{toast(errorText(error),true);$$('[data-vote]').forEach(b=>b.disabled=false);});}));
 $$('[data-fullscreen]').forEach(button=>button.addEventListener('click',()=>busy(button,async()=>{const shell=$('#game-'+button.dataset.fullscreen).closest('.game-shell');if(!shell.requestFullscreen)throw new Error(t('operation_failed'));await shell.requestFullscreen();})));
 $$('[data-restart]').forEach(button=>button.addEventListener('click',()=>{const frame=$('#game-'+button.dataset.restart);const url=new URL(frame.src,location.href);url.searchParams.set('restart',String(Date.now()));frame.src=url.href;}));
 function campaignBody(){const fields=new FormData($('#campaign-form'));return {name:fields.get('name'),configuration_id:fields.get('configuration_id'),suite_id:'web-v1',task_ids:[fields.get('task_id')],trials:Number(fields.get('trials')),authorized_microusd:Math.round(Number(fields.get('budget'))*1e6),paid_authorized:fields.has('paid_authorized')};}
 $('#campaign-quote')?.addEventListener('click',event=>busy(event.currentTarget,async()=>{const result=await api('/api/v1/admin/campaigns/quote',{method:'POST',body:campaignBody()});message($('#campaign-form'),new Intl.NumberFormat(lang,{style:'currency',currency:'USD',maximumFractionDigits:6}).format(result.upper_bound_microusd/1e6)+' / '+result.calls+' '+t('trials').toLowerCase());}));
 $('#campaign-form')?.addEventListener('submit',event=>{event.preventDefault();const form=event.currentTarget;busy(form.querySelector('[type=submit]'),async()=>{const result=await api('/api/v1/admin/campaigns',{method:'POST',body:campaignBody(),headers:{'Idempotency-Key':crypto.randomUUID()}});message(form,t('queued_notice')+' '+result.id);const a=document.createElement('a');a.className='text-link';a.href=location.href;a.textContent=t('campaigns');form.append(a);});});
 $$('[data-cancel-campaign]').forEach(button=>button.addEventListener('click',()=>busy(button,async()=>{await api('/api/v1/admin/campaigns/'+encodeURIComponent(button.dataset.cancelCampaign)+'/cancel',{method:'POST',body:{}});location.reload();})));
 $$('[data-revoke-worker]').forEach(button=>button.addEventListener('click',()=>busy(button,async()=>{await api('/api/v1/admin/workers/'+encodeURIComponent(button.dataset.revokeWorker)+'/revoke',{method:'POST',body:{}});location.reload();})));
 $('#review-form')?.addEventListener('submit',event=>{event.preventDefault();const form=event.currentTarget,fields=new FormData(form);busy(event.submitter,async()=>{const result=await api('/api/v1/admin/runs/'+encodeURIComponent(form.dataset.run)+'/review',{method:'POST',body:{verdict:event.submitter.value,notes:fields.get('notes'),rubric:{artifacts_inspected:fields.has('inspected'),brief_verified:fields.has('inspected'),controls_verified:fields.has('inspected'),restart_verified:fields.has('inspected'),score_verified:fields.has('inspected')},conflict_of_interest:false}});toast(t('operation_saved')+' '+t(result.state));location.reload();});});
 $$('[data-discover]').forEach(button=>button.addEventListener('click',()=>busy(button,async()=>{const result=await api('/api/v1/admin/providers/'+encodeURIComponent(button.dataset.discover)+'/discover',{method:'POST',body:{}});toast(t('operation_saved')+' '+result.discovered);} )));
 $('#checkout')?.addEventListener('click',event=>busy(event.currentTarget,async()=>{const result=await api('/api/v1/billing/checkout',{method:'POST',body:{},headers:{'Idempotency-Key':crypto.randomUUID()}});if(!result.url.startsWith('https://checkout.stripe.com/'))throw new Error(t('operation_failed'));location.assign(result.url);}));
 if(isStatic){$$('form:not(#compare-form):not(.top-search) button, [data-follow], #new-match, #checkout, #logout, [data-vote]').forEach(button=>{button.disabled=true;button.title=t('server_required');});if($('#vote-status'))$('#vote-status').textContent=t('server_required');}
})();
