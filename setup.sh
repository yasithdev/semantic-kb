#!/usr/bin/env bash
echo 'initializing...'
STANFORD_ZIP_NAME="stanford.zip"
ENV_DIRNAME="env"
LIB_DIRNAME="lib"
STANFORD_POSTAGGER_URL="https://nlp.stanford.edu/software/stanford-postagger-2017-06-09.zip"
MD5_HASH="607c78634a6aa1f1eebd7f375f720867"

# Switch to current directory
cd "${0%/*}"

# Check if Python3 is available, or exit if not found.
if [[ $(which python3) != "" ]]; then
    echo "python3 installed - OK"
else
    echo "Error - python3 not installed. Installing..."
    apt install python3
fi

# Install python3 headers
apt-get update
apt install python3-dev

# remove any existing env/ and lib/ directories
if [[ $(ls -d */ | grep ${ENV_DIRNAME}) == ${ENV_DIRNAME}/ ]]; then
    echo "$ENV_DIRNAME/ found. removing..."
    rm -r ${ENV_DIRNAME}
fi
if [[ $(ls -d */ | grep ${LIB_DIRNAME}) == ${LIB_DIRNAME}/ ]]; then
    echo "$LIB_DIRNAME/ found. removing..."
    rm -r ${LIB_DIRNAME}
fi

# create new directories
mkdir ${ENV_DIRNAME}
mkdir ${LIB_DIRNAME}

# download stanford zip if it does not exist
if [[ ($(ls | grep ${STANFORD_ZIP_NAME}) == ${STANFORD_ZIP_NAME}) && ($(md5sum ${STANFORD_ZIP_NAME} | grep -o ${MD5_HASH}) != "") ]]; then
    echo "File found - $STANFORD_ZIP_NAME. Skipping download..."
else
    rm -f ${STANFORD_ZIP_NAME}
    curl ${STANFORD_POSTAGGER_URL} > ${STANFORD_ZIP_NAME}
fi

# unzip contents to lib folders
echo "Unzipping contents from $STANFORD_ZIP_NAME to $LIB_DIRNAME/..."
unzip -p ${STANFORD_ZIP_NAME} stanford-postagger-2017-06-09/stanford-postagger.jar > ${LIB_DIRNAME}/stanford-postagger.jar
unzip -p ${STANFORD_ZIP_NAME} stanford-postagger-2017-06-09/models/english-bidirectional-distsim.tagger > ${LIB_DIRNAME}/english-bidirectional-distsim.tagger
unzip -p ${STANFORD_ZIP_NAME} stanford-postagger-2017-06-09/models/english-left3words-distsim.tagger > ${LIB_DIRNAME}/english-left3words-distsim.tagger

# check if pip installed, else install it
if [[ $(which pip3) != "" ]]; then
    echo "pip installed - OK"
else
    echo "pip not installed. Installing..."
    python3 get-pip.py
fi

# check if virtualenv installed, else install it
if [[ $(which virtualenv) != "" ]]; then
    echo "virtualenv installed - OK"
else
    echo "virtualenv not installed. Installing..."
    pip3 install virtualenv
fi

# create virtualenv in project directory
echo "creating virtual environment..."
virtualenv env -p python3

# activate virtual environment and install dependencies
echo "activating virtual environment..."
source env/bin/activate
echo "installing project requirements..."
pip install -U -r requirements.txt
echo "configuring nltk data"
python config.py
echo "closing virtual environment..."
deactivate
echo "DONE!"