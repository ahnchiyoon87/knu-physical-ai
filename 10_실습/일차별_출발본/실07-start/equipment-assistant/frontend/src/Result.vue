<script setup>
import { computed } from 'vue'
import ForecastResult from './ForecastResult.vue'
const props=defineProps({result:Object})
const labels={ok:'결과 있음',none:'조회 결과 없음',refused:'답변·실행 보류',failed:'실행 실패',error:'입력 확인',pending_approval:'승인 대기',insufficient:'판단 자료 부족'}
const answer=computed(()=>props.result?.answer)
const rows=computed(()=>Array.isArray(answer.value)?answer.value:answer.value?.rows||answer.value?.statistics||[])
const claims=computed(()=>rows.value.length&&rows.value.every(x=>x&&typeof x.text==='string'))
const keys=computed(()=>rows.value.length&&typeof rows.value[0]==='object'?Object.keys(rows.value[0]):[])
const fields=computed(()=>answer.value&&typeof answer.value==='object'&&!Array.isArray(answer.value)?
  Object.entries(answer.value).filter(([k,v])=>!['rows','statistics','sql','context','checks','preview'].includes(k)&&['string','number','boolean'].includes(typeof v)):[])
const display=value=>value===null?'없음':typeof value==='object'?JSON.stringify(value):String(value)
</script>
<template>
  <section v-if="result" class="result" aria-live="polite">
    <div class="section-head"><h2>답과 관측 결과</h2><span :class="['badge',result.status]">{{labels[result.status]||result.status}}</span></div>
    <p v-if="result.reason" class="reason">{{result.reason}}</p>
    <ForecastResult v-if="answer?.median" :answer="answer"/>
    <div v-if="fields.length" class="facts"><div v-for="[key,value] in fields" :key="key"><span>{{key}}</span><strong>{{display(value)}}</strong></div></div>
    <div v-if="claims" class="claims"><p v-for="(claim,index) in rows" :key="index">{{claim.text}} <small>[{{claim.evidence_ids?.join(', ')}}]</small></p></div>
    <div v-else-if="rows.length" class="table-scroll"><table><thead><tr><th v-for="key in keys" :key="key">{{key}}</th></tr></thead><tbody><tr v-for="(row,index) in rows" :key="index"><td v-for="key in keys" :key="key">{{display(row[key])}}</td></tr></tbody></table></div>
    <p v-else-if="typeof answer==='string'">{{answer}}</p>
    <p v-if="answer?.truncated" class="reason">화면의 행 상한에 도달했습니다. 표시된 행을 전체 자료로 해석하지 마세요.</p>
    <div v-if="answer?.checks" class="checks"><p v-for="check in answer.checks" :key="check.item"><b>{{check.result}}</b> {{check.item}}</p></div>
    <details v-if="answer?.sql"><summary>계산에 사용한 SQL</summary><pre>{{answer.sql}}</pre></details>
    <h3 v-if="result.evidence?.length">근거</h3>
    <article class="evidence" v-for="(item,index) in result.evidence||[]" :key="index">
      <small>{{item.kind}} · {{item.status||'기록'}} · {{item.provenance||''}}</small>
      <h4>{{item.id??index}} · {{item.ref}}</h4><p v-if="item.quote">{{item.quote}}</p>
      <p v-if="item.sql">{{item.rows}}행 · <code>{{item.sql}}</code></p>
    </article>
    <p v-for="warning in result.meta?.warnings||[]" :key="warning" class="notice">{{warning}}</p>
    <footer class="result-foot">요청 {{result.rid}}<span v-if="result.meta?.model"> · {{result.meta.model}} · 입력 {{result.meta.tokens_in??'미측정'}} / 출력 {{result.meta.tokens_out??'미측정'}} tokens · 비용 {{result.meta.cost_usd===null?'미측정':result.meta.cost_usd+' USD'}}</span></footer>
    <details><summary>전체 결과 구조 확인</summary><pre>{{JSON.stringify(result,null,2)}}</pre></details>
  </section>
</template>
