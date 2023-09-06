import argparse
import os
import subprocess
import requests
import zipfile
import shutil
import time
import json
import re

from colorama import Fore, Back, Style


def isValidPassword(password):
    # Check if the password respects the BH criteria
    pattern = r'^(?=.*[A-Z])(?=.*[a-z])(?=.*[0-9])(?=.*[!?:\-+,;.@#$%^&*<>]).{12,}$'

    return bool(re.match(pattern, password))

def checkDirWritable():
    directory_path = "/var/lib/postgresql/data"
    if os.path.exists(directory_path):
        if os.path.isdir(directory_path):
            if os.access(directory_path, os.W_OK):
                # Directory exists and is writable
                return True
            else:
                # Directory exists but is not writable
                return False
        else:
            # Path exists but is not a directory
            return False
    else:
        # Directory does not exist
        return False

def dockerSetup():
    with open("./templates/docker-compose.yml", "r") as ifile:
        with open("./docker-compose.yml", "w") as ofile:
            ofile.write(ifile.read().replace("7687", str(args.neo4j_port)).replace("8080", str(args.web_port)))
    
    with open("./templates/bloodhound.config.json", "r") as ifile:
        with open("./bloodhound.config.json", "w") as ofile:
            ofile.write(ifile.read().replace("8080", str(args.web_port)))


def getAdminPassword():
    start_time = time.time()
    while True:
        with open("/tmp/bh-auto-log.txt", "r") as logfile:
            log = logfile.read()
            if "Initial Password Set To" in log:
                start_index = log.find("Initial Password Set To:") + len("Initial Password Set To:")
                end_index = log.find('#"}', start_index)
                adminPassword = log[start_index:end_index].strip()
                return adminPassword
            if time.time() - start_time > 40:
                print(Fore.RED + "[-] Timeout : a problem occured, check the logs for more information" + Style.RESET_ALL)
                exit(1)


def getJWT(adminPassword):
    url = f"http://localhost:{args.web_port}/api/v2/login"
    data_to_send = {
        "login_method": "secret",
        "secret": adminPassword,
        "username": "admin"
    }
    response = requests.post(url, json=data_to_send)
    if response.status_code == 200:
        response_json = response.json()
        jwt = response_json["data"]["session_token"]
        return jwt
    else:
        print(Fore.RED + f"[-] Login request was not successful. Status code : {response.status_code}\n{response.text}" + Style.RESET_ALL)
        exit(1)


def extractZip():
    extract_directory = "/tmp/bh-automation-json"

    # Remove the existing directory if it exists
    if os.path.exists(extract_directory):
        shutil.rmtree(extract_directory)

    # Create the extraction directory
    os.makedirs(extract_directory)

    # Extract the contents of the zip file
    with zipfile.ZipFile(args.zip, 'r') as zip_ref:
        zip_ref.extractall(extract_directory)
    
    file_list = os.listdir(extract_directory)
    json_files = [extract_directory + "/" + file for file in file_list if file.endswith(".json")]

    return json_files


def uploadJSON(jwt, json_files):
    base_url = f"http://localhost:{args.web_port}"
    headers = {
                "User-Agent": "bh-automation",
                "Authorization": f"Bearer {jwt}",
                "Content-Type": "application/json",
            }

    # Reset password (needed for file upload)
    passwData = {
        "needs_password_reset": False,
        "secret": args.password
    }

    print(Fore.YELLOW + "[*] Starting json upload..." + Style.RESET_ALL)
    request0 = requests.get(base_url + f"/api/v2/self", headers=headers)
    
    userId = request0.json()["data"]["id"]
    print(Fore.GREEN + f"   [+] UserID found : {userId}" + Style.RESET_ALL)

    request0 = requests.put(base_url + f"/api/v2/bloodhound-users/{userId}/secret", headers=headers, data=json.dumps(passwData))
    print(Fore.GREEN + f"   [+] Changed admin password to : {passwData['secret']}" + Style.RESET_ALL)

    request1 = requests.post(base_url + "/api/v2/file-upload/start", headers=headers)
    uploadId = request1.json()["data"]["id"]
    print(Fore.GREEN + f"   [+] Started new upload batch, id : {uploadId}" + Style.RESET_ALL)

    for file in json_files:
        with open(file, "r", encoding="utf-8-sig") as f:
            data = f.read().encode("utf-8")
            request2 = requests.post(base_url + f"/api/v2/file-upload/{uploadId}", headers=headers, data=data)
            print(Fore.GREEN + f"   [+] Successfully uploaded {file.split('/')[-1]}" + Style.RESET_ALL)
    
    request3 = requests.post(base_url + f"/api/v2/file-upload/{uploadId}/end", headers=headers)

    print(Fore.YELLOW + f"   [*] Waiting for BloodHound to ingest the data. This could take a few minutes." + Style.RESET_ALL)
    while True:
        ingest = requests.get(base_url + f"/api/v2/file-upload?skip=0&limit=10&sort_by=-id", headers=headers)
        status = ingest.json()["data"][0]

        if status["id"] == uploadId and status["status_message"] == "Complete":
            print(Fore.GREEN + f"[+] The JSON upload was successful" + Style.RESET_ALL)
            return passwData['secret']
        else:
            time.sleep(5)
    

if __name__=="__main__":
    parser = argparse.ArgumentParser(description="Automatically deploy a bloodhound instance and populate it with the SharpHound data")
    parser.add_argument('-np', '--neo4j-port', type=int, required=True, help="The custom port for the neo4j container")
    parser.add_argument('-wp', '--web-port', type=int, required=False, default=8080, help="The custom port for the web container (default: 8080)")
    parser.add_argument('-z', '--zip', type=str, required=True, help="The zip file from SharpHound containing the json extracts")
    parser.add_argument('-P', '--password', type=str, required=False, default="Chien2Sang<3", help="Custom password for the web interface (12 chars min. & all types of characters)")
    args = parser.parse_args()

    if not isValidPassword(args.password):
        print(Fore.RED + f"[-] The chosen password '{args.password}' does not respect the complexity criteria\nYour password must be at least 12 characters long and must contain every type of characters (lowercase, uppercase, digit and special characters)" + Style.RESET_ALL)
        print('Exiting...')
        exit(1)

    # Check if /var/lib/postgresql/data is writable
    # If not, the docker command will crash
    if not checkDirWritable():
        print(Fore.RED + '[-] The folder "/var/lib/postgresql/data" does not exist or is not writable. Please run the following command and relaunch this script :')
        print('sudo mkdir /var/lib/postgresql && sudo mkdir /var/lib/postgresql/data && sudo chmod 777 /var/lib/postgresql/data')
        print(Style.RESET_ALL + 'Exiting...')
        exit(1)
    
    dockerSetup()
    print(Fore.GREEN + "[+] Docker setup done" + Style.RESET_ALL)
    print(Fore.YELLOW + "[*] Launching BloodHound..." + Style.RESET_ALL)
    print("The docker log are accessible in the /tmp/bh-auto-log.txt file")

    try:
        with open("/tmp/bh-auto-log.txt", "w") as output_log:
            docker_process = subprocess.Popen(["docker-compose", "up"], text=True, stdout=output_log, stderr=output_log)
    except subprocess.CalledProcessError as e:
        print(Fore.RED + f"An error occurred: {e}")
        print(Style.RESET_ALL + 'Exiting...')
        exit(1)
    
    adminPassword = getAdminPassword()
    print(Fore.GREEN + f"[+] Found admin temporary password : {adminPassword}" + Style.RESET_ALL)

    while True:
        with open("/tmp/bh-auto-log.txt", "r") as logfile:
            log = logfile.read()
            if "Server started successfully" in log:
                print(Fore.GREEN + "[+] Web server launched successfully" + Style.RESET_ALL)
                break
    
    jwt = getJWT(adminPassword)
    print(Fore.GREEN + f"[+] Found JWT token : {jwt}" + Style.RESET_ALL)

    json_files = extractZip()
    print(Fore.GREEN + f"[+] Successfully extracted {len(json_files)} file{'s' if len(json_files) > 0 else ''}" + Style.RESET_ALL)

    newAdminPassw = uploadJSON(jwt, json_files)
    print(Fore.GREEN + 
          f"""
        #############################################################################
        #                                                                           #
        #              Your neo4j instance was successfully populated               #
        #                        and is now accessible at :                         #
        #                             localhost:{args.neo4j_port}{" " * (36 - len(str(args.neo4j_port)))}#
        #                             username : neo4j                              #
        #                             password : neo5j                              # 
        #                                                                           #
        #                 The BloodHound Web GUI is accessible at :                 #
        #                         http://localhost:{args.web_port}                             #
        #                     with the following credentials :                      #
        #                         username : admin                                  #
        #                         password : {newAdminPassw}{" " * (39 - len(newAdminPassw))}#
        #                                                                           #
        #############################################################################
          """ 
          + Style.RESET_ALL)
    print(Fore.YELLOW + f"[+] All BloodHound dockers are still running. You can now manually shutdown them if you wish." + Style.RESET_ALL)
