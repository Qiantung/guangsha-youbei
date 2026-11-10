export async function api(path, body, {timeoutMs=0}={}) {
  const controller=timeoutMs>0?new AbortController():null;
  const timer=controller?setTimeout(()=>controller.abort(),timeoutMs):null;
  try {
    const options=body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)};
    if(controller)options.signal=controller.signal;
    const response=await fetch('/api'+path,options);
    const type=response.headers.get('content-type')||'';
    if(response.ok&&path==='/report'&&type.includes('text/markdown'))return await response.text();
    if(!type.includes('json'))throw new Error(`接口 /api${path} 未返回 JSON（HTTP ${response.status}），请确认从后端地址打开网页。`);
    let data;
    try {data=await response.json()} catch {throw new Error(`接口 /api${path} 返回的数据格式不正确。`)}
    if(!response.ok)throw new Error(data?.error?.message||`接口 /api${path} 请求失败（HTTP ${response.status}）。`);
    return data;
  } catch(error) {
    if(controller?.signal.aborted)throw new Error(`接口 /api${path} 加载超时，请检查后端后重试。`);
    if(error instanceof TypeError)throw new Error(`无法连接接口 /api${path}，请保持启动窗口开启。`);
    throw error;
  } finally {if(timer!==null)clearTimeout(timer)}
}
export const initialScenario={dataset_id:'demo_01',mode:'simulation',structure_type:'frame',fortification_intensity:7,pga:0.25,building_area:100,floor_count:6,age:45,sleeping:false,reference_floor_grade:4};
export function download(name,text,type='application/json') {const url=URL.createObjectURL(new Blob([text],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();URL.revokeObjectURL(url);}
