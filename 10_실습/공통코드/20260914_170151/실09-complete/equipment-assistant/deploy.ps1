param(
  [Parameter(Mandatory=$true)][string]$ProjectId,
  [Parameter(Mandatory=$true)][string]$Region,
  [Parameter(Mandatory=$true)][string]$ServiceName,
  [Parameter(Mandatory=$true)][string]$ServiceAccount,
  [Parameter(Mandatory=$true)][string]$ImageUri,
  [Parameter(Mandatory=$true)][string]$SecretBindings
)
$ErrorActionPreference='Stop'
& gcloud run deploy $ServiceName --project $ProjectId --region $Region --image $ImageUri --service-account $ServiceAccount --set-secrets $SecretBindings --set-env-vars 'ALLOW_MODEL_CALLS=false,ALLOW_MODEL_DOWNLOADS=false' --memory 8Gi --cpu 2 --concurrency 1 --max-instances 1 --no-allow-unauthenticated --quiet
if ($LASTEXITCODE -ne 0) { throw 'Cloud Run deploy failed' }
& gcloud run services describe $ServiceName --project $ProjectId --region $Region '--format=value(status.url)'
if ($LASTEXITCODE -ne 0) { throw 'Cloud Run URL lookup failed' }
