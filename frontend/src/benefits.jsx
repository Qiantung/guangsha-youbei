import React,{useEffect,useState} from 'react';
import {Check,RefreshCw,Undo2,Package} from 'lucide-react';
import {api} from './api';
import {Panel,Notice,Metric,Table,Json,fmt} from './components';
import {Friends,SupplyCabinet,SupplyIcon} from './story';

export function BenefitsPage({dataset,result,run,guard,notify,busy}) {
 const [account,setAccount]=useState(null),[pending,setPending]=useState(false),[selected,setSelected]=useState('whistle'),[feedback,setFeedback]=useState('');
 useEffect(()=>{let alive=true;api('/account/'+dataset).then(a=>alive&&setAccount(a)).catch(e=>guard(()=>Promise.reject(e)));return()=>{alive=false}},[dataset,result]);
 const item=account?.catalog.find(i=>i.id===selected);
 const redeem=()=>guard(async()=>{if(pending||!item)return;setPending(true);setFeedback('');try{const r=await api('/redeem',{dataset_id:dataset,item_id:item.id,redemption_id:crypto.randomUUID()});setAccount(r.account);setFeedback(item.name+'的模拟兑换已记入流水。');notify('模拟兑换成功，点数与库存已同步更新。')}finally{setPending(false)}});
 const refresh=()=>guard(async()=>{setAccount(await api('/account/'+dataset));notify('已读取数据库中的最新账户。')});
 const available=account?.balance.available||0;
 const allowed=item?.can_redeem&&!pending&&!busy;
 return <>
  <Notice>年度总额度以人身责任保费为基数，上限10%；库存、物资成本和兑换均为模拟，不收集实际配送地址。</Notice>
  {account?<>
   <div className="benefit-summary"><div className="metric-band"><Metric label="年度已发放" value={fmt(account.balance.granted,2)} unit="权益点"/><Metric label="年度已兑换" value={fmt(account.balance.used,2)} unit="权益点"/><Metric label="可用余额" value={fmt(available,2)} unit={account.balance.closed?'年度已结束':'权益点'}/><Metric label="年度额度上限" value={fmt(account.balance.cap_amount,2)} unit="模拟人身责任保费×10%"/></div><div className="benefit-actions"><button disabled={busy||pending||account.balance.closed} onClick={()=>run(true)}><Check size={16}/>运行达标核算并发放差额</button><button className="secondary" disabled={pending||busy} onClick={refresh}><RefreshCw size={16}/>刷新账户</button></div></div>
   <div className="benefits-layout">
    <section className="cabinet-section"><h2>应急物资库</h2><p className="muted">选一件物资，查看如何把权益点用于模拟准备。</p><SupplyCabinet catalog={account.catalog} selected={selected} onSelect={id=>{setSelected(id);setFeedback('')}} balance={available} uses={account.uses}/></section>
    <Panel title="物资详情" className="packing-note">{item&&<><div className="packing-stage"><div className="packing-box" key={item.id}><span className={'supply-drawing drawing-'+item.id}><SupplyIcon id={item.id} size={70}/></span></div><div className="packing-details"><h3>{item.name}</h3><strong>{item.cost} <small>权益点</small></strong><p>{item.description}</p><small>模拟库存 {item.stock} · {item.can_redeem?'兑换后剩余 '+fmt(item.available_after,2)+' 点':'当前不可兑换'}</small></div></div><p>模拟兑换 · 无实际配送</p><button className="wide" disabled={!allowed} onClick={redeem}><Package size={17}/>{pending?'兑换中…':'模拟兑换'}</button><p className="feedback" aria-live="polite">{feedback|| (account.balance.closed?'本模拟年度已结束。':available<item.cost?'当前额度不足，仍可查看物资。':'每次兑换均由后端核验余额与库存。')}</p></>}</Panel>
   </div>
   <div className="two-col benefit-history"><Panel title="兑换与冲正流水" description="收藏的是准备记录；冲正会返还点数并恢复模拟库存。"><Table columns={['物资','消耗点数','状态','操作']} rows={account.uses.map(r=>[account.catalog.find(i=>i.id===r.item)?.name||r.item,r.cost,r.status==='success'?'兑换成功':'已冲正',<button className="text-button" disabled={r.status!=='success'||pending||busy} onClick={()=>guard(async()=>{setPending(true);try{setAccount((await api('/reverse',{dataset_id:dataset,redemption_id:r.redemption_id})).account);notify('已冲正，余额与库存已更新。')}finally{setPending(false)}})}><Undo2 size={14}/>模拟失败冲正</button>])}/></Panel><Panel title="年度差额发放"><Table columns={['周期结束','新增权益点']} rows={account.grants.map(g=>[g.period,fmt(g.amount,6)])}/><details><summary>年度结束演示</summary><p>关闭当前模拟年度，未使用点数转为过期，历史流水保留。此年度无法再新增发放或兑换。</p><button className="secondary" disabled={account.balance.closed||pending||busy} onClick={()=>guard(async()=>{setAccount(await api('/close-year/'+dataset,{}));notify('本模拟年度已关闭，未使用余额转为过期。')})}>模拟年度结束并清零</button></details></Panel></div>
  </>:<Panel title="准备权益账户"><p>正在读取本地账户…</p></Panel>}
  {result&&<Json value={result.incentive} label="达标状态与年度额度核算"/>}
 </>;
}
