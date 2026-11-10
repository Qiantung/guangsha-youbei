# 前端、后端与SQLite数据库

浏览器 → 同源HTTP API → Python Service → SQLite。默认只监听127.0.0.1:8765；MCP stdio与HTTP共用Service。无需安装额外数据库服务。

## 开箱运行

`start.cmd` 创建Python3.13或3.12虚拟环境并安装依赖。Service首次启动自动创建 `private/demo.sqlite3`、数据表、三个虚拟对象各28天标准日记录与模拟物资库存。此前已有数据库的账户和流水保留；日数据由本地来源刷新。

交付目录 `database/demo-seed.sqlite3` 是独立、已初始化的合成演示数据种子库，没有真实健康CSV、兑换或发放记录；`database/schema.sql` 是表结构。启动不要求复制种子库，自动初始化产生相同基础数据。种子库用于查看表结构、调试与教学。

## 表

| 表 | 内容 |
|---|---|
| daily | 按对象与日期唯一的标准日指标和质量标记 |
| runs | 运行编号、对象、完整模拟结果 |
| events | 时间、对象、脱敏事件摘要 |
| account | 对象/年度的已发放、已使用、已过期和年度应享额度 |
| grants | 对象/年度/周期结束日期的差额发放记录 |
| uses | 全局唯一兑换编号、对象、物资、成本和兑换/冲正状态 |
| stock | 模拟物资库存 |
| policy_state | 模拟年度是否已结束 |

账户满足 `granted - used - expired = available`。发放按对象、年度与周期结束日期幂等；兑换与库存扣减在同一个 `BEGIN IMMEDIATE` 事务中完成；失败冲正只执行一次；年度关闭后不能新增发放或兑换。

## 自行初始化或导出表结构

在工程根目录执行：

```powershell
.\.venv\Scripts\python.exe -m backend.database --output private/demo.sqlite3 --schema database/schema.sql
```

此命令保留已有账户历史，不清空数据库。可通过环境变量 `QUAKE_DB` 指定其他本地SQLite路径。正常演示无需配置。

## 从旧版升级

先退出旧服务，在新目录解压运行。若要继承旧模拟账户，停止新服务后，将旧目录的 `private/demo.sqlite3` 复制到新目录对应位置，再启动。请自行保留一份备份；不要同时对同一文件运行两个不同版本。真实CSV和local.config.json不在交付包中。
