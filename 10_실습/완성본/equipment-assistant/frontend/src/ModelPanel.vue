<script setup>
import {ref,computed} from 'vue'
import {session,request} from './api'
const method=ref('table'),features=ref('302,303'),column=ref(22),lot=ref('4'),baseline=ref(200),horizon=ref(20),evaluateLast=ref(true),split=ref('ordered'),threshold=ref(10.5),direction=ref('above'),side=ref('left'),vision=ref('padim'),weights=ref('artifacts/padim-resnet18.pt'),output=ref('vision-review-01'),subset=ref('FD001')
const isSeries=computed(()=>['pyod','forecast','threshold'].includes(method.value))
function run(){
 let parameters
 if(method.value==='table') parameters={feature_ids:features.value.split(',').map(x=>Number(x.trim())),split:split.value,train_fraction:.7}
 else if(isSeries.value) parameters={column_id:column.value,lot_id:lot.value,...(method.value==='pyod'?{baseline_count:baseline.value}:method.value==='forecast'?{horizon:horizon.value,evaluate_last:evaluateLast.value}:{threshold:threshold.value,direction:direction.value})}
 else if(method.value==='rul') parameters={subset:subset.value,sensor_indices:[6,7,8,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25]}
 else parameters={side:side.value,method:vision.value,backbone_path:weights.value,output_name:output.value}
 request('/api/detect/models',{profile:session.profile,source_id:session.source,method:method.value,parameters})
}
</script>
<template><section class="panel"><p class="eyebrow">MODEL LAB</p><h1>같은 관측을 다른 방법으로 읽습니다</h1><p>입력 원천과 학습·평가 구간을 먼저 고르세요. 실행 버튼은 실제 CPU 분석을 시작합니다. 모델 점수는 확정 원인이나 불량 확률이 아닙니다.</p>
<div class="form-row"><label>분석<select v-model="method"><option value="table">표 분류</option><option value="pyod">PyOD 이상 점수</option><option value="forecast">Chronos 예측</option><option value="threshold">임계 도달 예측</option><option value="rul">C-MAPSS RUL</option><option value="vision">열화상 정상 학습</option></select></label></div>
<label v-if="method==='forecast'" class="check"><input type="checkbox" v-model="evaluateLast"/>마지막 관측을 남겨 직전값 기준선과 비교</label>
<div v-if="method==='table'" class="form-row"><label>특징 열 번호 · 쉼표로 구분<input v-model="features"/></label><label>분할<select v-model="split"><option value="ordered">파일 순서 앞 70% 학습</option><option value="random">무작위 70% 학습</option></select></label><p>교육용 분류 자료는 원천 ID를 labeled로 선택합니다. 합성 규칙 라벨을 실제 검사 라벨로 부르지 마세요.</p></div>
<div v-if="isSeries" class="form-row"><label>수치 열 번호<input type="number" v-model.number="column"/></label><label>LOT<input v-model="lot"/></label><label v-if="method==='pyod'">학습 기준 행 수<input type="number" v-model.number="baseline" min="10"/></label><label v-if="method==='forecast'">예측 샷 수<input type="number" v-model.number="horizon" min="1" max="64"/></label><template v-if="method==='threshold'"><label>임계값<input type="number" v-model.number="threshold" step="0.1"/></label><label>방향<select v-model="direction"><option value="above">이상으로 상승</option><option value="below">이하로 하강</option></select></label></template></div>
<div v-if="method==='vision'" class="form-row"><label>측면<select v-model="side"><option value="left">왼쪽</option><option value="right">오른쪽</option></select></label><label>방법<select v-model="vision"><option value="padim">PaDiM</option><option value="patchcore">PatchCore</option></select></label><label>준비된 특징 추출기 파일<input v-model="weights"/></label><label>새 결과 폴더명<input v-model="output"/></label><p>학습에는 정상만, 검증·평가에는 정상과 불량을 따로 남깁니다. 제품 측면을 LOT와 연결하지 않습니다.</p></div>
<label v-if="method==='rul'">C-MAPSS 부분집합<select v-model="subset"><option>FD001</option><option>FD002</option><option>FD003</option><option>FD004</option></select></label>
<div class="actions"><button :disabled="session.busy" @click="run">선택한 분석 실행</button><button class="secondary" :disabled="session.busy" @click="request('/api/detect/models')">저장한 분석 기록</button></div></section></template>
