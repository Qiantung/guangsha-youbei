import {api} from './api.js';

// Apply each result as soon as it arrives; optional metadata cannot block objects.
export function loadInitialResources(handlers,request=api) {
  const resources=[['datasets','对象列表'],['evidence','参数依据'],['verification','验证记录']];
  return Promise.allSettled(resources.map(async([key,label])=>{
    try {
      const value=await request('/'+key,undefined,{timeoutMs:15000});
      if(key==='datasets'&&(!Array.isArray(value?.datasets)||!value.datasets.length||value.datasets.some(d=>!d||typeof d.id!=='string'||!d.id||typeof d.name!=='string')))
        throw new Error('对象列表为空或格式不正确，请检查后端数据初始化。');
      handlers.onSuccess(key,value);
    } catch(error) {handlers.onError(key,`${label}：${error.message}`)}
    finally {handlers.onSettled(key)}
  }));
}
