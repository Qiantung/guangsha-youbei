# 验证记录

2026-11-10，Windows，Python 3.12.14。

- 本地核心与HTTP接口测试：34 passed，真实MCP测试单独运行。
- 真实MCP stdio三场景测试：1 passed。合计35项通过。
- 前端启动及API处理测试：Node test runner，9 passed。
- 修正测试脚本读取中文配置时未指定UTF-8的问题，未改变模型和模拟参数。
- FastAPI/Starlette输出一条httpx兼容性弃用警告，当前测试仍通过。
- 本次未进行完整网页视觉回归、真实设备接入或真实震害外部验证。

测试环境主要依赖：fastapi 0.143.0，pydantic 2.13.5，httpx 0.28.1，mcp 1.30.0，pytest 9.1.1。使用临时数据库和合成数据。
