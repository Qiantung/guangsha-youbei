import asyncio
import json
from datetime import date, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from backend.agent import Agent
from backend.app import create_app
from backend.models import Scenario
from backend.service import CONFIG, DomainError, Service


@pytest.fixture
def service(tmp_path):
    return Service(tmp_path / "demo.sqlite3")


def test_complete_chain(service):
    r = service.pipeline(Scenario().model_dump(),True)
    assert len(service.data("demo_01")["daily"]) == 28
    assert len(r["health"]["weekly_standard_status"]) == 4
    assert all(r["health"]["weekly_standard_status"])
    assert sum(r["building"]["damage_probabilities"].values()) == pytest.approx(1)
    assert r["building_isolation_verified"]
    assert r["incentive"]["new_grant"] == 20
    assert r["incentive"]["property_premium_final"] == 300
    assert r["losses"]["total_expected_loss"] == pytest.approx(r["losses"]["building_expected_loss"]+r["losses"]["human_expected_loss"])


def test_reference_does_not_fabricate(service):
    r = service.pipeline(Scenario(mode="reference").model_dump(),True)
    assert r["building"]["damage_probabilities"] is None
    assert r["losses"]["total_expected_loss"] is None
    assert r["person"]["health_effect"] == "未估计"
    assert r["incentive"]["new_grant"] == 0


@pytest.mark.parametrize("grade",range(1,6))
def test_reference_baselines(service,grade):
    r = service.risk(Scenario(mode="reference",reference_floor_grade=grade).model_dump())
    assert r["person"]["nominal_casualty_rates"]["injury"] == CONFIG["injury_rates"][grade-1]
    assert r["person"]["nominal_casualty_rates"]["death"] == CONFIG["death_rates"][grade-1]


@pytest.mark.parametrize("age,sleep",[(0,False),(120,True),(65,False)])
def test_building_isolation(service,age,sleep):
    r = service.risk(Scenario(age=age,sleeping=sleep).model_dump())
    original = service.building(Scenario().model_dump())
    assert r["building"]["damage_probabilities"] == original["damage_probabilities"]
    assert r["building_isolation_verified"]
    for v in r["person"]["nominal_casualty_rates"].values():
        assert 0<=v<=1


def test_zero_pga(service):
    r = service.pipeline(Scenario(pga=0).model_dump(),True)
    assert r["building"]["damage_probabilities"]["DS0"] == 1
    assert r["losses"]["total_expected_loss"] == 0
    assert r["risk_reduction_rate"] == 0
    assert r["incentive"]["new_grant"] == 0


def test_quality_prevents_false_achievement(service):
    r=service.rules("demo_03")
    assert not r["eligible"]
    assert any(w["status"]=="unknown" for w in r["weeks"])
    assert service.pipeline(Scenario(dataset_id="demo_03").model_dump(),True)["incentive"]["new_grant"]==0


def test_idempotent_grants(service):
    s=Scenario().model_dump()
    service.pipeline(s,True)
    r=service.pipeline(s,True)
    assert r["incentive"]["new_grant"]==0
    assert r["incentive"]["account"]["balance"]["granted"]==20


def test_redemption_and_reversal(service):
    service.pipeline(Scenario().model_dump(),True)
    service.redeem("demo_01","whistle","request-1")
    assert service.redeem("demo_01","whistle","request-1")["duplicate"]
    assert service.account("demo_01")["balance"]["available"]==15
    service.reverse("demo_01","request-1")
    assert service.reverse("demo_01","request-1")["duplicate"]
    assert service.account("demo_01")["balance"]["available"]==20
    assert service.account("demo_01")["catalog"][0]["stock"]==50


def test_concurrent_redemption_no_overdraw(service):
    service.pipeline(Scenario().model_dump(),True)
    def buy(i):
        try:
            service.redeem("demo_01","battery",f"buy-{i}")
            return True
        except DomainError:
            return False
    with ThreadPoolExecutor(2) as pool:
        success=list(pool.map(buy,range(2)))
    assert sum(success)==1
    assert service.account("demo_01")["balance"]["available"]==5


def test_insufficient_balance(service):
    with pytest.raises(DomainError) as err:
        service.redeem("demo_01","torch","r")
    assert err.value.code=="INSUFFICIENT_BALANCE"


def test_catalog_preview_matches_committed_balance(service):
    service.pipeline(Scenario().model_dump(),True)
    before = service.account("demo_01")
    item = next(i for i in before["catalog"] if i["id"] == "whistle")
    assert item["can_redeem"] and before["balance"]["cap_amount"] == 20
    after = service.redeem("demo_01","whistle","preview-test")["account"]
    assert item["available_after"] == after["balance"]["available"]
    closed = service.close_year("demo_01")
    assert all(not i["can_redeem"] and i["available_after"] is None for i in closed["catalog"])


def test_year_close_and_late_reversal(service):
    s=Scenario().model_dump()
    service.pipeline(s,True)
    service.redeem("demo_01","whistle","old-request")
    service.close_year("demo_01")
    service.close_year("demo_01")
    service.reverse("demo_01","old-request")
    a=service.account("demo_01")["balance"]
    assert a["available"]==0 and a["expired"]==20 and a["used"]==0
    with pytest.raises(DomainError):
        service.pipeline(s,True)
    with pytest.raises(DomainError):
        service.redeem("demo_01","whistle","new-request")


def test_data_and_account_survive_restart(service):
    service.pipeline(Scenario().model_dump(),True)
    service.redeem("demo_01","whistle","r")
    second=Service(service.db_path)
    assert second.account("demo_01")["balance"]["available"]==15
    with second.db() as db:
        assert db.execute("SELECT count(*) FROM daily WHERE dataset='demo_01'").fetchone()[0]==28


@pytest.mark.parametrize("field,value",[("pga",-1),("age",121),("sleeping","yes"),("floor_count",0),("structure_type","unknown"),("pga",float('inf')),("pga",True)])
def test_invalid_parameters(service,field,value):
    client=TestClient(create_app(service))
    data=Scenario().model_dump();data[field]=value
    # nonfinite cannot be encoded with strict JSON; model validation is tested directly.
    if value==float('inf'):
        with pytest.raises(ValueError):
            Scenario.model_validate(data)
        return
    response=client.post('/api/run',json={"scenario":data})
    assert response.status_code==422
    assert "traceback" not in response.text.lower()


def test_date_validation(service):
    client=TestClient(create_app(service))
    assert client.get('/api/data/demo_01?start=2026-09-10&end=2026-09-01').status_code==400


@pytest.mark.parametrize("message",["查询风险","生成防灾报告","保费与权益怎么计算"])
def test_agent_notices(service,message):
    r=asyncio.run(Agent(service).answer(message,Scenario().model_dump(),"test","core"))
    assert "医学" in r["reply"] and "定价" in r["reply"] and "单人" in r["reply"]
    assert len(r["trace"])>=4


def test_memory_and_magnitude(service):
    agent=Agent(service)
    a=asyncio.run(agent.answer("65岁 PGA 0.4g",Scenario().model_dump(),"session","core"))
    b=asyncio.run(agent.answer("睡眠状态呢",Scenario().model_dump(),"session","core"))
    assert b["scenario"]["pga"]==0.4 and b["scenario"]["age"]==65
    c=asyncio.run(agent.answer("7级地震会怎样",Scenario().model_dump(),"session","core"))
    assert not c["trace"]
    assert "不能直接换算" in c["reply"]


def test_real_mcp_three_scenarios(service):
    async def verify():
        agent=Agent(service)
        for message in ["查询风险","生成防灾报告","保费权益说明"]:
            r=await agent.answer(message,Scenario().model_dump(),"mcp-test","mcp")
            assert all(t["transport"]=="MCP stdio调用" for t in r["trace"])
            assert "定价" in r["reply"]
    asyncio.run(verify())


def test_missing_import_keeps_mock_available(tmp_path):
    config = {"source_type":"huawei", "huawei":{"enabled":True,"files":[]}}
    cfg = tmp_path / "local.config.json"
    cfg.write_text(json.dumps(config),encoding="utf-8")
    service = Service(tmp_path / "db.sqlite3", cfg)
    assert service.registry.import_error
    assert len(service.data("demo_01")["daily"]) == 28


def test_local_csv_import_enters_full_chain(tmp_path):
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / "config/local.config.example.json").read_text(encoding="utf-8"))
    config["source_type"] = "huawei"
    config["huawei"]["enabled"] = True
    mapping = config["huawei"]["files"][0]
    mapping["path"] = "daily.csv"
    mapping["single_source_confirmed"] = True
    for metric in mapping["metrics"].values():
        metric["confirmed"] = True
        metric["basis"] = "合成测试字段语义与单位已知"
    rows = ["日期,静息心率(次/分),活动时长(分钟),睡眠总时长(分钟)"]
    rows += [f"{date(2026,8,31)+timedelta(days=i)},62,30,480" for i in range(28)]
    (tmp_path / "daily.csv").write_text("\n".join(rows),encoding="utf-8")
    cfg = tmp_path / "local.config.json"
    cfg.write_text(json.dumps(config),encoding="utf-8")
    service = Service(tmp_path / "db.sqlite3", cfg)
    assert service.registry.import_error is None
    dataset = next(k for k in service.registry.datasets if k not in ("demo_01","demo_02","demo_03"))
    result = service.pipeline(Scenario(dataset_id=dataset).model_dump())
    assert service.rules(dataset)["eligible"]
    assert result["building_isolation_verified"]
    assert service.health(dataset)["sleep_pattern"]["sleep_duration_hour"] == 8
