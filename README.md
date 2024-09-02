# BloodHound automation
Automatically run and populate a new instance of BH CE.
Tested on Ubuntu 22.04 and MacOS. 

## How to run
```
usage: bloodhound-automation.py [-h] {list,start,data,stop,delete} ...

Automatically deploy a bloodhound instance and populate it with the SharpHound data

positional arguments:
  {list,start,data,stop,delete,clear}
                        Action to run
    list                List existing projects
    start               Create a new project or start an existing one
    data                Feed data into an existing project
    stop                Stop a running project (Not implemented yet)
    delete              Delete a project
    clear               Clear a project

options:
  -h, --help            show this help message and exit
```

You can edit the docker file in the template folder for more customization.

By default, it starts three containers. When the script is done, you can shutdown both the web and the postgresql containers if you only wish to keep the neo4j one.


## Example

### Create and start project
```
$ python3 bloodhound-automation.py start -bp 10001 -np 10501 -wp 8001 my_project

[*] Created ***/bloodhound-automation/projects directory
[*] Created my_project directory
[+] Docker setup done
[*] Launching BloodHound...
The docker log are accessible in the */bloodhound-automation/projects/my_project/logs.txt file
[+] Found admin temporary password : Hq2gYOOGgcRDfqk9xutVoU7LAQ4O0W2x
[+] Web server launched successfully
[+] Found JWT token : eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MDA4NzM3NTcsImp0aSI6IjEiLCJpYXQiOjE3MDA4NDQ5NTcsInN1YiI6IjZiM2JmMDc2LTE0YmEtNDE5Mi05OTNkLTQ4ZjBmMDljMDI3MyJ9.jwD8mGxAPIExOP_Xd1S1fWou85N2KqRGpXduH6AIWcc
[+] UserID found : 6b3bf076-14ba-4192-993d-48f0f09c0273
[+] Changed admin password to : Chien2Sang<3

        #############################################################################
        #                                                                           #
        #              Your neo4j instance was successfully populated               #
        #                        and is now accessible at :                         #
        #                             localhost:10001                               #
        #                             username : neo4j                              #
        #                             password : neo5j                              # 
        #                                                                           #
        #                 The BloodHound Web GUI is accessible at :                 #
        #                         http://localhost:8001                             #
        #                     with the following credentials :                      #
        #                         username : admin                                  #
        #                         password : Chien2Sang<3                           #
        #                                                                           #
        #############################################################################
          
```

### Import data

```
$ python3 bloodhound-automation.py data -z test.zip my_project

[+] Refreshed JWT token : eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MDExMDYxMTQsImp0aSI6IjIiLCJpYXQiOjE3MDEwNzczMTQsInN1YiI6IjFhZWY2ZGVmLWFlNWEtNDAxMC1hZDcxLTFmZWNiYzFjZDE2OSJ9.qOUAEc1Bxm6AoNMEunR1j_kQayawkm9kdUJzTsLDb58
[*] Starting json upload...
   [+] Started new upload batch, id : 1
   [+] Successfully uploaded 20230828025505_groups.json
   [+] Successfully uploaded 20230828025505_computers.json
   [+] Successfully uploaded 20230828025505_domains.json
   [+] Successfully uploaded 20230828025505_users.json
   [+] Successfully uploaded 20230828025505_gpos.json
   [+] Successfully uploaded 20230828025505_containers.json
   [+] Successfully uploaded 20230828025505_ous.json
   [*] Waiting for BloodHound to ingest the data. This could take a few minutes.
[+] The JSON upload was successful
```

### Delete and clear the data

```
$ python3.9 bloodhound-automation.py delete my_project
[*] Deleting my_project project...
[+] The project my_project has been successfuly deleted
```

```
$ python3.9 bloodhound-automation.py clear my_project
[+] Neo4j database cleared successfully
```


## Requirements

You need docker installed.

## Dependencies

Configure a virtualenv to ensure compatibility between packages.

```
virtualenv venv
```
```
source venv/bin/activate
```
```
pip3 install --upgrade pip
```
```
pip3 install -r requirements.txt
```
