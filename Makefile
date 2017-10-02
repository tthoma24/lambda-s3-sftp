# This Makefile is designed to be run from within a docker container
# based on the Dockerfile in this project. You can run the make commands
# by mounting this directory into the container as /lambda:
#
#    $ cd path/to/this/project
#    $ docker build -t packager .
#    $ docker run --rm -v $(pwd):/lambda packager [package|compile]
#
# The output from running the 'package' command is a single package.zip
# file that contains everything required to run the Lambda function. This
# should be uploaded to AWS.
#
# restore local file system to pre-packaging state, clear out the
# virtualenv and dist folder and remove any existing package.zip
clean:
	rm -rf .venv
	rm -rf dist/
	rm -f package.zip

# create a new virtualenv and install project requirements into it
install:
	virtualenv -p python3 .venv
	# must run on same line to ensure virtualenv is active
	source .venv/bin/activate &&  pip3 install -r requirements.txt

# zip up the contents of the virtualenv site-packages and py scripts
package: clean install
	mkdir -p dist
	cp *.py dist/
	cp -r .venv/lib/python3.6/site-packages/. dist/
	# package.zip is the file to upload to Lambda
	cd dist; zip -r ../package.zip .

# run pip-compile to re-generate the requirements.txt file
compile:
	# compile the set of requirements from requirements.in to requirements.txt
	# must set locale, see http://click.pocoo.org/5/python3/ for details
	LC_ALL=en_US.utf8 pip-compile --output-file requirements.txt requirements.in
