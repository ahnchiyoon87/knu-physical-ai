"""Configure only the dedicated KNU DB; keep credentials in Secret Manager."""
import json, subprocess, urllib.request, urllib.error
from 비밀값준비 import run, GCLOUD, PROJECT, SERVICE
INSTANCE = "knu-litellm-db"
CONNECTION = PROJECT+":asia-northeast3:"+INSTANCE

def main():
    instance = json.loads(run(["sql", "instances", "describe", INSTANCE, "--format=json(state)"]))
    if instance["state"] != "RUNNABLE":
        raise RuntimeError("Dedicated database is not ready yet")
    password = run(["secrets", "versions", "access", "latest", "--secret=knu-litellm-db-password"]).decode().strip()
    users = json.loads(run(["sql", "users", "list", "--instance="+INSTANCE, "--format=json(name)"]))
    if not any(user["name"] == "litellm" for user in users):
        token = run(["auth", "print-access-token"]).decode().strip()
        req = urllib.request.Request("https://sqladmin.googleapis.com/sql/v1beta4/projects/"+PROJECT+"/instances/"+INSTANCE+"/users",data=json.dumps({"name":"litellm", "password":password}).encode(),headers={"Authorization":"Bearer "+token, "Content-Type":"application/json"},method="POST")
        try:
            with urllib.request.urlopen(req,timeout=30) as response:
                operation = json.load(response)
        except urllib.error.HTTPError as error:
            raise RuntimeError("SQL user creation HTTP "+str(error.code)) from None
        run(["sql", "operations", "wait", operation["name"], "--timeout=45"])
    databases = json.loads(run(["sql", "databases", "list", "--instance="+INSTANCE, "--format=json(name)"]))
    if not any(db["name"] == "litellm" for db in databases):
        run(["sql", "databases", "create", "litellm", "--instance="+INSTANCE])
    name = "knu-litellm-database-url"
    names = run(["secrets", "list", "--format=value(name)"]).decode().splitlines()
    if name not in names:
        run(["secrets", "create", name, "--replication-policy=automatic"])
    versions = run(["secrets", "versions", "list", name, "--filter=state:ENABLED", "--format=value(name)"])
    if not versions.strip():
        value = "postgresql://litellm:"+password+"@localhost:5432/litellm?host=/cloudsql/"+CONNECTION+"&connection_limit=5&pool_timeout=30"
        run(["secrets", "versions", "add", name, "--data-file=-"], value.encode())
    run(["secrets", "add-iam-policy-binding", name, "--member=serviceAccount:"+SERVICE, "--role=roles/secretmanager.secretAccessor", "--format=value(etag)"])
    print("Dedicated user/database and socket connection secret ready; values withheld")
if __name__ == "__main__":
    main()
