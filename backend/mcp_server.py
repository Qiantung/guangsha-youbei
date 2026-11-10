"""stdio MCP. Updated schema intentionally differs from the old four-state model."""
from mcp.server.fastmcp import FastMCP

from .service import Service

mcp = FastMCP("广厦有备本地演示")
service = Service()


@mcp.tool()
def get_health_data(dataset_id: str = "demo_01", time_range: str = "30d") -> dict:
    """查询本地授权或模拟健康摘要。完整观测周才参与达标。"""
    return service.health(dataset_id, time_range)


@mcp.tool()
def building_vulnerability(scenario: dict) -> dict:
    """建筑模拟参考；国内参数未补证时不提供正式曲线计算。"""
    return service.building(scenario)


@mcp.tool()
def couple_risk(scenario: dict) -> dict:
    """人员两终点后果与情景对比。人员指标不改变建筑概率。"""
    result = service.risk(scenario)
    return {"person":result["person"],"comparison":result["comparison"],"building_isolation_verified":result["building_isolation_verified"]}


@mcp.tool()
def expected_losses(scenario: dict) -> dict:
    """Python计算单人后果金额，成本标记为模拟，非实际合同赔付。"""
    return service.risk(scenario)["losses"]


@mcp.tool()
def get_incentive_status(dataset_id: str = "demo_01") -> dict:
    """查询连续四周完整观测达标状态，不按自然月触发。"""
    return service.rules(dataset_id)


@mcp.tool()
def calculate_premium_discount(scenario: dict) -> dict:
    """预览年度人身责任额度，10%上限，不修改财产保费，不落发放流水。"""
    return service.incentive(service.risk(scenario), False)


@mcp.tool()
def get_available_benefits(dataset_id: str = "demo_01") -> dict:
    """读取模拟物资、权益余额和流水。"""
    return service.account(dataset_id)


@mcp.tool()
def run_pipeline(scenario: dict) -> dict:
    """串联时序、建筑、人员、损失、权益预览；不自动发放。"""
    return service.pipeline(scenario, False)


@mcp.tool()
def generate_disaster_report(scenario: dict) -> dict:
    """防灾报告内容由Python工具生成，数字不由语言模型计算。"""
    result = service.pipeline(scenario, False)
    return {"report":service.report(result),"result":result}


if __name__ == "__main__":
    mcp.run(transport="stdio")
