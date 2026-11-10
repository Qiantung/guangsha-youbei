"""并列厂商适配器：保留已验证的 Xiaomi 导出解析逻辑。"""
from .xiaomi import XiaomiSource
from .standard_frame import normalize_dataset

class XiaomiCSVParser(XiaomiSource):
    def load(self):
        dataset = super().load()
        dataset.metadata['source_type'] = 'xiaomi'
        return normalize_dataset(dataset)

    def load_dataframe(self):
        return self.load().to_dataframe()
