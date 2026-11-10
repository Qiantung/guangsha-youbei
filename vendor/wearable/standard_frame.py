"""所有数据源共享的日粒度 DataFrame 契约；不改变既有 Dataset/核心工具。"""
import math
import pandas as pd
from .models import METRICS, QUALITY_FLAGS, SafeError, parse_date

STANDARD_COLUMNS = ('date', 'timestamp', *METRICS, '_flags', '_updated')

def to_standard_dataframe(dataset):
    records = []
    for source in dataset.records:
        d = parse_date(source.get('date')).isoformat()
        raw_flags = source.get('_flags', {})
        flags = {m: [f for f in raw_flags.get(m, []) if isinstance(f, str) and f in QUALITY_FLAGS] for m in METRICS}
        row = {'date': d, 'timestamp': d + 'T00:00:00+08:00', '_flags': flags,
               '_updated': source.get('_updated', 0)}
        for m in METRICS:
            v = source.get(m)
            if v is not None:
                if isinstance(v, bool) or not isinstance(v, (int, float)):
                    v = None; flags[m].append('invalid_type')
                elif not math.isfinite(v):
                    v = None; flags[m].append('non_finite')
            row[m] = v
        if isinstance(row['_updated'], bool) or not isinstance(row['_updated'], (int, float)) or not math.isfinite(row['_updated']):
            raise SafeError('invalid_modification_time')
        records.append(row)
    df = pd.DataFrame(records, columns=STANDARD_COLUMNS)
    df['date'] = df['date'].astype('string')
    df['timestamp'] = df['timestamp'].astype('string')
    for m in METRICS:
        df[m] = df[m].astype('Float64')
    df['_updated'] = df['_updated'].astype('Float64')
    df.attrs = {'dataset_id': dataset.dataset_id, 'data_mode': dataset.mode,
                'timezone': 'Asia/Shanghai'}
    return df

def records_from_dataframe(frame):
    if tuple(frame.columns) != STANDARD_COLUMNS:
        raise SafeError('invalid_standard_dataframe')
    # 再次白名单，pd.NA 不得流到核心 JSON。attrs 不包含路径、原始行或身份。
    records = []
    for row in frame.to_dict(orient='records'):
        records.append({'date': row['date'], **{m: None if pd.isna(row[m]) else float(row[m]) for m in METRICS},
                        '_flags': row['_flags'], '_updated': float(row['_updated'])})
    return records

def normalize_dataset(dataset):
    dataset.records = records_from_dataframe(to_standard_dataframe(dataset))
    return dataset
