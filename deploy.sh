branch_name=$(git symbolic-ref -q HEAD)
branch_name=${branch_name##refs/heads/}
branch_name=${branch_name:-HEAD}
if [ "$branch_name" == "dev" ] && [ "$1" == "build" ]; then
    python3 -m build
    python3 -m pip install dist/otter_service_stdalone-${version}.tar.gz --force
    python3 -m twine upload dist/*$version*
    
    yq eval ".services.app.build.args.OTTER_SERVICE_STDALONE_VERSION=\"$version\"" -i docker-compose.yml
    # if breaks on Permission denied run: gcloud auth login
    gcloud builds submit --substitutions=_GITHUB_KEY=$github_key,_TAG_NAME=$version --config cloudbuild.yaml
fi
helm upgrade --install otter-srv otter-service-stdalone --values otter-service-stdalone/values.yaml --values otter-service-stdalone/values.$branch_name.yaml --namespace otter-stdalone-$branch_name

