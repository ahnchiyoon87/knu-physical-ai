import { reactive } from 'vue'
export const session=reactive({token:'',approver:'',profile:'synthetic',source:'shots',provider:'api',busy:false,
  response:null,history:[],context:null,catalog:[]})
export async function request(path,body=null,{approval=false,retain=false}={}) {
  if(session.busy) return null
  session.busy=true
  const rid=crypto.randomUUID()
  try {
    const headers={'Content-Type':'application/json','Authorization':`Bearer ${session.token}`,'X-Request-ID':rid}
    if(approval) headers['X-Approver-Token']=session.approver
    const response=await fetch(path,{method:body===null?'GET':'POST',headers,
      ...(body===null?{}:{body:JSON.stringify(body)})})
    const result=await response.json()
    if(!result.status) throw new Error('서비스 응답 형식을 확인하세요')
    if(!retain) session.response=result
    session.history.unshift({rid:result.rid,status:result.status,path,model:result.meta?.model,
      tokens:result.meta?.tokens_in,cost:result.meta?.cost_usd})
    return result
  } catch(error) {
    const result={rid,status:'failed',answer:null,evidence:[],reason:`연결 또는 응답 오류: ${error.message}`,meta:{warnings:[]}}
    session.response=result
    return result
  } finally {session.busy=false}
}
