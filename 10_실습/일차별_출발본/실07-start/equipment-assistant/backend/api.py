"""HTTP boundaries, request identifiers and role-specific approval authorization."""
import os
import secrets
from typing import Literal
from uuid import uuid4
import psycopg
from fastapi import Depends, FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException as StarletteHTTPException
from backend.common.config import ROOT, env, settings
from backend.common.gateway import database
from backend.common.log import emit, request_id, trace
from backend.common.response import reply
from backend.data import service as data
from backend.detect import gateway as detect_gateway
from backend.detect import service as detect
from backend.ontology import gateway as ontology_gateway
from backend.ontology import service as ontology
from backend.rag import service as rag
app = FastAPI(title='설비 이상 대응 어시스턴트', version='0.1.0')
app.add_middleware(CORSMiddleware, allow_origins=[settings()['service']['frontend']], allow_methods=['GET', 'POST'], allow_headers=['Authorization', 'Content-Type', 'X-Request-ID', 'X-Approver-Token'])

def authorize(authorization: str=Header(default='')):
    expected = env('SERVICE_TOKEN')
    if not secrets.compare_digest(authorization, 'Bearer ' + expected):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail='서비스 접속 토큰을 확인하세요')

@app.middleware('http')
async def request_context(request: Request, call_next):
    supplied = request.headers.get('X-Request-ID', '')
    rid = supplied if supplied and len(supplied) <= 80 and all((c.isalnum() or c in '-_' for c in supplied)) else str(uuid4())
    token = request_id.set(rid)
    try:
        response = await call_next(request)
        response.headers['X-Request-ID'] = rid
        return response
    finally:
        request_id.reset(token)

@app.exception_handler(ValueError)
async def invalid(request, exc):
    return JSONResponse(status_code=400, content=reply(request_id.get(), status='error', reason=str(exc)).model_dump())

@app.exception_handler(StarletteHTTPException)
async def http_error(request, exc):
    return JSONResponse(status_code=exc.status_code, content=reply(request_id.get(), status='error', reason=str(exc.detail)).model_dump())

@app.exception_handler(RequestValidationError)
async def invalid_request(request, exc):
    fields = ['.'.join((str(value) for value in error['loc'])) for error in exc.errors()]
    return JSONResponse(status_code=422, content=reply(request_id.get(), status='error', reason='요청 항목을 확인하세요: ' + ', '.join(fields)).model_dump())

@app.exception_handler(Exception)
async def failed(request, exc):
    emit('ui', 'ui.request', 'backend/api.py:failed', status='failed', reason=type(exc).__name__)
    return JSONResponse(status_code=500, content=reply(request_id.get(), status='failed', reason=f'요청 실행 실패({type(exc).__name__}). 요청 번호로 관측 기록을 확인하세요').model_dump())

class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

class Source(Input):
    profile: str
    source_id: str

class Query(Input):
    profile: str
    source_ids: list[str]
    question: str = Field(min_length=1, max_length=4000)
    provider: Literal['api', 'internal']
    context: dict | None = None
    verify: bool = True
    context_level: Literal['names', 'dictionary', 'probed'] = 'probed'

class Series(Source):
    column_id: int
    lot_id: str | None = None

class Profile(Input):
    profile: str

class GraphPath(Input):
    start: str
    end: str

class RuleRequest(Source):
    rule_id: str

class EventRequest(Source):
    lot_id: str | None = None

class RagQuestion(Profile):
    question: str = Field(min_length=1, max_length=4000)
    provider: Literal['api', 'internal'] = 'api'
    context: dict | None = None

class ModelJob(Source):
    method: Literal['forecast', 'pyod']
    parameters: dict

class Report(Source):
    lot_id: str | None = None
    provider: Literal['api', 'internal'] | None = None

class Meaning(Source):
    provider: Literal['api', 'internal']
    graph_end: str = Field(min_length=1, max_length=200)
    autonomy: Literal[0, 1, 2] = 1
    column_ids: list[int]
    excerpt: str = Field(min_length=1, max_length=12000)

@app.get('/health')
def health():
    checks = {'server': 'ok', 'database': 'unconfigured', 'model_calls_enabled': os.getenv('ALLOW_MODEL_CALLS', 'false').lower() == 'true'}
    if os.getenv('DATABASE_URL'):
        try:
            with database(readonly=True) as db:
                db.execute('SELECT 1').fetchone()
            checks['database'] = 'ok'
        except (psycopg.Error, ValueError, OSError) as exc:
            checks['database'] = 'failed:' + type(exc).__name__
    return reply(request_id.get(), {'checks': checks, 'day': settings()['service']['day'], 'routes': [route.path for route in app.routes if route.path.startswith('/api/')], 'readiness': '서버 상태와 DB 연결만 확인. 모델·실습 완주 확인 아님'})

@app.get('/trace/{rid}', dependencies=[Depends(authorize)])
def request_trace(rid: str):
    rows = trace(rid)
    return reply(request_id.get(), rows, status='ok' if rows else 'none', reason='' if rows else '요청 기록 없음')

@app.get('/api/data/catalog', dependencies=[Depends(authorize)])
def catalog(profile: str):
    return reply(request_id.get(), data.catalog(profile))

@app.post('/api/data/upload', dependencies=[Depends(authorize)])
def upload(body: Source):
    return data.upload(request_id.get(), **body.model_dump())

@app.post('/api/data/query', dependencies=[Depends(authorize)])
def query(body: Query):
    values = body.model_dump()
    values['text'] = values.pop('question')
    return data.question(request_id.get(), **values)

@app.post('/api/data/series', dependencies=[Depends(authorize)])
def series(body: Series):
    return data.series(request_id.get(), **body.model_dump())

@app.post('/api/data/quality', dependencies=[Depends(authorize)])
def quality(body: Source):
    return data.quality(request_id.get(), **body.model_dump())

@app.post('/api/data/clean', dependencies=[Depends(authorize)])
def clean(body: Source):
    from backend.data.quality import create_view
    return create_view(request_id.get(), **body.model_dump())

@app.post('/api/data/clean/preview', dependencies=[Depends(authorize)])
def clean_preview(body: Source):
    from backend.data.quality import preview
    return preview(request_id.get(), **body.model_dump())

@app.post('/api/data/duplicates', dependencies=[Depends(authorize)])
def duplicate_columns(body: Source):
    from backend.data.quality import duplicates
    return duplicates(request_id.get(), **body.model_dump())

@app.post('/api/data/meaning', dependencies=[Depends(authorize)])
def draft_meaning(body: Meaning):
    from backend.data.quality import meaning_draft
    return meaning_draft(request_id.get(), **body.model_dump())

@app.post('/api/ontology/load', dependencies=[Depends(authorize)])
def load_ontology(body: Profile):
    return ontology.load(request_id.get(), body.profile)

@app.post('/api/ontology/path', dependencies=[Depends(authorize)])
def graph_path(body: GraphPath):
    return ontology.path(request_id.get(), body.start, body.end)

@app.post('/api/ontology/sync', dependencies=[Depends(authorize)])
def sync_ontology():
    return reply(request_id.get(), ontology_gateway.flush_outbox())

@app.post('/api/detect/rules', dependencies=[Depends(authorize)])
def run_rules(body: RuleRequest):
    return detect.run_rules(request_id.get(), **body.model_dump())

@app.post('/api/detect/events', dependencies=[Depends(authorize)])
def events(body: EventRequest):
    return detect.list_events(request_id.get(), **body.model_dump())

@app.get('/api/detect/rules', dependencies=[Depends(authorize)])
def get_rule(rule_id: str):
    result = detect_gateway.rule(rule_id)
    return reply(request_id.get(), result, status='ok' if result else 'none', reason='' if result else '규칙 없음')

@app.post('/api/detect/models', dependencies=[Depends(authorize)])
def model_job(body: ModelJob):
    from backend.detect.model_gateway import job
    return reply(request_id.get(), job(**body.model_dump()))

@app.post('/api/report', dependencies=[Depends(authorize)])
def report(body: Report):
    from backend.report.service import create
    return create(request_id.get(), **body.model_dump())

@app.get('/api/detect/models', dependencies=[Depends(authorize)])
def model_history():
    with database(readonly=True) as db:
        rows = db.execute("SELECT id,payload FROM lab.artifacts WHERE kind='model' ORDER BY created_at DESC LIMIT 100").fetchall()
    return reply(request_id.get(), rows, status='ok' if rows else 'none', reason='' if rows else '분석 기록 없음')

@app.get('/api/rag/docs', dependencies=[Depends(authorize)])
def get_documents(profile: str):
    return reply(request_id.get(), rag.documents(profile))

@app.post('/api/rag/docs', dependencies=[Depends(authorize)])
def index_documents(body: Profile):
    return rag.index(request_id.get(), body.profile)

@app.post('/api/rag/search', dependencies=[Depends(authorize)])
def search_documents(body: RagQuestion):
    return rag.search(request_id.get(), body.profile, body.question)

@app.post('/api/rag/ask', dependencies=[Depends(authorize)])
def ask_documents(body: RagQuestion):
    return rag.ask(request_id.get(), **body.model_dump())
if (ROOT / 'frontend/dist').is_dir():
    from fastapi.staticfiles import StaticFiles
    app.mount('/', StaticFiles(directory=ROOT / 'frontend/dist', html=True), name='frontend')
