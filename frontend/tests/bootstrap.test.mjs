import test from 'node:test';
import assert from 'node:assert/strict';
import {loadInitialResources} from '../src/bootstrap.js';
import {api} from '../src/api.js';

const objects={datasets:[{id:'demo_01',name:'稳定记录',mode:'mock'},{id:'demo_02',name:'运动时长逐周增加',mode:'mock'},{id:'demo_03',name:'数据质量与故障处理',mode:'mock'}]};
function recorder(){const values={},errors={},settled=[];return {values,errors,settled,handlers:{onSuccess:(key,value)=>values[key]=value,onError:(key,error)=>errors[key]=error,onSettled:key=>settled.push(key)}}}

test('verification failure does not discard available objects or evidence',async()=>{
  const r=recorder();
  await loadInitialResources(r.handlers,async path=>{if(path==='/verification')throw new Error('HTTP 500');return path==='/datasets'?objects:{sources:[]}});
  assert.equal(r.values.datasets.datasets.length,3);assert.ok(r.values.evidence);assert.match(r.errors.verification,/验证记录/);assert.equal(r.settled.length,3);
});
test('slow metadata does not delay object callback',async()=>{
  const r=recorder();let release;const waiting=new Promise(resolve=>release=resolve);
  const done=loadInitialResources(r.handlers,async path=>path==='/datasets'?objects:waiting);
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(r.values.datasets.datasets[2].id,'demo_03');assert.deepEqual(r.settled,['datasets']);release({});await done;
});
test('evidence failure does not block object selection',async()=>{
  const r=recorder();await loadInitialResources(r.handlers,async path=>{if(path==='/evidence')throw new Error('missing');return path==='/datasets'?objects:{}});
  assert.ok(r.values.datasets);assert.ok(r.values.verification);assert.match(r.errors.evidence,/参数依据/);
});
test('empty and malformed object lists produce explicit error',async()=>{
  for(const value of [{datasets:[]},{datasets:null},{datasets:[null]},{datasets:[{id:'demo_01'}]},'<html>']){
    const r=recorder();await loadInitialResources(r.handlers,async()=>value);assert.equal(r.values.datasets,undefined);assert.match(r.errors.datasets,/对象列表为空或格式不正确/);
  }
});
test('retry can recover after object request fails',async()=>{
  const r=recorder();await loadInitialResources(r.handlers,async()=>{throw new Error('offline')});assert.equal(r.values.datasets,undefined);
  await loadInitialResources(r.handlers,async path=>path==='/datasets'?objects:{});assert.equal(r.values.datasets.datasets.length,3);
});

test('API recognizes JSON and preserves Markdown report export',async()=>{
  const original=globalThis.fetch;
  try{
    globalThis.fetch=async()=>new Response(JSON.stringify(objects),{headers:{'content-type':'application/json'}});
    assert.deepEqual(await api('/datasets'),objects);
    globalThis.fetch=async()=>new Response('# 防灾报告',{headers:{'content-type':'text/markdown; charset=utf-8'}});
    assert.equal(await api('/report',{}),'# 防灾报告');
  }finally{globalThis.fetch=original}
});
test('HTML fallback cannot silently masquerade as object data',async()=>{
  const original=globalThis.fetch;try{globalThis.fetch=async()=>new Response('<html>app</html>',{headers:{'content-type':'text/html'}});await assert.rejects(api('/datasets'),/未返回 JSON/)}finally{globalThis.fetch=original}
});
test('invalid JSON and HTTP failure report useful errors',async()=>{
  const original=globalThis.fetch;try{
    globalThis.fetch=async()=>new Response('{',{headers:{'content-type':'application/json'}});await assert.rejects(api('/verification'),/数据格式不正确/);
    globalThis.fetch=async()=>new Response('{"error":{"message":"服务暂不可用"}}',{status:503,headers:{'content-type':'application/json'}});await assert.rejects(api('/verification'),/服务暂不可用/);
  }finally{globalThis.fetch=original}
});
test('slow initial API requests time out instead of leaving blank selection',async()=>{
  const original=globalThis.fetch;try{
    globalThis.fetch=(_,options)=>new Promise((_,reject)=>options.signal.addEventListener('abort',()=>reject(new Error('aborted'))));
    await assert.rejects(api('/datasets',undefined,{timeoutMs:5}),/加载超时/);
  }finally{globalThis.fetch=original}
});
