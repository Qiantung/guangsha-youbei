import json
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .agent import Agent
from .models import ChatRequest, Redemption, Reversal, RunRequest, Scenario
from .service import DomainError, ROOT, Service


def create_app(service=None):
    service = service or Service()
    agent = Agent(service)
    app = FastAPI(title="广厦有备本地演示接口",version="2.0.0")

    @app.exception_handler(DomainError)
    async def domain_error(request, exc):
        return JSONResponse(status_code=400,content={"error":{"code":exc.code,"message":exc.message}})

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        fields = [".".join(str(x) for x in e["loc"][1:]) for e in exc.errors()]
        return JSONResponse(status_code=422,content={"error":{"code":"INVALID_PARAMETERS","message":"参数缺失或超出有效范围，请检查："+"、".join(fields)}})

    @app.exception_handler(Exception)
    async def unexpected_error(request, exc):
        # No raw health data, chat content, paths or stack traces in app logs.
        logging.getLogger("quake").error("operation_failed type=%s",type(exc).__name__)
        return JSONResponse(status_code=500,content={"error":{"code":"OPERATION_FAILED","message":"本次操作未完成，请检查服务状态或稍后重试。"}})

    @app.get("/api/status")
    def status():
        return {"ok":True,"backend":"Python","storage":"SQLite","local_only":True}

    @app.get("/api/datasets")
    def datasets():
        return service.datasets()

    @app.get("/api/data/{dataset}")
    def data(dataset: str, start: str | None=None, end: str | None=None):
        return service.data(dataset,start,end)

    @app.get("/api/events/{dataset}")
    def events(dataset: str):
        return service.events(dataset)

    @app.get("/api/rules/{dataset}")
    def rules(dataset: str):
        return service.rules(dataset)

    @app.post("/api/rules/{dataset}")
    def trigger(dataset: str):
        return service.trigger_rules(dataset)

    @app.post("/api/run")
    def run(req: RunRequest):
        return service.pipeline(req.scenario.model_dump(),req.grant)

    @app.get("/api/account/{dataset}")
    def account(dataset: str):
        return service.account(dataset)

    @app.post("/api/close-year/{dataset}")
    def close_year(dataset: str):
        return service.close_year(dataset)

    @app.post("/api/redeem")
    def redeem(req: Redemption):
        return service.redeem(req.dataset_id,req.item_id,req.redemption_id)

    @app.post("/api/reverse")
    def reverse(req: Reversal):
        return service.reverse(req.dataset_id,req.redemption_id)

    @app.post("/api/chat")
    async def chat(req: ChatRequest):
        return await agent.answer(req.message,req.scenario.model_dump(),req.session_id,req.transport)

    @app.post("/api/report")
    def report(req: RunRequest):
        result = service.pipeline(req.scenario.model_dump(),False)
        return Response(service.report(result),media_type="text/markdown",headers={"Content-Disposition":"attachment; filename=earthquake-report.md"})

    @app.get("/api/export/{dataset}")
    def export(dataset: str):
        # Minimal clean fields + quality, no original vendor identity columns.
        return Response(json.dumps(service.data(dataset),ensure_ascii=False,indent=2),media_type="application/json",headers={"Content-Disposition":"attachment; filename=wearable-demo.json"})

    @app.get("/api/evidence")
    def evidence():
        return service.evidence()

    @app.get("/api/verification")
    def verification():
        path = ROOT / "verification/results.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"status":"未运行验证"}

    dist = ROOT / "frontend/dist"
    if dist.exists():
        app.mount("/",StaticFiles(directory=dist,html=True),name="frontend")
    return app


app = create_app()
