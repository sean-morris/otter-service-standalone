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
    docker build --target image-cloud --build-arg BUILD_VERSION=cloud -t gcr.io/data8x-scratch/otter-srv-stdalone:$version -t gcr.io/data8x-scratch/otter-srv-stdalone . 
    docker push gcr.io/data8x-scratch/otter-srv-stdalone:$version
    docker push gcr.io/data8x-scratch/otter-srv-stdalone
fi
helm upgrade --install otter-srv --set otter_srv_stdalone.tag=$version otter-service-stdalone --values otter-service-stdalone/values.yaml --values otter-service-stdalone/values.$branch_name.yaml --namespace otter-stdalone-$branch_name --skip-crds 

#helm install otter-srv --set otter_srv_stdalone.tag=0.1.0 otter-service-stdalone --values otter-service-stdalone/values.yaml --values otter-service-stdalone/values.dev.yaml --create-namespace --namespace otter-stdalone-dev --skip-crds 

