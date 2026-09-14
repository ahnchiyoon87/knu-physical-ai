"""Produce actual previous-stage source trees, never full code behind hidden menus."""
import ast
import csv
import io
import hashlib
import json
import re
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

import yaml

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'10_실습/완성본/equipment-assistant'
OUT=ROOT/'10_실습/일차별_출발본'
MANIFEST=ROOT/'30_기록/출발본_매니페스트.json'
ROUTES={
 'catalog':'data','upload':'data','query':'data','load_ontology':'data','graph_path':'data',
 'quality':'quality','series':'visual','report':'visual',
 'clean':'quality','clean_preview':'quality','duplicate_columns':'quality','draft_meaning':'quality',
 'run_rules':'rules','events':'rules','get_rule':'rules','sync_ontology':'rag',
 'model_job':'models','model_history':'models','get_documents':'rag','index_documents':'rag','search_documents':'rag','ask_documents':'rag',
 'vision_image':'vision',
 'agent_draft':'agent','agent_eight_d':'agent',
 'evaluate':'eval','route_question':'eval','approvals':'agent','propose_action':'agent','decide_action':'agent','record_action':'agent','run_agent':'agent','resume_agent':'agent'}
PANELS=[('표와 질문','DataPanel','data'),('품질','QualityPanel','quality'),('관계','GraphPanel','data'),('감지','DetectPanel','rules'),
        ('분석','ModelPanel','models'),('리포트','ReportPanel','visual'),('문서 근거','RagPanel','rag'),('평가','EvalPanel','eval'),
        ('에이전트','AgentPanel','agent'),('사람 승인','ApprovalPanel','agent')]


def put(folder,name,text):
    path=folder/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8')


def source(name):return (APP/name).read_text(encoding='utf-8')


def filtered(text,names=None,transform=None,prune_classes=False):
    tree=ast.parse(text)
    if names is not None:
        tree.body=[n for n in tree.body if not isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) or n.name in names]
    if transform:tree=transform(tree)
    if prune_classes:
        classes={n.name:n for n in tree.body if isinstance(n,ast.ClassDef)}
        used={n.id for item in tree.body if not isinstance(item,ast.ClassDef) for n in ast.walk(item) if isinstance(n,ast.Name)}
        while True:
            expanded=used|{n.id for key,value in classes.items() if key in used for n in ast.walk(value) if isinstance(n,ast.Name)}
            if expanded==used:break
            used=expanded
        tree.body=[n for n in tree.body if not isinstance(n,ast.ClassDef) or n.name in used]
    used={n.id for n in ast.walk(tree) if isinstance(n,ast.Name)}
    for item in tree.body:
        if isinstance(item,ast.Import):item.names=[n for n in item.names if (n.asname or n.name.split('.')[0]) in used]
        elif isinstance(item,ast.ImportFrom):item.names=[n for n in item.names if (n.asname or n.name) in used]
    tree.body=[n for n in tree.body if not isinstance(n,(ast.Import,ast.ImportFrom)) or n.names]
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)+'\n'


def stages():
    data={'data'};quality=data|{'quality'};visual=quality|{'visual','judge'};rules=visual|{'rules'}
    pipeline=rules|{'pipeline','models','pyod','forecast'};rag=pipeline|{'rag'};evaluation=rag|{'eval'};agent=evaluation|{'agent'}
    practical=[set(),data,quality,visual,rules,pipeline,rag,evaluation,agent]
    table=visual|{'models','table'};vision=table|{'vision'};timeseries=vision|pipeline;rul=timeseries|{'rul'};integrated=rul|{'integration'}
    combined=[set(),visual,table,vision|{'rules'},timeseries,rul,integrated,integrated|{'rag'},integrated|{'rag','eval'},integrated|{'rag','eval','deploy'}]
    return [('실',i+1,x) for i,x in enumerate(practical)]+[('통',i+1,x) for i,x in enumerate(combined)]


def copy_assets(folder,features):
    common=['constitution.md','AGENTS.md','.gitignore','.env.example','config.yaml']
    for name in common:put(folder,name,source(name))
    for sub in (APP/'.agent').rglob('*'):
        if sub.is_file():put(folder,str(sub.relative_to(APP)),sub.read_text(encoding='utf-8'))
    config=yaml.safe_load(source('config.yaml'));config['service']['day']=folder.name
    put(folder,'config.yaml',yaml.safe_dump(config,allow_unicode=True,sort_keys=False))
    mapping=json.loads(source('mapping.json'))
    # Future raw data and finished domain-transfer answers are not distributed early.
    if 'transfer' not in features:mapping['profiles'].pop('transfer',None)
    for key,value in mapping['profiles'].items():
        if 'rag' not in features:value.pop('documents',None)
        if 'quality' not in features:value['sources'].pop('labeled',None)
    if 'vision' not in features:mapping.pop('vision',None)
    if 'rul' not in features:mapping.pop('rul',None)
    put(folder,'mapping.json',json.dumps(mapping,ensure_ascii=False,indent=2))
    for sub in (APP/'data/generated').glob('*.csv'):
        if sub.name=='labeled.csv' and 'quality' not in features:continue
        (folder/'data/generated').mkdir(parents=True,exist_ok=True);shutil.copy2(sub,folder/'data/generated'/sub.name)
    for sub in (APP/'ontology').glob('*.csv'):
        if sub.stem!='transfer' or 'transfer' in features:
            text=sub.read_text(encoding='utf-8-sig')
            if 'rag' not in features:
                reader=csv.DictReader(io.StringIO(text));fields=reader.fieldnames
                rows=[r for r in reader if r['source_type']!='document' and r['target_type']!='document']
                stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows);text=stream.getvalue()
            put(folder,'ontology/'+sub.name,text)
    if 'transfer' in features:
        for sub in (APP/'data/transfer').rglob('*'):
            if sub.is_file():
                target=folder/sub.relative_to(APP);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(sub,target)
    if 'rag' in features:
        for sub in (APP/'data/documents').glob('*.md'):put(folder,'data/documents/'+sub.name,sub.read_text(encoding='utf-8'))
    # Structure only in the first day. Empty placeholders contain no app implementation.
    for directory in ('backend/data','backend/ontology','backend/detect','backend/rag','backend/eval','backend/process','backend/agent','backend/common','frontend','scripts','specs','mcp_server'):
        (folder/directory).mkdir(parents=True,exist_ok=True)
        if not features:put(folder,directory+'/.gitkeep','')


def app_files(folder,features):
    names={'authorize','invalid','http_error','invalid_request','failed','request_context','health','request_trace'}
    names|={name for name,feature in ROUTES.items() if feature in features}
    if 'agent' in features:names.add('approve_role')
    def api_transform(tree):
        allowed=sorted(features&{'table','pyod','forecast','rul','vision'})
        if 'rul' in features:allowed.append('threshold')
        for node in tree.body:
            if isinstance(node,ast.ClassDef) and node.name=='ModelJob' and allowed:
                for field in node.body:
                    if isinstance(field,ast.AnnAssign) and isinstance(field.target,ast.Name) and field.target.id=='method':
                        field.annotation=ast.parse('Literal['+','.join(repr(x) for x in allowed)+']',mode='eval').body
        if 'judge' not in features:
            for n in ast.walk(tree):
                if isinstance(n,ast.AnnAssign) and isinstance(n.target,ast.Name) and n.target.id=='verify':n.value=ast.Constant(False)
        return tree
    put(folder,'backend/api.py',filtered(source('backend/api.py'),names,api_transform,True))
    for name in ['backend/__init__.py','backend/data/__init__.py','backend/ontology/__init__.py','backend/common/__init__.py',
                 'backend/common/config.py','backend/common/gateway.py','backend/common/log.py','backend/common/response.py','backend/common/service.py','backend/data/sql_guard.py']:
        if (APP/name).exists():put(folder,name,source(name))
    data_names={'catalog','upload','question'}|({'quality'} if 'quality' in features else set())|({'series'} if 'visual' in features else set())|({'validated_judgement'} if 'judge' in features else set())
    def data_transform(tree):
        if 'judge' not in features:
            question=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='question')
            question.body=[n for n in question.body if not (isinstance(n,ast.If) and 'verify and result' in ast.unparse(n.test))]
            question.body.insert(1,ast.Assign(targets=[ast.Name(id='verify',ctx=ast.Store())],value=ast.Constant(False)))
        return tree
    put(folder,'backend/data/service.py',filtered(source('backend/data/service.py'),data_names,data_transform))
    put(folder,'backend/data/gateway.py',filtered(source('backend/data/gateway.py'),{'import_csv','query_rows','sql_from_question','probe_sources'}|({'judge_query','repair_query'} if 'judge' in features else set())))
    if 'quality' in features:put(folder,'backend/data/quality.py',source('backend/data/quality.py'))
    put(folder,'backend/ontology/service.py',source('backend/ontology/service.py'))
    put(folder,'backend/ontology/gateway.py',source('backend/ontology/gateway.py' if 'rag' in features else 'backend/ontology/local.py'))
    for feature,directory in [('rag','rag'),('eval','eval'),('agent','process')]:
        if feature in features:
            for path in (APP/'backend'/directory).glob('*.py'):put(folder,str(path.relative_to(APP)),path.read_text(encoding='utf-8'))
    if 'visual' in features:
        text=source('backend/report/service.py')
        if 'rules' not in features:
            tree=ast.parse(text)
            for node in ast.walk(tree):
                if isinstance(node,ast.With):
                    node.body=[ast.Assign(targets=[ast.Name(id='events',ctx=ast.Store())],value=ast.List(elts=[],ctx=ast.Load())) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='events' for t in n.targets) else n for n in node.body]
            ast.fix_missing_locations(tree);text=ast.unparse(tree)+'\n'
        put(folder,'backend/report/service.py',text);put(folder,'backend/report/__init__.py','')
    if 'rules' in features or 'models' in features:
        for name in ('__init__.py','gateway.py'):
            if (APP/'backend/detect'/name).exists():put(folder,'backend/detect/'+name,source('backend/detect/'+name))
        helpers=({'detect_rows','detect_multichannel'} if 'rules' in features else set())|({'classification_counts'} if 'table' in features else set())|({'first_threshold_crossing'} if 'rul' in features else set())
        put(folder,'backend/detect/rules.py',filtered(source('backend/detect/rules.py'),helpers))
    if 'rules' in features:
        put(folder,'backend/detect/service.py',source('backend/detect/service.py'));put(folder,'rules.json',source('rules.json'));put(folder,'scripts/seed_rules.py',source('scripts/seed_rules.py'))
    if 'models' in features:
        method_functions={'table':'table_classifier','pyod':'pyod_scores','forecast':'chronos_forecast','rul':'cmapss_regression'}
        selected={value for key,value in method_functions.items() if key in features}
        if 'forecast' in features:selected.add('forecast_evaluation')
        if 'rul' in features:selected|={'threshold_forecast','chronos_forecast'}
        put(folder,'backend/detect/models.py',filtered(source('backend/detect/models.py'),selected))
        allowed=features&{'table','pyod','forecast','rul','vision'}
        if 'rul' in features:allowed|={'threshold'}
        # The dispatcher is explicitly rebuilt from present methods. Unsupported branch source is absent.
        text=source('backend/detect/model_gateway.py')
        tree=ast.parse(text)
        class Methods(ast.NodeTransformer):
            def visit_If(self,node):
                test=ast.unparse(node.test)
                if test.startswith('method == '):
                    value=ast.literal_eval(node.test.comparators[0])
                    if value not in allowed:return [self.visit(n) for n in node.orelse]
                elif test.startswith('method in '):
                    values=ast.literal_eval(node.test.comparators[0])&allowed
                    if not values:return [self.visit(n) for n in node.orelse]
                    node.test.comparators[0]=ast.Set(elts=[ast.Constant(x) for x in sorted(values)])
                return self.generic_visit(node)
        tree=Methods().visit(tree);ast.fix_missing_locations(tree)
        put(folder,'backend/detect/model_gateway.py',ast.unparse(tree)+'\n')
        if 'vision' in features:
            put(folder,'backend/detect/vision_gateway.py',source('backend/detect/vision_gateway.py'))
            for name in ('prepare_thermal.py','prepare_vision_weights.py'):put(folder,'scripts/'+name,source('scripts/'+name))
        put(folder,'scripts/model_job.py',source('scripts/model_job.py'))
    if 'pipeline' in features:
        put(folder,'backend/agent/__init__.py','');put(folder,'backend/agent/pipeline.py',source('backend/agent/pipeline.py'));put(folder,'scripts/reload.py',source('scripts/reload.py'))
    if 'eval' in features:
        put(folder,'backend/agent/__init__.py','')
        put(folder,'backend/agent/service.py',filtered(source('backend/agent/service.py'),None if 'agent' in features else {'route_question'},prune_classes=True))
        put(folder,'backend/agent/gateway.py',filtered(source('backend/agent/gateway.py'),None if 'agent' in features else {'route'}))
        put(folder,'scripts/eval.py',source('scripts/eval.py'))
    if 'agent' in features:
        put(folder,'backend/agent/drafts.py',source('backend/agent/drafts.py'))
        for path in (APP/'mcp_server').glob('*.py'):put(folder,str(path.relative_to(APP)),path.read_text(encoding='utf-8'))
    if 'rag' in features:put(folder,'scripts/cache_models.py',source('scripts/cache_models.py'))
    bootstrap=source('scripts/bootstrap.py')
    if 'agent' not in features:
        bootstrap=bootstrap.replace('    asyncio.run(checkpoint_schema())\n','')
        bootstrap=filtered(bootstrap,{'main'})
    put(folder,'scripts/bootstrap.py',bootstrap)
    put(folder,'scripts/data_check.py',source('scripts/data_check.py'))
    serve=source('scripts/serve.py')
    if 'agent' not in features:serve=serve.replace(",\n           [sys.executable,'-m','mcp_server.server']",'')
    put(folder,'scripts/serve.py',serve)
    if 'rag' in features:put(folder,'compose.yaml',source('compose.yaml'))
    for name in ('pyproject.toml','uv.lock'):put(folder,name,source(name))
    # Only schema objects used by the current implementation are present.
    tables={'imports','records'}
    if features&{'visual','models','rules'}:tables|={'artifacts','graph_outbox'}
    if 'rules' in features:tables|={'rules','events'}
    if 'rag' in features:tables|={'documents','chunks'}
    if 'eval' in features:tables|={'evaluations'}
    if 'agent' in features:tables|={'proposals','decisions'}
    statements=[]
    for statement in source('supabase/migrations/202609140001_service.sql').split(';'):
        refs=set(re.findall(r'\blab\.([a-z_]+)',statement))
        if not refs or refs<=tables:statements.append(statement.strip())
    put(folder,'supabase/migrations/202609140001_service.sql',';\n'.join(statements)+';\n')
    frontend(folder,features)
    if 'deploy' in features:
        for name in ('Dockerfile','.dockerignore','deploy.sh','deploy.ps1','배포.md'):put(folder,name,source(name))
        # These assets do not exist before the final transfer day.
        docker=(folder/'Dockerfile').read_text(encoding='utf-8')
        if 'agent' not in features:docker=docker.replace('COPY mcp_server/ mcp_server/\n','')
        if 'transfer' not in features:docker=docker.replace('COPY data/transfer/ data/transfer/\n','')
        put(folder,'Dockerfile',docker)


def frontend(folder,features):
    for name in ('package.json','package-lock.json','index.html','vite.config.js','src/main.js','src/api.js','src/Result.vue','src/style.css'):
        put(folder,'frontend/'+name,source('frontend/'+name))
    if features&{'forecast','rul'}:put(folder,'frontend/src/ForecastResult.vue',source('frontend/src/ForecastResult.vue'))
    else:
        text=(folder/'frontend/src/Result.vue').read_text(encoding='utf-8').replace("import ForecastResult from './ForecastResult.vue'\n",'')
        text=re.sub(r'    <ForecastResult.*?/>\n','',text)
        put(folder,'frontend/src/Result.vue',text)
    if 'vision' in features:put(folder,'frontend/src/VisionResult.vue',source('frontend/src/VisionResult.vue'))
    else:
        text=(folder/'frontend/src/Result.vue').read_text(encoding='utf-8').replace("import VisionResult from './VisionResult.vue'\n",'')
        text=re.sub(r'    <VisionResult.*?/>\n','',text)
        put(folder,'frontend/src/Result.vue',text)
    for label,panel,feature in PANELS:
        if feature not in features:continue
        text=source('frontend/src/'+panel+'.vue')
        if panel=='DataPanel':
            if 'visual' not in features:
                text=re.sub(r' <fieldset><legend>순서에 따른 변화</legend>.*?</fieldset>','',text,flags=re.S)
                text=re.sub(r'async function plot\(\).*?\nconst plotData=computed\(\(\)=>\{.*?\n\}\)\n','',text,flags=re.S)
            if 'judge' not in features:
                text=text.replace('verify=ref(true)','verify=ref(false)')
                text=text.replace('<label class="check"><input type="checkbox" v-model="verify"/>항목별 모델 심사와 한 번의 수리</label>','')
        if panel=='GraphPanel' and 'rag' not in features:
            text=re.sub(r'<button[^>]*@click="request\(\'/api/ontology/sync\'.*?</button>','',text,flags=re.S)
        if panel=='ModelPanel':
            examples={
                'table':{'feature_ids':[302,303],'split':'ordered','train_fraction':.7},
                'pyod':{'column_id':22,'lot_id':'4','baseline_count':200},
                'forecast':{'column_id':22,'lot_id':'4','horizon':20,'evaluate_last':True},
                'rul':{'subset':'FD001','sensor_indices':[6,7,8,10,11,12,13,14]},
                'threshold':{'column_id':22,'lot_id':'5','threshold':10.5,'direction':'above'},
                'vision':{'side':'left','method':'padim','backbone_path':'artifacts/padim-resnet18.pt','output_name':'vision-01'}}
            allowed={k:v for k,v in examples.items() if k in features or k=='threshold' and 'rul' in features}
            text="""<script setup>
import {ref,watch} from 'vue'
import {session,request} from './api'
const examples=EXAMPLES
const method=ref(Object.keys(examples)[0]),parameters=ref(JSON.stringify(examples[method.value],null,2)),error=ref('')
watch(method,()=>{parameters.value=JSON.stringify(examples[method.value],null,2)})
function run(){try {const body=JSON.parse(parameters.value);error.value='';request('/api/detect/models',{profile:session.profile,source_id:session.source,method:method.value,parameters:body})}catch(e){error.value='설정 JSON을 확인하세요: '+e.message}}
</script>
<template><section class="panel"><h2>지금까지 만든 분석을 비교합니다</h2><p>입력·분할·기준을 정하고 실제 CPU 분석을 실행합니다. 설정 작성은 코딩 에이전트에게 요청할 수 있습니다.</p><label>방법<select v-model="method"><option v-for="(value,key) in examples" :key="key" :value="key">{{key}}</option></select></label><label>이 실행의 설정<textarea v-model="parameters" rows="10"/></label><p v-if="error">{{error}}</p><button :disabled="session.busy" @click="run">선택한 분석 실행</button><button :disabled="session.busy" @click="request('/api/detect/models')">이전 결과</button></section></template>
""".replace('EXAMPLES',json.dumps(allowed,ensure_ascii=False))
        put(folder,'frontend/src/'+panel+'.vue',text)
    text=source('frontend/src/App.vue')
    for label,panel,feature in PANELS:
        if feature not in features:text=text.replace(f"import {panel} from './{panel}.vue'\n",'')
    chosen=[f"['{label}',{panel}]" for label,panel,feature in PANELS if feature in features]
    text=re.sub(r'const panels=\[.*?\]\n','const panels=['+','.join(chosen)+']\n',text)
    if 'transfer' not in features:text=text.replace('<option value="transfer">다른 주제</option>','')
    put(folder,'frontend/src/App.vue',text)


def main():
    # Preserve any external edits in prior outputs instead of silently regenerating over them.
    old=json.loads(MANIFEST.read_text(encoding='utf-8')) if MANIFEST.exists() else []
    for record in old:
        for name,digest in record.get('files',{}).items():
            path=ROOT/record['folder']/name
            if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
                raise ValueError('기존 출발본에 편집이 있습니다: '+str(path))
    records=[]
    for group,day,features in stages():
        folder=OUT/f'{group}{day:02d}-start'/'equipment-assistant'
        if folder.exists():
            # Checked workspace-local output and hashes above; remove only generated owned files.
            previous=next((r for r in old if r['folder']==str(folder.relative_to(ROOT)).replace('\\','/')),None)
            if previous:
                for name in previous['files']:(folder/name).unlink(missing_ok=True)
            elif any(folder.rglob('*')):raise ValueError('관리 기록 없는 출발본 경로: '+str(folder))
        copy_assets(folder,features)
        if features:app_files(folder,features)
        guidance=("앱 코드는 없습니다. 자료·약속을 읽고 오늘 필요한 서비스를 코딩 에이전트에게 요청하세요. 아직 서버 실행 명령을 성공으로 확인할 단계가 아닙니다." if not features else
          "이전 단계 코드가 들어 있습니다. 오늘 기능은 일차 가이드를 읽으며 추가합니다. 기본 실행은 uv sync --frozen --extra dev → uv run --env-file .env python scripts/bootstrap.py → npm.cmd --prefix frontend ci → npm.cmd --prefix frontend run build → uv run --env-file .env python scripts/serve.py 순서입니다. 필요한 models/documents/evaluation extra와 DB 준비는 실행 연결 안내에서 이어집니다.")
        put(folder,'README.md',f'# {group}{day:02d}-start\n\n{guidance}\n\n이전 단계 기능: '+(', '.join(sorted(features)) or '코드 없는 뼈대')+
            '\n\n자기 폴더는 보존하고 새 폴더에서 합류하세요. .env.example은 빈 설정 예시입니다. 실제 키는 넣지 않았습니다. 기본 합성 자료는 원본 측정 파일이 아닙니다.\n\n코드·구문·구성 검토와 실제 학생 완주는 별개입니다. 모델과 DB를 끝까지 실행한 확인본으로 표현하지 않습니다.\n')
        files={str(p.relative_to(folder)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
        archive=OUT/(folder.parent.name+'_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.zip')
        if archive.exists():raise ValueError('기존 ZIP을 덮지 않습니다: '+str(archive))
        listing=ROOT/'30_기록/출발본_포함목록'/f'{folder.parent.name}.json'
        listing.parent.mkdir(parents=True,exist_ok=True)
        listing.write_text(json.dumps(sorted(files),ensure_ascii=False,indent=2),encoding='utf-8')
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for name in sorted(files):z.write(folder/name,'equipment-assistant/'+name)
        records.append({'id':folder.parent.name,'features':sorted(features),'folder':str(folder.relative_to(ROOT)).replace('\\','/'),
            'archive':str(archive.relative_to(ROOT)).replace('\\','/'),'files':files,'archive_hash':hashlib.sha256(archive.read_bytes()).hexdigest()})
    MANIFEST.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'checkpoints':len(records),'files':sum(len(r['files']) for r in records)},ensure_ascii=False))


if __name__=='__main__':main()
