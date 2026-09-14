<script setup>
import {ref} from 'vue'
import {session,request} from './api'
const cases=ref(null),name=ref(''),error=ref('')
async function read(event){try {const file=event.target.files[0];if(!file)return; const data=JSON.parse(await file.text());if(!Array.isArray(data))throw new Error('배열 형식이 필요합니다');cases.value=data;name.value=file.name;error.value=''}catch(e){cases.value=null;error.value=e.message}}
</script>
<template><section class="panel"><p class="eyebrow">EVIDENCE REVIEW</p><h1>질문과 기대 근거를 고정한 뒤 비교합니다</h1><p>JSON 질문셋은 id, question, expected_documents, expected_statuses를 가집니다. 각 질문에 실제 모델 호출이 발생합니다. 계약 점수와 RAGAS의 의미 심사는 따로 읽습니다.</p><label>내 질문셋<input type="file" accept=".json" @change="read"/></label><p v-if="cases">{{name}} · {{cases.length}}개 질문</p><p v-if="error" role="alert">{{error}}</p><button :disabled="session.busy||!cases" @click="request('/api/eval/run',{profile:session.profile,provider:session.provider,cases})">현재 모델로 질문셋 평가</button><p>다른 모델과 비교할 때 질문 파일을 그대로 사용하세요. RAGAS 4개 지표와 DeepEval 결과는 scripts/eval.py의 저장 결과에서 확인합니다. 점수가 같다고 답이 항상 옳은 것은 아닙니다.</p></section></template>
