import React from 'react';
import {Home,Database,ChartNoAxesCombined,Building2,Users,ShieldCheck,MessageSquare,FileText,ArrowRight,BookOpen,Check,Leaf} from 'lucide-react';

export const nav=[['项目总览',Home],['数据接入',Database],['时序与规则',ChartNoAxesCombined],['建筑情景',Building2],['人员后果',Users],['防灾权益',ShieldCheck],['智能助手',MessageSquare],['方法与验证',FileText]];
export const fmt=(value,digits=4)=>value===null||value===undefined?'未估计':Number(value).toLocaleString('zh-CN',{maximumFractionDigits:digits});
export function Json({value,label='查看结构化结果'}) {return <details className="json-detail"><summary>{label}</summary><pre>{JSON.stringify(value,null,2)}</pre></details>}
export function Panel({title,description,children,className=''}) {return <section className={'panel '+className}><h2>{title}</h2>{description&&<p className="muted">{description}</p>}{children}</section>}
export function Notice({children}) {return <div className="notice"><Leaf size={17} aria-hidden="true"/><span>{children}</span></div>}
export function Steps({result,busy,setPage}) {
  const stages=[['数据准备','接入与预处理',1,FileText],['建筑损伤','模拟易损曲线',3,Building2],['人员后果','两终点后果估计',4,Users],['预期损失','统一后果成本口径',4,ChartNoAxesCombined],['防灾权益','年度额度与模拟兑换',5,ShieldCheck]];
  return <div className={'journey '+(result?'has-result':'')} aria-label="完整计算旅程"><svg className="journey-path" viewBox="0 0 1200 100" preserveAspectRatio="none" aria-hidden="true"><path d="M30 45C140 -10 190 110 300 45S460 -10 570 45S730 110 840 45S1000 -10 1170 45"/></svg>{stages.map(([title,caption,page,Icon],i)=>{
    const missing=result&&((i===1&&!result.building.damage_probabilities)||(i===3&&result.losses.total_expected_loss===null));
    return <button className={'journey-stop '+(result&&!missing?'complete':'')} key={title} onClick={()=>setPage(page)} aria-label={'查看'+title}><span className="journey-number">{result&&!missing?<Check size={17}/>:i+1}</span><Icon className="journey-icon" size={29} strokeWidth={1.35}/><span className="journey-copy"><b>{title}</b><small>{caption}</small><em>{busy?'正在计算':missing?'待补证':result?'已记录':'等待运行'}</em></span></button>;
  })}</div>;
}
export function Bars({values}) {
 if(!values)return <div className="empty"><BookOpen size={38} strokeWidth={1.2}/><span>这一页，等待一次计算。</span><small>运行完整链路后展示后端结果；参考模式保留未估计值。</small></div>;
 return <div className="bars" role="img" aria-label={Object.entries(values).map(([k,v])=>k+' '+fmt(v*100,2)+'%').join('，')}>{Object.entries(values).map(([k,v])=><div className="bar-col" key={k}><div className="bar-space"><div className="bar-stack" style={{height:Math.max(v*150,1)+'px'}}><span className="bar-value">{fmt(v*100,2)}%</span><div className="bar"/></div></div><span>{k}</span></div>)}</div>;
}
export function Metric({label,value,unit}) {return <div className="metric"><span>{label}</span><strong>{value}</strong><small>{unit}</small></div>}
export function Table({columns,rows}) {return <div className="table-scroll" tabIndex={0} role="region" aria-label={columns.join('、')+'表格'}><table><thead><tr>{columns.map((c,i)=><th scope="col" key={i}>{c}</th>)}</tr></thead><tbody>{rows.length?rows.map((r,i)=><tr key={i}>{r.map((c,j)=><td key={j}>{c}</td>)}</tr>):<tr><td colSpan={columns.length} className="table-empty">还没有记录，完成操作后会记在这里。</td></tr>}</tbody></table></div>}
export function Lines({records,metric}) {
 const values=records.map(r=>r.values[metric]),valid=values.filter(v=>v!==null&&Number.isFinite(v));
 if(!valid.length)return <div className="empty">当前范围没有可绘制的有效观测。</div>;
 const min=Math.min(...valid),max=Math.max(...valid),scale=max-min||1;
 const x=i=>34+i*630/Math.max(records.length-1,1),y=v=>175-(v-min)/scale*130;
 let segments=[],segment=[];values.forEach((v,i)=>{if(v===null||!Number.isFinite(v)){if(segment.length)segments.push(segment);segment=[]}else segment.push(`${x(i)},${y(v)}`)});if(segment.length)segments.push(segment);
 return <svg className="line-chart" viewBox="0 0 700 220" role="img" aria-label="日指标趋势，绿色为观测，橙色为插值，缺失处断线">{[45,88,132,175].map(y=><line key={y} x1="34" y1={y} x2="670" y2={y} stroke="#d8d1c4" strokeDasharray="4 4"/>)}{segments.map((s,i)=><polyline key={i} points={s.join(' ')} fill="none" stroke="#527f6d" strokeWidth="2.5" strokeLinejoin="round"/>)}{records.map((r,i)=>values[i]!==null&&Number.isFinite(values[i])&&<circle key={i} cx={x(i)} cy={y(values[i])} r="3.5" fill={r.quality[metric].status==='interpolated'?'#b26b36':'#527f6d'}/>)}<text x="34" y="205">{records[0]?.date}</text><text x="580" y="205">{records.at(-1)?.date}</text><text x="34" y="22">范围 {fmt(min,1)} — {fmt(max,1)}</text></svg>;
}
// Compatibility export for older page imports; scene art is now a separate asset layer.
export function BuildingArt(){return null;}
