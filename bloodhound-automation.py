import argparse
import os
import subprocess
import requests
import zipfile
import shutil
import time
import json

from colorama import Fore, Back, Style


def check_directory_writable():
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

def docker_setup():
    with open("./templates/docker-compose.yml", "r") as ifile:
        with open("./docker-compose.yml", "w") as ofile:
            ofile.write(ifile.read().replace("7687:", str(args.port) + ":"))
    
    with open("./templates/bloodhound.config.json", "r") as ifile:
        with open("./bloodhound.config.json", "w") as ofile:
            ofile.write(ifile.read())


def getAdminPassword():
    while True:
        with open("/tmp/bh-auto-log.txt", "r") as logfile:
            log = logfile.read()
            if "Initial Password Set To" in log:
                start_index = log.find("Initial Password Set To:") + len("Initial Password Set To:")
                end_index = log.find('#"}', start_index)
                adminPassword = log[start_index:end_index].strip()
                return adminPassword


def getJWT(adminPassword):
    url = "http://localhost:8080/api/v2/login"
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
        print("Request was not successful. Status code:", response.status_code)


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
    base_url = "http://localhost:8080"
    headers = {
                "User-Agent": "bh-automation",
                "Authorization": f"Bearer {jwt}",
                "Content-Type": "application/json",
            }

    # Reset password (needed for file upload)
    data = {
        "needs_password_reset": False,
        "secret": "Chien2Sang<3"
    }

    request0 = requests.get(base_url + f"/api/v2/self", headers=headers)
    
    userId = request0.json()["data"]["id"]
    print(f"USERID : {userId}")

    request0 = requests.put(base_url + f"/api/v2/bloodhound-users/{userId}/secret", headers=headers, data=json.dumps(data))

    request1 = requests.post(base_url + "/api/v2/file-upload/start", headers=headers)
    uploadId = request1.json()["data"]["id"]

    for file in json_files:
        print(f"Uploading: {file}")
        with open(file, "r", encoding="utf-8-sig") as f:
            data = f.read().encode("utf-8")
            request2 = requests.post(base_url + f"/api/v2/file-upload/{uploadId}", headers=headers, data=data)
    
    request3 = requests.post(base_url + f"/api/v2/file-upload/{uploadId}/end", headers=headers)

    print("Waiting for BloodHound to ingest the data")
    while True:
        ingest = requests.get(base_url + f"/api/v2/file-upload?skip=0&limit=10&sort_by=-id", headers=headers)
        status = ingest.json()["data"][0]

        if status["id"] == uploadId and status["status_message"] == "Complete":
            print("Ingest done")
            break
        else:
            time.sleep(5)
    

if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, required=True)
    parser.add_argument('-z', '--zip', type=str, required=True)
    args = parser.parse_args()

    # Check if /var/lib/postgresql/data is writable
    # If not, the docker command will crash
    if not check_directory_writable():
        print(Fore.RED + 'The folder "/var/lib/postgresql/data" does not exist or is not writable. Please run the following command and relaunch this script :')
        print('sudo mkdir /var/lib/postgresql && sudo mkdir /var/lib/postgresql/data && sudo chmod 777 /var/lib/postgresql/data')
        print(Style.RESET_ALL + 'Exiting...')
        exit(1)
    
    docker_setup()
    try:
        with open("/tmp/bh-auto-log.txt", "w") as output_log:
            docker_process = subprocess.Popen(["docker-compose", "up"], text=True, stdout=output_log, stderr=output_log)
    except subprocess.CalledProcessError as e:
        print(Fore.RED + f"An error occurred: {e}")
        print(Style.RESET_ALL + 'Exiting...')
        exit(1)
    
    adminPassword = getAdminPassword()
    print(adminPassword)

    while True:
        with open("/tmp/bh-auto-log.txt", "r") as logfile:
            log = logfile.read()
            if "Server started successfully" in log:
                print("Server launched")
                break
    
    jwt = getJWT(adminPassword)
    print(jwt)

    json_files = extractZip()
    print(json_files)

    uploadJSON(jwt, json_files)
