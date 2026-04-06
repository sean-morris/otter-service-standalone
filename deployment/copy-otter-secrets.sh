#!/usr/bin/env bash

set -euo pipefail

source_context=""
target_context=""
namespace="otter-stdalone-prod"
copy_issuer=true

usage() {
    echo "Usage: ./deployment/copy-otter-secrets.sh --source-context SOURCE --target-context TARGET [--namespace NAMESPACE] [--skip-issuer]" >&2
}

require_arg() {
    local flag="$1"
    local value="${2:-}"
    if [[ -z "$value" ]]; then
        echo "Missing value for $flag" >&2
        usage
        exit 1
    fi
}

copy_resource() {
    local resource_type="$1"
    local resource_name="$2"

    kubectl --context "$source_context" -n "$namespace" get "$resource_type" "$resource_name" -o json \
        | python3 -c '
import json, sys
target_namespace = sys.argv[1]
resource = json.load(sys.stdin)
resource.pop("status", None)
metadata = resource.setdefault("metadata", {})
for key in [
    "creationTimestamp",
    "deletionGracePeriodSeconds",
    "deletionTimestamp",
    "generateName",
    "generation",
    "managedFields",
    "ownerReferences",
    "resourceVersion",
    "selfLink",
    "uid",
]:
    metadata.pop(key, None)
annotations = metadata.get("annotations") or {}
annotations.pop("kubectl.kubernetes.io/last-applied-configuration", None)
if annotations:
    metadata["annotations"] = annotations
else:
    metadata.pop("annotations", None)
metadata["namespace"] = target_namespace
print(json.dumps(resource))
' "$namespace" \
        | kubectl --context "$target_context" apply -f -
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --source-context)
            require_arg "$1" "${2:-}"
            source_context="$2"
            shift 2
            ;;
        --target-context)
            require_arg "$1" "${2:-}"
            target_context="$2"
            shift 2
            ;;
        --namespace)
            require_arg "$1" "${2:-}"
            namespace="$2"
            shift 2
            ;;
        --skip-issuer)
            copy_issuer=false
            shift
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage
            exit 1
            ;;
    esac
done

if [[ -z "$source_context" || -z "$target_context" ]]; then
    usage
    exit 1
fi

kubectl --context "$target_context" get namespace "$namespace" >/dev/null 2>&1 || kubectl --context "$target_context" create namespace "$namespace"

copy_resource secret tls-secret
copy_resource secret letsencrypt

if [[ "$copy_issuer" == true ]]; then
    copy_resource issuer letsencrypt
fi

echo "Copied tls-secret, letsencrypt, and issuer resources into $namespace on $target_context"