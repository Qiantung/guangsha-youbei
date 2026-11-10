"""本地厂商解析器工厂；兼容未设置 source_type 的上一版 Xiaomi 配置。"""
from copy import deepcopy
from pathlib import Path
from .models import SafeError
from .huawei_parser import HuaweiCSVParser
from .xiaomi_parser import XiaomiCSVParser

PARSERS = {'xiaomi': XiaomiCSVParser, 'huawei': HuaweiCSVParser}

def create_parser(config, config_dir=None):
    if not isinstance(config, dict): raise SafeError('local_config_invalid')
    source_type = config.get('source_type', 'xiaomi')
    if not isinstance(source_type, str) or source_type not in PARSERS:
        raise SafeError('unsupported_source_type')
    settings = deepcopy(config.get(source_type, {}))
    if not isinstance(settings, dict): raise SafeError('local_config_invalid')
    if settings.get('enabled') is not True: return None
    root = Path(config_dir or Path.cwd())
    # 相对路径统一相对 local.config.json 所在目录，不依赖 MCP 主机的工作目录。
    def resolve_path(value):
        if not isinstance(value, str) or not value: raise SafeError('local_csv_unavailable')
        if '://' in value or value.startswith(('\\\\', '//')):
            raise SafeError('local_file_path_required')
        p = Path(value)
        return str(p if p.is_absolute() else root / p)
    if source_type == 'xiaomi':
        settings['aggregated_csv'] = resolve_path(settings.get('aggregated_csv'))
        if settings.get('fitness_csv'): settings['fitness_csv'] = resolve_path(settings['fitness_csv'])
    else:
        files = settings.get('files')
        if not isinstance(files, list): raise SafeError('huawei_files_required')
        for f in files:
            if not isinstance(f, dict): raise SafeError('huawei_mapping_invalid')
            f['path'] = resolve_path(f.get('path'))
    return PARSERS[source_type](settings)
