<script setup>
import {computed} from 'vue'
const props=defineProps({answer:Object})
const series=computed(()=>[
 {name:'예측 중앙값',values:props.answer.median,color:'#205c88'},
 {name:'관측 정답',values:props.answer.expected,color:'#bd521e'},
 {name:'직전값 기준선',values:props.answer.last_value_baseline,color:'#6c657e'}
].filter(s=>Array.isArray(s.values)&&s.values.length))
const bounds=computed(()=>{
 const values=[...series.value.flatMap(s=>s.values),...(props.answer.lower||[]),...(props.answer.upper||[])].filter(Number.isFinite)
 const low=Math.min(...values),high=Math.max(...values),pad=(high-low||1)*.1
 return {low:low-pad,high:high+pad,n:Math.max(...series.value.map(s=>s.values.length))}
})
const x=i=>65+i/Math.max(1,bounds.value.n-1)*620
const y=v=>230-(v-bounds.value.low)/(bounds.value.high-bounds.value.low)*190
const line=values=>values.map((v,i)=>Number.isFinite(v)?`${i===0?'M':'L'}${x(i)},${y(v)}`:'').join(' ')
const band=computed(()=>{
 const a=props.answer.lower,b=props.answer.upper
 if(!Array.isArray(a)||!Array.isArray(b)||a.length!==b.length||a.some(v=>!Number.isFinite(v))||b.some(v=>!Number.isFinite(v)))return ''
 return a.map((v,i)=>`${x(i)},${y(v)}`).concat(b.map((v,i)=>`${x(i)},${y(v)}`).reverse()).join(' ')
})
</script>
<template><figure v-if="series.length" class="forecast"><figcaption>{{answer.evaluation||'예측 결과'}} · {{answer.axis}}</figcaption><svg viewBox="0 0 740 285" role="img" aria-label="예측 중앙값, 관측 정답과 직전값 기준선 비교"><line x1="65" y1="40" x2="65" y2="230" stroke="#666"/><line x1="65" y1="230" x2="685" y2="230" stroke="#666"/><text x="5" y="48">{{bounds.high.toFixed(2)}}</text><text x="5" y="234">{{bounds.low.toFixed(2)}}</text><text x="65" y="255">1</text><text x="660" y="255">{{bounds.n}}</text><text x="280" y="280">예측 위치 · 샷 순서</text><polygon v-if="band" :points="band" fill="#205c8820"/><path v-for="s in series" :key="s.name" :d="line(s.values)" fill="none" :stroke="s.color" stroke-width="2.5" :stroke-dasharray="s.name==='직전값 기준선'?'6 4':undefined"/></svg><p><span v-for="s in series" :key="s.name" :style="{color:s.color,marginRight:'1rem'}">● {{s.name}}</span></p><p>{{answer.interval}}</p><dl v-if="answer.metrics"><dt>중앙값 예측 MAE</dt><dd>{{answer.metrics.median_mae}}</dd><dt>직전값 MAE</dt><dd>{{answer.metrics.last_value_mae}}</dd><dt>이 평가 구간의 분위수 포함률</dt><dd>{{answer.metrics.interval_coverage}}</dd></dl></figure></template>
