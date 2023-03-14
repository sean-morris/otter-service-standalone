version=$(<src/otter_service_stdalone/__init__.py)
version=${version##__version__ = }
version=`sed -e 's/^"//' -e 's/"$//' <<<"$version"`
firebase emulators:start --only firestore --project data8x-scratch &
python3 -m build
python3 -m pip install dist/otter_service_stdalone-${version}.tar.gz --force
yq eval ".services.app.build.args.OTTER_SERVICE_STDALONE_VERSION=\"$version\"" -i docker-compose.yml
docker-compose --no-cache build
rm -rf ./otter-grader
docker-compose up
