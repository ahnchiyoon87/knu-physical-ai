"""Create gateway secrets without displaying or writing secret values locally."""
import os, secrets, shutil, subprocess
PROJECT = "project-f49d373f-f76d-47a1-bdb"
SERVICE = f"knu-litellm@{PROJECT}.iam.gserviceaccount.com"
GCLOUD = shutil.which("gcloud.cmd") or shutil.which("gcloud")
def run(args, data=None):
    result = subprocess.run([GCLOUD, *args, "--project="+PROJECT, "--quiet"], input=data, capture_output=True)
    if result.returncode:
        raise RuntimeError("gcloud operation failed: "+" ".join(args[:3])+"; exit="+str(result.returncode))
    return result.stdout

def main():
    names = run(["secrets", "list", "--format=value(name)"]).decode().splitlines()
    for suffix in ("master-key", "salt-key", "db-password"):
        name = "knu-litellm-"+suffix
        if name not in names:
            run(["secrets", "create", name, "--replication-policy=automatic"])
        versions = run(["secrets", "versions", "list", name, "--filter=state:ENABLED", "--format=value(name)"])
        if not versions.strip():
            value = ("sk-" if suffix != "db-password" else "") + secrets.token_hex(32)
            run(["secrets", "versions", "add", name, "--data-file=-"], value.encode())
        if suffix != "db-password":
            run(["secrets", "add-iam-policy-binding", name, "--member=serviceAccount:"+SERVICE, "--role=roles/secretmanager.secretAccessor", "--format=value(etag)"])
        print(name+": ready (value withheld)")
if __name__ == "__main__":
    main()
