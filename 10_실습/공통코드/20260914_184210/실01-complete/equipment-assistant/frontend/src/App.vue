<script setup>
import {ref,watch} from 'vue'
import {session,request} from './api'
import Result from './Result.vue'
import DataPanel from './DataPanel.vue'
import GraphPanel from './GraphPanel.vue'
const panels=[['표와 질문',DataPanel],['관계',GraphPanel]]
const active=ref(0),settingsOpen=ref(true),traceId=ref('')
watch(()=>session.profile,()=>{session.context=null;session.catalog=[];session.source=session.profile==='transfer'?'books':'shots';session.response=null})
</script>
<template>
 <header class="top"><div class="brand">FIELD NOTES <span>설비 이상 대응 어시스턴트</span></div><button @click="settingsOpen=!settingsOpen">연결 설정</button></header>
 <section class="connection" v-if="settingsOpen"><label>서비스 접속 토큰<input type="password" v-model="session.token" autocomplete="off"/></label><label>자료<select v-model="session.profile"><option value="synthetic">교육용 합성</option><option value="kamp">KAMP 원본</option></select></label><label>서비스 모델<select v-model="session.provider"><option value="api">API 모델</option><option value="internal">사내 모델</option></select></label><label>원천 ID<input v-model="session.source" list="sources"/><datalist id="sources"><option v-for="item in session.catalog" :key="item.source_id" :value="item.source_id"/></datalist></label><button :disabled="session.busy" @click="request('/health')">연결 확인</button></section>
 <main><aside><p class="eyebrow">WORKSPACE</p><nav><button v-for="(panel,index) in panels" :key="panel[0]" :class="{selected:index===active}" @click="active=index">{{panel[0]}}</button></nav><div class="source-note"><strong>{{session.profile==='synthetic'?'교육용 합성 자료':session.profile==='kamp'?'원본 연결 자료':'다른 주제 자료'}}</strong><p>현재 선택한 자료의 출처와 해석 범위가 모든 판단의 출발점입니다.</p></div></aside>
 <div class="content"><component :is="panels[active][1]"/><p v-if="session.busy" class="progress" role="status">요청을 처리하고 있습니다. 같은 요청을 중복 실행하지 마세요.</p><Result :result="session.response"/>
 <details class="trace"><summary>요청 관측</summary><div class="form-row"><label>요청 번호<input v-model="traceId"/></label><button :disabled="session.busy||!traceId" @click="request('/trace/'+encodeURIComponent(traceId))">단계별 기록 읽기</button></div><table><thead><tr><th>요청</th><th>상태</th><th>모델</th></tr></thead><tbody><tr v-for="item in session.history" :key="item.rid"><td><button class="text-button" @click="traceId=item.rid">{{item.rid}}</button></td><td>{{item.status}}</td><td>{{item.model||'모델 호출 없음/미측정'}}</td></tr></tbody></table></details></div></main>
</template>
