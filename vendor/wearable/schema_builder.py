"""严格输出白名单 JSON Schema，所有固定对象 additionalProperties=false。"""
import json
from pathlib import Path
from .models import METRICS,UNITS

def obj(props): return {'type':'object','properties':props,'required':list(props),'additionalProperties':False}
def arr(item,max_items=366): return {'type':'array','items':item,'maxItems':max_items}
num={'type':['number','null']}; count={'type':'integer','minimum':0}; boolean={'type':'boolean'}
string={'type':'string'}; day={'type':'string','format':'date'}; coverage={'type':'number','minimum':0,'maximum':1}
flags={'enum':['missing_date','missing','invalid_type','non_finite','out_of_range','semantic_unconfirmed','unit_unconfirmed','invalid_summary','interpolated','data_gap','endpoint_gap','not_interpolated']}
q=obj({'status':{'enum':['observed','interpolated','missing']},'flags':arr(flags,20)})
daily=obj({'records':arr(obj({'date':day,'timestamp':{'type':'string','pattern':r'^\d{4}-\d{2}-\d{2}T00:00:00\+08:00$'},'values':obj({m:num for m in METRICS}),'quality':obj({m:q for m in METRICS})}))})
stat=obj({'observed_statistic':num,'processed_statistic':num,'statistic_kind':{'enum':['sum','mean']},'observed_days':count,'interpolated_days':count,'missing_days':count,'observed_coverage':coverage,'processed_coverage':coverage,'observed_complete':boolean,'processed_complete':boolean})
status={'enum':['achieved','not_achieved','unknown']}
week=obj({'weeks':arr(obj({'week_start':day,'week_end':day,'calendar_complete':boolean,'calendar_days':count,'metrics':obj({m:stat for m in METRICS}),'activity_threshold_minutes':{'type':'number','minimum':1},'activity_status':status,'estimated_activity_status':status,'activity_statistic_label':{'enum':['完整周观测总量','已观测累计']}}),54)})
quality=obj({'calendar_days':count,'metrics':obj({m:obj({'observed_days':count,'interpolated_days':count,'missing_days':count,'observed_coverage':coverage,'processed_coverage':coverage,'reason_counts':{'type':'object','propertyNames':flags,'additionalProperties':count}}) for m in METRICS}), 'dataset_diagnostics':obj({'duplicate_records':count,'missing_calendar_dates':count,'duplicate_daily_summaries':count}),'diagnostics_scope':{'const':'whole_dataset'}})
error=obj({'code':{'enum':['unknown_tool','unknown_dataset','invalid_date','invalid_date_range','date_range_too_long','date_out_of_bounds','too_many_records']},'message':string})

def schema(kind):
    props={'schema_version':{'const':'1.0.0'},'ok':boolean,'dataset_id':{'enum':['demo_01','demo_02','demo_03','real_local_01',None]},'data_mode':{'enum':['mock','real',None]},'timezone':{'const':'Asia/Shanghai'},'units':obj({m:{'const':u} for m,u in UNITS.items()}),'source_status':{'enum':['synthetic','local_csv',None]},'activity_semantic_status':{'enum':['confirmed','semantic_unconfirmed',None]},'start_date':{'type':['string','null'],'format':'date'},'end_date':{'type':['string','null'],'format':'date'},'data':{'anyOf':[{'type':'null'},{'daily':daily,'weekly':week,'quality':quality}[kind]]},'error':{'anyOf':[{'type':'null'},error]}}
    base=obj(props); base['$schema']='https://json-schema.org/draft/2020-12/schema'
    base['allOf']=[{'if':{'properties':{'ok':{'const':True}}},'then':{'properties':{'data':{'type':'object'},'error':{'type':'null'},'dataset_id':{'type':'string'},'data_mode':{'type':'string'},'start_date':{'type':'string'},'end_date':{'type':'string'}}},'else':{'properties':{'data':{'type':'null'},'error':{'type':'object'},'dataset_id':{'type':'null'},'data_mode':{'type':'null'},'start_date':{'type':'null'},'end_date':{'type':'null'}}}}]
    return base
if __name__=='__main__':
    for kind in ('daily','weekly','quality'):
        Path('schemas/'+kind+'.schema.json').write_text(json.dumps(schema(kind),ensure_ascii=False,indent=2),encoding='utf-8')
