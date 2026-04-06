# otter-service-standalone

## Use: [Instructions](https://docs.google.com/document/d/1Hih6No17ffvLcNImf8uOueRSo0UT-fvEIDMFUhfLSPk/edit)

## Deployment
The cloud deployment is configured using a helm chart. The branch you are on(e.g. dev, staging, prod) determines what environment/k8 namespace you deploy into.

See the ./deploy.sh for details. The script will determine the branch and 
deploy properly. If you are on the dev branch and pass "build" as an argument,
(e.g. `./deploy.sh build`) then the docker image used on the container is built and pushed to the gcloud image repository (gcr.io). You need to be sure to bump
the version number in src/otter_service_stdalone/__init__.py before a new build.

To deploy to a different Kubernetes cluster, pass an explicit kube context instead of relying on your current default context. The script will first run `kubectl config use-context` and then use that same context for kubectl and helm:

`./deploy.sh --context my-other-cluster-context`

You can also override the namespace or Helm release name when needed:

`./deploy.sh --context my-other-cluster-context --namespace otter-stdalone-prod --release otter-srv`

You can layer a cluster-specific Helm override on top of the normal branch values:

`./deploy.sh --context my-other-cluster-context --values-file otter-service-stdalone/values.cb-prod.yaml`

The same values can be provided via environment variables:

`KUBE_CONTEXT=my-other-cluster-context KUBE_NAMESPACE=otter-stdalone-prod HELM_EXTRA_VALUES_FILE=otter-service-stdalone/values.cb-prod.yaml ./deploy.sh`

If you are migrating the standalone service to a different cluster and need to preserve TLS and ACME secret material, copy the live Kubernetes secrets before running Helm:

`./deployment/copy-otter-secrets.sh --source-context gke_data8x-scratch_us-central1_otter-cluster-v3 --target-context gke_cb-1003-1696_us-central1-b_cb-cluster --namespace otter-stdalone-prod`

The chart now supports clusters that do not expose the GKE `FrontendConfig` resource and deployments that use an existing TLS secret instead of creating a new cert-manager `Certificate`. Set `frontendConfig.create=false` and `certificate.create=false` in your target values when needed.

For the cb cluster specifically, a starter override file is included at `otter-service-stdalone/values.cb-prod.yaml`. It disables FrontendConfig and cert creation, clears source-cluster static IP assumptions, switches the app project id to `cb-1003-1696`, and lowers the dind resource requests to fit the observed target node sizes.

## Safe Cluster Migration

Review and complete this checklist before the first `deploy.sh` run against the target cluster.

### Step By Step Before Running deploy.sh

1. Confirm the target kube context exists locally.

	`kubectl config get-contexts`

	Expected target context for the cb cluster:

	`gke_cb-1003-1696_us-central1-b_cb-cluster`

2. Confirm you can talk to the target cluster.

	`kubectl --context gke_cb-1003-1696_us-central1-b_cb-cluster get nodes`

3. Copy TLS and ACME secret material from the current source cluster into the target namespace.

	`./deployment/copy-otter-secrets.sh --source-context gke_data8x-scratch_us-central1_otter-cluster-v3 --target-context gke_cb-1003-1696_us-central1-b_cb-cluster --namespace otter-stdalone-prod`

4. Verify the copied secrets and issuer exist on the target cluster.

	`kubectl --context gke_cb-1003-1696_us-central1-b_cb-cluster -n otter-stdalone-prod get secret tls-secret letsencrypt`

	`kubectl --context gke_cb-1003-1696_us-central1-b_cb-cluster -n otter-stdalone-prod get issuer letsencrypt`

5. Reserve a global static IP in the target project before deploy, then set that name in `ingress.static_ip_name`.

	Example commands:

	`PROJECT_ID=cb-1003-1696`

	`IP_NAME=otter-stdalone-prod-ip`

	`gcloud compute addresses create "$IP_NAME" --project="$PROJECT_ID" --global`

	`gcloud compute addresses describe "$IP_NAME" --project="$PROJECT_ID" --global --format="get(address)"`

	Then set:

	`ingress.static_ip_name: otter-stdalone-prod-ip`

6. Review the target override file before deploy.

	File to review:

	`otter-service-stdalone/values.cb-prod.yaml`

	Check these settings carefully:

	- `serviceAccount.annotations`
	- `otter_env.parameters.gcp_project_id`
	- `nodeSelector`
	- `frontendConfig.create`
	- `certificate.create`
	- `issuer.create` and `issuer.name`

	If the target pool selected by `nodeSelector` is tainted or does not have enough capacity, create a dedicated pool first and point `nodeSelector` at it. For the cb cluster, we mirrored the old prod pool shape with a single-node pool named `oss-production`:

	`gcloud container node-pools create oss-production --project=cb-1003-1696 --cluster=cb-cluster --zone=us-central1-b --machine-type=e2-standard-8 --disk-type=pd-balanced --disk-size=100 --image-type=COS_CONTAINERD --num-nodes=1`

	Then set:

	`nodeSelector.cloud.google.com/gke-nodepool: oss-production`

7. If the application needs Google Cloud access from inside the pod, configure Workload Identity and set a valid target-cluster service account annotation before deploy.

	Example commands (cb cluster/project):

	`PROJECT_ID=cb-1003-1696`
	`NAMESPACE=otter-stdalone-prod`
	`KSA_NAME=otter-stdalone-k8-sa`
	`GSA_NAME=otter-stdalone-sa`
	`GSA_EMAIL="${GSA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"`

	`gcloud iam service-accounts create "$GSA_NAME" --project "$PROJECT_ID" --display-name "Otter standalone runtime SA"`

	`gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$GSA_EMAIL" --role="roles/datastore.user"`

	`gcloud iam service-accounts add-iam-policy-binding "$GSA_EMAIL" --project "$PROJECT_ID" --role="roles/iam.workloadIdentityUser" --member="serviceAccount:${PROJECT_ID}.svc.id.goog[$NAMESPACE/$KSA_NAME]"`

	Then set this in `otter-service-stdalone/values.cb-prod.yaml`:

	`serviceAccount.annotations.iam.gke.io/gcp-service-account: otter-stdalone-sa@cb-1003-1696.iam.gserviceaccount.com`

	If you leave `serviceAccount.annotations` empty, that is only correct if the target cluster already provides another working credential path.

8. Create the default Firestore database in the target project if it does not already exist.

	This service writes startup and runtime logs to Firestore, and the app will crash on boot if `(default)` is missing in the target project.

	Example command (matching the source deployment's mode/location):

	`gcloud firestore databases create --project=cb-1003-1696 --location=us-west2 --type=firestore-native`

9. Render the chart locally once with the target values to catch obvious configuration mistakes before the real deploy.

	`helm template otter-srv otter-service-stdalone --values otter-service-stdalone/values.yaml --values otter-service-stdalone/values.prod.yaml --values otter-service-stdalone/values.cb-prod.yaml >/tmp/otter-render-cb.yaml`

10. Keep the current deployment untouched until the new cluster is healthy and tested.

Recommended order of operations for a zero-downtime migration:

1. Do not change or delete anything on the current cluster.
2. Deploy to the target cluster explicitly with the target context and override values:
	`./deploy.sh --context gke_cb-1003-1696_us-central1-b_cb-cluster --values-file otter-service-stdalone/values.cb-prod.yaml`
3. Verify the target deployment is healthy with `kubectl get pods,svc,ingress -n otter-stdalone-prod` on the target cluster.
4. Test the target deployment directly before cutover, using its service external IP, ingress IP, or port-forwarding.
5. Only after validation, cut traffic over by changing DNS or whichever external routing points users to the current cluster.
6. Leave the old cluster running until the new cluster has served production traffic successfully and rollback risk is acceptable.

Important: deploying the same app into the new cluster does not by itself take down the old deployment. The real cutover point is external traffic routing, typically DNS. As long as DNS still points to the current cluster, production traffic stays on the current deployment.

## Version
A git tag with the version is pushed to git whenever the version is bumped and
deployed in production. `git tag` will show you the format of the tag(e.g. 0.0.30)

## Local Dev:
Execute: sh deployment/local/build.sh
- FireStore: http://127.0.0.1:4007/firestore/
- App: http://127.0.0.1/
