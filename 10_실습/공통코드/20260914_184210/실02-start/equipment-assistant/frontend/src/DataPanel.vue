<script setup>
import { computed,ref,watch } from 'vue'
import { session,request } from './api'
const question=ref(''),lot=ref(''),column=ref(null),series=ref(null)
const sources=ref([]),verify=ref(false),level=ref('probed')
watch(()=>session.source,()=>{column.value=numeric.value[0]?.id??null;session.context=null;series.value=null})
watch(()=>session.profile,()=>{sources.value=[];series.value=null})
const selected=computed(()=>session.catalog.find(x=>x.source_id===session.source))
const numeric=computed(()=>(selected.value?.columns||[]).filter(x=>x.type==='number'))
async function catalog(){const r=await request(`/api/data/catalog?profile=${encodeURIComponent(session.profile)}`);if(r&&r.status==='ok'){session.catalog=r.answer;if(!r.answer.some(x=>x.source_id===session.source))session.source=r.answer[0]?.source_id||'';column.value=numeric.value[0]?.id}}
async function ask(){const r=await request('/api/data/query',{profile:session.profile,source_ids:sources.value.length?sources.value:[session.source],question:question.value,provider:session.provider,context:session.context,verify:verify.value,context_level:level.value});if(r&&r.status==='ok')session.context=r.answer.context}
</script>
<template>
 <section class="panel"><p class="eyebrow">표 → 의미 → 질문</p><h2>숫자를 읽기 전에 뜻을 확인합니다</h2>
 <div class="actions"><button @click="catalog" :disabled="session.busy">원천과 열 사전 보기</button><button @click="request('/api/data/upload',{profile:session.profile,source_id:session.source})" :disabled="session.busy">선택한 원천 적재</button></div>
 <p class="muted">원천 매핑에 등록한 파일을 읽습니다. 원본과 교육용 합성의 선택을 확인하세요.</p>
 <div v-if="selected" class="catalog"><strong>{{selected.provenance}}</strong><table><thead><tr><th>열 번호</th><th>이름</th><th>뜻</th><th>단위</th></tr></thead><tbody><tr v-for="c in selected.columns" :key="c.id"><td>{{c.id}}</td><td>{{c.name}}</td><td>{{c.meaning}}</td><td>{{c.unit}}</td></tr></tbody></table></div>
 <label>표에 묻고 싶은 것<textarea v-model="question" placeholder="비교 대상, 범위와 계산 기준을 포함해 질문을 적으세요."/></label>
 <fieldset><legend>질문에 함께 사용할 원천</legend><label class="check" v-for="item in session.catalog" :key="item.source_id"><input type="checkbox" v-model="sources" :value="item.source_id" @change="session.context=null"/>{{item.source_id}}</label><p class="muted">선택하지 않으면 상단의 원천 하나를 사용합니다.</p></fieldset>
 <details><summary>학습용 비교 조건</summary><label>모델에 전달할 정보<select v-model="level" @change="session.context=null"><option value="names">열 이름과 형식만 · 첫 비교</option><option value="dictionary">열 뜻·단위 포함</option><option value="probed">사전과 실제 값 정찰 포함</option></select></label><p>비교 조건을 바꿔도 읽기 전용 실행과 열 번호 검사는 유지됩니다. 심사를 끈 결과는 직접 대조하세요.</p></details>
 <div class="actions"><button class="primary" :disabled="session.busy||!question.trim()" @click="ask">선택한 모델로 질문</button><button @click="session.context=null">이전 질문 연결 지우기</button></div>
</section>
</template>
