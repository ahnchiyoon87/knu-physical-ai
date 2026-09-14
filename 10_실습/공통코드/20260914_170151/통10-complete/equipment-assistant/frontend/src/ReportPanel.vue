<script setup>
import {ref} from 'vue'
import {session,request} from './api'
const lot=ref(''),prose=ref(false)
function printReport(){window.print()}
</script>
<template><section class="panel"><p class="eyebrow">REPORT</p><h1>같은 관측에서 현장용과 관리자용 보고서를 만듭니다</h1><p>행과 LOT 수는 SQL로 계산합니다. 모델을 켜면 근거 번호가 달린 설명을 추가합니다. 두 보고서의 수치는 동일한 범위에서 나옵니다.</p><div class="form-row"><label>LOT · 비워 두면 전체<input v-model="lot"/></label><label class="check"><input type="checkbox" v-model="prose"/>모델 설명 추가 · 실제 호출</label></div><div class="actions"><button :disabled="session.busy" @click="request('/api/report',{profile:session.profile,source_id:session.source,lot_id:lot||null,provider:prose?session.provider:null})">보고서 작성</button><button class="secondary" :disabled="!session.response" @click="printReport">현재 화면 인쇄 / PDF 저장</button></div><p>원인과 조치가 미확정이면 그대로 남깁니다. 경보가 적어졌다는 이유만으로 품질이 개선됐다고 쓰지 마세요.</p></section></template>
