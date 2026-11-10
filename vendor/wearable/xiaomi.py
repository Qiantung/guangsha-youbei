"""本地 Xiaomi CSV；只读取聚合目标类别与 resting_heart_rate 明细。"""
import csv
import json
import math
from collections import Counter
from .models import Dataset, METRICS, SafeError, unix_seconds

TARGETS={'heart_rate':('avg_rhr',METRICS[0]),'sleep':('total_duration',METRICS[2]),'intensity':('duration',METRICS[1])}


def finite_number(v):
    return not isinstance(v,bool) and isinstance(v,(int,float)) and math.isfinite(v)


def sleep_minutes_evidence(v):
    """保守的单记录单位核验：每段(睡眠+清醒)*60=醒来-入睡，段睡眠之和=日汇总。
    不根据数值大小猜单位；不重新累计睡眠阶段，不将明细添加到汇总。
    """
    try:
        segs=v['segment_details']; total=v['total_duration']
        if not segs or not finite_number(total) or total<0: return False
        summed=0; intervals=[]
        for s in segs:
            duration,awake=s['duration'],s['sleep_awake_duration']
            if not all(finite_number(x) and x>=0 for x in (duration,awake)): return False
            begin,finish=unix_seconds(s['bedtime']),unix_seconds(s['wake_up_time'])
            intervals.append((begin,finish))
            elapsed=(finish-begin).total_seconds()
            if elapsed<=0 or abs(elapsed-60*(duration+awake))>60: return False
            summed+=duration
        intervals.sort()
        if any(a[1]>b[0] for a,b in zip(intervals,intervals[1:])): return False
        return abs(summed-total)<0.01
    except (KeyError,TypeError,SafeError): return False

class XiaomiSource:
    def __init__(self, config): self.config=config
    def load(self):
        cfg=self.config
        activity=cfg.get('activity_mapping',{})
        confirmed=activity.get('confirmed') is True
        if confirmed and (activity.get('unit') not in ('seconds','minutes') or not isinstance(activity.get('basis'),str) or not activity['basis'].strip() or activity.get('semantic')!='moderate_activity'):
            raise SafeError('mapping_confirmation_incomplete')
        sleep=cfg.get('sleep_mapping',{})
        if sleep.get('confirmed') and (sleep.get('unit')!='minutes' or not isinstance(sleep.get('basis'),str) or not sleep['basis'].strip()):
            raise SafeError('sleep_confirmation_incomplete')
        try:
            with open(cfg['aggregated_csv'],encoding='utf-8-sig',newline='') as f:
                reader=csv.DictReader(f)
                if not {'Uid','Sid','Tag','Key','Time','Value','UpdateTime'}<=set(reader.fieldnames or []):
                    raise SafeError('unsupported_csv_columns')
                # 身份仅用来分区，绝不传出；无原始行日志。
                rows=list(reader)
        except (OSError,KeyError,UnicodeError,csv.Error):
            raise SafeError('local_csv_unavailable') from None
        groups=sorted({(r['Uid'],r['Sid']) for r in rows})
        if not groups: raise SafeError('empty_dataset')
        selected=cfg.get('source_group_index')
        if len(groups)>1 and selected is None: raise SafeError('multiple_sources_require_selection')
        if selected is None: selected=1
        if isinstance(selected,bool) or not isinstance(selected,int) or not 1<=selected<=len(groups):
            raise SafeError('invalid_source_selection')
        pair=groups[selected-1]
        chosen={}; counts=Counter(); dates=set(); vendor=[]; corrupt_flags={}
        for index,r in enumerate(rows):
            if (r['Uid'],r['Sid'])!=pair: continue
            if r['Tag']=='daily_mark':
                counts['daily_mark_ignored']+=1; continue
            if r['Tag']!='daily_report' or r['Key'] not in TARGETS: continue
            key=r['Key']
            try:
                dt=unix_seconds(r['Time']); updated=unix_seconds(r['UpdateTime']).timestamp()
                d=dt.date().isoformat(); dates.add(d)
                try:
                    v=json.loads(r['Value'])
                    if not isinstance(v,dict): raise ValueError()
                except (ValueError,TypeError):
                    corrupt_flags.setdefault(d,{})[TARGETS[key][1]]=['invalid_summary']
                    counts['invalid_target_records']+=1
                    continue
            except (SafeError,ValueError,TypeError):
                counts['invalid_target_records']+=1; continue
            identity=(d,key)
            if identity in chosen: counts['duplicate_daily_summaries']+=1
            rank=(updated,index)
            if identity not in chosen or rank>=chosen[identity][0]: chosen[identity]=(rank,v)
        dayrows={d:{'date':d,'_flags':corrupt_flags.get(d,{})} for d in dates}
        for (d,key),(_,v) in chosen.items():
            source_field,metric=TARGETS[key]; raw=v.get(source_field)
            counts[key+'_reports']+=1
            if source_field in v: counts[key+'_field_present']+=1
            row=dayrows[d]; flags=[]
            if raw is not None and (isinstance(raw,bool) or not isinstance(raw,(int,float))):
                raw=None; flags.append('invalid_type')
            elif raw is not None and not math.isfinite(raw):
                raw=None; flags.append('non_finite')
            if key=='sleep':
                if raw is not None and (sleep.get('confirmed') or sleep_minutes_evidence(v)):
                    raw=raw/60 if finite_number(raw) else raw
                    counts['sleep_minutes_verified']+=1
                else:
                    raw=None; flags.append('unit_unconfirmed')
                    counts['sleep_unit_unconfirmed']+=1
            if key=='intensity':
                vendor.append({'date':d,'source_field':'intensity.duration','value':raw if finite_number(raw) else None,
                    'unit':activity.get('unit') if confirmed else 'unconfirmed',
                    'semantic_status':'confirmed' if confirmed else 'semantic_unconfirmed'})
                if not confirmed: raw=None; flags.append('semantic_unconfirmed')
                elif activity['unit']=='seconds' and finite_number(raw): raw=raw/60
            row[metric]=raw; row['_flags'][metric]=flags
        if not dayrows: raise SafeError('no_target_daily_reports')
        # 核验静息心率明细，不把普通心率替代静息心率，不进行二次累计。
        detail_path=cfg.get('fitness_csv')
        if detail_path:
            try:
                with open(detail_path,encoding='utf-8-sig',newline='') as f:
                    for r in csv.DictReader(f):
                        if (r.get('Uid'),r.get('Sid'))!=pair or r.get('Key')!='resting_heart_rate': continue
                        try:
                            d=unix_seconds(r['Time']).date().isoformat()
                            v=json.loads(r['Value']); bpm=v.get('bpm')
                            if finite_number(bpm):
                                counts['resting_detail_records']+=1
                                if d in dayrows and dayrows[d].get(METRICS[0]) is not None: counts['resting_detail_same_day_summary']+=1
                        except (SafeError,ValueError,TypeError,AttributeError): counts['invalid_resting_detail']+=1
                counts['fitness_file_read']=1
            except (OSError,UnicodeError,csv.Error): counts['fitness_file_unavailable']=1
        metadata={'file_status':{'aggregated':'read','fitness':'read' if counts['fitness_file_read'] else 'not_available'},
            'parser_counts':dict(counts),
            'field_mapping':{METRICS[0]:'heart_rate.avg_rhr',METRICS[1]:'intensity.duration',METRICS[2]:'sleep.total_duration'},
            'activity_confirmation':'confirmed' if confirmed else 'semantic_unconfirmed',
            'sleep_unit_rule':'minutes: per-record segment timestamp consistency or explicit evidenced local config',
            'vendor_activity':vendor,
            'limitations':['仅使用 daily_report 日汇总；daily_mark 不作为数值。',
                '日期归属采用汇总 Time 在 Asia/Shanghai 的日期，不重分配跨午夜睡眠。',
                '多段与午睡由厂商日汇总决定；不重复累加明细或推断睡眠阶段。',
                '没有单记录单位核验证据且无显式确认配置时，睡眠输出 null。',
                '真实运动缺失不插值、不补零；活动语义默认未确认。',
                '移除直接身份字段不意味着完全匿名。']}
        return Dataset('real_local_01','real',sorted(dayrows.values(),key=lambda r:r['date']),confirmed,metadata)
