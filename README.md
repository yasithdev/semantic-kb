# Install Requirements

## Python 3.x.x
``` shell
sudo apt-get update
sudo apt-get install python3
```

## Python 3.x.x-dev
``` shell
sudo apt-get update
sudo apt-get install python3-dev
```

## MongoDB v3.x
``` shell
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 0C49F3730359A14518585931BC711F9BA15703C6
echo "deb [ arch=amd64 ] http://repo.mongodb.org/apt/ubuntu "$(lsb_release -cs)"/mongodb-org/3.4 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-3.4.list
sudo apt-get update
sudo apt-get install -y mongodb-org
```

## PostgreSQL
``` shell
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
```

### Create PostgreSQL Role for KB access
``` shell
sudo -u postgres createuser -sdP semantic_kb
```
When prompted for a password, type password as ```semantic_kb```.
If a different password is entered, update the PASSWORD variable in ```core/api/postgres_api.py``` with that password.

