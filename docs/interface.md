# 演示接口 v2

## 公共场景

dataset_id默认demo_01；mode为simulation/reference；structure_type为brick/frame/shear_wall；fortification_intensity整数6—9；pga为0—3 g；building_area为正平方米；floor_count为1—100整数；age为0—120岁；sleeping布尔；reference_floor_grade为1—5。

本版本人为模拟的曲线仅按结构、设防倍率、PGA计算；楼层数记录但不参与该曲线。无Sa入口，无震级转PGA入口。不是国内住宅模型校准。

## HTTP API

| 接口 | 功能 |
|---|---|
| GET /api/status、/api/datasets | 服务状态与已注册对象 |
| GET /api/data/{dataset}?start=&end= | 本地持久化标准日记录、质量与周统计 |
| GET/POST /api/rules/{dataset} | 达标查询 / 手动触发并记录事件 |
| GET /api/events/{dataset} | 脱敏事件 |
| POST /api/run | 输入{scenario,grant:false}，输出完整链路；grant=true显式发放 |
| GET /api/account/{dataset} | 年度账户、目录、流水 |
| POST /api/redeem | {dataset_id,item_id,redemption_id}，点数与库存同事务 |
| POST /api/reverse | {dataset_id,redemption_id}，仅可冲正一次 |
| POST /api/close-year/{dataset} | 结束当前模拟年度，余额过期；关闭后禁止新增发放和兑换 |
| POST /api/chat | {message,scenario,session_id,transport:core/mcp} |
| POST /api/report | 输入{scenario}，输出Markdown |
| GET /api/export/{dataset} | 标准数据JSON |
| GET /api/evidence、/api/verification | 依据、假设与实际验证记录 |

错误：HTTP422 INVALID_PARAMETERS；HTTP400 UNKNOWN_DATASET、INVALID_DATE_RANGE、INSUFFICIENT_BALANCE、OUT_OF_STOCK、ID_CONFLICT、NOT_FOUND、INSUFFICIENT_DATA；HTTP500 OPERATION_FAILED。响应不回显技术堆栈或文件路径。

## MCP工具

get_health_data(dataset_id,time_range)、building_vulnerability(scenario)、couple_risk(scenario)、expected_losses(scenario)、get_incentive_status(dataset_id)、calculate_premium_discount(scenario)、get_available_benefits(dataset_id)、run_pipeline(scenario)、generate_disaster_report(scenario)。所有工具共用Service；MCP只预览不发放，兑换通过明确的网页操作。

账户展示扩展：`balance.cap_amount`、物资的 `can_redeem` 和 `available_after` 由Python返回。前端只显示核算值；余额不足、缺货或年度已关闭时，`can_redeem=false`，余额预览为null。兑换提交时仍重新核验，预览不等于余额预留。

## 版本变化与参考文件关系

1. 未沿用旧Excel的none/minor/serious/death四态。返回nominal_casualty_rates.injury/death两个独立名义终点。
2. 整栋DS与楼层I—V分别保存。floor_transition为模拟假设，不称国标映射。
3. 用odds_modifiers表达OR，模拟系数为health_log_or，不称RR；不使用旧0.75—3和低中高医学式等级。
4. 激励采用B新版年度人身责任基数、k=0.6、cap=0.1、四周触发。三者是原型业务规则。
5. 物资兑换预算同池；保费仅预览，未实际抵扣；未实现保额提升。
6. 不执行全家联合风险。睡眠双情景始终返回，页面震时状态只选择当前情景。

## 账户一致性

granted-used-expired=available，granted≤200×10%。同一对象/年度/四周结束日期为发放幂等键，兑换编号全局唯一。SQLite BEGIN IMMEDIATE序列化余额与库存更新。模拟年份来自展示数据末日，不从运行日推断保单年度。当前28天样本只有一期，跨期差额逻辑已实现但尚未由页面生成全年时序。

## 可穿戴摘要

静息心率使用观测中位数；活动使用完整观测周均值；插值不用于达标。time_range=30d在只有28天时返回28天并明确window_days。sleep_pattern的起止时刻没有来源，返回null，不由时长反推。实际健康输入仅保存在本地必要数据表，不放到日志。
