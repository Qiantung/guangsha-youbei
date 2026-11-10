import React from 'react';
import {ArrowUpRight} from 'lucide-react';
import {Panel,Metric,Table,Json,Bars,Steps,fmt} from './components';
import {StoryHero,Friends,NotebookLinks} from './story';

export function Overview({result,run,setPage,busy}) {
 const names=['数据准备','建筑损伤','人员后果','预期损失','防灾权益'];
 return <>
  <StoryHero/>
  <Steps result={result} busy={busy} setPage={setPage}/>
  <div className="two-col overview-panels">
   <Panel title="建筑损伤概率" description="基于当前选择的对象与地震动情景；模拟曲线尚未完成国内校准。"><Bars values={result?.building.damage_probabilities}/></Panel>
   <Panel title="这次的准备记录" description="从输入到权益，每一步都有迹可循。"><div className="run-note"><ol className="trace-list">{names.map((name,i)=>{
    const missing=result&&((i===1&&!result.building.damage_probabilities)||(i===3&&result.losses.total_expected_loss===null));
    return <li key={name}><i className={result&&!missing?'complete':''}/><div><b>{name}</b><small>{missing?'保留未估计值':result?'已完成本次处理':'运行后记录处理结果'}</small></div><span>{busy?'计算中':missing?'待补证':result?'已记录':'等待中'}</span></li>;
   })}</ol><button className="text-button" onClick={()=>setPage(6)}>查看工具调用 <ArrowUpRight size={15}/></button><Friends/></div></Panel>
  </div>
  {result&&<div className="metric-band"><Metric label="模拟财产后果" value={fmt(result.losses.building_expected_loss,2)} unit="元"/><Metric label="模拟人身后果" value={fmt(result.losses.human_expected_loss,2)} unit="元 / 单人"/><Metric label="年度应享权益" value={fmt(result.incentive.annual_entitlement,2)} unit="模拟额度 / 元"/><Metric label="建筑概率隔离核验" value={result.building_isolation_verified?'通过':'失败'} unit="人员参数不改变建筑侧"/></div>}
  <NotebookLinks setPage={setPage}/>
  <details className="method-note"><summary>翻开参数与依据笔记</summary><Panel title="参数与依据" description="参考依据、模拟假设与未估计内容分别记录。"><Table columns={['内容','模式','说明']} rows={[["建筑曲线","模拟参考","函数形式参考既有易损方法；曲线参数为人为假设"],["人员修正","模拟假设","楼层名义率参考国内标准；健康系数及状态转换为模拟"],["激励规则","原型规则","连续四周达标、年度差额发放、仅人身责任额度参与"]]}/></Panel></details>
 </>;
}
