#!/usr/bin/env bash


# -------------
# INITIAL SETUP
# -------------
echo 'initializing...'
# Switch to current directory and update apt repository
cd "${0%/*}"
apt-get update


# ---------
# VARIABLES
# ---------
STANFORD_ZIP_NAME="stanford.zip"
ENV_DIRNAME="env"
LIB_DIRNAME="lib"
STANFORD_POSTAGGER_URL="https://nlp.stanford.edu/software/stanford-postagger-2017-06-09.zip"
MD5_HASH="607c78634a6aa1f1eebd7f375f720867"
USERNAME="semantic_kb"
PASSWORD="semantic_kb"


# ----------------------
# REQUIREMENT - PYTHON 3
# ----------------------
# Check if Python3 is available. Install Python3 if not found.
if [[ $(which python3) != "" ]]; then
    echo -e "\nPython3 installed - OK"
else
    echo "Python3 not installed! Installing..."
    apt install python3
    echo "Python3 Installed!"
fi

# Install Python3-dev
echo "Installing Python3-dev..."
apt install python3-dev
echo "Python3-dev Installed!"


# ---------------------
# REQUIREMENT - MONGODB
# ---------------------
# Check if MongoDB is installed
if [[ $(which mongo) != "" ]]; then
    echo -e "\nMongoDB installed - OK"
else
    echo "MongoDB not installed! Installing..."
    apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 0C49F3730359A14518585931BC711F9BA15703C6
    echo "deb [ arch=amd64 ] http://repo.mongodb.org/apt/ubuntu "$(lsb_release -cs)"/mongodb-org/3.4 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-3.4.list
    apt-get update
    apt-get install -y mongodb-org
    echo "MongoDB Installed!"

    echo "Starting MongoDB..."
    service mongod start
    echo "MongoDB Started!"
fi


# ------------------------
# REQUIREMENT - POSTGRESQL
# ------------------------
# Check if postgres is installed
if [[ $(which psql) != "" ]]; then
    echo -e "\nPostgreSQL installed - OK"
else
    echo "PostgreSQL not installed! Installing..."
    apt-get install postgresql postgresql-contrib
    echo "PostgreSQL Installed!"

    echo "Setting up user account for KB access. Please enter password as $PASSWORD when prompted..."
    sudo -u postgres createuser -sdP $USERNAME
fi


# -------------
# CONFIGURATION
# -------------
# Remove any existing env/ and lib/ directories
if [[ $(ls -d */ | grep ${ENV_DIRNAME}) == ${ENV_DIRNAME}/ ]]; then
    echo "$ENV_DIRNAME/ found. removing..."
    rm -r ${ENV_DIRNAME}
fi
if [[ $(ls -d */ | grep ${LIB_DIRNAME}) == ${LIB_DIRNAME}/ ]]; then
    echo "$LIB_DIRNAME/ found. removing..."
    rm -r ${LIB_DIRNAME}
fi

# Create new directories
mkdir ${ENV_DIRNAME}
mkdir ${LIB_DIRNAME}

# Download stanford zip if it does not exist
if [[ ($(ls | grep ${STANFORD_ZIP_NAME}) == ${STANFORD_ZIP_NAME}) && ($(md5sum ${STANFORD_ZIP_NAME} | grep -o ${MD5_HASH}) != "") ]]; then
    echo "File found - $STANFORD_ZIP_NAME. Skipping download..."
else
    rm -f ${STANFORD_ZIP_NAME}
    curl ${STANFORD_POSTAGGER_URL} > ${STANFORD_ZIP_NAME}
fi

# Unzip contents to lib folders
echo "Unzipping contents from $STANFORD_ZIP_NAME to $LIB_DIRNAME/..."
unzip -p ${STANFORD_ZIP_NAME} stanford-postagger-2017-06-09/stanford-postagger.jar > ${LIB_DIRNAME}/stanford-postagger.jar
unzip -p ${STANFORD_ZIP_NAME} stanford-postagger-2017-06-09/models/english-bidirectional-distsim.tagger > ${LIB_DIRNAME}/english-bidirectional-distsim.tagger
unzip -p ${STANFORD_ZIP_NAME} stanford-postagger-2017-06-09/models/english-left3words-distsim.tagger > ${LIB_DIRNAME}/english-left3words-distsim.tagger

# Check if pip installed, else install it
if [[ $(which pip3) != "" ]]; then
    echo "pip installed - OK"
else
    echo "pip not installed. Installing..."
    python3 get-pip.py
fi

# Check if virtualenv installed, else install it
if [[ $(which virtualenv) != "" ]]; then
    echo "virtualenv installed - OK"
else
    echo "virtualenv not installed. Installing..."
    pip3 install virtualenv
fi

# Create virtualenv in project directory
echo "creating virtual environment..."
virtualenv env -p python3

# Activate virtual environment and install dependencies
echo "activating virtual environment..."
source env/bin/activate
echo "installing project requirements..."
pip install -U -r requirements.txt

# Download NLTK dependencies inside virtual environment
echo "configuring nltk data"
python config.py
echo "closing virtual environment..."
deactivate
echo "DONE!"