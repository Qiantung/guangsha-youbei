"""华为离线 CSV 显式映射适配器。

不猜测厂商固定列名/单位；支持单份宽表或三类独立日汇总 CSV。
人工样例不是厂商真实导出规范。无网络、云 API、自动格式猜测或原始行日志。
"""
import csv
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from .models import Dataset, METRICS, SafeError, TZ, parse_date, unix_seconds
from .standard_frame import normalize_dataset

SEMANTICS = dict(zip(METRICS, ('resting_heart_rate', 'moderate_activity', 'sleep_duration')))
UNITS = {METRICS[0]: {'bpm'}, METRICS[1]: {'seconds', 'minutes', 'hours', 'hhmmss'},
         METRICS[2]: {'seconds', 'minutes', 'hours', 'hhmmss'}}
# 仅用于本地分区，不作为输出字段；显式 identity_columns 可补充实际导出列名。
IDENTITY_HEADERS = {'uid', 'sid', 'userid', 'user_id', 'deviceid', 'device_id', 'account',
                    '账号', '帐号', '用户id', '用户标识', '设备id', '设备标识', '设备序列号'}


def _basis(mapping):
    return isinstance(mapping.get('basis'), str) and bool(mapping['basis'].strip())


def parse_time(value, fmt, source_timezone):
    """ISO 带偏移保留绝对时刻；无偏移必须有显式时区，Unix 单位必须配置。"""
    if not isinstance(value, str) or not value.strip():
        raise SafeError('invalid_source_time')
    text = value.strip()
    try:
        zone = ZoneInfo(source_timezone) if source_timezone else None
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        raise SafeError('invalid_source_timezone') from None
    if fmt == 'unix_seconds':
        return unix_seconds(text)
    if fmt == 'unix_milliseconds':
        if not re.fullmatch(r'\d{13}', text):
            raise SafeError('invalid_source_time')
        number = int(text)
        unix_seconds(str(number // 1000))  # 明确毫秒后验证同一时间范围
        return datetime.fromtimestamp(number / 1000, TZ)
    try:
        if fmt == 'iso8601':
            if 'T' not in text and ' ' not in text:
                raise ValueError()
            dt = datetime.fromisoformat(text.replace('Z', '+00:00'))
        elif isinstance(fmt, str) and '%' in fmt:
            dt = datetime.strptime(text, fmt)
        else:
            raise SafeError('source_time_format_required')
        if dt.tzinfo is None:
            if zone is None: raise SafeError('source_timezone_required')
            # 不静默处理夏令时重复/不存在的墙上时间。
            if dt.replace(tzinfo=zone, fold=0).utcoffset() != dt.replace(tzinfo=zone, fold=1).utcoffset():
                raise SafeError('ambiguous_source_time')
            dt = dt.replace(tzinfo=zone)
        converted = dt.astimezone(TZ)
        unix_seconds(str(int(converted.timestamp())))
        return converted
    except (ValueError, TypeError, OverflowError, OSError):
        raise SafeError('invalid_source_time') from None


def parse_number(text, unit, metric):
    if text is None or not isinstance(text, str) or text.strip() == '':
        return None, ['missing']
    if not isinstance(unit,str) or unit not in UNITS[metric]:
        return None, ['unit_unconfirmed']
    value = text.strip()
    if unit == 'hhmmss':
        match = re.fullmatch(r'(\d+):([0-5]\d):([0-5]\d)', value)
        if not match: return None, ['invalid_type']
        n = int(match[1]) * 3600 + int(match[2]) * 60 + int(match[3])
        unit = 'seconds'
    else:
        if value.lower() in {'nan', '+nan', '-nan', 'inf', '+inf', '-inf', 'infinity', '+infinity', '-infinity'}:
            return None, ['non_finite']
        if not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?', value):
            return None, ['invalid_type']
        try: n = float(value)
        except (ValueError, OverflowError): return None, ['invalid_type']
    if not math.isfinite(n): return None, ['non_finite']
    if metric == METRICS[0]: return n, []
    seconds = n * {'seconds': 1, 'minutes': 60, 'hours': 3600}[unit]
    if not math.isfinite(seconds): return None, ['non_finite']
    return seconds / (60 if metric == METRICS[1] else 3600), []


class HuaweiCSVParser:
    def __init__(self, config):
        self.config = config

    def load_dataframe(self):
        return self.load().to_dataframe()

    def _validate_file(self, cfg):
        if not isinstance(cfg, dict): raise SafeError('huawei_mapping_invalid')
        if cfg.get('granularity') != 'daily_summary':
            raise SafeError('huawei_daily_summary_required')
        if cfg.get('delimiter') not in (',', ';', '\t'):
            raise SafeError('huawei_delimiter_required')
        if cfg.get('encoding') not in ('utf-8-sig', 'utf-8', 'gb18030', 'utf-16'):
            raise SafeError('huawei_encoding_required')
        if not isinstance(cfg.get('date_column'), str) or not cfg['date_column']:
            raise SafeError('huawei_date_column_required')
        if not cfg.get('date_format'): raise SafeError('source_time_format_required')
        if not cfg.get('timezone') and cfg['date_format'] != 'iso8601':
            raise SafeError('source_timezone_required')
        mappings = cfg.get('metrics')
        if not isinstance(mappings, dict) or not mappings or not set(mappings) <= set(METRICS):
            raise SafeError('huawei_mapping_invalid')
        for metric, mapping in mappings.items():
            if not isinstance(mapping, dict) or not isinstance(mapping.get('column'), str) or not mapping['column']:
                raise SafeError('huawei_mapping_invalid')
            if mapping.get('confirmed') is True:
                if mapping.get('semantic') != SEMANTICS[metric] or not _basis(mapping) or not isinstance(mapping.get('unit'),str) or mapping['unit'] not in UNITS[metric]:
                    raise SafeError('mapping_confirmation_incomplete')
        identities = cfg.get('identity_columns', [])
        if not isinstance(identities, list) or any(not isinstance(x, str) or not x for x in identities):
            raise SafeError('huawei_identity_columns_invalid')
        if cfg.get('single_source_confirmed') not in (True, False, None):
            raise SafeError('huawei_mapping_invalid')
        if cfg.get('updated_column') and not cfg.get('updated_format'):
            raise SafeError('huawei_updated_format_required')
        return mappings

    def _read_file(self, cfg):
        try:
            # 只允许本机普通文件，不支持 URL、压缩包或跟随下载链接。
            path = Path(cfg['path'])
            if not path.is_file(): raise SafeError('local_csv_unavailable')
            with path.open(encoding=cfg['encoding'], newline='') as f:
                reader = csv.DictReader(f, delimiter=cfg['delimiter'], strict=True)
                headers = reader.fieldnames or []
                if not headers or len(headers) != len(set(headers)):
                    raise SafeError('huawei_duplicate_or_missing_headers')
                required = {cfg['date_column'], *(m['column'] for m in cfg['metrics'].values()), *cfg.get('identity_columns', [])}
                if cfg.get('updated_column'): required.add(cfg['updated_column'])
                if not required <= set(headers): raise SafeError('huawei_required_columns_missing')
                rows = list(reader)
                if any(None in row for row in rows): raise SafeError('huawei_row_width_invalid')
        except (OSError, UnicodeError, csv.Error, KeyError, TypeError, ValueError):
            raise SafeError('local_csv_unavailable') from None
        identity_columns = list(dict.fromkeys(cfg.get('identity_columns', []) +
            [h for h in headers if h.lower().strip() in IDENTITY_HEADERS]))
        if identity_columns:
            if any(not row.get(c) for row in rows for c in identity_columns):
                raise SafeError('huawei_identity_value_missing')
            groups = sorted({tuple(row[c] for c in identity_columns) for row in rows})
            selected = cfg.get('source_group_index')
            if len(groups) > 1 and selected is None:
                raise SafeError('multiple_sources_require_selection')
            if selected is None: selected = 1
            if isinstance(selected, bool) or not isinstance(selected, int) or not 1 <= selected <= len(groups):
                raise SafeError('invalid_source_selection')
            pair = groups[selected - 1]
            return [r for r in rows if tuple(r[c] for c in identity_columns) == pair], pair
        if cfg.get('single_source_confirmed') is not True:
            raise SafeError('huawei_single_source_confirmation_required')
        if not rows: raise SafeError('empty_dataset')
        return rows, None

    def load(self):
        files = self.config.get('files')
        if not isinstance(files, list) or not 1 <= len(files) <= 3:
            raise SafeError('huawei_files_required')
        chosen = {}; counts = Counter(); dates = set(); source_pairs = []; vendor = {}
        confirmed_activity = False; seen_metrics = set()
        for file_index, cfg in enumerate(files):
            mappings = self._validate_file(cfg)
            # 同一指标禁止跨文件重复映射，以免汇总与明细重复统计。
            if seen_metrics & set(mappings): raise SafeError('huawei_metric_mapped_twice')
            seen_metrics.update(mappings)
            rows, pair = self._read_file(cfg)
            if pair is not None: source_pairs.append(pair)
            for index, raw in enumerate(rows):
                try:
                    dt = parse_time(raw.get(cfg['date_column']), cfg['date_format'], cfg.get('timezone'))
                    updated = parse_time(raw.get(cfg['updated_column']), cfg['updated_format'], cfg.get('timezone')).timestamp() if cfg.get('updated_column') else 0
                except SafeError:
                    # 明确拒绝而不悄悄抹去业务日期；错误码不含原始输入。
                    raise SafeError('huawei_invalid_time') from None
                d = dt.date().isoformat(); dates.add(d)
                if len(dates) > 3660: raise SafeError('dataset_too_large')
                for metric, mapping in mappings.items():
                    value, flags = parse_number(raw.get(mapping['column']), mapping.get('unit'), metric)
                    semantic_confirmed = mapping.get('confirmed') is True
                    unit_confirmed = semantic_confirmed or mapping.get('unit_confirmed') is True
                    if not unit_confirmed:
                        flags.append('unit_unconfirmed')
                    if metric == METRICS[1]:
                        confirmed_activity = semantic_confirmed
                        # 厂商字段仅留日粒度、标量，本地独立展示；不回显原始表头/配置依据。
                        vendor_rank = (updated, index)
                        if (d,file_index) not in vendor or vendor_rank >= vendor[(d,file_index)][0]:
                            display_value = value if unit_confirmed else parse_number(raw.get(mapping['column']),'bpm',METRICS[0])[0]
                            vendor[(d,file_index)] = (vendor_rank, {'date': d, 'source_field': 'huawei.activity_daily',
                                'value': display_value, 'unit': 'minutes' if unit_confirmed and 'unit_unconfirmed' not in flags else 'unconfirmed',
                                'semantic_status': 'confirmed' if semantic_confirmed else 'semantic_unconfirmed'})
                    if not semantic_confirmed:
                        value = None; flags.append('semantic_unconfirmed')
                    key = (d, metric)
                    rank = (updated, index)
                    if key in chosen: counts['duplicate_daily_summaries'] += 1
                    if key not in chosen or rank >= chosen[key][0]:
                        chosen[key] = (rank, value, flags)
                    counts['target_fields_read'] += 1
            counts['files_read'] += 1
        # 分开的目标文件如有来源身份，必须同一对象；没有身份列的文件靠本地显式确认。
        if source_pairs and any(p != source_pairs[0] for p in source_pairs[1:]):
            raise SafeError('huawei_cross_file_source_mismatch')
        if not dates: raise SafeError('empty_dataset')
        records = []
        for d in sorted(dates):
            row = {'date': d, '_flags': {}, '_updated': 0}
            for metric in METRICS:
                _, value, flags = chosen.get((d, metric), ((0, 0), None, ['missing']))
                row[metric] = value; row['_flags'][metric] = sorted(set(flags))
            records.append(row)
        metadata = {'source_type': 'huawei', 'synthetic_fixture': self.config.get('synthetic_fixture') is True, 'file_status': {'huawei': 'read'},
            'parser_counts': dict(counts), 'vendor_activity': [vendor[k][1] for k in sorted(vendor)],
            'activity_confirmation': 'confirmed' if confirmed_activity else 'semantic_unconfirmed',
            'field_mapping': {m: 'huawei.configured_daily_field' for m in seen_metrics},
            'limitations': ['列名、分隔符、单位、语义与时区来自本地显式配置，未假定厂商固定 CSV 规范。',
                '仅解析日汇总；秒级普通心率、睡眠阶段和运动明细不导出，也不冒充日汇总。',
                '睡眠日期归属遵从所配置日汇总业务时间，不二次累加睡眠段或午睡。',
                '真实活动缺失不插值、不补零，语义未确认时正式达标 unknown。',
                '多个文件必须属于同一明确选择对象，不能将不同设备合并。',
                '移除直接身份字段不保证完全匿名。']}
        return normalize_dataset(Dataset('real_local_01', 'real', records, confirmed_activity, metadata))
