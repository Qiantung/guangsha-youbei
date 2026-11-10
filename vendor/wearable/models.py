from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Protocol

TZ = timezone(timedelta(hours=8), 'Asia/Shanghai')
METRICS = ('resting_heart_rate_bpm', 'moderate_activity_minutes', 'sleep_duration_hours')
UNITS = dict(zip(METRICS, ('bpm', 'minutes', 'hours')))
MOCK_RANGES = dict(zip(METRICS, ((55,85),(0,90),(6,9))))
# 宽松的原型有效性边界，不是医学正常范围；可按经核实的设备规则替换。
REAL_RANGES = dict(zip(METRICS, ((1,300),(0,1440),(0,24))))
QUALITY_FLAGS = frozenset(('missing_date','missing','invalid_type','non_finite','out_of_range','semantic_unconfirmed','unit_unconfirmed','invalid_summary','interpolated','data_gap','endpoint_gap','not_interpolated'))
SCENARIOS = {'demo_01':'稳定记录', 'demo_02':'运动时长逐周增加', 'demo_03':'数据质量与故障处理'}

class SafeError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)

@dataclass
class Dataset:
    dataset_id: str
    mode: str
    records: list[dict]
    activity_confirmed: bool = True
    metadata: dict = field(default_factory=dict)
    faults: list[dict] = field(default_factory=list)

    def to_dataframe(self):
        """同一白名单/单位/日时间格式，pd.NA 只存在于内部 DataFrame。"""
        from .standard_frame import to_standard_dataframe
        return to_standard_dataframe(self)

class DataSource(Protocol):
    def load(self) -> Dataset: ...

class VendorCloudSource:
    """接口占位，未连接任何厂商云端或 OAuth。"""
    def load(self):
        raise SafeError('cloud_adapter_not_implemented')

def parse_date(value):
    try:
        d = date.fromisoformat(value)
        if d.isoformat() != value: raise ValueError()
        return d
    except (TypeError, ValueError):
        raise SafeError('invalid_date') from None

def unix_seconds(value):
    try:
        if isinstance(value, bool): raise ValueError()
        n = int(value)
        if str(n) != str(value) or not 946684800 <= n <= 4102444800:
            raise ValueError()
        return datetime.fromtimestamp(n, TZ)
    except (ValueError, TypeError, OverflowError, OSError):
        raise SafeError('invalid_unix_seconds') from None

def days(start, end):
    for i in range((end-start).days+1):
        yield start+timedelta(days=i)
