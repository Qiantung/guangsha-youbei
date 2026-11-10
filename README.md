# 广厦有备 · Guangsha Youbei

An InsurTech research prototype connecting wearable-data quality, earthquake-risk scenarios, and auditable risk-reduction incentives.

保险科技学生团队项目。探索如何把多源数据接入、风险计算、激励核算和工具交互连成可解释的本地演示流程。

## 运行演示

Python 3.12 或 3.13。在仓库根目录执行：

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m backend.database
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8765
```

访问 http://127.0.0.1:8765 。已保留构建后的网页，正常演示不需要安装 Node.js。数据库从合成对象自动初始化；真实健康数据不随仓库分发。

## 实现与结构

| 部分 | 内容 |
| --- | --- |
| `backend/` | FastAPI 接口、Python计算、工具调用与报告 |
| `vendor/wearable/` | 已集成的数据接入、清洗与质量处理模块 |
| `config/demo.json` | 明确标记的演示参数 |
| `frontend/src/` | React 页面源码 |
| `frontend/dist/` | 可本地托管的构建产物 |
| `database/` | 数据库结构；运行时流水保存在忽略的 `private/` |
| `tests/` | 核算、幂等、模式边界及接口测试 |
| `docs/` | 接口、数据库、表现层资源说明 |

建议演示顺序：选择对象 → 查看数据质量 → 调整建筑与人员情景 → 查看后果与权益 → 重复核算观察幂等行为 → 查询助手工具返回。

## 模型边界

- `simulation` 使用人工设定的参数与合成对象，用于检查计算和交互流程。
- `reference` 中缺少证据的建筑概率、后果金额等返回空值及原因；不将缺失参数补成事实。
- 可穿戴指标与地震后果的关系仍是探索性假设；模拟拟合不能证明真实运动减量效果。
- 当前是一体化单人演示，独立多人耦合研究包尚未据此认定已集成。
- 本原型不是已校准的工程风险模型、医学评价或实际保险定价系统。

## 验证

```bash
python -m pytest -q
```

本次整理的实际验证范围与环境见 [验证记录](docs/VALIDATION.md)。历史交付记录不作为本次运行通过的证据。

## 个人贡献与协作

本人提出项目想法，并承担主要非论文技术工作：原型设计、模块开发与集成、数据处理、交互及验证。论文写作属于团队协作部分。开发过程中使用 AI 辅助；本人负责需求、技术取舍、集成检查与结果解释。

## 后续工作

补全建筑参数原文证据；开展独立真实样本验证；统一独立研究模块与平台接口；完善可复现演示和失败案例。

字体许可保留在随包的许可证目录；插画来源见 [资源说明](docs/art-assets.md)。项目整体代码许可证尚未指定，第三方资源按各自许可使用。
