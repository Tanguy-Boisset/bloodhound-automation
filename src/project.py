import os
import subprocess
import requests
import zipfile
import shutil
import time
import json
import re

from pathlib import Path
from colorama import Fore, Back, Style

import src.utils as utils

class Project:
    def __init__(self, name: str, source_directory: Path, ports: dict, password: str):
        """
        Represents a project
        """
        self.name = name
        self.source_directory = source_directory
        self.ports = ports
        self.password = password


    def isValidPassword(self) -> bool:
        """
        Check if the password respects the BH criteria
        """
        pattern = r'^(?=.*[A-Z])(?=.*[a-z])(?=.*[0-9])(?=.*[!?:\-+,;.@#$%^&*<>]).{12,}$'

        return bool(re.match(pattern, self.password))


    def createProject(self) -> bool:
        """
        Create a new directory for the project
        """
        return utils.createDir(self.source_directory, self.name)


    def dockerSetup(self) -> None:
        """
        Fill and copy the docker templates into the project folder
        """
        with open("./templates/docker-compose.yml", "r") as ifile:
            with open(self.source_directory / self.name / "docker-compose.yml", "w") as ofile:
                ofile.write(ifile.read().replace("7687", str(self.ports["neo4j"])).replace("8080", str(self.ports["web"])))
        
        with open("./templates/bloodhound.config.json", "r") as ifile:
            with open(self.source_directory / self.name / "bloodhound.config.json", "w") as ofile:
                ofile.write(ifile.read().replace("8080", str(self.ports["web"])))


    def start(self) -> None:
        # Check that the password respects the complexity criteria of BH
        if not self.isValidPassword():
            print(Fore.RED + f"[-] The chosen password '{self.password}' does not respect the complexity criteria\nYour password must be at least 12 characters long and must contain every type of characters (lowercase, uppercase, digit and special characters)" + Style.RESET_ALL)
            print('Exiting...')
            exit(1)
        
        # Create projects directory
        if not utils.createDir(Path(__file__).parent, self.source_directory):
            print(Fore.RED + f'[-] The folder "{self.source_directory}" could not be created.')
            print(Style.RESET_ALL + 'Exiting...')
            exit(1)
        
        # Create project directory
        self.createProject()
        
        # Setup the docker files for the project
        self.dockerSetup()
        print(Fore.GREEN + "[+] Docker setup done" + Style.RESET_ALL)
        print(Fore.YELLOW + "[*] Launching BloodHound..." + Style.RESET_ALL)
        print("The docker log are accessible in the /tmp/bh-auto-log.txt file")

        # Run docker-compose
        try:
            with open("/tmp/bh-auto-log.txt", "w") as output_log:
                docker_process = subprocess.Popen(
                    ["docker-compose", "up"], cwd=self.source_directory / self.name, text=True, stdout=output_log, stderr=output_log
                    )
        except subprocess.CalledProcessError as e:
            print(Fore.RED + f"An error occurred: {e}")
            print(Style.RESET_ALL + 'Exiting...')
            exit(1)


    def getAdminPassword(self) -> str:
        """
        Find and return the random temporary admin password
        """
        start_time = time.time()
        while True:
            with open("/tmp/bh-auto-log.txt", "r") as logfile:
                log = logfile.read()
                if "Initial Password Set To" in log:
                    start_index = log.find("Initial Password Set To:") + len("Initial Password Set To:")
                    end_index = log.find('#"}', start_index)
                    adminPassword = log[start_index:end_index].strip()
                    return adminPassword
                if time.time() - start_time > 90:
                    print(Fore.RED + "[-] Timeout : a problem occured, check the logs for more information" + Style.RESET_ALL)
                    exit(1)


    def getJWT(self, adminPassword: str) -> str:
        """
        Get the JWT token required for actions
        """
        url = f"http://localhost:{self.ports['web']}/api/v2/login"
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


    def extractZip(self, zip_file: str) -> list[str]:
        """
        Extract the zip file into a temporary directory
        """
        extract_directory = "/tmp/bh-automation-json"

        # Remove the existing directory if it exists
        if os.path.exists(extract_directory):
            shutil.rmtree(extract_directory)

        # Create the extraction directory
        os.makedirs(extract_directory)

        # Extract the contents of the zip file
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(extract_directory)
        
        file_list = os.listdir(extract_directory)
        json_files = [extract_directory + "/" + file for file in file_list if file.endswith(".json")]

        return json_files


    def uploadJSON(self, jwt: str, json_files: list[str]):
        """
        Upload json files into BH
        """
        base_url = f"http://localhost:{self.ports['web']}"
        headers = {
                    "User-Agent": "bh-automation",
                    "Authorization": f"Bearer {jwt}",
                    "Content-Type": "application/json",
                }

        # Reset password (needed for file upload)
        passwData = {
            "needs_password_reset": False,
            "secret": self.password
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