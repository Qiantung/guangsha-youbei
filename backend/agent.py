import json
import os
import re
import sys

from .models import Scenario
from .service import CONFIG, HEALTH_NOTICE, INSURANCE_NOTICE, ROOT, SYSTEM_NOTICE


class Agent:
    def __init__(self, service):
        self.service = service
        self.sessions = {}

    async def answer(self, message, scenario, session_id, transport):
        scenario = Scenario.model_validate(scenario).model_dump()
        key = (session_id, scenario["dataset_id"])
        memory = self.sessions.get(key, {})
        # Remember explicitly stated overrides; dataset changes isolate memory.
        values = dict(scenario, **memory)
        if "清除记忆" in message:
            self.sessions.pop(key, None)
            return {"reply":"本对象的对话参数记忆已清除。\n"+SYSTEM_NOTICE,"trace":[],"scenario":scenario}
        changes = {}
        patterns = {"pga":r"(?:PGA|pga)\s*[=:：]?\s*(\d+(?:\.\d+)?)", "age":r"(\d+(?:\.\d+)?)\s*岁",
                    "fortification_intensity":r"([6-9])\s*度设防", "building_area":r"(\d+(?:\.\d+)?)\s*(?:平方米|平米|㎡)"}
        for name, pattern in patterns.items():
            match = re.search(pattern,message)
            if match:
                changes[name] = int(match[1]) if name=="fortification_intensity" else float(match[1])
        for label, enum in [("砖混","brick"),("框架","frame"),("剪力墙","shear_wall")]:
            if label in message:
                changes["structure_type"] = enum
        if "睡眠" in message or "睡觉" in message:
            changes["sleeping"] = True
        if "清醒" in message:
            changes["sleeping"] = False
        if re.search(r"\d\s*级地震", message) and not re.search(r"PGA|pga",message):
            return {"reply":"震级不能直接换算为住宅所在地PGA。请给出场地PGA（单位g），例如“PGA 0.25g”；也可使用建筑页面的模拟场景。\n"+SYSTEM_NOTICE,"trace":[],"scenario":values}
        values.update(changes)
        values = Scenario.model_validate(values).model_dump()
        self.sessions[key] = {k: values[k] for k in set(memory)|set(changes)}
        intent = "report" if any(w in message for w in ("报告","建议","逃生")) else "incentive" if any(w in message for w in ("权益","兑换","折扣","保费","优惠","达标")) else "risk"
        tools = (["get_health_data","get_incentive_status","calculate_premium_discount","get_available_benefits"] if intent=="incentive" else
                 ["get_health_data","building_vulnerability","couple_risk","expected_losses","generate_disaster_report" if intent=="report" else "run_pipeline"])
        trace, results = [], {}
        if transport == "mcp":
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            params = StdioServerParameters(command=sys.executable,args=["-m","backend.mcp_server"],cwd=str(ROOT),env=dict(os.environ,QUAKE_DB=str(self.service.db_path)))
            async with stdio_client(params) as (read,write):
                async with ClientSession(read,write) as session:
                    await session.initialize()
                    for name in tools:
                        args = {"dataset_id":values["dataset_id"]} if name in ("get_health_data","get_incentive_status","get_available_benefits") else {"scenario":values}
                        out = await session.call_tool(name,args)
                        if out.isError:
                            raise ValueError("MCP tool failed")
                        payload = out.structuredContent
                        if payload is None:
                            payload = json.loads(next(c.text for c in out.content if hasattr(c,"text")))
                        results[name] = payload
                        trace.append({"tool":name,"transport":"MCP stdio调用","status":"success","input":args,"output":payload})
        else:
            r = self.service.pipeline(values,False)
            results = {"run_pipeline":r,"generate_disaster_report":{"report":self.service.report(r),"result":r},
                       "get_health_data":r["health"],"building_vulnerability":r["building"],"couple_risk":r["person"],
                       "expected_losses":r["losses"],"get_incentive_status":r["incentive"]["rules"],
                       "calculate_premium_discount":r["incentive"],"get_available_benefits":r["incentive"]["account"]}
            trace = [{"tool":n,"transport":"核心函数调用","status":"success","output":results[n]} for n in tools]
        if intent == "report":
            reply = results["generate_disaster_report"]["report"]
        elif intent == "incentive":
            r = results["calculate_premium_discount"]
            reply = ("保费分为建筑财产责任与人身伤亡责任；风险减量权益只针对人身责任，财产责任保费保持不变。\n"
                     f"本场景年度模拟应享额度：{r['annual_entitlement']:.6f} 元；年度人身保费额度上限：{r['cap_amount']:.2f} 元。\n"
                     "连续4个完整观测周达标后触发风险更新，年度只发差额；物资兑换消耗同一额度池，不可提现或现金补差。\n"
                     "当前只预览，不自动发放。\n"+"\n".join([HEALTH_NOTICE,INSURANCE_NOTICE,SYSTEM_NOTICE]))
        else:
            r = results["run_pipeline"]
            p = r["person"]["nominal_casualty_rates"]
            reply = (f"已按当前页面情景与本轮明确参数调用后端。模式：{r['person']['status']}。\n"
                     f"名义受伤率：{p['injury']:.8f}；名义死亡率：{p['death']:.8f}。\n"
                     f"建筑概率保持不变核验：{r['building_isolation_verified']}。\n"
                     "两个终点分别展示，不组成100%的饼图。健康修正数字为模拟，非真实减量效果。\n"+"\n".join(r["notices"]))
        return {"reply":reply,"intent":intent,"trace":trace,"scenario":values,
                "parser":"离线规则解析（未使用实际大模型推理）","version":CONFIG["version"]}
