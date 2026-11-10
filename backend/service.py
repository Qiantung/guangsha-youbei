"""All calculations are Python. Demo parameters are explicitly synthetic."""
import json
import math
import os
import sqlite3
import statistics
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .models import Scenario

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from wearable.service import Registry  # noqa: E402
from wearable.processing import clean  # noqa: E402
from wearable.models import METRICS, SCENARIOS  # noqa: E402

HEALTH_NOTICE = "注：可穿戴指标仅用于地震灾害场景的探索性风险分层，不构成医学诊断、健康建议或医疗评价。"
INSURANCE_NOTICE = "注：当前结果为技术原型仿真测算，不构成保险产品承诺或定价依据，正式落地需保险精算专业校验。"
SYSTEM_NOTICE = "注：当前成果为本地单人演示技术原型，不代表正式产品的数据接入能力。"
CONFIG = json.loads((ROOT / "config/demo.json").read_text(encoding="utf-8"))
DS = [f"DS{i}" for i in range(5)]
GRADES = ["I", "II", "III", "IV", "V"]


class DomainError(Exception):
    def __init__(self, code, message):
        self.code, self.message = code, message


class Service:
    def __init__(self, db_path=None, config_path=None):
        self.db_path = Path(db_path or os.environ.get("QUAKE_DB", ROOT / "private/demo.sqlite3"))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        local_config = config_path or ROOT / "local.config.json"
        self.registry = Registry(str(local_config) if Path(local_config).exists() else None)
        # Stable object A: four complete observed achieved weeks; B keeps trend, C faults.
        a = self.registry.datasets["demo_01"]
        for i, row in enumerate(a.records):
            row[METRICS[1]] = 28 + i % 5
        a.metadata["demo_override"] = "四周达标演示；固定日活动28至32分钟"
        self.registry.processed["demo_01"] = clean(a)
        with self.db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS daily(dataset TEXT,day TEXT,payload TEXT,PRIMARY KEY(dataset,day));
            CREATE TABLE IF NOT EXISTS account(dataset TEXT,year TEXT,granted REAL DEFAULT 0,used REAL DEFAULT 0,expired REAL DEFAULT 0,entitlement REAL DEFAULT 0,PRIMARY KEY(dataset,year));
            CREATE TABLE IF NOT EXISTS grants(dataset TEXT,year TEXT,period TEXT,amount REAL,payload TEXT,PRIMARY KEY(dataset,year,period));
            CREATE TABLE IF NOT EXISTS uses(redemption_id TEXT PRIMARY KEY,dataset TEXT,year TEXT,item TEXT,cost REAL,status TEXT,at TEXT);
            CREATE TABLE IF NOT EXISTS stock(item TEXT PRIMARY KEY,quantity INTEGER);
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,at TEXT,dataset TEXT,kind TEXT,payload TEXT);
            CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,dataset TEXT,payload TEXT);
            CREATE TABLE IF NOT EXISTS policy_state(dataset TEXT,year TEXT,closed INTEGER DEFAULT 0,PRIMARY KEY(dataset,year));
            """)
            for item in CONFIG["catalog"]:
                db.execute("INSERT OR IGNORE INTO stock VALUES(?,?)", (item["id"], item["stock"]))
            for key, (rows, _) in self.registry.processed.items():
                db.executemany("INSERT OR REPLACE INTO daily VALUES(?,?,?)", [(key, r["date"], json.dumps(r)) for r in rows])

    def db(self):
        db = sqlite3.connect(self.db_path, timeout=15)
        db.row_factory = sqlite3.Row
        return db

    def ensure(self, dataset):
        if dataset not in self.registry.datasets:
            raise DomainError("UNKNOWN_DATASET", "请选择已注册的演示对象。")

    def datasets(self):
        return {"datasets": [{"id": k, "name": SCENARIOS.get(k, "本地真实数据导入示范"),
                               "mode": d.mode, "days": len(self.registry.processed[k][0])}
                              for k, d in self.registry.datasets.items()],
                "import_status": "文件未配置或停用" if not (ROOT / "local.config.json").exists() else
                ("导入不可用，模拟演示正常" if self.registry.import_error else "配置已读取"),
                "version": CONFIG["version"]}

    def data(self, dataset, start=None, end=None):
        self.ensure(dataset)
        result = self.registry.query("get_daily_metrics", dataset, start, end)
        if not result["ok"]:
            raise DomainError("INVALID_DATE_RANGE", "日期须位于数据范围内，起始日期不能晚于结束日期。")
        with self.db() as db:
            result["data"]["records"] = [json.loads(r[0]) for r in db.execute(
                "SELECT payload FROM daily WHERE dataset=? AND day>=? AND day<=? ORDER BY day",
                (dataset,result["start_date"],result["end_date"]))]
        return {"raw": self.registry.datasets[dataset].records,
                "daily": result["data"]["records"],
                "weeks": self.registry.query("get_weekly_features", dataset, start, end)["data"]["weeks"],
                "quality": self.registry.query("get_data_quality_report", dataset, start, end)["data"],
                "mode": self.registry.datasets[dataset].mode, "units": result["units"]}

    def health(self, dataset, time_range="30d"):
        self.ensure(dataset)
        if time_range not in ("7d", "30d", "1week", "1month"):
            raise DomainError("INVALID_TIME_RANGE", "时间范围支持7d、30d、1week、1month。")
        rows = self.registry.processed[dataset][0]
        rows = rows[-7:] if time_range in ("7d", "1week") else rows[-30:]
        hr = [r["values"][METRICS[0]] for r in rows if r["quality"][METRICS[0]]["status"] == "observed"]
        sleep = [r["values"][METRICS[2]] for r in rows if r["quality"][METRICS[2]]["status"] == "observed"]
        all_weeks = self.data(dataset)["weeks"]
        weeks = all_weeks[-1:] if time_range in ("7d", "1week") else all_weeks
        full = [w["metrics"][METRICS[1]]["observed_statistic"] for w in weeks if w["metrics"][METRICS[1]]["observed_complete"]]
        return {"resting_hr_median": statistics.median(hr) if hr else None,
                "mvpa_minutes_week_avg": statistics.mean(full) if full else None,
                "sleep_pattern": {"avg_sleep_start": None, "avg_sleep_end": None,
                                  "sleep_duration_hour": statistics.mean(sleep) if sleep else None},
                "weekly_standard_status": [True if w["activity_status"] == "achieved" else False if w["activity_status"] == "not_achieved" else None for w in all_weeks],
                "available_complete_weeks": len(full), "window_days": len(rows),
                "note": "仅完整周观测用于达标；平均睡眠时刻未采集，不推算。"}

    def building(self, scenario):
        s = Scenario.model_validate(scenario)
        if s.mode == "reference":
            return {"damage_probabilities": None, "expected_property_loss": None,
                    "status": "参数待补证", "note": "国内住宅整栋易损曲线尚未补齐。参考模式只计算指定楼层名义率。"}
        p = CONFIG["fragility"][s.structure_type]
        factor = CONFIG["fortification_factors"][str(s.fortification_intensity)]
        exceed = [0.0 if s.pga == 0 else .5 * (1 + math.erf(math.log(s.pga / (m * factor)) / p["beta"] / math.sqrt(2))) for m in p["medians_g"]]
        probs = [1-exceed[0], *(exceed[i]-exceed[i+1] for i in range(3)), exceed[-1]]
        replacement = s.building_area * CONFIG["unit_cost_yuan_m2"]
        loss = math.fsum(v*r for v, r in zip(probs, CONFIG["loss_ratios"])) * replacement
        return {"damage_probabilities": dict(zip(DS, probs)), "expected_property_loss": loss,
                "building_replacement_cost": replacement, "damage_state_desc": dict(zip(DS, ["基本完好", "轻微破坏", "中等破坏", "严重破坏", "毁坏（非自动等于倒塌）"])),
                "status": "模拟参考", "parameter_version": CONFIG["version"],
                "note": "曲线、设防倍率和损失率均为模拟；楼层数仅记录，未用于该模拟曲线。"}

    def person(self, building, profile, mode="simulation", grade=4):
        if mode == "reference":
            weights = [float(i == grade-1) for i in range(5)]
        else:
            probs = building["damage_probabilities"]
            if set(probs) != set(DS) or not all(math.isfinite(v) and 0 <= v <= 1 for v in probs.values()) or abs(sum(probs.values())-1) > 1e-8:
                raise DomainError("INVALID_PROBABILITY", "建筑破坏概率参数不合法，请检查输入。")
            weights = [sum(probs[d]*CONFIG["floor_transition"][i][g] for i,d in enumerate(DS)) for g in range(5)]
        rates, modifiers, conditional = {}, {}, {}
        for endpoint in ("injury", "death"):
            eta = 0.0
            if mode == "simulation":
                b = CONFIG["health_log_or"][endpoint]
                x = [(profile["age"]-45)/10, (profile["resting_hr"]-70)/10,
                     (min(profile["mvpa_minutes_week"],300)-150)/150, float(profile["sleeping"])]
                eta = max(-2.0, min(2.0, math.fsum(a*c for a,c in zip(b,x))))
            factor = math.exp(eta)
            vals = [0 if r == 0 else factor*r/(1-r+factor*r) for r in CONFIG[endpoint+"_rates"]]
            rates[endpoint] = math.fsum(p*r for p,r in zip(weights,vals))
            modifiers[endpoint] = factor
            conditional[endpoint] = dict(zip(GRADES, vals))
        return {"nominal_casualty_rates": rates, "odds_modifiers": modifiers,
                "floor_grade_probabilities": dict(zip(GRADES,weights)), "conditional_by_floor_grade": conditional,
                "damage_probabilities": building["damage_probabilities"],
                "status": "模拟健康修正" if mode == "simulation" else "楼层名义率参考",
                "note": "受伤/死亡为分别估计的名义终点，不拼成四态分布；不属于医学诊断。",
                "health_effect": "模拟假设" if mode == "simulation" else "未估计"}

    def risk(self, scenario):
        s = Scenario.model_validate(scenario)
        h = self.health(s.dataset_id)
        if s.mode == "simulation" and (h["resting_hr_median"] is None or h["mvpa_minutes_week_avg"] is None):
            raise DomainError("INSUFFICIENT_DATA", "缺少静息心率观测或完整周活动记录，请切换对象或参考模式。")
        b = self.building(s.model_dump())
        profile = {"age": s.age, "resting_hr": h["resting_hr_median"],
                   "mvpa_minutes_week": h["mvpa_minutes_week_avg"], "sleeping": s.sleeping}
        current = self.person(b, profile, s.mode, s.reference_floor_grade)
        baseline_profile = dict(profile, mvpa_minutes_week=0)
        baseline = self.person(b, baseline_profile, s.mode, s.reference_floor_grade)
        awake = self.person(b, dict(profile,sleeping=False), s.mode,s.reference_floor_grade)
        asleep = self.person(b, dict(profile,sleeping=True), s.mode,s.reference_floor_grade)
        def human(result):
            return math.fsum(result["nominal_casualty_rates"][k]*CONFIG["casualty_costs"][k] for k in ("injury", "death")) if s.mode == "simulation" else None
        base_loss, human_loss = human(baseline), human(current)
        reduction = max(0, (base_loss-human_loss)/base_loss) if base_loss and s.mode == "simulation" else 0
        return {"scenario": s.model_dump(), "health": h, "building": b, "person": current,
                "comparison": {"no_activity": baseline, "awake": awake, "sleeping": asleep},
                "losses": {"building_expected_loss": b["expected_property_loss"], "human_expected_loss": human_loss,
                           "total_expected_loss": b["expected_property_loss"]+human_loss if human_loss is not None else None,
                           "cost_status": "模拟后果成本，非合同赔付" if human_loss is not None else "缺少后果金额，未估计"},
                "risk_reduction_rate": reduction, "risk_metric_type": "SIMULATED_EXPECTED_LOSS_COST",
                "baseline_definition": "同一建筑、年龄、心率与睡眠，周活动设为0的模拟对照；非真实投保基线",
                "building_isolation_verified": all(r["damage_probabilities"] == b["damage_probabilities"] for r in (current,baseline,awake,asleep)),
                "notices": [HEALTH_NOTICE,INSURANCE_NOTICE,SYSTEM_NOTICE]}

    def rules(self, dataset):
        weeks = self.data(dataset)["weeks"]
        count, periods = 0, []
        for w in weeks:
            count = count+1 if w["activity_status"] == "achieved" else 0
            if count == 4:
                periods.append(w["week_end"])
                count = 0
        return {"weeks": [{"week_start":w["week_start"],"status":w["activity_status"],"minutes":w["metrics"][METRICS[1]]["observed_statistic"]} for w in weeks],
                "completed_periods":periods,"remaining_streak":count,"threshold":150,
                "eligible":bool(periods),"note":"连续4个完整观测自然周触发；非自然月；未知周不视为达标。"}

    def event(self, db, dataset, kind, payload):
        db.execute("INSERT INTO events(at,dataset,kind,payload) VALUES(?,?,?,?)", (datetime.now(timezone.utc).isoformat(),dataset,kind,json.dumps(payload,ensure_ascii=False)))

    def trigger_rules(self, dataset):
        r = self.rules(dataset)
        with self.db() as db:
            self.event(db,dataset,"rules_evaluated",{"eligible":r["eligible"],"periods":r["completed_periods"]})
        return r

    def incentive(self, result, grant=False):
        dataset = result["scenario"]["dataset_id"]
        rules = self.rules(dataset)
        policy = CONFIG["policy"]
        rate = min(result["risk_reduction_rate"]*policy["k"],policy["cap"]) if rules["eligible"] and result["scenario"]["mode"] == "simulation" else 0
        entitlement = policy["casualty_premium"] * rate
        end = self.registry.processed[dataset][0][-1]["date"]
        year = end[:4]
        period = rules["completed_periods"][-1] if rules["completed_periods"] else end
        new = 0
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT OR IGNORE INTO account(dataset,year) VALUES(?,?)",(dataset,year))
            a = db.execute("SELECT * FROM account WHERE dataset=? AND year=?",(dataset,year)).fetchone()
            if grant and result["scenario"]["mode"] == "simulation" and rules["eligible"]:
                closed = db.execute("SELECT closed FROM policy_state WHERE dataset=? AND year=?",(dataset,year)).fetchone()
                if closed and closed[0]:
                    raise DomainError("POLICY_CLOSED","模拟保单年度已结束，不能继续发放。")
                exists = db.execute("SELECT 1 FROM grants WHERE dataset=? AND year=? AND period=?",(dataset,year,period)).fetchone()
                if not exists:
                    new = round(max(0,entitlement-a["granted"]),6)
                    db.execute("INSERT INTO grants VALUES(?,?,?,?,?)",(dataset,year,period,new,json.dumps({"version":CONFIG["version"],"entitlement":entitlement})))
                    db.execute("UPDATE account SET granted=granted+?,entitlement=? WHERE dataset=? AND year=?",(new,entitlement,dataset,year))
                    self.event(db,dataset,"incentive_granted",{"new_grant":new,"period":period,"mode":"simulation"})
        return {"rules":rules,"discount_rate":rate,"annual_entitlement":entitlement,"new_grant":new,
                "property_premium_final":policy["property_premium"],
                "casualty_premium_preview":policy["casualty_premium"]-entitlement,
                "note":"保费预览与物资共用同一额度，预览不会再次发放或扣减；仅物资兑换落账。",
                "cap_amount":policy["casualty_premium"]*policy["cap"],"account":self.account(dataset)}

    def account(self,dataset):
        self.ensure(dataset)
        year = self.registry.processed[dataset][0][-1]["date"][:4]
        with self.db() as db:
            a = db.execute("SELECT * FROM account WHERE dataset=? AND year=?",(dataset,year)).fetchone()
            account = dict(a) if a else {"dataset":dataset,"year":year,"granted":0,"used":0,"expired":0,"entitlement":0}
            account["available"] = round(account["granted"]-account["used"]-account["expired"],6)
            ledger = [dict(r) for r in db.execute("SELECT * FROM uses WHERE dataset=? AND year=? ORDER BY at DESC",(dataset,year))]
            grants = [dict(r) for r in db.execute("SELECT period,amount FROM grants WHERE dataset=? AND year=?",(dataset,year))]
            stocks = {r["item"]:r["quantity"] for r in db.execute("SELECT * FROM stock")}
            closed = db.execute("SELECT closed FROM policy_state WHERE dataset=? AND year=?",(dataset,year)).fetchone()
            account["closed"] = bool(closed and closed[0])
        account["cap_amount"] = CONFIG["policy"]["casualty_premium"] * CONFIG["policy"]["cap"]
        catalog = []
        for item in CONFIG["catalog"]:
            can_redeem = not account["closed"] and stocks[item["id"]] > 0 and account["available"] >= item["cost"]
            catalog.append(dict(item, stock=stocks[item["id"]], can_redeem=can_redeem,
                                available_after=round(account["available"]-item["cost"],6) if can_redeem else None))
        return {"balance":account,"uses":ledger,"grants":grants,"catalog":catalog,"unit":"权益点（1点=1元模拟额度）"}

    def redeem(self,dataset,item_id,redemption_id):
        self.ensure(dataset)
        item = next((i for i in CONFIG["catalog"] if i["id"]==item_id),None)
        if not item:
            raise DomainError("UNKNOWN_ITEM","物资不存在。")
        year = self.registry.processed[dataset][0][-1]["date"][:4]
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT * FROM uses WHERE redemption_id=?",(redemption_id,)).fetchone()
            if old:
                if old["dataset"]!=dataset or old["item"]!=item_id:
                    raise DomainError("ID_CONFLICT","兑换编号已用于其他请求。")
                return {"duplicate":True,"status":old["status"],"account":self.account(dataset)}
            closed = db.execute("SELECT closed FROM policy_state WHERE dataset=? AND year=?",(dataset,year)).fetchone()
            if closed and closed[0]:
                raise DomainError("POLICY_CLOSED","模拟保单年度已结束，不能继续兑换。")
            a = db.execute("SELECT * FROM account WHERE dataset=? AND year=?",(dataset,year)).fetchone()
            if not a or a["granted"]-a["used"]-a["expired"]+1e-9 < item["cost"]:
                raise DomainError("INSUFFICIENT_BALANCE","权益点不足，不支持现金补差。")
            if db.execute("SELECT quantity FROM stock WHERE item=?",(item_id,)).fetchone()[0] < 1:
                raise DomainError("OUT_OF_STOCK","模拟库存不足。")
            db.execute("UPDATE account SET used=used+? WHERE dataset=? AND year=?",(item["cost"],dataset,year))
            db.execute("UPDATE stock SET quantity=quantity-1 WHERE item=?",(item_id,))
            db.execute("INSERT INTO uses VALUES(?,?,?,?,?,?,?)",(redemption_id,dataset,year,item_id,item["cost"],"success",datetime.now(timezone.utc).isoformat()))
            self.event(db,dataset,"redeemed",{"item":item_id,"cost":item["cost"]})
        return {"duplicate":False,"status":"success","account":self.account(dataset)}

    def reverse(self,dataset,redemption_id):
        self.ensure(dataset)
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            r = db.execute("SELECT * FROM uses WHERE redemption_id=? AND dataset=?",(redemption_id,dataset)).fetchone()
            if not r:
                raise DomainError("NOT_FOUND","兑换记录不存在。")
            if r["status"]=="reversed":
                return {"duplicate":True,"account":self.account(dataset)}
            closed = db.execute("SELECT closed FROM policy_state WHERE dataset=? AND year=?",(dataset,r["year"])).fetchone()
            if closed and closed[0]:
                # Reverse prior consumption into expired balance, not active points.
                db.execute("UPDATE account SET expired=expired+? WHERE dataset=? AND year=?",(r["cost"],dataset,r["year"]))
            db.execute("UPDATE account SET used=used-? WHERE dataset=? AND year=?",(r["cost"],dataset,r["year"]))
            db.execute("UPDATE stock SET quantity=quantity+1 WHERE item=?",(r["item"],))
            db.execute("UPDATE uses SET status='reversed' WHERE redemption_id=?",(redemption_id,))
            self.event(db,dataset,"reversal",{"item":r["item"],"cost":r["cost"]})
        return {"duplicate":False,"account":self.account(dataset)}

    def close_year(self,dataset):
        self.ensure(dataset)
        year=self.registry.processed[dataset][0][-1]["date"][:4]
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT OR IGNORE INTO account(dataset,year) VALUES(?,?)",(dataset,year))
            a=db.execute("SELECT * FROM account WHERE dataset=? AND year=?",(dataset,year)).fetchone()
            available=max(0,a["granted"]-a["used"]-a["expired"])
            db.execute("UPDATE account SET expired=expired+? WHERE dataset=? AND year=?",(available,dataset,year))
            db.execute("INSERT OR REPLACE INTO policy_state VALUES(?,?,1)",(dataset,year))
            self.event(db,dataset,"year_closed",{"expired":available,"year":year})
        return self.account(dataset)

    def events(self,dataset):
        self.ensure(dataset)
        with self.db() as db:
            return [dict(r,payload=json.loads(r["payload"])) for r in db.execute("SELECT * FROM events WHERE dataset=? ORDER BY id DESC LIMIT 100",(dataset,))]

    def pipeline(self,scenario,grant=False):
        result = self.risk(scenario)
        result["incentive"] = self.incentive(result,grant)
        run_id = str(uuid.uuid4())
        result["run_id"] = run_id
        result["trace"] = [{"tool":name,"status":"success","transport":"核心函数调用"} for name in ["get_health_data","building_vulnerability","couple_risk","expected_losses","get_incentive_status"]]
        with self.db() as db:
            db.execute("INSERT INTO runs VALUES(?,?,?)",(run_id,result["scenario"]["dataset_id"],json.dumps(result,ensure_ascii=False)))
            self.event(db,result["scenario"]["dataset_id"],"pipeline_completed",{"run_id":run_id,"mode":result["scenario"]["mode"],"parameter_version":CONFIG["version"]})
        return result

    def report(self,result):
        b,p,l=result["building"],result["person"],result["losses"]
        def fmt(v):
            return "未估计" if v is None else f"{v:,.6f}"
        return "\n".join(["# 地震情景防灾报告",f"运行编号：{result['run_id']}",f"模式：{p['status']}；参数版本：{CONFIG['version']}",
            "## 情景与结果",f"PGA：{result['scenario']['pga']} g；建筑概率保持不变：{result['building_isolation_verified']}",
            f"名义受伤率：{fmt(p['nominal_casualty_rates']['injury'])}；名义死亡率：{fmt(p['nominal_casualty_rates']['death'])}",
            f"财产后果：{fmt(l['building_expected_loss'])} 元；人身后果：{fmt(l['human_expected_loss'])} 元；总后果：{fmt(l['total_expected_loss'])} 元", 
            "## 防灾准备", "提前固定可能坠落的家具，保持疏散通道畅通；准备应急照明与求救工具；熟悉当地应急部门发布的避险流程。", 
            "## 依据与限制",b['note'],p['note'],result['baseline_definition'],"活动与心率效应仅为模拟，不提供真实风险下降承诺。",*result['notices']])

    def evidence(self):
        return {"version":CONFIG["version"],"assumptions":CONFIG,
                "sources":[{"title":"GB/T 24335—2009 建（构）筑物地震破坏等级划分","url":"https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=FDE9BFF4C69F29CCD2ADAFE4F20E1CA1","use":"整栋损伤术语参考，非曲线参数来源"},
                           {"title":"GB/T 38591—2020 建筑抗震韧性评价标准","url":"https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=AFF19F2AC0C8196157D39E2F79DC32FF","use":"8.2.3表4楼层名义伤亡率参考；须有楼层判定依据"},
                           {"title":"Shapira et al., 2016","url":"https://doi.org/10.1371/journal.pone.0151111","use":"既有建筑与人口因素整合方法参考，未导入数值"},
                           {"title":"中国人群身体活动指南（2021）","url":"https://doi.org/10.3760/cma.j.cn112338-20211119-00903","use":"成人活动推荐量参考，不提供地震伤亡系数"}],
                "missing":["中国住宅易损曲线完整参数证据","整栋到楼层的工程转换依据","真实心率/活动/睡眠地震效应系数","保险后果金额与年度定价依据"],
                "innovation":"在既有框架上探索授权时序指标动态修正与防灾权益接口衔接；不宣称全概率公式原创。"}
