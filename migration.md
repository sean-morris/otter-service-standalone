# Cluster Migration Runbook

This document contains internal migration and cutover steps that are not needed in the public package README.

## Prerequisites

- Access to source and target Kubernetes contexts.
- Access to target cloud project IAM, KMS, Firestore, and GKE resources.
- Helm and kubectl configured locally.
- `sops`, `docker`, `gcloud`, and `ripgrep` (`rg`) installed locally.
- A working Python runtime for `gcloud`. On macOS, `export CLOUDSDK_PYTHON="$(which python3)"` was needed when the bundled wrapper picked an unsupported Python.

## Migration Checklist (Before First Target Deploy)

1. Confirm target kube context exists locally.

	`kubectl config get-contexts`

	Expected target context for cb cluster:

	`gke_cb-1003-1696_us-central1-b_cb-cluster`

2. Confirm you can talk to the target cluster.

	`kubectl --context gke_cb-1003-1696_us-central1-b_cb-cluster get nodes`

3. Copy TLS and ACME secret material from source cluster into target namespace.

	`./deployment/copy-otter-secrets.sh --source-context gke_data8x-scratch_us-central1_otter-cluster-v3 --target-context gke_cb-1003-1696_us-central1-b_cb-cluster --namespace otter-stdalone-prod`

4. Verify copied secrets and issuer in target cluster.

	`kubectl --context gke_cb-1003-1696_us-central1-b_cb-cluster -n otter-stdalone-prod get secret tls-secret letsencrypt`

	`kubectl --context gke_cb-1003-1696_us-central1-b_cb-cluster -n otter-stdalone-prod get issuer letsencrypt`

5. Reserve a global static IP in target project and set it in values.

	`PROJECT_ID=cb-1003-1696`

	`IP_NAME=otter-stdalone-prod-ip`

	`gcloud compute addresses create "$IP_NAME" --project="$PROJECT_ID" --global`

	`gcloud compute addresses describe "$IP_NAME" --project="$PROJECT_ID" --global --format="get(address)"`

	Set:

	`ingress.static_ip_name: otter-stdalone-prod-ip`

6. Review target override file.

	`otter-service-stdalone/values.cb-prod.yaml`

	Check:

	- `serviceAccount.annotations`
	- `otter_env.parameters.gcp_project_id`
	- `nodeSelector`
	- `frontendConfig.create`
	- `certificate.create`
	- `issuer.create` and `issuer.name`

	If selected pool is tainted or undersized, create dedicated pool and set node selector.

	`gcloud container node-pools create oss-production --project=cb-1003-1696 --cluster=cb-cluster --zone=us-central1-b --machine-type=e2-standard-8 --disk-type=pd-balanced --disk-size=100 --image-type=COS_CONTAINERD --num-nodes=1`

	Set:

	`nodeSelector.cloud.google.com/gke-nodepool: oss-production`

7. Configure Workload Identity and target service account annotation.

	`PROJECT_ID=cb-1003-1696`
	`NAMESPACE=otter-stdalone-prod`
	`KSA_NAME=otter-stdalone-k8-sa`
	`GSA_NAME=otter-stdalone-sa`
	`GSA_EMAIL="${GSA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"`

	`gcloud iam service-accounts create "$GSA_NAME" --project "$PROJECT_ID" --display-name "Otter standalone runtime SA"`

	`gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$GSA_EMAIL" --role="roles/datastore.user"`

	`gcloud iam service-accounts add-iam-policy-binding "$GSA_EMAIL" --project "$PROJECT_ID" --role="roles/iam.workloadIdentityUser" --member="serviceAccount:${PROJECT_ID}.svc.id.goog[$NAMESPACE/$KSA_NAME]"`

	Set in values:

	`serviceAccount.annotations.iam.gke.io/gcp-service-account: otter-stdalone-sa@cb-1003-1696.iam.gserviceaccount.com`

	Grant decrypt on target KMS key:

	`gcloud kms keys add-iam-policy-binding otter-service --project=cb-1003-1696 --location=global --keyring=cb-sops --member="serviceAccount:$GSA_EMAIL" --role="roles/cloudkms.cryptoKeyDecrypter"`

8. Create target-project KMS key and re-encrypt SOPS files.

	`PROJECT_ID=cb-1003-1696`
	`KMS_LOCATION=global`
	`KMS_KEYRING=cb-sops`
	`KMS_KEY=otter-service`
	`NEW_KMS="projects/$PROJECT_ID/locations/$KMS_LOCATION/keyRings/$KMS_KEYRING/cryptoKeys/$KMS_KEY"`

	`gcloud kms keyrings describe "$KMS_KEYRING" --project="$PROJECT_ID" --location="$KMS_LOCATION" >/dev/null 2>&1 || gcloud kms keyrings create "$KMS_KEYRING" --project="$PROJECT_ID" --location="$KMS_LOCATION"`

	`gcloud kms keys describe "$KMS_KEY" --project="$PROJECT_ID" --location="$KMS_LOCATION" --keyring="$KMS_KEYRING" >/dev/null 2>&1 || gcloud kms keys create "$KMS_KEY" --project="$PROJECT_ID" --location="$KMS_LOCATION" --keyring="$KMS_KEYRING" --purpose=encryption`

	`for f in src/otter_service_stdalone/secrets/gh_key.dev.yaml src/otter_service_stdalone/secrets/gh_key.local.yaml src/otter_service_stdalone/secrets/gh_key.prod.yaml src/otter_service_stdalone/secrets/gh_key.staging.yaml; do tmp="$(mktemp)"; sops -d "$f" | sops --encrypt --input-type yaml --output-type yaml --gcp-kms "$NEW_KMS" /dev/stdin > "$tmp" && mv "$tmp" "$f"; done`

	Rebuild and redeploy after re-encryption because these files are packaged in the image.

9. Create Firestore default database in target project if missing.

	`gcloud firestore databases create --project=cb-1003-1696 --location=us-west2 --type=firestore-native`

10. Render chart locally with target values.

	`helm template otter-srv otter-service-stdalone --values otter-service-stdalone/values.yaml --values otter-service-stdalone/values.prod.yaml --values otter-service-stdalone/values.cb-prod.yaml >/tmp/otter-render-cb.yaml`

	For the cb migration, we also had to override storage behavior in `otter-service-stdalone/values.cb-prod.yaml`:

	- `storageClass.create: false`
	- `storageClass.name: standard-rwo`
	- `volume_claims.create: true`

11. Keep current deployment untouched until target is healthy.

	If temporary old-key decrypt access was granted, remove after target is healthy on new key:

	`gcloud kms keys remove-iam-policy-binding otter-service --project=data8x-scratch --location=global --keyring=data8x-sops --member="serviceAccount:otter-stdalone-sa@cb-1003-1696.iam.gserviceaccount.com" --role="roles/cloudkms.cryptoKeyDecrypter"`

## Build And Release Notes

The main app image is built from the published Python package, not directly from the working tree. After changing packaged files such as `src/otter_service_stdalone/secrets/*.yaml` or `src/otter_service_stdalone/app.py`, you must build/publish a new version and deploy that new tag.

Recommended release flow used for this migration:

1. Switch to `dev`.
2. Bump version in `src/otter_service_stdalone/__init__.py`.
3. Run:

	`./deploy.sh build`

	This performs the standard package build, Twine upload, and both Docker image builds/pushes.

4. Switch back to `prod`.
5. Deploy the new version to the target cluster:

	`./deploy.sh --context gke_cb-1003-1696_us-central1-b_cb-cluster --values-file otter-service-stdalone/values.cb-prod.yaml`

6. Verify the deployment is using the expected image tags:

	`kubectl --context gke_cb-1003-1696_us-central1-b_cb-cluster -n otter-stdalone-prod get deploy otter-pod -o jsonpath='{.spec.template.spec.containers[*].image}{"\\n"}'`

If the app pod reports `ErrImagePull` for a new version while the cron image exists, the main app image tag did not reach the registry. Build/push the missing main image tag and redeploy.

## Ingress And Pre-Cutover Testing

We validated the target deployment in three stages.

### 1. Service IP Testing

Before ingress was ready, the app was reachable directly through the service load balancer IP:

	`kubectl --context gke_cb-1003-1696_us-central1-b_cb-cluster -n otter-stdalone-prod get svc otter-pod -o wide`

Use the service `EXTERNAL-IP` to test `/` and `/otterhealth`.

Note: OAuth cannot be fully validated against the raw IP because the app builds callback URLs from `GRADER_DNS`, so GitHub redirects back to the DNS hostname.

### 2. Ingress Provisioning

If ingress is created but shows no `ADDRESS` for an extended period:

1. Confirm GKE HTTP load balancing is enabled:

	`gcloud container clusters describe cb-cluster --project=cb-1003-1696 --zone=us-central1-b --format="value(addonsConfig.httpLoadBalancing.disabled)"`

2. If needed, enable it:

	`gcloud container clusters update cb-cluster --project=cb-1003-1696 --zone=us-central1-b --update-addons=HttpLoadBalancing=ENABLED`

3. Recreate ingress and redeploy once after addon reconciliation:

	`kubectl --context gke_cb-1003-1696_us-central1-b_cb-cluster -n otter-stdalone-prod delete ingress otter-stdalone-ingress`

	`./deploy.sh --context gke_cb-1003-1696_us-central1-b_cb-cluster --values-file otter-service-stdalone/values.cb-prod.yaml`

4. Watch until ingress gets the reserved address:

	`kubectl --context gke_cb-1003-1696_us-central1-b_cb-cluster -n otter-stdalone-prod get ingress otter-stdalone-ingress -w`

For the cb migration, ingress eventually attached the reserved static IP `34.117.205.145`.

### 3. Local Hosts-File Testing

Once ingress has the expected external address, you can validate the real hostname and OAuth flow locally before public DNS cutover.

1. Add a temporary hosts override:

	`sudo sh -c 'grep -v "grader.datahub.berkeley.edu" /etc/hosts > /tmp/hosts.tmp && echo "34.117.205.145 grader.datahub.berkeley.edu" >> /tmp/hosts.tmp && cat /tmp/hosts.tmp > /etc/hosts'`

2. Flush macOS caches:

	`sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder`

3. Verify local resolution:

	`dscacheutil -q host -a name grader.datahub.berkeley.edu`

4. Test `https://grader.datahub.berkeley.edu` in the browser, including OAuth login and upload flow.

5. Remove the temporary override after testing:

	`sudo sed -i '' '/grader.datahub.berkeley.edu/d' /etc/hosts`

	`sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder`

## Runtime Issues Observed During CB Migration

### Firestore Missing

If startup fails with a Firestore `404 The database (default) does not exist` error, create the default Firestore database in the target project before retrying.

### Upload Directory Failure

The cb migration exposed an upload bug where non-zip notebook uploads could fail with:

	`FileNotFoundError: [Errno 2] No such file or directory: '/tmp/uploads/<results_path>'`

The fix was to ensure `/tmp/uploads` exists before creating request-specific subdirectories. Deploy a version that includes that fix before validating upload behavior.

## Recommended Zero-Downtime Order

1. Do not change or delete anything on current cluster.
2. Deploy to target cluster with explicit context and override values.

	`./deploy.sh --context gke_cb-1003-1696_us-central1-b_cb-cluster --values-file otter-service-stdalone/values.cb-prod.yaml`

3. Verify target deployment health.

	`kubectl get pods,svc,ingress -n otter-stdalone-prod`

4. Post-deploy checks.

	`kubectl --context gke_cb-1003-1696_us-central1-b_cb-cluster -n otter-stdalone-prod get deploy otter-pod -o jsonpath='{.spec.template.spec.containers[*].image}{"\\n"}'`

	`kubectl --context gke_cb-1003-1696_us-central1-b_cb-cluster -n otter-stdalone-prod rollout status deployment otter-pod --timeout=240s`

	`kubectl --context gke_cb-1003-1696_us-central1-b_cb-cluster -n otter-stdalone-prod get pods`

	`kubectl --context gke_cb-1003-1696_us-central1-b_cb-cluster -n otter-stdalone-prod logs deployment/otter-pod -c otter-srv-stdalone --tail=80`

	`kubectl --context gke_cb-1003-1696_us-central1-b_cb-cluster -n otter-stdalone-prod logs deployment/otter-pod -c otter-srv-stdalone --tail=200 | rg -i "Key not decrypted|sops|cloudkms|Firestore|Traceback"`

5. Test target directly before cutover.

	Use service IP, ingress IP, or port-forwarding as appropriate.

	If testing via the real hostname before DNS cutover, use the temporary hosts-file override procedure above.

6. Confirm ingress address matches reserved static IP before DNS changes.

	`kubectl --context gke_cb-1003-1696_us-central1-b_cb-cluster -n otter-stdalone-prod get ingress otter-stdalone-ingress`

	`gcloud compute addresses describe otter-stdalone-prod-ip --project=cb-1003-1696 --global`

7. Only after validation, cut traffic by changing DNS/routing.
8. Keep old cluster running until rollback risk is acceptable.

Important: deploying to a new cluster does not by itself take down old deployment. Cutover happens when external routing (typically DNS) changes.
