branch_name=$(git symbolic-ref -q HEAD)
branch_name=${branch_name##refs/heads/}
branch_name=${branch_name:-HEAD}
helm upgrade --install otter-srv otter-service-stdalone --values otter-service-stdalone/values.yaml --values otter-service-stdalone/values.dev.yaml --namespace otter-stdalone-$branch_name

