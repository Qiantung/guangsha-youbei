import React,{useEffect,useRef,useState} from 'react';
import {createRoot} from 'react-dom/client';
import {Play,Download,X,Home,Map,Package,BookOpen,Check} from 'lucide-react';
import {api,initialScenario,download} from './api';
import {loadInitialResources} from './bootstrap';
import {nav} from './components';
import {BrandMark,PageNote} from './story';
import {Overview,DataPage,TimeseriesPage,ScenarioPage,PersonPage,BenefitsPage,AssistantPage,EvidencePage} from './pages';
import '@fontsource/nunito/latin-400.css';
import '@fontsource/nunito/latin-600.css';
import '@fontsource/nunito/latin-700.css';
import './tokens.css';
import './style.css';

const descriptions=['从数据到情景，从风险到行动，探索更有准备的生活。','观测、插值与缺失，保留每一步的质量信息。','持久化查询与规则触发，让数据进入业务流程。','明确输入口径，展示建筑风险计算边界。','同一建筑情景，比较不同人员状态。','从连续达标，到年度额度与防灾物资。','自然语言入口与实际后端工具调用。','可考证的参考、明确的假设、可检查的验证。'];
const Pages=[Overview,DataPage,TimeseriesPage,ScenarioPage,PersonPage,BenefitsPage,AssistantPage,EvidencePage];

function App(){
 const [page,setPage]=useState(0),[scenario,setScenario]=useState(initialScenario),[datasets,setDatasets]=useState([]),[data,setData]=useState(null),[result,setResult]=useState(null),[evidence,setEvidence]=useState(null),[verification,setVerification]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[importStatus,setImportStatus]=useState(''),[toast,setToast]=useState('');
 const revision=useRef(0);
 const [resourceErrors,setResourceErrors]=useState({}),[datasetsLoading,setDatasetsLoading]=useState(true),[loadAttempt,setLoadAttempt]=useState(0);
 const goToPage=n=>{setPage(n);setError('');window.scrollTo({top:0,behavior:'instant'})};
 async function guard(fn){setError('');try{return await fn()}catch(e){setError(e.message)}}
 function notify(message){setToast(message)}
 useEffect(()=>{if(!toast)return;const timer=setTimeout(()=>setToast(''),4500);return()=>clearTimeout(timer)},[toast]);
 useEffect(()=>{
   let alive=true;
   setResourceErrors({});setDatasetsLoading(true);
   loadInitialResources({
     onSuccess:(key,value)=>{if(!alive)return;if(key==='datasets'){setDatasets(value.datasets);setImportStatus(value.import_status);setScenario(s=>value.datasets.some(d=>d.id===s.dataset_id)?s:{...s,dataset_id:value.datasets[0].id})}else if(key==='evidence')setEvidence(value);else setVerification(value)},
     onError:(key,message)=>{if(alive)setResourceErrors(previous=>({...previous,[key]:message}))},
     onSettled:key=>{if(alive&&key==='datasets')setDatasetsLoading(false)}
   });
   return()=>{alive=false};
 },[loadAttempt]);
 useEffect(()=>{let alive=true;setData(null);api('/data/'+scenario.dataset_id).then(d=>alive&&setData(d)).catch(e=>alive&&setError(e.message));return()=>{alive=false}},[scenario.dataset_id]);
 const updateScenario=s=>{revision.current+=1;setScenario(s);setResult(null)};
 const run=grant=>guard(async()=>{if(busy)return;const current=revision.current;setBusy(true);try{const r=await api('/run',{scenario,grant});if(current===revision.current){setResult(r);notify(grant?(r.incentive.new_grant>0?'核算完成，新增 '+r.incentive.new_grant+' 权益点。':'核算完成，本次没有重复发放。'):'完整链路已计算，结果已记入本地数据库。')}return r}finally{setBusy(false)}});
 const props={dataset:scenario.dataset_id,data,scenario,setScenario:updateScenario,result,run,guard,notify,busy,evidence,verification,setPage:goToPage};
 const Page=Pages[page];
 return <div className="app">
   <a className="skip-link" href="#main-content">跳到主要内容</a>
   <div className="brand-bar"><a className="brand" href="#" onClick={e=>{e.preventDefault();goToPage(0)}} aria-label="广厦有备首页"><BrandMark/><b>广厦有备</b><span>把安心，慢慢准备好。</span></a><span className="local-label"><span/> 本地演示 · 模拟数据</span></div>
   <div className="app-shell"><nav className="chapter-nav" aria-label="主要栏目">{nav.map(([name,Icon],i)=><button key={name} aria-current={page===i?'page':undefined} className={page===i?'active':''} onClick={()=>goToPage(i)}><Icon size={20} strokeWidth={1.5}/><span>{name}</span></button>)}</nav>
   <main id="main-content"><header className="page-header"><div><h1>{nav[page][0]}</h1><p>{descriptions[page]}</p></div><div className="header-actions"><select aria-label="选择虚拟对象" aria-busy={datasetsLoading} disabled={busy||datasetsLoading||!datasets.length} value={datasets.length?scenario.dataset_id:''} onChange={e=>updateScenario({...scenario,dataset_id:e.target.value})}>{!datasets.length&&<option value="">{datasetsLoading?'正在加载对象…':'对象加载失败，请重试'}</option>}{datasets.map((d,i)=><option key={d.id} value={d.id}>{d.mode==='mock'?`虚拟对象 ${String.fromCharCode(65+i)}`:'本地导入对象'} · {d.name}</option>)}</select><button disabled={busy||datasetsLoading||!datasets.length} onClick={()=>run(false)}><Play size={17} fill="currentColor"/>{busy?'计算中…':'运行完整链路'}</button></div></header>
   {Object.keys(resourceErrors).length>0&&<div className="error" role="alert"><div>{Object.entries(resourceErrors).map(([key,message])=><p key={key}>{message}</p>)}</div><button className="secondary" onClick={()=>setLoadAttempt(n=>n+1)}>重新加载</button></div>}
   {error&&<div className="error" role="alert"><span>{error}</span><button onClick={()=>setError('')} aria-label="关闭错误"><X size={18}/></button></div>}
   <PageNote page={page}/><div className={'page-content page-'+page} aria-busy={busy}><Page key={page+'-'+scenario.dataset_id} {...props}/></div>
   {result&&<div className="export-bar"><button className="secondary" onClick={()=>download('guangsha-result.json',JSON.stringify(result,null,2))}><Download size={16}/>导出计算结果</button><button className="secondary" onClick={()=>guard(async()=>download('guangsha-report.md',await api('/report',{scenario,grant:false}),'text/markdown'))}><BookOpen size={16}/>导出防灾报告</button><span>参数版本 {result.building.parameter_version||'参考模式'}</span></div>}
   <footer><p><b>广厦有备</b> · 为每一份准备，留下一页记录。</p><p>{importStatus} · 本地单人原型，参考计算与模拟结果仅用于验证。</p>{result&&result.notices.map(n=><p key={n}>{n}</p>)}</footer></main></div>
   <nav className="mobile-nav" aria-label="快捷栏目">{[[0,'总览',Home],[1,'准备旅程',Map],[5,'防灾权益',Package],[6,'防灾手账',BookOpen]].map(([n,label,Icon])=><button key={n} aria-label={'快捷前往'+label} className={page===n||(n===1&&page>=1&&page<=4)||(n===6&&page>=6)?'active':''} onClick={()=>goToPage(n)}><Icon size={22} strokeWidth={1.5}/><span>{label}</span></button>)}</nav>
   {toast&&<div className="toast" role="status"><Check size={18}/>{toast}<button onClick={()=>setToast('')} aria-label="关闭提示"><X size={16}/></button></div>}
 </div>;
}
createRoot(document.getElementById('root')).render(<App/>);
