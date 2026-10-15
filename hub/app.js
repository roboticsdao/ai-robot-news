/* Independent static UI. All source content is rendered as text, not HTML. */
(() => {
  'use strict';
  const $ = (q, root=document) => root.querySelector(q);
  const $$ = (q, root=document) => [...root.querySelectorAll(q)];
  const read = (key, fallback) => { try { return JSON.parse(localStorage.getItem('rdao-'+key)) ?? fallback; } catch { return fallback; } };
  const save = (key,value) => { try { localStorage.setItem('rdao-'+key,JSON.stringify(value)); } catch {} };
  const selected = read('companies',null);
  const S = {lang:read('lang','zh'),theme:read('theme','system'),companies:selected===null?null:new Set(selected),q:'',topic:'all',country:'all',days:'7',scope:'all',onlySaved:false,showSummary:false,limit:100,sort:'val',sortDir:-1,saved:new Set(read('saved',[])),view:'news',date:'',netLayout:'chain',netSize:'relations',edgeTypes:new Set(['supplies','partners','competes','invests','acquires','alternative']),changes:false,axisX:'application',axisY:'commercial',lean:true,picks:{},milestone:'all',period:24};
  const E = value => String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const t = (zh,en) => S.lang==='zh'?zh:en;
  const L = value => typeof value==='object' && value!==null ? value[S.lang] ?? value.en ?? value.zh ?? '' : value??'';
  const I = name => `<i data-lucide="${E(name)}"></i>`;
  const safe = url => { if(!url||typeof url!=='string')return '#';try { const u=new URL(url,location.href);return ['https:','http:'].includes(u.protocol)?u.href:'#'; } catch { return '#'; } };
  const canonical = url => {try{const u=new URL(url);u.hash='';u.pathname=u.pathname.replace(/\/$/,'');for(const key of [...u.searchParams.keys()])if(key.startsWith('utm_')||['fbclid','gclid'].includes(key))u.searchParams.delete(key);return u.href.replace(/\/$/,'');}catch{return url;}};
  const nameMatches = (name,text) => {name=name.toLowerCase();text=text.toLowerCase();if(/[\u3040-\u9fff]/.test(name))return name.length>=2&&text.includes(name);if(name.length<3&&name!=='1x')return false;return new RegExp('(^|[^a-z0-9])'+name.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'($|[^a-z0-9])').test(text);};
  const matchCompany = (c,text) => {const aliases={nvidia:['英伟达','エヌビディア'],tesla:['特斯拉','テスラ'],microsoft:['微软'],amazon:['亚马逊'],gdm:['deepmind','谷歌'],bd:['boston dynamics','波士顿动力']};const names=c.id==='humanoid'?["HMND","Humanoid Robotics","Humanoid Limited","Humanoid's","Humanoid CEO"]:c.id==='sunday'?["Sunday Robotics","Sunday's robot","Sunday机器人","Sunday 机器人"]:[...Object.values(c.name),...(aliases[c.id]||[])];return names.some(name=>nameMatches(name,text));};
  const external = (url,label) => `<a class="original-link" href="${E(safe(url))}" target="_blank" rel="noopener noreferrer">${label}${I('external-link')}</a>`;
  const A = window.App={S,E,t,L,I,$,$$,safe,external,views:{},cleanup:null,D:null};
  A.iconize = () => window.lucide?.createIcons({attrs:{'aria-hidden':'true'}});
  A.co = id => A.byId?.get(id) || {id,name:{en:id,zh:id},seg:'data'};
  A.name = id => L(A.co(id).name);
  A.color = seg => getComputedStyle(document.documentElement).getPropertyValue('--'+(seg||'maker')).trim() || '#287bdb';
  A.logo = (id,large=false) => { const c=A.co(id);return `<img class="co-logo${large?' large':''}" src="${E(c.logo||'assets/robot-anatomy.png')}" alt="${E(A.name(id))}" loading="lazy" onerror="this.onerror=null;this.src='assets/robot-anatomy.png'">`; };
  A.coButton = (id,detail=true) => `<button class="co-name" data-co="${E(id)}">${A.logo(id)}<span class="co-copy">${E(A.name(id))}${detail?`<small><i class="dot" style="background:${A.color(A.co(id).seg)}"></i>${E(L(A.D.segments[A.co(id).seg]))} · ${E(A.co(id).cc||'—')}</small>`:''}</span></button>`;
  A.chip = (id,showName=true) => `<button class="co-chip" data-co="${E(id)}" title="${E(A.name(id))}">${A.logo(id)}${showName?`<span>${E(A.name(id))}</span>`:''}</button>`;
  A.picked = id => S.companies===null || S.companies.has(id);
  A.companies = () => A.D.companies.filter(c=>A.picked(c.id));
  A.amount = number => { if(!Number.isFinite(+number)||number===null)return '—';if(S.lang==='en')return new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',notation:'compact',maximumFractionDigits:1}).format(number*1e9);if(number>=1000)return `${+(number/1000).toFixed(2)}万亿美元`;if(number>=.1)return `${+(number*10).toFixed(2)}亿美元`;return `${+(number*100000).toFixed(0)}万美元`; };
  A.date = value => { if(!value)return '—';const d=String(value).slice(0,10);return S.lang==='zh'?d.replaceAll('-','.') : d; };
  A.stage = value => ({'Unknown':t('待补充','Unknown'),'Division':t('部门','Division'),'Public':t('上市','Public'),'Private':t('未上市','Private')})[value]||value||'—';
  A.latest = rows => (rows||[]).filter(r=>r[0]<=S.date).sort((a,b)=>a[0].localeCompare(b[0])).at(-1);
  A.stackAt = (id,layer) => A.latest(A.D.stack[id]?.[layer]);
  A.suppliers = layer => {const walk=value=>Array.isArray(value)?value.flatMap(walk):value&&typeof value==='object'?Object.values(value).flatMap(walk):typeof value==='string'&&A.byId.has(value)?[value]:[];return [...new Set(walk(A.D.layerGroups[layer]))].filter(A.picked);};
  A.pos = (id,debate) => A.latest(A.D.betHist[id]?.[debate.id])?.[1] ?? debate.pos?.[id];
  A.bucket = pos => pos==null?-1:Math.max(0,Math.min(4,Math.round(pos*4)));
  A.posLabel = (debate,pos) => {const b=A.bucket(pos);return b<0?t('未知','Unknown'):b===0?L(debate.left):b===4?L(debate.right):b===2?t('兼顾','Both'):t('偏向','Leans ')+L(b<2?debate.left:debate.right);};
  A.isActive = edge => (!edge.from||edge.from<=S.date)&&(!edge.to||edge.to>S.date);
  A.feedState=(s,key)=>{const age=Date.now()-Date.parse(s?.checked_at||'');return !Number.isFinite(age)?'unknown':age>(key==='market'?10:36)*3600000?'stale':s.state;};
  A.conf = item => item.origin==='digest'?`<span class="tag body">${t('全文摘要','Full text')}</span>`:`<span class="tag ${item.conf==='confirmed'?'confirmed':'reported'}">${t('参考索引','Indexed source')}</span>`;
  const topics = A.topics={all:['全部主题','All topics'],robots:['整机与应用','Robots & deployment'],hands:['灵巧手与夹爪','Hands & grippers'],components:['零部件与芯片','Components & silicon'],brains:['模型与数据','Models & data'],business:['融资与产业','Business & funding'],markets:['股市与宏观','Markets & macro']};
  const names = A.viewNames={news:['全球新闻','Global news'],hand:['灵巧手专题','Dexterous hands'],markets:['股市与宏观','Markets & macro'],milestones:['里程碑','Milestones'],finance:['融资','Funding'],debates:['路线对比','Debates'],betmap:['路线象限','Bet map'],screener:['路线筛选','Screener'],companies:['公司库','Companies'],anatomy:['机器人解剖','Anatomy'],matrix:['供应矩阵','Supply matrix'],network:['产业关系网','Network'],status:['更新状态与来源','Status & sources']};
  const groups=[['news',['新闻','News'],[['news','newspaper'],['hand','hand'],['markets','chart-no-axes-combined'],['milestones','flag'],['finance','circle-dollar-sign']]],['bets',['路线','Bets'],[['debates','git-branch'],['betmap','grid-2x2'],['screener','list-filter']]],['ecosystem',['生态','Ecosystem'],[['companies','building-2'],['anatomy','bot'],['matrix','table-2'],['network','network']]]];
  A.register = (name,render) => A.views[name]=render;
  A.selectionChanged = () => {save('companies',S.companies===null?null:[...S.companies]);renderNav();A.render();};
  A.title = item => L(item.title)||item.headline||'';
  A.visibleNews = (scope=S.scope) => {
    const since=new Date();since.setUTCDate(since.getUTCDate()-(+S.days||3650));const cutoff=since.toISOString().slice(0,10);
    return A.D.news.filter(n=>{
      if(S.onlySaved&&!S.saved.has(n.id))return false;
      if(S.companies!==null&&!(n.cos||[]).some(A.picked))return false;
      if(S.topic!=='all'&&n.topic!==S.topic)return false;
      if(scope==='hand'&&n.topic!=='hands')return false;
      if(scope==='market'&&n.kind!=='market')return false;
      if(scope==='robot'&&n.kind==='market'&&S.topic!=='markets')return false;
      if(S.days!=='all'&&n.d<cutoff)return false;
      if(S.country!=='all'){
        const countries=(n.cos||[]).map(id=>A.co(id).cc);
        if(n.section?.includes('日本'))countries.push('JP');if(n.section?.includes('中国'))countries.push('CN');if(n.section?.includes('美国'))countries.push('US');
        if(!countries.includes(S.country))return false;
      }
      const hay=[A.title(n),n.summary_zh||'',n.summary||'',n.src,...(n.cos||[]).map(A.name)].join(' ').toLowerCase();
      return !S.q||hay.includes(S.q.toLowerCase());
    }).sort((a,b)=>b.d.localeCompare(a.d)||(b.published_at||'').localeCompare(a.published_at||''));
  };
  A.newsHTML = (n,short=false) => `<article class="news-row" data-news="${E(n.id)}">${n.cos?.length?`<button class="co-name" data-co="${E(n.cos[0])}" title="${E(A.name(n.cos[0]))}">${A.logo(n.cos[0])}</button>`:`<span class="muted">${I(n.kind==='market'?'chart-no-axes-combined':'newspaper')}</span>`}<div><button class="news-title" data-article="${E(n.id)}">${E(A.title(n))}</button><div class="news-meta"><time>${A.date(n.d)}</time>${external(n.url,E(n.src||''))}${A.conf(n)}${n.section?`<span>${E(n.section.replace(/^[^\w\u3040-\u9fff]+/,''))}</span>`:''}</div>${S.showSummary&&n.summary_zh?`<p class="preview">${E(n.summary_zh)}</p>`:''}</div><div class="news-tags"><span class="tag">${E(L({zh:topics[n.topic]?.[0],en:topics[n.topic]?.[1]}))}</span></div><button class="saved ${S.saved.has(n.id)?'on':''}" data-save="${E(n.id)}" title="${t('收藏新闻','Save story')}" aria-label="${t('收藏新闻','Save story')}" aria-pressed="${S.saved.has(n.id)}">${I('bookmark')}</button></article>`;
  function renderNav(){
    $('#brandSub').textContent=t('机器人产业情报','Robotics intelligence');
    $('#navigation').innerHTML=groups.map(([key,label,children])=>`<div class="nav-group ${children.some(([v])=>v===S.view)?'current':''}"><button aria-haspopup="menu" aria-expanded="false">${E(L({zh:label[0],en:label[1]}))}${I('chevron-down')}</button><div class="nav-menu" role="menu">${children.map(([v,icon])=>`<a href="#${v}" role="menuitem" ${v===S.view?'aria-current="page"':''}>${I(icon)}${E(L({zh:names[v][0],en:names[v][1]}))}</a>`).join('')}</div></div>`).join('');
    $('#filterCount').textContent=S.companies===null?t('全部公司','All companies'):`${S.companies.size} / ${A.D.companies.length}`;
    $('#contextLeft').innerHTML=`<strong>${E(L({zh:names[S.view]?.[0],en:names[S.view]?.[1]}))}</strong><span class="muted">· ${A.D.companies.length} ${t('家公司','companies')}</span>`;
    $('#contextRight').innerHTML=`<span>${t('图谱截至','Index as of')} ${A.date(A.D.asOf)}</span><a href="#status" title="${t('更新状态','Update status')}">${I('activity')}</a>`;
    const partial=Object.entries(A.D.feed_status||{}).filter(([k,v])=>['partial','stale'].includes(A.feedState(v,k)));
    $('#healthbar').innerHTML=partial.length?`<div class="notice warning">${t('部分日报新稿不足、摘要缺失或已超过更新周期。','Some feeds have fewer stories, missing translations or are overdue.')}<a href="#status">${t('更新详情','Update details')}</a></div>`:'';
    A.iconize();
  }
  A.render=()=>{
    if(!A.D)return;
    A.cleanup?.();A.cleanup=null;
    (A.views[S.view]||A.views.news)?.();
    A.iconize();
  };
  A.refresh=()=>{renderNav();A.render();};
  A.open = (type,id)=>{lastFocus=document.activeElement;location.hash=`${S.view}/${type}/${encodeURIComponent(id)}`;};
  let lastFocus=null,modalTrail=[],modalCursor=-1,modalTravel=false;
  const modalSession=String(Date.now())+Math.random();
  A.modal=(title,content)=>{
    const fresh=$('#modalLayer').hidden;
    $('#modalTitle').textContent=title;$('#modalContent').innerHTML=content;
    $('#modalLayer').hidden=false;document.body.style.overflow='hidden';
    if(fresh)$('.modal').focus();
    $('#modalBack').disabled=modalCursor<=0;$('#modalForward').disabled=modalCursor>=modalTrail.length-1;A.iconize();
  };
  A.close=()=>{location.hash=S.view;};
  function hideModal(){ $('#modalLayer').hidden=true;document.body.style.overflow='';lastFocus?.focus?.();modalTrail=[];modalCursor=-1; }
  function route(){
    const [view,type,encoded]=location.hash.slice(1).split('/');
    const next=names[view]?view:'news';if(S.view!==next){S.q='';S.limit=100;S.topic='all';S.country='all';}
    S.view=next;S.scope=next==='hand'?'hand':next==='markets'?'market':next==='news'?'robot':'all';
    renderNav();A.render();
    const id=decodeURIComponent(encoded||'');
    if(type){const hash=location.hash;if(modalTravel)modalTravel=false;else if(history.state?.rdaoModal===modalSession&&modalTrail[history.state.index]===hash)modalCursor=history.state.index;else if(modalTrail[modalCursor]!==hash){modalTrail=modalTrail.slice(0,modalCursor+1);modalTrail.push(hash);modalCursor=modalTrail.length-1;history.replaceState({rdaoModal:modalSession,index:modalCursor},'',location.href);}}
    if(type==='co'&&A.byId.has(id))A.companyDetail(id);
    else if(type==='article')A.articleDetail(id);
    else if(type==='layer')A.layerDetail(id);
    else if(type==='event')A.eventDetail(id);
    else if(type==='relation')A.relationDetail(+id);
    else if(type==='bet')A.betDetail(id);
    else hideModal();
  }
  A.miniBets=id=>`<div class="mini-bets">${A.D.debates.filter(d=>A.pos(id,d)!=null).map(d=>`<div class="mini-bet"><span>${E(L(d.left))}</span><button class="bet-track" data-bet="${E(id+'~'+d.id)}" title="${E(L(d.q))}: ${E(A.posLabel(d,A.pos(id,d)))}"><i style="left:${A.pos(id,d)*100}%"></i></button><span>${E(L(d.right))}</span></div>`).join('')}</div>`;
  A.miniStack=id=>`<div class="mini-stack">${A.D.layers.map(l=>{const v=A.stackAt(id,l.id)?.[1];return `<button class="stack-cell ${v==='in'?'in':v&&v!=='none'?'out':'na'}" title="${E(L(l))}: ${E(v==='in'?t('自研','In-house'):v?A.name(v):t('未知','Unknown'))}" data-layer="${E(l.id)}"></button>`;}).join('')}</div>`;
  A.rail=(id)=>{
    S.railCompany=id;
    const c=A.co(id),rounds=(A.D.rounds[id]||[]).slice().sort((a,b)=>b[0].localeCompare(a[0]));
    return `<div class="rail-section"><div class="profile-head">${A.logo(id,true)}<div><button class="co-name" data-co="${E(id)}"><h3>${E(A.name(id))}</h3></button><small>${E(L(A.D.segments[c.seg]))} · ${E(c.cc||'—')} · ${E(A.stage(c.stage))}</small></div></div><div class="value">${A.amount(c.val)}<small>${c.valKind==='parent'?t('母公司市值','Parent market cap'):t('市值 / 估值，非实时报价','Value / valuation, not a live quote')}</small></div></div><section class="rail-section"><h4>${t('技术层覆盖','Technology layers')}</h4>${A.miniStack(id)}</section><section class="rail-section"><h4>${t('技术路线 · 参考站分类','Technology bets · reference classifications')}</h4>${A.miniBets(id)}</section>${rounds.length?`<section class="rail-section"><h4>${t('最近融资记录','Recent funding')}</h4>${rounds.slice(0,3).map(r=>`<div class="fund-row"><span>${A.date(r[0])} ${E(L(r[2]))}</span>${external(r[3],`<b>${A.amount(r[1])}</b>`)}</div>`).join('')}</section>`:''}<section><h4>${t('相关新闻','Related stories')}</h4>${A.D.news.filter(n=>n.cos?.includes(id)).slice(0,5).map(n=>`<button class="rail-story" data-article="${E(n.id)}">${E(A.title(n))}<small>${A.date(n.d)} · ${E(n.src)}</small></button>`).join('')||`<small>${t('暂无索引记录','No indexed stories')}</small>`}</section>`;
  };
  A.attachRail=()=>{
    const pinButton=()=>{if(!$('#railPin'))$('#newsRail')?.insertAdjacentHTML('afterbegin',`<button id="railPin" class="icon-button ${S.railPinned?'active':''}" title="${S.railPinned?t('取消固定','Unpin context'):t('固定公司资料','Pin context')}" aria-label="${t('固定公司资料','Pin context')}" aria-pressed="${!!S.railPinned}">${I('pin')}</button>`);A.iconize();};
    pinButton();
    $$('.news-row').forEach(row=>{
      row.addEventListener('mouseenter',()=>{if(S.railPinned)return;const n=A.D.news.find(n=>n.id===row.dataset.news);if(n?.cos?.length){$('#newsRail').innerHTML=A.rail(n.cos[0]);pinButton();}});
    });
  };
  function applyTheme(theme){S.theme=theme;document.documentElement.dataset.theme=theme==='system'?(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'):theme;save('theme',theme);}
  function settings(){
    $('#settings').innerHTML=`<h3>${t('外观','Appearance')}</h3><div class="segments">${[['light','白色','Light'],['dark','黑色','Dark'],['system','系统','System']].map(([v,zh,en])=>`<button data-theme="${v}" class="${S.theme===v?'active':''}">${t(zh,en)}</button>`).join('')}</div><h3>${t('语言','Language')}</h3><div class="segments"><button data-lang="zh" class="${S.lang==='zh'?'active':''}">中文</button><button data-lang="en" class="${S.lang==='en'?'active':''}">English</button></div><h3>${t('原日报','Daily editions')}</h3><a href="../latest.html" target="_blank">AI Robot News ${I('external-link')}</a><a href="../../stock-market-daily/latest.html" target="_blank">Stock Market Daily ${I('external-link')}</a><a href="../dexterous-hand-news/latest.html" target="_blank">Dexterous Hand News ${I('external-link')}</a><a href="#status">${t('更新状态与数据来源','Update status & sources')}</a><div class="source-credit">${t('产业资料索引参考','Industry index references')} ${external(A.D.reference_url,'RobotOverflow')} · ${t('日报与界面由 RoboticsDAO 独立维护','Daily editions & interface by RoboticsDAO')}</div>`;
    A.iconize();
  }
  function filterCompanies(){
    $('#filterTitle').textContent=t('筛选公司','Filter companies');
    $('#filterContent').innerHTML=`<div class="filter-tools"><input id="companySearch" type="search" placeholder="${t('搜索公司','Find a company')}"><button class="compact" id="selectAll">${t('全选','All')}</button><button class="compact" id="selectNone">${t('全不选','None')}</button><span id="selectedCount" class="muted"></span></div><div id="filterGroups"></div>`;
    const draw=()=>{
      const q=$('#companySearch').value.toLowerCase();
      $('#selectedCount').textContent=`${S.companies===null?A.D.companies.length:S.companies.size} / ${A.D.companies.length}`;
      $('#filterGroups').innerHTML=Object.entries(A.D.segments).map(([seg,label])=>{
        const cs=A.D.companies.filter(c=>c.seg===seg&&(!q||Object.values(c.name).join(' ').toLowerCase().includes(q)));
        return cs.length?`<section class="filter-segment"><h3><button data-segment="${E(seg)}">${E(L(label))}</button><small>${cs.filter(c=>A.picked(c.id)).length}/${cs.length}</small></h3><div class="filter-company-grid">${cs.map(c=>`<label class="filter-company"><input type="checkbox" data-company="${E(c.id)}" ${A.picked(c.id)?'checked':''}>${A.logo(c.id)}<span>${E(A.name(c.id))}</span></label>`).join('')}</div></section>`:'';
      }).join('')||`<div class="empty">${t('没有匹配公司','No matching company')}</div>`;
    };
    $('#companySearch').oninput=draw;
    $('#selectAll').onclick=()=>{S.companies=null;A.selectionChanged();draw();};
    $('#selectNone').onclick=()=>{S.companies=new Set();A.selectionChanged();draw();};
    $('#filterGroups').onchange=e=>{const id=e.target.dataset.company;if(!id)return;if(S.companies===null)S.companies=new Set(A.D.companies.map(c=>c.id));e.target.checked?S.companies.add(id):S.companies.delete(id);A.selectionChanged();draw();};
    $('#filterGroups').onclick=e=>{const seg=e.target.closest('[data-segment]')?.dataset.segment;if(!seg)return;const ids=A.D.companies.filter(c=>c.seg===seg).map(c=>c.id);if(S.companies===null)S.companies=new Set(A.D.companies.map(c=>c.id));const all=ids.every(id=>S.companies.has(id));ids.forEach(id=>all?S.companies.delete(id):S.companies.add(id));A.selectionChanged();draw();};
    $('#filterGroups').ondblclick=e=>{const id=e.target.closest('[data-company]')?.dataset.company||e.target.closest('.filter-company')?.querySelector('input')?.dataset.company;const seg=e.target.closest('[data-segment]')?.dataset.segment;if(id||seg){S.companies=new Set(id?[id]:A.D.companies.filter(c=>c.seg===seg).map(c=>c.id));A.selectionChanged();draw();}};
    draw();$('#filterLayer').hidden=false;$('#companySearch').focus();
  }
  document.addEventListener('click',e=>{
    const bet=e.target.closest('[data-bet]');if(bet)A.open('bet',bet.dataset.bet);
    if(e.target.closest('#railPin')){S.railPinned=!S.railPinned;const button=$('#railPin');button.classList.toggle('active',S.railPinned);button.setAttribute('aria-pressed',S.railPinned);button.title=S.railPinned?t('取消固定','Unpin context'):t('固定公司资料','Pin context');}
    const co=e.target.closest('[data-co]'),story=e.target.closest('[data-article]'),layer=e.target.closest('[data-layer]'),event=e.target.closest('[data-event]'),relation=e.target.closest('[data-relation]'),saved=e.target.closest('[data-save]');
    if(co)A.open('co',co.dataset.co);else if(story)A.open('article',story.dataset.article);else if(layer)A.open('layer',layer.dataset.layer);else if(event)A.open('event',event.dataset.event);else if(relation)A.open('relation',relation.dataset.relation);
    else if(saved){const id=saved.dataset.save;S.saved.has(id)?S.saved.delete(id):S.saved.add(id);save('saved',[...S.saved]);saved.classList.toggle('on',S.saved.has(id));saved.setAttribute('aria-pressed',S.saved.has(id));if(S.onlySaved)A.render();}
    if(e.target.closest('[data-close]'))A.close();
    if(e.target.closest('[data-filter-close]')){$('#filterLayer').hidden=true;$('#companyFilter').focus();}
    const nb=e.target.closest('.nav-group>button');if(nb){const el=nb.parentElement;const open=!el.classList.contains('open');$$('.nav-group.open').forEach(n=>n.classList.remove('open'));el.classList.toggle('open',open);nb.setAttribute('aria-expanded',open);}
    else if(!e.target.closest('.nav-group'))$$('.nav-group.open').forEach(n=>n.classList.remove('open'));
    if(e.target.closest('.nav-menu a'))$$('.nav-group.open').forEach(n=>n.classList.remove('open'));
    const theme=e.target.closest('button[data-theme]');if(theme){applyTheme(theme.dataset.theme);settings();A.refresh();}
    const lang=e.target.closest('[data-lang]');if(lang){S.lang=lang.dataset.lang;save('lang',S.lang);document.documentElement.lang=S.lang==='zh'?'zh-CN':'en';settings();route();}
    if(!e.composedPath().includes($('#settings'))&&!e.composedPath().includes($('#settingsButton')))$('#settings').hidden=true;
  });
  document.addEventListener('keydown',e=>{
    if(e.key==='Escape'){if(!$('#filterLayer').hidden)$('#filterLayer').hidden=true;else if(!$('#modalLayer').hidden)A.close();$('#settings').hidden=true;$$('.nav-group.open').forEach(n=>n.classList.remove('open'));}
    if(e.key==='Tab'){
      const root=!$('#filterLayer').hidden?$('#filterLayer'):!$('#modalLayer').hidden?$('#modalLayer'):null;if(!root)return;
      const els=$$('button:not([disabled]),a[href],input,select,[tabindex="0"]',root).filter(n=>n.offsetParent!==null);if(!els.length)return;
      if(e.shiftKey&&document.activeElement===els[0]){e.preventDefault();els.at(-1).focus();}else if(!e.shiftKey&&document.activeElement===els.at(-1)){e.preventDefault();els[0].focus();}
    }
  });
  $('#companyFilter').onclick=filterCompanies;$('#settingsButton').onclick=()=>{settings();$('#settings').hidden=!$('#settings').hidden;};
  $('#modalBack').onclick=()=>{if(modalCursor>0){modalTravel=true;location.hash=modalTrail[--modalCursor];}};$('#modalForward').onclick=()=>{if(modalCursor<modalTrail.length-1){modalTravel=true;location.hash=modalTrail[++modalCursor];}};
  A.tooltip=(html,event)=>{const el=$('#tooltip');el.innerHTML=html;el.hidden=false;el.style.left=Math.max(8,Math.min(innerWidth-330,event.clientX+12))+'px';el.style.top=Math.min(innerHeight-130,event.clientY+12)+'px';};
  A.hideTooltip=()=>$('#tooltip').hidden=true;
  async function load(){
    try{
      const response=await fetch('data/catalog.json',{cache:'no-cache'});if(!response.ok)throw new Error('catalog '+response.status);A.D=await response.json();
      const urls=[['robot','../feed.json'],['hand','../dexterous-hand-news/feed.json'],['market','../../stock-market-daily/feed.json']];
      const live=await Promise.allSettled(urls.map(async([kind,url])=>{const r=await fetch(url,{cache:'no-cache'});if(!r.ok)throw new Error(r.status);return [kind,await r.json()];}));
      A.byId=new Map(A.D.companies.map(c=>[c.id,c]));
      const byURL=new Map(A.D.news.map(n=>[canonical(n.url),n]));
      for(const result of live){if(result.status!=='fulfilled')continue;const[kind,feed]=result.value;A.D.feed_status[kind]=feed.status;
        for(const item of feed.articles||[]){const key=canonical(item.url);let n=byURL.get(key);if(!n){const cos=A.D.companies.filter(c=>matchCompany(c,item.headline)).map(c=>c.id);const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(key));n={id:[...new Uint8Array(digest)].map(v=>v.toString(16).padStart(2,'0')).join('').slice(0,16),title:{en:item.headline,zh:item.headline},url:item.url,cos,tags:[]};byURL.set(key,n);}
          Object.assign(n,{d:item.date.replaceAll('.','-'),published_at:item.published_at,src:item.source,summary:item.summary,summary_zh:item.summary_zh,section:item.section,language:item.language,origin:'digest',kind,conf:'body-read',topic:kind==='market'?'markets':kind==='hand'?'hands':n.topic||'robots'});
        }
      }
      A.D.news=[...byURL.values()].sort((a,b)=>b.d.localeCompare(a.d));
      S.date=A.D.asOf.slice(0,7);if(!A.D.debates.find(d=>d.id===S.axisX))S.axisX=A.D.debates.at(-2)?.id;if(!A.D.debates.find(d=>d.id===S.axisY))S.axisY=A.D.debates.at(-1)?.id;
      applyTheme(S.theme);addEventListener('hashchange',route);route();
    }catch(error){$('#main').innerHTML=`<div class="empty"><h2>${t('资料暂时无法载入','Data temporarily unavailable')}</h2><p>${E(error.message)}</p><a href="../latest.html">AI Robot News</a> · <a href="../../stock-market-daily/latest.html">Stock Market Daily</a></div>`;console.error(error);}
  }
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{if(S.theme==='system')applyTheme('system');});
  document.addEventListener('DOMContentLoaded',load);
})();
