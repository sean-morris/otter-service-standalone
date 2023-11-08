version=$(<src/otter_service_stdalone/__init__.py)
version=${version##__version__ = }
version=`sed -e 's/^"//' -e 's/"$//' <<<"$version"`
lsof -t -i:8080 -i:4401 -i:4501 -i:4400 -i:9000 -i:9099 -i:9199 -i:9090 | xargs kill -9
firebase emulators:start --only firestore --project data8x-scratch &
python3 -m build
python3 -m pip install dist/otter_service_stdalone-${version}.tar.gz --force
yq eval ".services.app.build.args.OTTER_SERVICE_STDALONE_VERSION=\"$version\"" -i docker-compose.yml
docker-compose build
rm -rf ./otter-grader
docker-compose up
