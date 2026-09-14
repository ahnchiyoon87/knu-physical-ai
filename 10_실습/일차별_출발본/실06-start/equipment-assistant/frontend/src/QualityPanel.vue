<script setup>
import {ref} from 'vue'
import {session,request} from './api'
const ids=ref('22'),excerpt=ref('')
const body=()=>({profile:session.profile,source_id:session.source})
function meaning(){request('/api/data/meaning',{...body(),provider:session.provider,column_ids:ids.value.split(',').map(x=>Number(x.trim())),excerpt:excerpt.value})}
</script>
<template><section class="panel"><p class="eyebrow">관측값 → 처리 기준</p><h2>낯선 값을 구분하고 원본을 보존합니다</h2><p>결측·0·음수·범위를 실제 값에서 확인합니다. 범위 이탈은 의심 표시이며 확정 원인이 아닙니다.</p><div class="actions"><button :disabled="session.busy" @click="request('/api/data/quality',body())">기본 품질 통계</button><button :disabled="session.busy" @click="request('/api/data/duplicates',body())">상수 열·지정 열 쌍 대조</button><button :disabled="session.busy" @click="request('/api/data/clean',body())">설정한 기준으로 정제 뷰 만들기</button><button :disabled="session.busy" @click="request('/api/data/clean/preview',body())">정제 뷰와 표시 사유</button></div><p>quality_rules에 근거를 확인한 기준만 넣습니다. 오류 코드는 NULL로 읽고 범위는 표시하며 원본 행을 삭제하지 않습니다.</p><details><summary>설명서에서 열 뜻 초안 받기</summary><label>열 번호 · 쉼표 구분<input v-model="ids"/></label><label>실제 설명서 발췌<textarea v-model="excerpt" rows="6"/></label><button :disabled="session.busy||!excerpt.trim()" @click="meaning">선택 모델로 뜻 초안 작성</button><p>실제 모델 호출입니다. 인용 존재는 코드가 검사하고, 그 인용이 뜻을 지지하는지는 사람이 검수합니다. 사전에 자동 저장하지 않습니다.</p></details></section></template>
