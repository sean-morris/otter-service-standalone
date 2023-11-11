version=$(<src/otter_service_stdalone/__init__.py)
version=${version##__version__ = }
version=`sed -e 's/^"//' -e 's/"$//' <<<"$version"`
branch_name=$(git symbolic-ref -q HEAD)
branch_name=${branch_name##refs/heads/}
branch_name=${branch_name:-HEAD}
if [ "$branch_name" == "dev" ] && [ "$1" == "build" ]; then
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
fi
ns=$(kubectl get namespaces | grep otter-stdalone-${branch_name})
if [[ $ns == *"otter-stdalone-${branch_name}"* ]]; then
    helm upgrade --install otter-srv --set otter_srv_stdalone.tag=$version --set otter_srv_remove_uploads_cron.tag=$version otter-service-stdalone --values otter-service-stdalone/values.yaml --values otter-service-stdalone/values.$branch_name.yaml --namespace otter-stdalone-$branch_name --skip-crds 
else
    # Use this when namespace completely deleted
    helm install otter-srv --set otter_srv_stdalone.tag=$version --set otter_srv_remove_uploads_cron.tag=$version otter-service-stdalone --values otter-service-stdalone/values.yaml --values otter-service-stdalone/values.$branch_name.yaml --create-namespace --namespace otter-stdalone-$branch_name --skip-crds 
fi

