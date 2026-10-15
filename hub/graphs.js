(() => {
  'use strict';
  const A=window.App,{S,E,t,L,I,$,$$,external}=A;
  const d3=window.d3;
  const parse=d3.utcParse('%Y-%m');
  const month=d3.utcFormat('%Y-%m');
  const themeColor=key=>getComputedStyle(document.documentElement).getPropertyValue('--'+key).trim();
  const edgeType=e=>({partner:'partners',alt:'alternative',compete:'competes',supply:'supplies'})[e.type]||e.type;
  const pastMonths=n=>{const d=parse(A.D.asOf.slice(0,7));return d3.utcMonth.range(d3.utcMonth.offset(d,-n+1),d3.utcMonth.offset(d,1)).map(month);};
  function svgHost(selector,width,height){const host=$(selector);host.innerHTML='';return d3.select(host).append('svg').attr('viewBox',`0 0 ${width} ${height}`).attr('role','img');}
  function logoNode(g,id,r=13){
    const c=A.co(id);g.append('circle').attr('r',r).attr('fill','#fff').attr('stroke',A.color(c.seg)).attr('stroke-width',2);
    g.append('image').attr('href',c.logo||'assets/robot-anatomy.png').attr('x',-r+4).attr('y',-r+4).attr('width',r*2-8).attr('height',r*2-8).attr('preserveAspectRatio','xMidYMid meet');
  }
  A.drawValue=(selector,rows)=>{
    const valid=rows.filter(r=>parse(r[0])&&Number.isFinite(+r[1]));if(!valid.length){$(selector).innerHTML=A.empty();return;}
    const W=$(selector).clientWidth||600,H=180,svg=svgHost(selector,W,H),x=d3.scaleTime().domain(d3.extent(valid,r=>parse(r[0]))).range([60,W-15]),y=d3.scaleLinear().domain([0,d3.max(valid,r=>+r[1])*1.1]).range([H-30,15]);
    svg.append('g').attr('transform',`translate(0,${H-30})`).call(d3.axisBottom(x).ticks(Math.min(5,valid.length)).tickFormat(d3.timeFormat('%Y.%m')));
    svg.append('g').attr('transform','translate(60,0)').call(d3.axisLeft(y).ticks(3).tickFormat(v=>A.amount(v)));
    svg.append('path').datum(valid).attr('d',d3.line().x(r=>x(parse(r[0]))).y(r=>y(+r[1])).curve(d3.curveStepAfter)).attr('fill','none').attr('stroke',themeColor('accent')).attr('stroke-width',2);
    svg.selectAll('.point').data(valid).join('circle').attr('cx',r=>x(parse(r[0]))).attr('cy',r=>y(+r[1])).attr('r',3).attr('fill',themeColor('accent')).append('title').text(r=>`${r[0]} ${A.amount(r[1])}`);
  };
  A.drawSparks=()=>$$('[data-spark]').forEach(host=>{
    const rows=(A.D.valHist[host.dataset.spark]||[]).filter(r=>r[0]<=S.date);if(!rows.length)return;
    const x=d3.scaleLinear().domain([0,Math.max(1,rows.length-1)]).range([2,92]),extent=d3.extent(rows,r=>r[1]);if(extent[0]===extent[1])extent[0]=0;
    const y=d3.scaleLinear().domain(extent).range([27,3]),svg=d3.select(host).append('svg').attr('viewBox','0 0 95 30');
    svg.append('path').datum(rows).attr('d',d3.line().x((r,i)=>x(i)).y(r=>y(r[1])).curve(d3.curveStepAfter)).attr('stroke',themeColor('accent')).attr('stroke-width',1.5).attr('fill','none');
    svg.selectAll('circle').data(rows).join('circle').attr('cx',(r,i)=>x(i)).attr('cy',r=>y(r[1])).attr('r',1.5).attr('fill',themeColor('accent'));
  });
  A.drawEvolution=(selector,id)=>{
    const categories=[t('估值','Value'),t('融资','Funding'),t('里程碑','Milestones'),t('技术栈','Stack'),t('产业关系','Relations'),t('技术路线','Bets')],rows=[];
    const add=(kind,date,label,url)=>{if(parse(date))rows.push({kind,date,label,url});};
    (A.D.valHist[id]||[]).forEach(r=>add(0,r[0],A.amount(r[1])+' · '+L(r[2]),r[3]));
    (A.D.rounds[id]||[]).forEach(r=>add(1,r[0],A.amount(r[1])+' · '+L(r[2]),r[3]));
    (A.D.roadmap.find(r=>r.id===id)?.items||[]).forEach(r=>add(2,r.d,L(r.label)+' · '+A.statusName(r.s),r.src));
    Object.entries(A.D.stack[id]||{}).forEach(([layer,history])=>history.forEach(r=>add(3,r[0],L(A.D.layers.find(l=>l.id===layer))+' · '+(r[1]==='in'?t('自研','In-house'):A.byId.has(r[1])?A.name(r[1]):r[1]),r[2]?.s?.[0])));
    A.D.edges.filter(e=>e.a===id||e.b===id).forEach(e=>{const label=A.relationName(e.type)+' · '+A.name(e.a===id?e.b:e.a);add(4,e.from,label,Array.isArray(e.src)?e.src[0]:e.src);if(e.to)add(4,e.to,label+' · '+t('结束','Ended'),Array.isArray(e.src)?e.src[0]:e.src);});
    Object.entries(A.D.betHist[id]||{}).forEach(([key,history])=>{const d=A.D.debates.find(d=>d.id===key);if(d)history.forEach(r=>add(5,r[0],L(d.q)+' · '+A.posLabel(d,r[1]),A.D.reference_url));});
    if(!rows.length){$(selector).innerHTML=A.empty();return;}
    const W=$(selector).clientWidth||600,H=300,extent=d3.extent(rows,r=>parse(r.date));if(+extent[0]===+extent[1])extent[1]=d3.utcMonth.offset(extent[1],1);
    const x=d3.scaleTime().domain(extent).range([75,W-20]),y=i=>25+i*40,svg=svgHost(selector,W,H);
    categories.forEach((label,i)=>{svg.append('text').attr('x',0).attr('y',y(i)+4).attr('font-size',11).attr('fill',themeColor('muted')).text(label);svg.append('line').attr('x1',75).attr('x2',W-20).attr('y1',y(i)).attr('y2',y(i)).attr('stroke',themeColor('line'));});
    svg.append('g').attr('transform',`translate(0,${H-35})`).call(d3.axisBottom(x).ticks(innerWidth<760?3:6).tickFormat(d3.timeFormat('%Y.%m')));
    svg.selectAll('.evolution-event').data(rows).join('circle').attr('class','evolution-event').attr('cx',r=>x(parse(r.date))).attr('cy',(r,i)=>y(r.kind)+(i%3-1)*6).attr('r',4).attr('fill',r=>d3.schemeTableau10[r.kind]).attr('role','link').attr('tabindex',0).attr('aria-label',r=>r.date+' '+r.label).style('cursor','pointer').on('mouseenter',(e,r)=>A.tooltip(E(r.date)+'<br>'+E(r.label),e)).on('mouseleave',A.hideTooltip).on('click',(e,r)=>{if(r.url)window.open(A.safe(r.url),'_blank','noopener,noreferrer');}).on('keydown',(e,r)=>{if(e.key==='Enter'&&r.url)window.open(A.safe(r.url),'_blank','noopener,noreferrer');}).append('title').text(r=>r.date+' · '+r.label);
  };
  function milestones(){
    const all=A.D.roadmap.filter(r=>A.picked(r.id)).flatMap(r=>r.items.map((event,index)=>({id:r.id,index,event})));
    const counts=Object.fromEntries(['open','risk','hit','slipped'].map(s=>[s,all.filter(r=>r.event.s===s).length]));
    const start=d3.utcMonth.offset(parse(A.D.asOf.slice(0,7)),-12),end=d3.utcMonth.offset(start,36),extent=end-start;
    const pct=value=>Math.max(0,Math.min(100,(parse(value)-start)/extent*100));
    $('#main').innerHTML=`<div class="stats">${Object.entries(counts).map(([key,count])=>`<div class="stat"><button data-status="${key}"><strong>${count}</strong><small>${E(A.statusName(key))}</small></button></div>`).join('')}</div><div class="toolbar"><select id="milestoneStatus" aria-label="${t('里程碑状态','Milestone status')}">${A.options([['all',t('全部状态','All statuses')],...Object.keys(counts).map(s=>[s,A.statusName(s)])],S.milestone)}</select><span class="muted">${t('时间线：前12个月至未来24个月','Timeline: past 12 to next 24 months')}</span></div><div class="timeline-wrap"><div class="timeline"><div class="time-head"><span></span><div class="time-axis">${d3.utcMonth.range(start,end,3).map(d=>`<span>${month(d)}</span>`).join('')}</div></div>${A.D.roadmap.filter(r=>A.picked(r.id)&&r.items.some(e=>S.milestone==='all'||e.s===S.milestone)).map(r=>`<div class="time-row">${A.coButton(r.id,false)}<div class="time-track"><i class="time-today" style="left:${pct(A.D.asOf.slice(0,7))}%"></i>${r.items.map((event,index)=>({event,index})).filter(({event})=>(S.milestone==='all'||event.s===S.milestone)&&parse(event.d)>=start&&parse(event.d)<=end).map(({event,index},i)=>`<button class="time-event ${E(event.s)}" style="left:${pct(event.d)}%;top:${14+(i%3)*12}px" data-event="${E(r.id+'~'+index)}" title="${E(A.date(event.d)+' · '+L(event.label)+' · '+A.statusName(event.s))}" aria-label="${E(L(event.label))}"></button>`).join('')}</div></div>`).join('')}</div></div><div class="notice">${t('已承诺、风险、延误与已达成严格区分；未来目标不视为已完成。','Promises, risks, delays and achievements remain distinct; future targets are not completed events.')}</div>`;
    $('#milestoneStatus').onchange=e=>{S.milestone=e.target.value;A.render();};$$('[data-status]').forEach(el=>el.onclick=()=>{S.milestone=S.milestone===el.dataset.status?'all':el.dataset.status;A.render();});
  }
  A.register('milestones',milestones);
  function finance(){
    const months=pastMonths(+S.period),records=Object.entries(A.D.rounds).filter(([id])=>A.picked(id)).flatMap(([id,rows])=>rows.map(r=>({id,d:r[0],amount:+r[1],round:L(r[2]),url:r[3]}))).filter(r=>r.amount>0&&r.d>=months[0]&&r.d<=months.at(-1));
    const sums=d3.rollup(records,rows=>d3.sum(rows,r=>r.amount),r=>A.co(r.id).seg);
    $('#main').innerHTML=`<div class="toolbar"><select id="financePeriod" aria-label="${t('融资时间范围','Funding period')}">${A.options([[12,t('近12个月','Past 12 months')],[24,t('近24个月','Past 24 months')],[36,t('近36个月','Past 36 months')]],S.period)}</select><span class="muted">${records.length} ${t('轮有公开金额的融资','rounds with public amounts')}</span><span class="spacer"></span>${external(A.D.reference_url,t('来源索引','Source index'))}</div><div class="stats">${[...sums].sort((a,b)=>b[1]-a[1]).slice(0,4).map(([seg,value])=>`<div class="stat"><strong>${A.amount(value)}</strong><small><i class="dot" style="background:${A.color(seg)}"></i>${E(L(A.D.segments[seg]))}</small></div>`).join('')}</div><div class="chart-section"><div class="chart-host" id="fundChart"></div></div><div class="notice">${t('单轮金额采用对数刻度；仅统计资料中有金额与出处的轮次，不代表实时市场估值。','Log scale for round sizes. Only rounds with disclosed amounts and evidence are included; these are not live valuations.')}</div><div class="table-wrap"><table><thead><tr><th>${t('公司','Company')}</th><th>${t('日期','Date')}</th><th>${t('轮次','Round')}</th><th>${t('金额','Amount')}</th><th>${t('来源','Source')}</th></tr></thead><tbody>${records.slice().sort((a,b)=>b.d.localeCompare(a.d)).map(r=>`<tr><td>${A.coButton(r.id,false)}</td><td>${A.date(r.d)}</td><td>${E(r.round)}</td><td>${A.amount(r.amount)}</td><td>${external(r.url,t('原始来源','Evidence'))}</td></tr>`).join('')}</tbody></table></div>`;
    $('#financePeriod').onchange=e=>{S.period=+e.target.value;A.render();};
    if(!records.length){$('#fundChart').innerHTML=A.empty();return;}
    const W=$('#fundChart').clientWidth||1200,H=570,svg=svgHost('#fundChart',W,H),left=innerWidth<760?66:90;
    const x=d3.scaleTime().domain([parse(months[0]),d3.utcMonth.offset(parse(months.at(-1)),1)]).range([left,W-20]);
    const y=d3.scaleLog().domain([Math.max(.00001,d3.min(records,r=>r.amount)*.6),d3.max(records,r=>r.amount)*1.5]).range([H-130,25]);
    svg.append('g').attr('transform',`translate(${left},0)`).call(d3.axisLeft(y).ticks(5).tickFormat(v=>A.amount(v))).call(g=>g.selectAll('.tick line').attr('x2',W-left-20));
    svg.append('g').attr('transform',`translate(0,${H-30})`).call(d3.axisBottom(x).ticks(innerWidth<760?4:12).tickFormat(d3.timeFormat('%Y.%m')));
    records.forEach((r,i)=>{
      const date=parse(r.d),offset=((i%5)-2)*4,g=svg.append('g').attr('transform',`translate(${x(date)+offset},${y(r.amount)})`).style('cursor','pointer').attr('tabindex',0).attr('role','button').attr('aria-label',A.name(r.id)+' '+A.amount(r.amount));logoNode(g,r.id,10);
      g.on('mouseenter',e=>A.tooltip(`${E(A.name(r.id))}<br>${A.date(r.d)} · ${E(r.round)}<br><b>${A.amount(r.amount)}</b>`,e)).on('mouseleave',A.hideTooltip).on('click',()=>A.open('co',r.id)).on('keydown',e=>{if(e.key==='Enter')A.open('co',r.id);});
    });
    const totals=d3.rollup(records,v=>d3.sum(v,r=>r.amount),r=>r.d),barY=d3.scaleLinear().domain([0,d3.max(totals.values())]).range([0,75]),bw=Math.max(5,(W-left-20)/months.length*.55);
    for(const[m,total]of totals){svg.append('rect').attr('x',x(parse(m))-bw/2).attr('y',H-42-barY(total)).attr('width',bw).attr('height',barY(total)).attr('fill',themeColor('accent')).attr('opacity',.7).append('title').text(`${m} ${A.amount(total)}`);}
  }
  A.register('finance',finance);
  function betmap(){
    const dx=A.D.debates.find(d=>d.id===S.axisX)||A.D.debates[0],dy=A.D.debates.find(d=>d.id===S.axisY)||A.D.debates[1];
    const rows=A.companies().filter(c=>A.pos(c.id,dx)!=null&&A.pos(c.id,dy)!=null);
    $('#main').innerHTML=`<div class="toolbar"><label>${t('横轴','Across')}<select id="axisX">${A.options(A.D.debates.map(d=>[d.id,L(d.q)]),dx.id)}</select></label><label>${t('纵轴','Down')}<select id="axisY">${A.options(A.D.debates.map(d=>[d.id,L(d.q)]),dy.id)}</select></label><span class="spacer"></span><small>${rows.length} ${t('家公司','companies')}</small></div><div class="split"><section class="chart-section"><div class="map-legend"><span>${E(L(dx.left))}</span><span>${E(L(dx.right))}</span></div><div class="chart-host" id="betChart"></div></section><aside id="betRail" class="rail">${A.rail(rows[0]?.id||'omakase')}</aside></div><div class="notice">${t('路线位置为参考站分类。公司只有已知的两个轴位置时才进入象限，不对未知项打分。','Only companies with known positions on both selected axes are plotted; unknown positions are not scored.')}</div>`;
    $('#axisX').onchange=e=>{S.axisX=e.target.value;if(S.axisX===S.axisY)S.axisY=A.D.debates.find(d=>d.id!==S.axisX).id;A.render();};
    $('#axisY').onchange=e=>{S.axisY=e.target.value;if(S.axisX===S.axisY)S.axisX=A.D.debates.find(d=>d.id!==S.axisY).id;A.render();};
    const W=$('#betChart').clientWidth||900,H=570,svg=svgHost('#betChart',W,H),x=d3.scaleLinear().domain([0,1]).range([60,W-30]),y=d3.scaleLinear().domain([0,1]).range([40,H-50]);
    for(let i=0;i<5;i++)for(let j=0;j<5;j++)svg.append('rect').attr('x',x(i*.2)).attr('y',y(j*.2)).attr('width',(W-90)/5).attr('height',(H-90)/5).attr('fill','none').attr('stroke',themeColor('line'));
    svg.append('text').attr('x',4).attr('y',20).attr('fill',themeColor('muted')).attr('font-size',10).text(L(dy.left));svg.append('text').attr('x',4).attr('y',H-10).attr('fill',themeColor('muted')).attr('font-size',10).text(L(dy.right));
    const nodes=rows.map((c,i)=>({c,x:x(A.pos(c.id,dx)),y:y(A.pos(c.id,dy)),tx:x(A.pos(c.id,dx)),ty:y(A.pos(c.id,dy))}));
    const sim=d3.forceSimulation(nodes).force('x',d3.forceX(n=>n.tx).strength(.5)).force('y',d3.forceY(n=>n.ty).strength(.5)).force('collide',d3.forceCollide(innerWidth<760?13:18)).stop();for(let i=0;i<150;i++)sim.tick();
    const groups=svg.selectAll('.bet-co').data(nodes).join('g').attr('transform',n=>`translate(${Math.max(28,Math.min(W-20,n.x))},${Math.max(35,Math.min(H-45,n.y))})`).style('cursor','pointer').attr('role','button').attr('tabindex',0).attr('aria-label',n=>A.name(n.c.id));
    groups.each(function(n){logoNode(d3.select(this),n.c.id,innerWidth<760?10:14);}).on('mouseenter',(e,n)=>{A.tooltip(`${E(A.name(n.c.id))}<br>${E(A.posLabel(dx,A.pos(n.c.id,dx)))} · ${E(A.posLabel(dy,A.pos(n.c.id,dy)))}`,e);$('#betRail').innerHTML=A.rail(n.c.id);A.iconize();}).on('mouseleave',A.hideTooltip).on('click',(e,n)=>A.open('co',n.c.id)).on('keydown',(e,n)=>{if(e.key==='Enter')A.open('co',n.c.id);});
  }
  A.register('betmap',betmap);
  function network(){
    const months=pastMonths(24);if(!months.includes(S.date))months.push(S.date);months.sort();
    $('#main').innerHTML=`<div class="toolbar"><select id="netLayout" aria-label="${t('网络布局','Network layout')}">${A.options([['chain',t('产业链','Value chain')],['clusters',t('聚类','Clusters')]],S.netLayout)}</select><select id="netSize" aria-label="${t('节点大小','Node size')}">${A.options([['relations',t('按连接数','By connections')],['val',t('按市值 / 估值','By value')],['raised',t('按融资额','By raised capital')]],S.netSize)}</select><label><input id="showChanges" type="checkbox" ${S.changes?'checked':''}>${t('突出当月变化','Highlight monthly changes')}</label><span class="spacer"></span><span id="netCounts" class="muted"></span></div><div class="legend" id="edgeLegend">${['supplies','partners','competes','invests','acquires','alternative'].map(type=>`<button class="legend-button ${S.edgeTypes.has(type)?'':'off'}" data-edge-type="${type}"><i class="dot" style="background:${({supplies:'#8399a7',partners:'#2781cf',competes:'#c96666',invests:'#8f74b4',acquires:'#394c59',alternative:'#caab49'})[type]}"></i>${E(A.relationName(type))}</button>`).join('')}</div><div class="graph-shell"><div class="graph-toolbar"><button class="icon-button" id="zoomIn" title="${t('放大','Zoom in')}" aria-label="${t('放大','Zoom in')}">${I('plus')}</button><button class="icon-button" id="zoomOut" title="${t('缩小','Zoom out')}" aria-label="${t('缩小','Zoom out')}">${I('minus')}</button><button class="icon-button" id="zoomReset" title="${t('重置视图','Reset view')}" aria-label="${t('重置视图','Reset view')}">${I('maximize')}</button></div><div class="chart-host graph-chart" id="networkChart"></div></div><div class="time-controls"><button class="icon-button" id="playHistory" title="${t('播放历史','Play history')}" aria-label="${t('播放历史','Play history')}">${I('play')}</button><input type="range" id="networkDate" min="0" max="${months.length-1}" value="${Math.max(0,months.indexOf(S.date))}" aria-label="${t('关系网月份','Network month')}"><output id="networkDateLabel">${E(S.date)}</output></div><div class="legend">${Object.entries(A.D.segments).map(([id,name])=>`<span><i class="dot" style="background:${A.color(id)}"></i>${E(L(name))}</span>`).join('')}</div>`;
    const W=$('#networkChart').clientWidth||1200,H=$('#networkChart').clientHeight||650,svg=svgHost('#networkChart',W,H),canvas=svg.append('g');
    const zoom=d3.zoom().scaleExtent([.25,4]).on('zoom',e=>canvas.attr('transform',e.transform));svg.call(zoom);
    $('#zoomIn').onclick=()=>svg.transition().duration(180).call(zoom.scaleBy,1.3);$('#zoomOut').onclick=()=>svg.transition().duration(180).call(zoom.scaleBy,1/1.3);$('#zoomReset').onclick=()=>svg.transition().duration(200).call(zoom.transform,d3.zoomIdentity);
    let sim=null,timer=null;
    function draw(){
      sim?.stop();canvas.selectAll('*').remove();
      const edges=A.D.edges.filter(e=>A.picked(e.a)&&A.picked(e.b)&&A.byId.has(e.a)&&A.byId.has(e.b)&&A.isActive(e)&&S.edgeTypes.has(edgeType(e))).map(e=>({...e,index:A.D.edges.indexOf(e),source:e.a,target:e.b}));
      const counts=d3.rollup(edges.flatMap(e=>[e.a,e.b]),v=>v.length,v=>v),visible=A.companies().filter(c=>counts.has(c.id));
      const nodes=visible.map((c,i)=>({...c,x:W/2+(i%10)*8,y:H/2+Math.floor(i/10)*8,r:Math.max(innerWidth<760?9:10,Math.min(25,S.netSize==='relations'?8+Math.sqrt(counts.get(c.id)||0)*2:9+Math.log10(1+(+c[S.netSize]||0))*4))}));
      $('#netCounts').textContent=`${nodes.length} ${t('节点','nodes')} · ${edges.length} ${t('条关系','relations')}`;
      if(!nodes.length){canvas.append('text').attr('x',W/2).attr('y',H/2).attr('text-anchor','middle').attr('fill',themeColor('muted')).text(t('当前筛选没有关系记录','No relations for these filters'));return;}
      const segments=['component','silicon','maker','brain','data','deployer','investor'];
      const xs={component:.1,silicon:.28,maker:.49,brain:.73,data:.88,deployer:.52,investor:.3};
      const bySegment=d3.group(nodes,c=>c.seg);
      const target=c=>{const peers=bySegment.get(c.seg),i=peers.indexOf(c);if(S.netLayout!=='chain')return {x:W*(.5+.37*Math.cos(segments.indexOf(c.seg)*Math.PI*2/segments.length)),y:H*(.5+.35*Math.sin(segments.indexOf(c.seg)*Math.PI*2/segments.length))};if(['deployer','investor'].includes(c.seg))return {x:W*(.2+.62*(i+.5)/peers.length),y:H*(c.seg==='deployer'?.92:.07)};const cols=c.seg==='maker'?4:2,rows=Math.ceil(peers.length/cols);return {x:W*((xs[c.seg]??.5)+((i%cols)-(cols-1)/2)*.043),y:H*(.2+.6*(Math.floor(i/cols)+.5)/rows)};};
      const edge=canvas.append('g').selectAll('line').data(edges).join('line').attr('class',e=>`graph-edge ${edgeType(e)} ${S.changes&&e.from===S.date?'changed':''}`).attr('role','button').attr('tabindex',0).attr('aria-label',e=>`${A.name(e.a)} ${A.relationName(e.type)} ${A.name(e.b)}`).style('cursor','pointer').on('click',(event,e)=>A.open('relation',e.index)).on('mouseenter',(event,e)=>A.tooltip(`${E(A.name(e.a))} → ${E(A.name(e.b))}<br>${E(A.relationName(e.type))} · ${A.date(e.from)}`,event)).on('mouseleave',A.hideTooltip);
      const node=canvas.append('g').selectAll('g').data(nodes).join('g').attr('class','graph-node').attr('role','button').attr('tabindex',0).attr('aria-label',c=>A.name(c.id));
      node.each(function(c){logoNode(d3.select(this),c.id,c.r);d3.select(this).append('text').attr('text-anchor','middle').attr('y',c.r+12).text(A.name(c.id));});
      node.on('mouseenter',(event,c)=>{const neighbors=new Set(edges.filter(e=>e.a===c.id||e.b===c.id).flatMap(e=>[e.a,e.b]));node.classed('faded',n=>!neighbors.has(n.id));edge.classed('faded',e=>e.a!==c.id&&e.b!==c.id);A.tooltip(`${E(A.name(c.id))}<br>${E(L(A.D.segments[c.seg]))} · ${counts.get(c.id)} ${t('条连接','connections')}`,event);}).on('mouseleave',()=>{node.classed('faded',false);edge.classed('faded',false);A.hideTooltip();}).on('click',(event,c)=>A.open('co',c.id)).on('keydown',(event,c)=>{if(event.key==='Enter')A.open('co',c.id);});
      sim=d3.forceSimulation(nodes).force('link',d3.forceLink(edges).id(c=>c.id).strength(.015).distance(100)).force('charge',d3.forceManyBody().strength(-45)).force('x',d3.forceX(c=>target(c).x).strength(.16)).force('y',d3.forceY(c=>target(c).y).strength(.14)).force('collide',d3.forceCollide(c=>c.r+10)).stop();
      for(let i=0;i<170;i++)sim.tick();
      const tick=()=>{nodes.forEach(c=>{c.x=Math.max(c.r+8,Math.min(W-c.r-8,c.x));c.y=Math.max(c.r+10,Math.min(H-c.r-25,c.y));});edge.attr('x1',e=>e.source.x).attr('y1',e=>e.source.y).attr('x2',e=>e.target.x).attr('y2',e=>e.target.y);node.attr('transform',c=>`translate(${c.x},${c.y})`);};
      tick();node.call(d3.drag().on('start',(event,c)=>{sim.alphaTarget(.2).restart();c.fx=c.x;c.fy=c.y;}).on('drag',(event,c)=>{c.fx=event.x;c.fy=event.y;tick();}).on('end',(event,c)=>{sim.alphaTarget(0);c.fx=null;c.fy=null;}));sim.on('tick',tick);
    }
    $('#netLayout').onchange=e=>{S.netLayout=e.target.value;draw();};$('#netSize').onchange=e=>{S.netSize=e.target.value;draw();};$('#showChanges').onchange=e=>{S.changes=e.target.checked;draw();};
    $$('[data-edge-type]').forEach(button=>button.onclick=()=>{const type=button.dataset.edgeType;S.edgeTypes.has(type)?S.edgeTypes.delete(type):S.edgeTypes.add(type);button.classList.toggle('off',!S.edgeTypes.has(type));draw();});
    $('#networkDate').oninput=e=>{S.date=months[+e.target.value];$('#networkDateLabel').textContent=S.date;draw();};
    $('#playHistory').onclick=()=>{if(timer){clearInterval(timer);timer=null;$('#playHistory').innerHTML=I('play');A.iconize();return;}$('#playHistory').innerHTML=I('pause');A.iconize();timer=setInterval(()=>{const input=$('#networkDate');let next=+input.value+1;if(next>=months.length)next=0;input.value=next;input.dispatchEvent(new Event('input',{bubbles:true}));},1200);};
    A.cleanup=()=>{sim?.stop();clearInterval(timer);A.hideTooltip();};draw();
  }
  A.register('network',network);
})();
