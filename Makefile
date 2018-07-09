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
# should be uploaded to AWS. If you have the aws-sdk installed and configured
# you can use `make upload` to upload package.zip directly.
#

# restore local file system to pre-packaging state
clean:
	rm -rf package/
	rm -f package.zip

package: clean
	# install dependencies into package directory
	python3 -m pip install -r requirements.txt -t package
	# copy in the .py source file(s)
	cp *.py package/
	# zip up the entire directory into package.zip
	cd package; zip -r ../package.zip .
	# tidy up
	rm -rf package/

# run pip-compile to re-generate the requirements.txt file
compile:
	# compile the set of requirements from requirements.in to requirements.txt
	# must set locale, see http://click.pocoo.org/5/python3/ for details
	python3 -m pip install -U pip pip-tools
	pip-compile --output-file requirements.txt requirements.in

upload:
	aws lambda update-function-code --function-name $(ARN) --zip-file fileb://package.zip