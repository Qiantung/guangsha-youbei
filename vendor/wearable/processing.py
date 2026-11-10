import math
from datetime import timedelta
from .models import METRICS, MOCK_RANGES, REAL_RANGES, QUALITY_FLAGS, SafeError, parse_date, days


def clean(dataset):
    """按业务日期/指标去重后建立日历，在整段日历上插值；查询切片不改变结果。"""
    if not dataset.records: raise SafeError('empty_dataset')
    chosen={}; duplicates=0
    for order,row in enumerate(dataset.records):
        d=parse_date(row.get('date'))
        key=d.isoformat()
        rank=(row.get('_updated',0),order)
        if key in chosen: duplicates+=1
        if key not in chosen or rank>=chosen[key][0]: chosen[key]=(rank,row)
    start,end=min(map(parse_date,chosen)),max(map(parse_date,chosen))
    if (end-start).days>3659: raise SafeError('dataset_too_large')
    out=[]; ranges=MOCK_RANGES if dataset.mode=='mock' else REAL_RANGES
    for d in days(start,end):
        source=chosen.get(d.isoformat(),(None,{}))[1]
        result={'date':d.isoformat(),'timestamp':d.isoformat()+'T00:00:00+08:00','values':{},'quality':{}}
        for m in METRICS:
            flags=[f for f in source.get('_flags',{}).get(m,[]) if isinstance(f,str) and f in QUALITY_FLAGS]
            v=source.get(m)
            if not source: flags.append('missing_date')
            if v is None:
                flags.append('missing')
            elif isinstance(v,bool) or not isinstance(v,(int,float)):
                v=None; flags.append('invalid_type')
            elif not math.isfinite(v):
                v=None; flags.append('non_finite')
            elif not ranges[m][0]<=v<=ranges[m][1]:
                v=None; flags.append('out_of_range')
            if m==METRICS[1] and not dataset.activity_confirmed:
                v=None; flags.append('semantic_unconfirmed')
            result['values'][m]=v
            result['quality'][m]={'status':'observed' if v is not None else 'missing','flags':sorted(set(flags))}
        out.append(result)
    for m in METRICS:
        i=0
        while i<len(out):
            if out[i]['values'][m] is not None: i+=1; continue
            a=i
            while i<len(out) and out[i]['values'][m] is None: i+=1
            b=i; bounded=a>0 and b<len(out)
            can_fill=bounded and b-a<=2 and not (dataset.mode=='real' and m==METRICS[1])
            # 未确认单位/语义的缺失不允许用插值绕过确认。
            blocked={'semantic_unconfirmed','unit_unconfirmed','invalid_summary'}
            can_fill=can_fill and not any(blocked.intersection(out[j]['quality'][m]['flags']) for j in range(a,b))
            for j in range(a,b):
                q=out[j]['quality'][m]
                if can_fill:
                    l,r=out[a-1]['values'][m],out[b]['values'][m]
                    out[j]['values'][m]=round(l+(r-l)*(j-a+1)/(b-a+1),4)
                    q['status']='interpolated'; q['flags'].append('interpolated')
                else:
                    q['flags'].append('data_gap' if b-a>=3 else 'endpoint_gap' if not bounded else 'not_interpolated')
    return out, {'duplicate_records':duplicates,'missing_calendar_dates':sum('missing_date' in r['quality'][METRICS[0]]['flags'] for r in out)}


def weekly(rows, activity_confirmed=True, threshold=150):
    buckets={}
    for r in rows:
        d=parse_date(r['date']); mon=d-timedelta(days=d.weekday())
        buckets.setdefault(mon.isoformat(),[]).append(r)
    result=[]
    for mon,group in sorted(buckets.items()):
        complete=len(group)==7
        w={'week_start':mon,'week_end':(parse_date(mon)+timedelta(days=6)).isoformat(),
           'calendar_complete':complete,'calendar_days':len(group),'metrics':{},'activity_threshold_minutes':threshold}
        for m in METRICS:
            obs=[r['values'][m] for r in group if r['quality'][m]['status']=='observed']
            vals=[r['values'][m] for r in group if r['values'][m] is not None]
            reduce=lambda vs: round(sum(vs) if m==METRICS[1] else sum(vs)/len(vs),4) if vs else None
            w['metrics'][m]={'observed_statistic':reduce(obs),'processed_statistic':reduce(vals),
                'statistic_kind':'sum' if m==METRICS[1] else 'mean',
                'observed_days':len(obs),'interpolated_days':len(vals)-len(obs),'missing_days':len(group)-len(vals),
                'observed_coverage':round(len(obs)/7,4),'processed_coverage':round(len(vals)/7,4),
                'observed_complete':complete and len(obs)==7,'processed_complete':complete and len(vals)==7}
        act=w['metrics'][METRICS[1]]
        w['activity_status']=('achieved' if act['observed_statistic']>=threshold else 'not_achieved') if activity_confirmed and act['observed_complete'] else 'unknown'
        w['estimated_activity_status']=('achieved' if act['processed_statistic']>=threshold else 'not_achieved') if activity_confirmed and act['processed_complete'] else 'unknown'
        w['activity_statistic_label']='完整周观测总量' if act['observed_complete'] else '已观测累计'
        result.append(w)
    return result
