import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Workbook, SpreadsheetFile, FileBlob} from '@oai/artifact-tool';

const here=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(here,'../..');
const out=path.join(root,'30_기록/비용측정_20260915');
const target=path.join(out,'일차별_60명_비용환산.xlsx');
const refresh=process.argv.includes('--refresh');
await fs.mkdir(out,{recursive:true});
let exists=false; try {await fs.access(target);exists=true;} catch {}
if(exists&&!refresh) throw new Error('Workbook exists; use --refresh to preserve manual inputs.');
const wb=exists?await SpreadsheetFile.importXlsx(await FileBlob.load(target)):Workbook.create();
const names=['60명 환산','일차별 기록','입력과 근거'];
if(!exists) names.forEach(n=>wb.worksheets.add(n));
const [sum,days,inputs]=names.map(n=>wb.worksheets.getItem(n));
const timing=JSON.parse(await fs.readFile(path.join(root,'30_기록/재설계_편성.json'),'utf8')).offline;
const plan=timing.map(x=>({id:(x.cohort==='실전반'?'P':'I')+String(parseInt(x.id.slice(1))).padStart(2,'0'),...x}));
// The source id is retained separately; output IDs are P01..I10.
plan.forEach(x=>x.day=(x.cohort==='실전반'?'P':'I')+String(parseInt(x.id.slice(1))).padStart(2,'0'));
const totals=JSON.parse(await fs.readFile(path.join(here,'.runtime/day_totals.json'),'utf8'));
function put(s,cell,value){s.getRange(cell).values=[[value]];}
function formula(s,cell,value){s.getRange(cell).formulas=[[value]];}
function header(s,range){s.getRange(range).format={fill:'#24364B',font:{color:'#FFFFFF',bold:true},rowHeight:34,wrapText:true};}
if(!exists){
  for(const s of [sum,days,inputs]){
    s.showGridLines=false;
    s.getRange(s===days?'A1:Q30':'A1:F35').format.font={name:'Malgun Gothic',size:11};
    s.getRange(s===days?'A1:Q30':'A1:F35').format.rowHeight=25;
  }
  sum.getRange('A2').values=[['60명 운영비 환산']];sum.getRange('A2').format.font={size:16,bold:true};
  sum.getRange('A4:E4').values=[['항목','실전반 9일','통합반 10일','전체','판정 기준']];header(sum,'A4:E4');
  sum.getRange('A5:A9').values=[['등록 인원'],['완주 기록 일차 수'],['청구 확인 일차 수'],['1인 과정 모델 비용 USD'],['반별 모델 비용 USD']];
  formula(sum,'B5',"=IF('입력과 근거'!B5=\"\",\"미입력\",'입력과 근거'!B5)");
  formula(sum,'C5',"=IF('입력과 근거'!B6=\"\",\"미입력\",'입력과 근거'!B6)");
  formula(sum,'D5','=IF(COUNT(B5:C5)=2,SUM(B5:C5),"미입력")');
  put(sum,'E5','두 반 합계 60명');
  for(const [col,cohort,n] of [['B','실전반',9],['C','통합반',10]]){
    formula(sum,col+'6',`=COUNTIFS('일차별 기록'!$B$5:$B$23,"${cohort}",'일차별 기록'!$D$5:$D$23,"완주(사용자 기록)")`);
    formula(sum,col+'7',`=COUNTIFS('일차별 기록'!$B$5:$B$23,"${cohort}",'일차별 기록'!$P$5:$P$23,"청구 확인")`);
    formula(sum,col+'8',`=IF(AND(${col}6=${n},${col}7=${n}),SUMIFS('일차별 기록'!$O$5:$O$23,'일차별 기록'!$B$5:$B$23,"${cohort}"),"미측정")`);
    formula(sum,col+'9',`=IF(AND(ISNUMBER(${col}5),ISNUMBER(${col}8)),${col}5*${col}8,"미측정")`);
  }
  formula(sum,'D6','=SUM(B6:C6)');formula(sum,'D7','=SUM(B7:C7)');
  formula(sum,'D9','=IF(COUNT(B9:C9)=2,SUM(B9:C9),"미측정")');
  put(sum,'E6','완주는 사용자가 기록');put(sum,'E7','원가·크레딧·앱 비용 입력');
  put(sum,'A12','60명 비용 범위');put(sum,'B12','하한');put(sum,'C12','상한');header(sum,'A12:C12');
  put(sum,'A13','전체 운영비 KRW');
  for(const [col,mul] of [['B','B8'],['C','B9']]){
    formula(sum,col+'13',`=IF(AND(ISNUMBER(D9),D5=60,ISNUMBER('입력과 근거'!B7),ISNUMBER('입력과 근거'!B10)),(D9*'입력과 근거'!${mul}+'입력과 근거'!B10)*'입력과 근거'!B7*(1+'입력과 근거'!B11),"미측정 / 입력 필요")`);
  }
  put(sum,'A15','범위는 학생 사용량 가정이며 통계적 신뢰구간이 아닙니다.');
  put(sum,'A16','Google 크레딧 차감 후 0원이어도 운영 원가는 0원이 아닙니다.');
  sum.getRange('A19:D21').values=[['비교 기준','하한 KRW','상한 KRW','근거 성격'],['리서치 운영안',1100000,1550000,'실측 전 추산'],['Luna 모델 추산',740000,740000,'모델 비용 추산; 위 총액과 더하지 않음']];header(sum,'A19:D19');
  put(sum,'A24','Gemini 실측만으로 Luna 완주 비용을 확정하지 않습니다.');
  put(sum,'A25','현재 배포본을 측정합니다. 개편 후에는 영향 일차를 다시 측정합니다.');
  sum.getRange('A4:A25').format.columnWidth=37;sum.getRange('B4:C25').format.columnWidth=25;
  sum.getRange('D4:D25').format.columnWidth=29;sum.getRange('E4:E25').format.columnWidth=31;
  sum.getRange('B8:D13').setNumberFormat('#,##0.00;(#,##0.00);"-"');sum.getRange('B20:C21').setNumberFormat('#,##0');
  inputs.getRange('A2').values=[['입력값과 출처']];inputs.getRange('A2').format.font={size:16,bold:true};
  inputs.getRange('A4:C13').values=[['설정','값','뜻'],['실전반 인원',null,'학교 명단 확인 후 입력'],['통합반 인원',null,'학교 명단 확인 후 입력'],['USD → KRW 환율',null,'학교 견적 기준일 환율'],['하한 사용량 배수',1,'측정자 대비 가정; 실측 아님'],['상한 사용량 배수',1.5,'측정자 대비 가정; 변경 가능'],['공유 서버·DB 총 USD',null,'전체 기간 총액 한 번만; 60배 하지 않음'],['세금·환전·결제 여유율',0,'포함 범위 확인 후 입력; 기본 미반영'],['총 등록 인원',60,'사용자 요구'],['측정 대상','현행 배포본','HydOps 조정 전; 추산 전제를 섞지 않음']];header(inputs,'A4:C4');
  inputs.getRange('B5:B11').format={fill:'#FFF0C2',font:{color:'#0000FF'}};
  inputs.getRange('B11').setNumberFormat('0.0%');
  inputs.getRange('A16:C20').values=[['단가 참고 USD/1M','값','공식 문서 확인 2026-09-15'],['Luna 일반 입력',0.2,'https://developers.openai.com/api/docs/models/gpt-5.6-luna'],['Luna 캐시 읽기',0.02,'동일 출처'],['Luna 출력',1.2,'동일 출처'],['Luna 장문 조건','272K 초과','입력 2배·출력 1.5배; 캐시 쓰기 일반 입력 1.25배']];header(inputs,'A16:C16');
  inputs.getRange('A23:C26').values=[['리서치/측정 출처','구분','자료'],['운영안','사용자 제공','KNU_60명_AI_Coding_Agent_1순위_운영안_CloudRun.md'],['사용량 로그','로컬 예상 비용','https://github.com/jorsm/vertex-ai-models-chat-provider/blob/HEAD/docs/usage-and-billing.md'],['Google 청구','확정 사용량 대조','https://docs.cloud.google.com/billing/docs/how-to/export-data-bigquery']];header(inputs,'A23:C23');
  inputs.getRange('A4:A26').format.columnWidth=31;inputs.getRange('B4:B26').format.columnWidth=25;inputs.getRange('C4:C26').format.columnWidth=90;
  days.getRange('A2').values=[['일차별 사용량과 청구 대조']];days.getRange('A2').format.font={size:16,bold:true};
  days.getRange('A4:Q4').values=[['일차','반','학교 날짜','완주 상태','요청 수','입력 토큰','출력 토큰','캐시 읽기','캐시 쓰기','확장 예상 USD','코딩 청구 원가 USD','크레딧 차감 USD','순 청구 USD','앱 모델 원가 USD','1인 모델 원가 USD','청구 상태','관측 모델']];header(days,'A4:Q4');
  plan.forEach((p,i)=>{
    const r=i+5;
    days.getRange(`A${r}:C${r}`).values=[[p.day,p.cohort,new Date(p.date+'T00:00:00Z')]];
    formula(days,`M${r}`,`=IF(COUNT(K${r}:L${r})=2,K${r}-L${r},"")`);
    formula(days,`O${r}`,`=IF(AND(ISNUMBER(K${r}),ISNUMBER(N${r})),K${r}+N${r},"")`);
    formula(days,`P${r}`,`=IF(AND(COUNT(K${r}:L${r})=2,ISNUMBER(N${r})),"청구 확인","청구 미확인")`);
  });
  days.getRange('C5:C23').setNumberFormat('yyyy-mm-dd');days.getRange('E5:I23').setNumberFormat('#,##0');
  days.getRange('J5:O23').setNumberFormat('0.0000');days.getRange('K5:L23').format={fill:'#FFF0C2',font:{color:'#0000FF'}};
  days.getRange('N5:N23').format={fill:'#FFF0C2',font:{color:'#0000FF'}};
  days.getRange('A4:A23').format.columnWidth=9;days.getRange('B4:B23').format.columnWidth=11;
  days.getRange('C4:C23').format.columnWidth=14;days.getRange('D4:D23').format.columnWidth=24;
  days.getRange('E4:I23').format.columnWidth=14;days.getRange('J4:O23').format.columnWidth=17;
  days.getRange('P4:P23').format.columnWidth=18;days.getRange('Q4:Q23').format.columnWidth=36;
  days.freezePanes.freezeRows(4);days.freezePanes.freezeColumns(2);
  put(days,'A26','노란 칸은 사용자가 청구서와 앱 로그로 입력합니다. 크레딧은 차감액을 양수로 적습니다.');
  put(days,'A27','J열은 확장 예상액입니다. K열은 청구 확인 원가이며 서로 대체하지 않습니다.');
  put(days,'A28','다른 창의 Vertex 호출은 중지합니다. 확장 로그는 워크스페이스를 구분하지 않습니다.');
}
// Refresh only machine-collected fields. Preserve roster, FX, billing and app inputs.
for(const p of plan){
  const matches=[];for(let r=5;r<=23;r++)if(days.getRange(`A${r}`).values[0][0]===p.day)matches.push(r);
  if(matches.length!==1)throw new Error('Missing or duplicated day '+p.day);
  const r=matches[0],v=totals.find(x=>x.day===p.day);if(!v)throw new Error('Missing total '+p.day);
  days.getRange(`D${r}:J${r}`).values=[[v.status,v.calls,v.input,v.output,v.cache_read,v.cache_create,v.estimated_usd]];
  put(days,`Q${r}`,v.models);
}
wb.recalculate();
console.log((await wb.inspect({kind:'table',range:"'60명 환산'!A4:D13",include:'values,formulas',tableMaxRows:10,tableMaxCols:4,maxChars:2000})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!',options:{useRegex:true,maxResults:20},maxChars:1000})).ndjson);
// Preserve an existing workbook before export; don't replace manual edits without a backup.
if(exists){await fs.mkdir(path.join(here,'.runtime/workbook-backups'),{recursive:true});await fs.copyFile(target,path.join(here,'.runtime/workbook-backups',Date.now()+'.xlsx'));}
await (await SpreadsheetFile.exportXlsx(wb)).save(target);
await fs.mkdir(path.join(here,'previews'),{recursive:true});
for(const [name,range,file] of [['60명 환산','A1:E25','summary'],['일차별 기록','A1:Q10','days'],['입력과 근거','A1:C26','inputs']]){
  const blob=await wb.render({sheetName:name,range,scale:1.4,format:'png'});
  await fs.writeFile(path.join(here,'previews',file+'.png'),new Uint8Array(await blob.arrayBuffer()));
}
console.log(target);
