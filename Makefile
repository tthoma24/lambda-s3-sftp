# This Makefile is designed to be run from within a docker container
# based on the yunojuno/amazonlinux-lambda-python3 image. You can run
# the make commands by mounting this directory into the container as
# /lambda:
#
#     $ docker run --rm -v $(pwd):/lambda yunojuno/amazonlinux-lambda-python3 package
#
install:
	pip3 install -r requirements.txt

package: install
	mkdir -p dist
	cp *.py dist/
	cp -r /.venv/lambda/lib/python3.6/site-packages/. dist/
	cd dist; zip -r ../package.zip .

clean:
	rm -rf dist/
	rm package.zip

compile:
	# compile the set of requirements
	# must set locale, see http://click.pocoo.org/5/python3/ for details
	LC_ALL=en_US.utf8 pip-compile --output-file requirements.txt requirements.in
