import logging
import sys
from mcp.server.fastmcp import FastMCP
from .service import Registry
logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
# SDK 自身的工具参数/协议日志限制为 WARNING，不输出调用者原始输入。
logging.getLogger('mcp').setLevel(logging.WARNING)
registry=Registry()
mcp=FastMCP('wearable-module-1')

@mcp.tool()
def get_daily_metrics(dataset_id: str, start_date: str | None = None, end_date: str | None = None) -> dict:
    """查询已注册数据集的最小化日指标，最多 366 天。"""
    return registry.query('get_daily_metrics',dataset_id,start_date,end_date)

@mcp.tool()
def get_weekly_features(dataset_id: str, start_date: str | None = None, end_date: str | None = None) -> dict:
    """周一至周日统计：观测与估算分离，正式达标不使用插值。"""
    return registry.query('get_weekly_features',dataset_id,start_date,end_date)

@mcp.tool()
def get_data_quality_report(dataset_id: str, start_date: str | None = None, end_date: str | None = None) -> dict:
    """无身份字段的覆盖率、插值与缺失汇总。"""
    return registry.query('get_data_quality_report',dataset_id,start_date,end_date)

if __name__=='__main__': mcp.run(transport='stdio')
