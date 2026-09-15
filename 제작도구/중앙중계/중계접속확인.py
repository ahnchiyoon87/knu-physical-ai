"""Read-only gateway checks; no inference requests or credential output."""
import json, urllib.request, urllib.error
from pathlib import Path
from 비밀값준비 import run

def request(url, headers):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=45) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()

def main():
    service = json.loads(run(["run", "services", "describe", "knu-litellm", "--region=asia-northeast3", "--format=json(status)"]))["status"]
    if not any(c["type"] == "Ready" and c["status"] == "True" for c in service["conditions"]):
        raise RuntimeError("Cloud Run is not ready")
    url = service["url"]
    token = run(["auth", "print-identity-token"]).decode().strip()
    master = run(["secrets", "versions", "access", "1", "--secret=knu-litellm-master-key"]).decode().strip()
    iam = {"X-Serverless-Authorization": "Bearer "+token}
    checks=[]
    for label, headers, expected in [("no_iam", {}, [401,403]), ("iam_without_proxy_key", iam, [401,403]), ("invalid_proxy_key", {**iam,"Authorization":"Bearer sk-invalid-setup-check"},[401,403]), ("master_key", {**iam,"Authorization":"Bearer "+master},[200])]:
        status, body = request(url+"/v1/models", headers)
        checks.append({"case":label,"status":status,"passed":status in expected})
        if label == "master_key" and status == 200:
            checks[-1]["model_count"] = len(json.loads(body).get("data",[]))
    for endpoint in ["/health/liveliness", "/health/readiness"]:
        status,body=request(url+endpoint, {**iam,"Authorization":"Bearer "+master})
        checks.append({"case":endpoint,"status":status,"passed":status==200})
    evidence={"url":url,"revision":service.get("latestReadyRevisionName"),"checks":checks,"scope":"IAM/proxy auth, model listing and health. No model inference; no cost or concurrency verification."}
    output=Path(__file__).resolve().parents[2]/"작업기록/LiteLLM설정_20260915"
    output.mkdir(parents=True,exist_ok=True)
    (output/"접속확인.json").write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(evidence,ensure_ascii=False))
    if not all(c["passed"] for c in checks):
        raise RuntimeError("Some gateway checks failed; see redacted evidence")
if __name__ == "__main__":
    main()
