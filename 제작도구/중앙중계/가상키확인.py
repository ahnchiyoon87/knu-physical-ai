"""Create an expiring setup key, verify its scope, then revoke. No inference."""
import json,urllib.request,urllib.error,uuid
from pathlib import Path
from 비밀값준비 import run

def main():
    url = run(["run","services","describe","knu-litellm","--region=asia-northeast3","--format=value(status.url)"]).decode().strip()
    identity=run(["auth","print-identity-token"]).decode().strip()
    master=run(["secrets","versions","access","1","--secret=knu-litellm-master-key"]).decode().strip()
    def request(path,key,payload=None):
        headers={"X-Serverless-Authorization":"Bearer "+identity,"Authorization":"Bearer "+key}
        data=None
        if payload is not None:
            data=json.dumps(payload).encode();headers["Content-Type"]="application/json"
        try:
            with urllib.request.urlopen(urllib.request.Request(url+path,data=data,headers=headers),timeout=45) as response:
                return response.status,json.load(response)
        except urllib.error.HTTPError as error:
            try:
                failure=json.loads(error.read())
                message=str(failure.get("error",{}).get("message",""))
            except (ValueError,AttributeError):
                message=""
            return error.code,{"budget_error": "budget" in message.lower()}
    zero_status,zero_body=request("/key/generate",master,{"key_alias":"knu-zero-budget-check","models":["coding"],"duration":"1h","max_budget":0,"rpm_limit":10})
    if zero_status != 200: raise RuntimeError("Zero budget key creation failed")
    try:
        zero_code,zero_error=request("/v1/models",zero_body["key"])
    finally:
        zero_delete,_=request("/key/delete",master,{"keys":[zero_body["key"]]})
    zero_check={"case":"zero_budget_denied","status":zero_code,"budget_error":zero_error.get("budget_error"),"passed":zero_code==429 and zero_error.get("budget_error") is True and zero_delete==200}
    before=run(["run","services","describe","knu-litellm","--region=asia-northeast3","--format=value(status.latestReadyRevisionName)"]).decode().strip()
    status,body=request("/key/generate",master,{"key_alias":"knu-setup-check","models":["coding"],"duration":"1h","max_budget":0.01,"rpm_limit":10,"metadata":{"purpose":"setup-auth-check"}})
    checks=[zero_check,{"case":"generate_expiring_test_key","status":status,"passed":status==200}]
    if status!=200:
        print(json.dumps(checks));raise RuntimeError("Key creation failed")
    key=body["key"]
    try:
        for label,path,expected in [("virtual_key_models","/v1/models",200),("virtual_key_cannot_list_admin_keys","/key/list",403)]:
            code,_=request(path,key)
            checks.append({"case":label,"status":code,"passed":code==expected})
        result=run(["run","services","update","knu-litellm","--region=asia-northeast3","--update-env-vars=DISABLE_SCHEMA_UPDATE=true,KNU_VERIFY_RUN="+uuid.uuid4().hex[:12],"--format=value(status.latestReadyRevisionName)"])
        checks.append({"case":"new_revision", "before":before,"revision":result.decode().strip(),"passed":result.decode().strip()!=before})
        code,_=request("/v1/models",key)
        checks.append({"case":"key_valid_after_new_revision","status":code,"passed":code==200})
    finally:
        code,_=request("/key/delete",master,{"keys":[key]})
        checks.append({"case":"delete_setup_key","status":code,"passed":code==200})
    code,_=request("/v1/models",key)
    checks.append({"case":"deleted_key_denied","status":code,"passed":code in [401,403]})
    output=Path(__file__).resolve().parents[2]/"작업기록/LiteLLM설정_20260915/가상키확인_v2.json"
    output.write_text(json.dumps({"checks":checks,"scope":"Temporary key lifecycle and revision persistence; no inference calls"},ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(checks,ensure_ascii=False))
    if not all(c["passed"] for c in checks):raise RuntimeError("Key checks failed")
if __name__ == "__main__":main()
