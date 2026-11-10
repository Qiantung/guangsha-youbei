import React from 'react';
import {Home, Leaf, ArrowUpRight, ClipboardCheck, BookOpen, Database, Flashlight, Hand, Battery, Megaphone, Check} from 'lucide-react';

export function BrandMark() {
  return <span className="brand-mark" aria-hidden="true"><Home size={30} strokeWidth={1.5}/><Leaf size={17} strokeWidth={1.5}/></span>;
}

export function Friends({className=''}) {
  return <img className={'friends-art '+className} src="/art/forest-friends.png" alt="" aria-hidden="true"/>;
}

export function StoryHero() {
  return <section className="story-hero" aria-label="广厦有备森林小镇">
    <div className="scene-layer" aria-hidden="true"/>
    <Friends className="hero-friends"/>
    <div className="hero-copy"><h2>把每一份准备，<br/>变成家的安心。</h2><p>从一段日常记录，走向更有准备的生活。</p><small>探索性研究原型 · 数据与健康修正为模拟假设</small></div>
  </section>;
}

export function PageNote({page}) {
  const copy=[null,['翻开日常记录','每一个观测值，都留有自己的来处。'],['一周一页，慢慢积累','完整的观测，才记作一次达标。'],['为家描一张情景图','把建筑条件与这次地震动，分别说清楚。'],['同一幢家，不同的状态','人员状态的改变，只进入人员后果估计。'],['把准备，装进应急箱','权益来自演示规则，物资兑换也只在本地模拟。'],['有问题，一起理一理','让本地工具计算，把过程留在手账里。'],['每一条依据，都有来处','把标准参考、模拟假设和待补证项分开记录。']][page];
  if(!copy||page===5)return null;
  return <div className={'page-note note-'+page}><div><h2>{copy[0]}</h2><p>{copy[1]}</p></div><Friends/></div>;
}

export function NotebookLinks({setPage}) {
  const entries=[{title:'方法与验证',body:'参考与假设，都在这里认真记录。',page:7,Icon:BookOpen,tone:'lavender'}, {title:'防灾手账',body:'查询风险，生成一份自己的防灾报告。',page:6,Icon:ClipboardCheck,tone:'sky'}, {title:'日常数据记录',body:'翻看四周记录，认识数据的质量。',page:1,Icon:Database,tone:'mint'}];
  return <div className="notebook-links">{entries.map(({title,body,page,Icon,tone})=><button className={'notebook-link '+tone} key={title} onClick={()=>setPage(page)}><Icon size={30} strokeWidth={1.4}/><span><b>{title} <ArrowUpRight size={16}/></b><small>{body}</small></span></button>)}</div>;
}

const items={whistle:Megaphone,battery:Battery,gloves:Hand,torch:Flashlight};
export function SupplyIcon({id,size=52}) {if(items[id])return <span className={'prop-sprite prop-'+id} style={{width:size*1.5,height:size*1.5}} aria-hidden="true"/>;return <ClipboardCheck size={size} strokeWidth={1.35} aria-hidden="true"/>;}

export function SupplyCabinet({catalog,selected,onSelect,balance,uses}) {
  return <div className="supply-cabinet" aria-label="应急物资陈列柜"><div className="cabinet-sign"><Leaf size={16}/> 小小物资柜</div><div className="supply-shelves">{catalog.map(item=>{
    const collected=uses.some(r=>r.item===item.id&&r.status==='success');
    return <button key={item.id} aria-label={'选择'+item.name} aria-pressed={selected===item.id} className={'supply-object '+(selected===item.id?'selected ':'')+(balance<item.cost?'unavailable':'')} onClick={()=>onSelect(item.id)}>
      <span className={'supply-drawing drawing-'+item.id}><SupplyIcon id={item.id}/>{collected&&<Check className="supply-check" size={17}/>}</span><b>{item.name}</b><small>{item.cost} 权益点 · 库存 {item.stock}</small><span className="selection-label">{selected===item.id?'已放入准备位':collected?'有兑换记录':balance>=item.cost?'查看这件物资':'额度不足 · 可查看'}</span>
    </button>;
  })}</div></div>;
}
