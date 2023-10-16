# BloodHound automation
Automatically run and populate a new instance of BH CE.
Only works on Linux (tested on Ubuntu 22.04). 

## How to run
```
usage: test.py [-h] -np NEO4J_PORT [-wp WEB_PORT] -z ZIP [-P PASSWORD]

Automatically deploy a bloodhound instance and populate it with the SharpHound data

options:
  -h, --help            show this help message and exit
  -np NEO4J_PORT, --neo4j-port NEO4J_PORT
                        The custom port for the neo4j container
  -wp WEB_PORT, --web-port WEB_PORT
                        The custom port for the web container (default: 8080)
  -z ZIP, --zip ZIP     The zip file from SharpHound containing the json extracts
  -P PASSWORD, --password PASSWORD
                        Custom password for the web interface (12 chars min. & all types of characters)
```

You can edit the docker file in the template folder for more customization.

By default, it starts three containers. When the script is done, you can shutdown both the web and the postgresql containers if you only wish to keep the neo4j one.


## Requirements

You need docker and docker-compose installed.
