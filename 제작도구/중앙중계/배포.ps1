param([switch]$InitializeSchema)
$ErrorActionPreference = 'Stop'
$schemaUpdateDisabled = if ($InitializeSchema) { 'false' } else { 'true' }
& gcloud.cmd run deploy knu-litellm `
  --project=project-f49d373f-f76d-47a1-bdb `
  --region=asia-northeast3 `
  --image=asia-northeast3-docker.pkg.dev/project-f49d373f-f76d-47a1-bdb/knu-ai-gateway/litellm@sha256:ce03f5f693f47f7ae57dde05734683f9a53768a3abc996559c1a38f6ff255bc5 `
  --service-account=knu-litellm@project-f49d373f-f76d-47a1-bdb.iam.gserviceaccount.com `
  --execution-environment=gen2 --port=4000 --cpu=1 --memory=2Gi `
  --min=0 --max=1 --concurrency=20 --timeout=600 `
  --add-cloudsql-instances=project-f49d373f-f76d-47a1-bdb:asia-northeast3:knu-litellm-db `
  --set-secrets=LITELLM_MASTER_KEY=knu-litellm-master-key:1,LITELLM_SALT_KEY=knu-litellm-salt-key:1,DATABASE_URL=knu-litellm-database-url:1 `
  "--set-env-vars=LITELLM_LOG=ERROR,STORE_MODEL_IN_DB=True,STORE_PROMPTS_IN_SPEND_LOGS=False,DISABLE_SCHEMA_UPDATE=$schemaUpdateDisabled" `
  --args=--config=/app/knu-config.yaml,--port=4000,--num_workers=1 `
  --no-allow-unauthenticated --quiet
if ($LASTEXITCODE -ne 0) { throw 'Cloud Run deployment failed' }
