const {chromium}=await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
import {spawn} from 'node:child_process';
import fs from 'node:fs/promises';
import path from 'node:path';

const root=path.resolve(import.meta.dirname,'..');
const db=path.join(root,'private/browser-test.sqlite3');
const output=process.env.QUAKE_QA_DIR||path.join(root,'verification');
await fs.mkdir(output,{recursive:true});
await fs.rm(db,{force:true});
const server=spawn(path.join(root,process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python'),['-m','uvicorn','backend.app:app','--host','127.0.0.1','--port','8770'],{cwd:root,env:{...process.env,QUAKE_DB:db},stdio:'pipe'});
let browser;
const errors=[];
try{
 for(let i=0;i<40;i++){try{if((await fetch('http://127.0.0.1:8770/api/status')).ok)break}catch{}await new Promise(r=>setTimeout(r,150))}
 browser=await chromium.launch({executablePath:process.env.QUAKE_CHROMIUM_PATH||undefined,args:JSON.parse(process.env.QUAKE_CHROMIUM_ARGS||'[]'),headless:true});
 const page=await browser.newPage({viewport:{width:1536,height:1024}});
 page.on('pageerror',e=>errors.push(e.message));
 page.on('console',e=>{if(e.type()==='error')errors.push(e.text())});
 await page.goto('http://127.0.0.1:8770');
 await page.evaluate(()=>document.fonts.ready);
 await page.locator('.hero-friends').waitFor();
 await page.waitForFunction(()=>[...document.images].every(i=>i.complete));
 await page.getByRole('combobox',{name:'选择虚拟对象'}).selectOption('demo_01');
 await page.screenshot({path:path.join(output,'overview-before.png'),fullPage:true,animations:'disabled'});
 await page.getByRole('button',{name:'运行完整链路',exact:true}).click();
 await page.getByText('通过',{exact:true}).waitFor();
 if(await page.getByRole('button',{name:'关闭提示',exact:true}).count())await page.getByRole('button',{name:'关闭提示',exact:true}).click();
 await page.screenshot({path:path.join(output,'overview.png'),fullPage:true,animations:'disabled'});
 const checks=[];
 for(const [label,filename] of [['导出计算结果','guangsha-result.json'],['导出防灾报告','guangsha-report.md']]){
  const awaited=page.waitForEvent('download');
  await page.getByRole('button',{name:label,exact:true}).click();
  const file=await awaited;
  if(file.suggestedFilename()!==filename)throw new Error('Unexpected export filename');
 }
 checks.push({flow:'JSON与Markdown报告真实导出',passed:true});
 for(const name of ['数据接入','时序与规则','建筑情景','人员后果','防灾权益','智能助手','方法与验证']){
  await page.getByRole('button',{name,exact:true}).click();
  await page.getByRole('heading',{name,exact:true,level:1}).waitFor();
  checks.push({page:name,rendered:true});
  await page.screenshot({path:path.join(output,'page-'+name+'.png'),fullPage:true,animations:'disabled'});
 }
 await page.getByRole('button',{name:'防灾权益',exact:true}).click();
 await page.getByRole('button',{name:'运行达标核算并发放差额'}).click();
 await page.getByRole('button',{name:'选择防护手套'}).click();
 await page.getByRole('heading',{name:'防护手套',exact:true}).waitFor();
 await page.getByRole('button',{name:'选择应急哨'}).click();
 await page.getByRole('button',{name:'模拟兑换',exact:true}).first().waitFor();
 await page.getByRole('button',{name:'模拟兑换',exact:true}).first().click();
 await page.getByText('兑换成功',{exact:true}).waitFor();
 await page.getByRole('button',{name:'模拟失败冲正'}).click();
 await page.getByText('已冲正',{exact:true}).waitFor();
 checks.push({flow:'发放→物资兑换→失败冲正',passed:true});
 if(await page.getByRole('button',{name:'关闭提示',exact:true}).count())await page.getByRole('button',{name:'关闭提示',exact:true}).click();
 await page.screenshot({path:path.join(output,'benefits.png'),fullPage:true,animations:'disabled'});
 await page.getByRole('button',{name:'智能助手',exact:true}).click();
 await page.getByRole('combobox',{name:'调用方式'}).selectOption('mcp');
 await page.getByRole('button',{name:'查询当前地震风险'}).click();
 await page.getByText('5. run_pipeline',{exact:true}).waitFor({timeout:30000});
 checks.push({flow:'网页真实MCP风险查询',passed:true});
 await page.screenshot({path:path.join(output,'assistant.png'),fullPage:true,animations:'disabled'});
 await page.getByRole('button',{name:'建筑情景',exact:true}).click();
 await page.getByLabel('计算模式').selectOption('reference');
 await page.getByRole('button',{name:'计算并更新完整链路'}).click();
 await page.getByText('国内住宅整栋易损曲线尚未补齐',{exact:false}).first().waitFor();
 checks.push({flow:'网页参考模式返回未估计',passed:true});
 await page.getByRole('button',{name:'防灾权益',exact:true}).click();
 await page.getByText('年度结束演示',{exact:true}).click();
 await page.getByRole('button',{name:'模拟年度结束并清零',exact:true}).click();
 await page.getByText('年度已结束',{exact:true}).waitFor();
 checks.push({flow:'网页年度关闭及余额过期',passed:true});
 await page.getByRole('button',{name:'项目总览',exact:true}).click();
 await page.getByRole('button',{name:'查看数据准备',exact:true}).click();
 await page.getByRole('heading',{name:'数据接入',exact:true,level:1}).waitFor();
 checks.push({flow:'旅程节点跳转及物资柜选择',passed:true});
 await page.getByRole('button',{name:'项目总览',exact:true}).click();
 await page.setViewportSize({width:390,height:844});
 if(await page.getByRole('button',{name:'关闭提示',exact:true}).count())await page.getByRole('button',{name:'关闭提示',exact:true}).click();
 await page.screenshot({path:path.join(output,'mobile.png'),fullPage:true,animations:'disabled'});
 const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
 if(overflow)throw new Error('Mobile horizontal overflow');
 for(const width of [390,768]){
  await page.setViewportSize({width,height:900});
  for(const name of ['项目总览','数据接入','时序与规则','建筑情景','人员后果','防灾权益','智能助手','方法与验证']){
   await page.getByRole('button',{name,exact:true}).click();
   await page.getByRole('heading',{name,exact:true,level:1}).waitFor();
   if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw new Error('Overflow '+width+' '+name);
  }
  checks.push({flow:width+'px全部八页无横向溢出',passed:true});
 }
 if((await page.title()).includes('震衡'))throw new Error('Old brand remains');
 checks.push({flow:'网页标题品牌替换',passed:true});
 if(errors.length)throw new Error('Browser page errors: '+errors.join(';'));
 await fs.writeFile(path.join(output,'browser-results.json'),JSON.stringify({checks,console_errors:errors,mobile_horizontal_overflow:overflow},null,2));
 console.log(JSON.stringify({checks:checks.length,console_errors:errors.length,mobile_overflow:overflow}));
}finally{if(browser)await browser.close();server.kill();}
