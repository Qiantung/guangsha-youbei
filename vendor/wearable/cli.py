import argparse
import asyncio
import json
from pathlib import Path
from .service import Registry,TOOL_KINDS

def main():
    p=argparse.ArgumentParser(description='可穿戴数据接入原型，仅用于原型验证')
    p.add_argument('command',choices=['generate','daily','weekly','quality','mcp-demo','real-check'])
    p.add_argument('--dataset',default='demo_01'); p.add_argument('--start'); p.add_argument('--end')
    p.add_argument('--config'); p.add_argument('--output',default='examples')
    a=p.parse_args(); reg=Registry(a.config)
    if a.command=='generate':
        dest=Path(a.output); dest.mkdir(parents=True,exist_ok=True)
        for ds in reg.datasets.values():
            if ds.mode!='mock': continue
            (dest/(ds.dataset_id+'.json')).write_text(json.dumps({'label':'原型模拟数据','records':ds.records,'fault_injections':ds.faults},ensure_ascii=False,indent=2),encoding='utf-8')
        out={'ok':True,'mock_records':84,'message':'已生成三个场景和故障说明'}
    elif a.command=='mcp-demo':
        if a.config:
            import os
            os.environ['WEARABLE_LOCAL_CONFIG']=str(Path(a.config).resolve())
        from .client import call
        out=asyncio.run(call('get_weekly_features',a.dataset,a.start,a.end))
    elif a.command=='real-check':
        ds=reg.datasets.get('real_local_01')
        out={'executed':ds is not None,'error_code':reg.import_error,'metadata':ds.metadata if ds else None,
             'quality':reg.query('get_data_quality_report','real_local_01',a.start,a.end) if ds else None}
    else:
        tool=next(k for k,v in TOOL_KINDS.items() if v==a.command)
        out=reg.query(tool,a.dataset,a.start,a.end)
    print(json.dumps(out,ensure_ascii=False,allow_nan=False,indent=2))

if __name__=='__main__': main()
