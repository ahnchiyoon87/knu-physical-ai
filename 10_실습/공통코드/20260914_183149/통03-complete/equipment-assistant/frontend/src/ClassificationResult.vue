<script setup>
defineProps({answer:Object})
const metrics=[['n','평가 행 수'],['tp','TP'],['tn','TN'],['fp','FP'],['fn','FN'],['accuracy','정확도'],['precision','정밀도'],['recall','재현율']]
const show=value=>value==null?'정의되지 않음':Number.isInteger(value)?value:Number(value).toFixed(4)
</script>
<template><section><h3>같은 평가 행에서 비교합니다</h3>
<p>학습 {{answer.train_rows}}행 · 평가 {{answer.test_rows}}행 · {{answer.split}}</p>
<div class="table-scroll"><table><thead><tr><th>지표</th><th>분류 모델</th><th>항상 0 기준선</th></tr></thead><tbody>
<tr v-for="[key,label] in metrics" :key="key"><th>{{label}}</th><td>{{show(answer.metrics[key])}}</td><td>{{answer.baseline?show(answer.baseline.metrics[key]):'이 기록에는 없음'}}</td></tr>
</tbody></table></div><p>양성 정답이 없으면 재현율을 정의할 수 없습니다. 정확도만으로 희소한 양성을 잘 찾았다고 판단하지 않습니다.</p>
<template v-if="answer.feature_importances"><h3>모델이 학습에 사용한 특징</h3><p>{{answer.importance_meaning}}</p>
<table><thead><tr><th>열 ID</th><th>중요도</th></tr></thead><tbody><tr v-for="item in answer.feature_importances" :key="item.column_id"><td>{{item.column_id}}</td><td>{{show(item.importance)}}</td></tr></tbody></table></template>
<p>{{answer.limitations}}</p></section></template>
