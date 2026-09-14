<script setup>
import {ref,watch} from 'vue'
import {session,request} from './api'
const examples={"table": {"feature_ids": [302, 303], "split": "ordered", "train_fraction": 0.7}}
const method=ref(Object.keys(examples)[0]),parameters=ref(JSON.stringify(examples[method.value],null,2)),error=ref('')
watch(method,()=>{parameters.value=JSON.stringify(examples[method.value],null,2)})
function run(){try {const body=JSON.parse(parameters.value);error.value='';request('/api/detect/models',{profile:session.profile,source_id:session.source,method:method.value,parameters:body})}catch(e){error.value='설정 JSON을 확인하세요: '+e.message}}
</script>
<template><section class="panel"><h2>지금까지 만든 분석을 비교합니다</h2><p>입력·분할·기준을 정하고 실제 CPU 분석을 실행합니다. 설정 작성은 코딩 에이전트에게 요청할 수 있습니다.</p><label>방법<select v-model="method"><option v-for="(value,key) in examples" :key="key" :value="key">{{key}}</option></select></label><label>이 실행의 설정<textarea v-model="parameters" rows="10"/></label><p v-if="error">{{error}}</p><button :disabled="session.busy" @click="run">선택한 분석 실행</button><button :disabled="session.busy" @click="request('/api/detect/models')">이전 결과</button></section></template>
