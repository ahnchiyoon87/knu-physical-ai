<script setup>
import {ref,computed,watch,onBeforeUnmount} from 'vue'
import {session} from './api'
const props=defineProps({answer:Object})
const split=ref('validation'),threshold=ref(.5),selected=ref(''),original=ref(''),heatmap=ref(''),error=ref('')
const rows=computed(()=>(props.answer.predictions||[]).filter(x=>x.split===split.value))
const counts=computed(()=>{const c={tp:0,tn:0,fp:0,fn:0};for(const row of rows.value){const predicted=row.score>=threshold.value?1:0;c[row.expected===1?(predicted?'tp':'fn'):(predicted?'fp':'tn')]++}return c})
function clear(){for(const url of [original.value,heatmap.value])if(url)URL.revokeObjectURL(url);original.value='';heatmap.value=''}
watch(()=>props.answer.id,()=>{clear();selected.value='';split.value='validation'})
watch(split,()=>{clear();selected.value=''})
async function show(){
 clear();error.value=''
 try{for(const kind of ['original','heatmap']){const r=await fetch(`/api/vision/${encodeURIComponent(props.answer.id)}/${encodeURIComponent(selected.value)}?kind=${kind}`,{headers:{Authorization:`Bearer ${session.token}`}});if(!r.ok)throw Error('저장된 이미지에 접근하지 못했습니다');const url=URL.createObjectURL(await r.blob());if(kind==='original')original.value=url;else heatmap.value=url}}
 catch(e){clear();error.value=e.message}
}
onBeforeUnmount(clear)
</script>
<template><section><h3>정상과 다른 모습을 확인합니다</h3><p>임계값 비교는 검증 자료에서 먼저 합니다. 평가 결과를 반복해서 보고 기준을 맞추면 마지막 평가의 역할이 달라집니다.</p><div class="form-row"><label>분할<select v-model="split"><option value="validation">검증 · 기준 선택</option><option value="test">평가 · 선택한 기준 확인</option></select></label><label>비교 임계<input type="number" min="0" max="1" step="0.01" v-model.number="threshold"/></label></div><p>놓친 불량 {{counts.fn}} · 잘못 버린 양품 {{counts.fp}} · 잡은 불량 {{counts.tp}} · 양품 통과 {{counts.tn}}</p><div class="form-row"><label>이미지<select v-model="selected"><option value="">선택하세요</option><option v-for="row in rows" :key="row.id" :value="row.id">{{row.id}} · 정답 {{row.expected}} · 점수 {{row.score.toFixed(3)}}</option></select></label><button :disabled="!selected" @click="show">원본 표현과 열지도 읽기</button></div><p v-if="error" role="alert">{{error}}</p><div class="image-pair"><figure v-if="original"><img :src="original" alt="선택한 온도 배열의 공통 범위 이미지"/><figcaption>온도 표현 · 자료 변환의 공통 범위</figcaption></figure><figure v-if="heatmap"><img :src="heatmap" alt="선택한 이미지의 모델 이상 점수 지도"/><figcaption>모델의 후처리 점수 0~1 · 결함 위치 정답 아님</figcaption></figure></div></section></template>
