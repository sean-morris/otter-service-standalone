#!/usr/bin/env bash

version=$(<src/otter_service_stdalone/__init__.py)
version=${version##__version__ = }
version=`sed -e 's/^"//' -e 's/"$//' <<<"$version"`
branch_name=$(git symbolic-ref -q HEAD)
branch_name=${branch_name##refs/heads/}
branch_name=${branch_name:-HEAD}

build_images=false
kube_context=${KUBE_CONTEXT:-}
target_namespace=${KUBE_NAMESPACE:-}
release_name=${HELM_RELEASE_NAME:-otter-srv}
extra_values_file=${HELM_EXTRA_VALUES_FILE:-}

while [[ $# -gt 0 ]]; do
    case "$1" in
        build)
            build_images=true
            shift
            ;;
        --context)
            kube_context="$2"
            shift 2
            ;;
        --namespace)
            target_namespace="$2"
            shift 2
            ;;
        --release)
            release_name="$2"
            shift 2
            ;;
        --values-file)
            extra_values_file="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1" >&2
            echo "Usage: ./deploy.sh [build] [--context KUBE_CONTEXT] [--namespace NAMESPACE] [--release RELEASE_NAME] [--values-file VALUES_FILE]" >&2
            exit 1
            ;;
    esac
done

if [[ -z "$target_namespace" ]]; then
    target_namespace="otter-stdalone-$branch_name"
fi

extra_values_args=()
if [[ -n "$extra_values_file" ]]; then
    extra_values_args+=(--values "$extra_values_file")
fi

kubectl_args=()
helm_args=()
if [[ -n "$kube_context" ]]; then
    kubectl config use-context "$kube_context"
    kubectl_args+=(--context "$kube_context")
    helm_args+=(--kube-context "$kube_context")
fi

echo "$branch_name"
if [ "$branch_name" == "dev" ] && [ "$build_images" = true ]; then
    #Temp while building otter-grader locally
    #cp -r ../otter-grader ./otter-grader
    
    python3 -m build
    python3 -m pip install dist/otter_service_stdalone-${version}.tar.gz --force
    python3 -m twine upload dist/*$version*
    
    #for local dev
    yq eval ".services.app.build.args.OTTER_SERVICE_STDALONE_VERSION=\"$version\"" -i docker-compose.yml
    # if breaks on Permission denied run: gcloud auth login
    # build and push otter-srv-stdalone
    docker build --target image-cloud --build-arg BUILD_VERSION=cloud --build-arg OTTER_SERVICE_STDALONE_VERSION=$version -t gcr.io/data8x-scratch/otter-srv-stdalone:$version -t gcr.io/data8x-scratch/otter-srv-stdalone . 
    docker push gcr.io/data8x-scratch/otter-srv-stdalone:$version
    docker push gcr.io/data8x-scratch/otter-srv-stdalone


    # build and push otter-srv-stdalone-remove-uploads-cron
    docker build -t gcr.io/data8x-scratch/otter-srv-stdalone-remove-uploads-cron:$version -t gcr.io/data8x-scratch/otter-srv-stdalone-remove-uploads-cron -f Dockerfile-remove-uploads-cron .
    docker push gcr.io/data8x-scratch/otter-srv-stdalone-remove-uploads-cron:$version
    docker push gcr.io/data8x-scratch/otter-srv-stdalone-remove-uploads-cron
    #rm -rf ./otter-grader
elif [ "$branch_name" != "dev" ]; then
    if kubectl "${kubectl_args[@]}" get namespace "$target_namespace" >/dev/null 2>&1; then
        helm upgrade --install "$release_name" otter-service-stdalone --set otter_srv_stdalone.tag=$version --set otter_srv_remove_uploads_cron.tag=$version --values otter-service-stdalone/values.yaml --values otter-service-stdalone/values.$branch_name.yaml "${extra_values_args[@]}" --namespace "$target_namespace" --skip-crds "${helm_args[@]}"
    else
        # Use this when namespace completely deleted
        helm install "$release_name" otter-service-stdalone --set otter_srv_stdalone.tag=$version --set otter_srv_remove_uploads_cron.tag=$version --values otter-service-stdalone/values.yaml --values otter-service-stdalone/values.$branch_name.yaml "${extra_values_args[@]}" --create-namespace --namespace "$target_namespace" --skip-crds "${helm_args[@]}"
    fi
fi
