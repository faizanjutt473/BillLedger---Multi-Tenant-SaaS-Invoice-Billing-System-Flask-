const INV=[
{id:'INV-1042',client:'Nadeem Traders',date:'2026-10-24',due:'2026-11-08',amount:184500,status:'paid'},
{id:'INV-1043',client:'Bright Pixel Agency',date:'2026-10-26',due:'2026-11-10',amount:96000,status:'sent'},
{id:'INV-1044',client:'Lahore Fabrics',date:'2026-10-02',due:'2026-10-17',amount:312000,status:'overdue'},
{id:'INV-1045',client:'Mehr Clinic',date:'2026-10-29',due:'2026-11-13',amount:45000,status:'draft'},
{id:'INV-1046',client:'Nadeem Traders',date:'2026-10-30',due:'2026-11-14',amount:128750,status:'sent'}];
const PKR=n=>'Rs '+n.toLocaleString('en-PK');
const ROLE=(()=>{try{return localStorage.getItem('role')||'admin'}catch(e){return 'admin'}})();
const A=['admin','accountant'],ALL=['admin','accountant','client'];
const NAV=[['dashboard','Dashboard',A],['invoices','Invoices',ALL],['create-invoice','New invoice',A],['clients','Clients',A],['recurring','Recurring',A],['payments','Payments',ALL],['team','Team and reminders',['admin']]];
function toast(m){const t=document.createElement('div');t.className='toast';t.setAttribute('role','status');t.textContent=m;document.body.append(t);setTimeout(()=>t.remove(),2500)}
function shell(){
  const b=document.body,pg=b.dataset.page;if(!pg)return;
  const main=document.createElement('div');main.className='main';
  main.innerHTML=`<header class="top"><button class="btn ghost menu" aria-label="Open menu">Menu</button><h1>${b.dataset.title}</h1><input type="search" placeholder="Search invoices or clients" aria-label="Search"><a class="btn" href="create-invoice.html">New invoice</a></header>`;
  const wrap=b.querySelector('.wrap');main.append(wrap);
  const side=document.createElement('aside');side.className='side';
  side.innerHTML=`<a class="logo" href="dashboard.html" style="display:block">Bill<b>Ledger</b></a><div class="tenant"><label for="tn" style="color:#9fb8b5">Company</label><select id="tn"><option>Sparking Traders</option><option>Hussain Academy</option></select></div><nav class="nav">${NAV.filter(n=>n[2].includes(ROLE)).map(([h,t])=>`<a href="${h}.html" class="${h===pg?'on':''}">${t}</a>`).join('')}</nav><div class="me"><label for="role" style="color:#9fb8b5">Viewing as</label><select id="role" style="background:none;border:0;color:#fff;font-weight:700;padding:0"><option value="admin">Admin</option><option value="accountant">Accountant</option><option value="client">Client</option></select><br><a href="login.html">Log out</a></div>`;
  const s=document.createElement('div');s.className='shell';s.append(side,main);b.prepend(s);
  main.querySelector('.menu').onclick=()=>side.classList.toggle('open');
  const rs=document.getElementById('role');rs.value=ROLE;rs.onchange=()=>{try{localStorage.setItem('role',rs.value)}catch(e){}location.href='invoices.html'};
  const me=NAV.find(n=>n[0]===pg);if(me&&!me[2].includes(ROLE))location.replace('invoices.html');
  document.getElementById('tn').onchange=e=>toast('Switched to '+e.target.value);
}
function rows(list){return list.length?list.map(i=>`<tr><td><a href="invoice-view.html#${i.id}"><b>${i.id}</b></a></td><td>${i.client}</td><td>${i.due}</td><td class="r">${PKR(i.amount)}</td><td><span class="tag ${i.status}">${i.status}</span></td></tr>`).join(''):'<tr><td colspan="5" class="empty">No invoices here yet. Create your first invoice.</td></tr>'}
function dashboard(){
  const sum=s=>INV.filter(i=>!s||i.status===s).reduce((a,i)=>a+i.amount,0);
  document.getElementById('stats').innerHTML=[['Billed this month',sum()],['Paid',sum('paid')],['Awaiting payment',sum('sent')],['Overdue',sum('overdue')]].map(([l,v],k)=>`<div class="card stat ${k==3?'due':''}"><small>${l}</small><strong>${PKR(v)}</strong></div>`).join('');
  const m=[['May',210],['Jun',260],['Jul',240],['Aug',330],['Sep',290],['Oct',767]];
  document.getElementById('chart').innerHTML=m.map(([n,v])=>`<div>${v}k<i style="height:${v/8}%"></i>${n}</div>`).join('');
  document.getElementById('recent').innerHTML=rows(INV.slice(0,4));
}
function invoices(){
  const body=document.getElementById('list'),tabs=document.querySelectorAll('.tabs button');
  const draw=()=>{const f=document.querySelector('.tabs .on').dataset.f,q=document.getElementById('q').value.toLowerCase();
    body.innerHTML=rows(INV.filter(i=>(f==='all'||i.status===f)&&(i.client+i.id).toLowerCase().includes(q)))};
  tabs.forEach(t=>t.onclick=()=>{tabs.forEach(x=>x.classList.remove('on'));t.classList.add('on');draw()});
  document.getElementById('q').oninput=draw;draw();
}
function create(){
  const tb=document.getElementById('lines');
  const add=()=>{const r=document.createElement('tr');r.innerHTML=`<td><input placeholder="Item or service" aria-label="Description"></td><td style="width:80px"><input type="number" min="1" value="1" class="q" aria-label="Quantity"></td><td style="width:130px"><input type="number" min="0" value="0" class="p" aria-label="Price"></td><td class="r a" style="width:120px">Rs 0</td><td><button type="button" class="btn ghost" aria-label="Remove line">x</button></td>`;
    r.querySelector('button').onclick=()=>{r.remove();calc()};tb.append(r)};
  const calc=()=>{let sub=0;tb.querySelectorAll('tr').forEach(r=>{const a=r.querySelector('.q').value*r.querySelector('.p').value;r.querySelector('.a').textContent=PKR(a);sub+=a});
    const tax=sub*document.getElementById('tax').value/100;document.getElementById('sub').textContent=PKR(sub);document.getElementById('taxv').textContent=PKR(tax);document.getElementById('tot').textContent=PKR(sub+tax)};
  tb.addEventListener('input',calc);document.getElementById('tax').oninput=calc;
  document.getElementById('add').onclick=add;add();
  document.getElementById('save').onclick=()=>toast('Invoice saved as draft');
  document.getElementById('send').onclick=()=>toast('Invoice sent to client');
}
const CL=[['Nadeem Traders','nadeem@example.com',3,'Rs 313,250'],['Bright Pixel Agency','accounts@brightpixel.example',1,'Rs 96,000'],['Lahore Fabrics','finance@lahorefabrics.example',1,'Rs 312,000']];
const REC=[['Nadeem Traders','Monthly retainer',60000,'Monthly','2026-11-15',1],['Mehr Clinic','Software support',15000,'Monthly','2026-11-20',1],['Bright Pixel Agency','Hosting',24000,'Yearly','2027-03-01',0]];
const GW=[['Stripe','Cards, international',1],['Paymob','Cards and wallets in Pakistan',0],['Bank transfer','Manual confirmation',1]];
const PAYS=[['2026-10-28','INV-1042','Nadeem Traders','Stripe',184500],['2026-10-20','INV-1039','Mehr Clinic','Bank transfer',45000]];
const TEAM=[['Faizan','faizan@company.example','admin'],['Ayesha','ayesha@company.example','accountant'],['Nadeem Traders','nadeem@example.com','client']];
function clients(){const t=document.getElementById('cl');const d=()=>t.innerHTML=CL.map(c=>`<tr><td><b>${c[0]}</b></td><td>${c[1]}</td><td class="r">${c[2]}</td><td class="r">${c[3]}</td></tr>`).join('');d();
  document.getElementById('cf').onsubmit=e=>{e.preventDefault();CL.unshift([cn.value,ce.value,0,'Rs 0']);e.target.reset();d();toast('Client added')}}
function recurring(){const t=document.getElementById('rc');const d=()=>{t.innerHTML=REC.map((r,k)=>`<tr><td><b>${r[0]}</b><br><small>${r[1]}</small></td><td>${r[3]}</td><td>${r[4]}</td><td class="r">${PKR(r[2])}</td><td><button class="btn ghost" data-k="${k}">${r[5]?'Pause':'Resume'}</button> <span class="tag ${r[5]?'paid':'draft'}">${r[5]?'active':'paused'}</span></td></tr>`).join('');
  t.querySelectorAll('button').forEach(b=>b.onclick=()=>{REC[b.dataset.k][5]^=1;d();toast('Schedule updated')})};d()}
function payments(){document.getElementById('gw').innerHTML=GW.map((g,k)=>`<div class="card"><h2>${g[0]}</h2><p style="color:var(--mut)">${g[1]}</p><br><button class="btn ${g[2]?'ghost':''}" data-k="${k}">${g[2]?'Connected':'Connect'}</button></div>`).join('');
  document.querySelectorAll('#gw button').forEach(b=>b.onclick=()=>{const g=GW[b.dataset.k];g[2]^=1;b.textContent=g[2]?'Connected':'Connect';b.className='btn '+(g[2]?'ghost':'');toast(g[0]+(g[2]?' connected':' disconnected'))});
  document.getElementById('py').innerHTML=PAYS.map(p=>`<tr><td>${p[0]}</td><td><b>${p[1]}</b></td><td>${p[2]}</td><td>${p[3]}</td><td class="r">${PKR(p[4])}</td></tr>`).join('')}
function team(){const t=document.getElementById('tm');const d=()=>{t.innerHTML=TEAM.map((m,k)=>`<tr><td><b>${m[0]}</b></td><td>${m[1]}</td><td><select data-k="${k}" aria-label="Role">${['admin','accountant','client'].map(r=>`<option ${r===m[2]?'selected':''}>${r}</option>`).join('')}</select></td></tr>`).join('');
  t.querySelectorAll('select').forEach(x=>x.onchange=()=>{TEAM[x.dataset.k][2]=x.value;toast('Role updated')})};d();
  document.getElementById('inv').onsubmit=e=>{e.preventDefault();TEAM.push([ie.value.split('@')[0],ie.value,ir.value]);e.target.reset();d();toast('Invitation sent')};
  document.getElementById('rem').onclick=()=>toast('Reminder rules saved')}
function view(){const i=INV.find(x=>'#'+x.id===location.hash)||INV[1];
  document.getElementById('doc').innerHTML=`<div class="head"><div><h2 style="font-size:22px">Invoice ${i.id}</h2><span class="tag ${i.status}">${i.status}</span></div><div style="text-align:right"><b>Sparking Traders</b><br><small>Jhang Sadar, Punjab</small></div></div>
  <div class="form2"><div><small>Billed to</small><br><b>${i.client}</b></div><div><small>Issued ${i.date}</small><br><small>Due ${i.due}</small></div></div>
  <table class="tbl"><thead><tr><th>Description</th><th class="r">Amount</th></tr></thead><tbody><tr><td>Services for October</td><td class="r">${PKR(i.amount)}</td></tr></tbody></table>
  <div class="sum"><div class="tot"><span>Total due</span><span>${PKR(i.amount)}</span></div></div>`;
  document.getElementById('pdf').onclick=()=>print();document.getElementById('mail').onclick=()=>toast('Invoice emailed to '+i.client);
  document.getElementById('pay').onclick=()=>toast('Opening payment gateway');document.getElementById('paid').onclick=()=>toast('Marked as paid')}
document.addEventListener('DOMContentLoaded',()=>{shell();({dashboard,invoices,'create-invoice':create,clients,recurring,payments,team,'invoice-view':view})[document.body.dataset.page]?.();
  document.getElementById('login')?.addEventListener('submit',e=>{e.preventDefault();location.href='dashboard.html'})});
