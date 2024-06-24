# otter-service-standalone

## Use: [Instructions](https://docs.google.com/document/d/1Hih6No17ffvLcNImf8uOueRSo0UT-fvEIDMFUhfLSPk/edit)

## Deployment
The cloud deployment is configured using a helm chart. The branch you are on(e.g. dev, staging, prod) determines what environment/k8 namespace you deploy into.

See the ./deploy.sh for details. The script will determine the branch and 
deploy properly. If you are on the dev branch and pass "build" as an argument,
(e.g. `./deploy.sh build`) then the docker image used on the container is built and pushed to the gcloud image repository (gcr.io). You need to be sure to bump
the version number in src/otter_service_stdalone/__init__.py before a new build.

## Version
A git tag with the version is pushed to git whenever the version is bumped and
deployed in production. `git tag` will show you the format of the tag(e.g. 0.0.30)

## Local Dev:
Execute: sh deployment/local/build.sh
- FireStore: http://127.0.0.1:4007/firestore/
- App: http://127.0.0.1/
