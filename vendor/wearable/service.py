import json
import os
from collections import Counter
from pathlib import Path
from .models import METRICS, UNITS, SafeError, parse_date
from .mock import MockSource
from .processing import clean, weekly
from .parser_factory import create_parser

TOOL_KINDS={'get_daily_metrics':'daily','get_weekly_features':'weekly','get_data_quality_report':'quality'}

class Registry:
    def __init__(self, config_path=None):
        self.datasets={k:MockSource(k).load() for k in ('demo_01','demo_02','demo_03')}
        self.threshold=150
        self.import_error=None
        config_path=config_path or os.environ.get('WEARABLE_LOCAL_CONFIG')
        if config_path is None and Path('local.config.json').is_file():
            config_path='local.config.json'
        if config_path:
            try:
                cfg=json.loads(Path(config_path).read_text(encoding='utf-8-sig'))
                if not isinstance(cfg,dict): raise SafeError('local_config_invalid')
                t=cfg.get('weekly_activity_threshold_minutes',150)
                if isinstance(t,bool) or not isinstance(t,(int,float)) or not 1<=t<=10080: raise SafeError('invalid_threshold')
                self.threshold=t
                parser=create_parser(cfg,Path(config_path).resolve().parent)
                if parser is not None:
                    source=parser.load()
                    self.datasets[source.dataset_id]=source
            except SafeError as e: self.import_error=e.code
            except (OSError,ValueError,KeyError,TypeError): self.import_error='local_config_invalid'
        self.processed={k:clean(v) for k,v in self.datasets.items()}

    def query(self, tool, dataset_id, start_date=None, end_date=None):
        try:
            if tool not in TOOL_KINDS: raise SafeError('unknown_tool')
            if dataset_id not in self.datasets: raise SafeError('unknown_dataset')
            rows,diag=self.processed[dataset_id]
            lo,hi=parse_date(rows[0]['date']),parse_date(rows[-1]['date'])
            start=parse_date(start_date) if start_date is not None else lo
            end=parse_date(end_date) if end_date is not None else hi
            if start>end: raise SafeError('invalid_date_range')
            if (end-start).days+1>366: raise SafeError('date_range_too_long')
            if start<lo or end>hi: raise SafeError('date_out_of_bounds')
            ds=self.datasets[dataset_id]
            sliced=[r for r in rows if start.isoformat()<=r['date']<=end.isoformat()]
            if len(sliced)>366: raise SafeError('too_many_records')
            if tool=='get_daily_metrics': data={'records':sliced}
            elif tool=='get_weekly_features': data={'weeks':weekly(sliced,ds.activity_confirmed,self.threshold)}
            else:
                q={}
                for m in METRICS:
                    states=Counter(r['quality'][m]['status'] for r in sliced)
                    flags=Counter(f for r in sliced for f in r['quality'][m]['flags'])
                    q[m]={'observed_days':states['observed'],'interpolated_days':states['interpolated'],
                        'missing_days':states['missing'],'observed_coverage':round(states['observed']/len(sliced),4),
                        'processed_coverage':round((states['observed']+states['interpolated'])/len(sliced),4),'reason_counts':dict(flags)}
                # 去重诊断明确是整个数据集范围，避免声称属于查询片段。
                data={'calendar_days':len(sliced),'metrics':q,'dataset_diagnostics':{
                    **diag,'duplicate_daily_summaries':ds.metadata.get('parser_counts',{}).get('duplicate_daily_summaries',0)},'diagnostics_scope':'whole_dataset'}
            return {'schema_version':'1.0.0','ok':True,'dataset_id':dataset_id,'data_mode':ds.mode,
                'timezone':'Asia/Shanghai','units':UNITS,'source_status':'synthetic' if ds.mode=='mock' else 'local_csv',
                'activity_semantic_status':'confirmed' if ds.activity_confirmed else 'semantic_unconfirmed',
                'start_date':start.isoformat(),'end_date':end.isoformat(),'data':data,'error':None}
        except SafeError as e:
            # 不回显调用者输入、未知别名、配置、路径或原始数据。
            return {'schema_version':'1.0.0','ok':False,'dataset_id':None,'data_mode':None,
                'timezone':'Asia/Shanghai','units':UNITS,'source_status':None,'activity_semantic_status':None,
                'start_date':None,'end_date':None,'data':None,'error':{'code':e.code,'message':'请求无法处理，请检查已注册数据集与日期范围。'}}
