#!/usr/bin/env bash
set -euo pipefail
: "${PROJECT_ID:?Set PROJECT_ID}"
: "${REGION:?Set REGION}"
: "${SERVICE_NAME:?Set SERVICE_NAME}"
: "${SERVICE_ACCOUNT:?Set a dedicated runtime service account email}"
: "${IMAGE_URI:?Set the already built Artifact Registry image URI including a version tag}"
: "${SECRET_BINDINGS:?Set ENV=SECRET:VERSION comma-separated bindings, never secret values}"
gcloud run deploy "$SERVICE_NAME" --project "$PROJECT_ID" --region "$REGION" \
  --image "$IMAGE_URI" --service-account "$SERVICE_ACCOUNT" \
  --set-secrets "$SECRET_BINDINGS" \
  --set-env-vars ALLOW_MODEL_CALLS=false,ALLOW_MODEL_DOWNLOADS=false \
  --memory 8Gi --cpu 2 --concurrency 1 --max-instances 1 \
  --no-allow-unauthenticated --quiet
gcloud run services describe "$SERVICE_NAME" --project "$PROJECT_ID" --region "$REGION" \
  --format='value(status.url)'
