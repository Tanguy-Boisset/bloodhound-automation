import os
import subprocess
import requests
import zipfile
import shutil
import time
import json
import re
import pickle

from pathlib import Path
from colorama import Fore, Back, Style

from typing import List

import src.utils as utils

class Project:
    def __init__(self, name: str, source_directory: Path, ports: dict, password: str, timeout: int, no_gds: bool):
        """
        Represents a project
        """
        self.name = name
        self.source_directory = source_directory
        self.ports = ports
        self.password = password
        self.base_url = f"http://localhost:{self.ports['web']}"
        self.user_ID = ""
        self.jwt = ""
        self.timeout = timeout
        self.no_gds = no_gds


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
                tmp_file = (ifile.read()
                            .replace("7687:", str(self.ports["bolt"])+":")
                            .replace("7474:", str(self.ports["neo4j"])+":")
                            .replace("8080", str(self.ports["web"])))
                if self.no_gds:
                    tmp_file = tmp_file.replace('- NEO4J_PLUGINS=["graph-data-science"]', '')
                ofile.write(tmp_file)
        
        with open("./templates/bloodhound.config.json", "r") as ifile:
            with open(self.source_directory / self.name / "bloodhound.config.json", "w") as ofile:
                ofile.write(ifile.read()
                            .replace("8080", str(self.ports["web"])))


    def getAdminPassword(self) -> str:
        """
        Find and return the random temporary admin password
        """
        start_time = time.time()
        while True:
            with open(self.source_directory / self.name / "logs.txt", "r") as logfile:
                log = logfile.read()
                if "Initial Password Set To" in log:
                    start_index = log.find("Initial Password Set To:") + len("Initial Password Set To:")
                    end_index = log.find('#"}', start_index)
                    adminPassword = log[start_index:end_index].strip()
                    return adminPassword
                if time.time() - start_time > self.timeout:
                    print(Fore.RED + "[-] Timeout : a problem occured, check the logs for more information" + Style.RESET_ALL)
                    exit(1)


    def refreshJWT(self, adminPassword: str) -> None:
        """
        Get the JWT token required for actions
        """
        url = self.base_url + "/api/v2/login"
        data_to_send = {
            "login_method": "secret",
            "secret": adminPassword,
            "username": "admin"
        }
        response = requests.post(url, json=data_to_send)
        if response.status_code == 200:
            response_json = response.json()
            self.jwt = response_json["data"]["session_token"]
            return
        else:
            print(Fore.RED + f"[-] Login request was not successful. Could not extract JWT. Status code : {response.status_code}\n{response.text}" + Style.RESET_ALL)
            return


    def getUserID(self) -> None:
        """
        Get the user ID of the admin account
        """
        headers = {
                    "User-Agent": "bh-automation",
                    "Authorization": f"Bearer {self.jwt}"
                }

        request0 = requests.get(self.base_url + f"/api/v2/self", headers=headers)
        self.user_ID = request0.json()["data"]["id"]

        print(Fore.GREEN + f"[+] UserID found : {self.user_ID}" + Style.RESET_ALL)
        return


    def resetPassword(self, adminPassword: str) -> None:
        """
        Reset the admin's password
        """
        headers = {
                    "User-Agent": "bh-automation",
                    "Authorization": f"Bearer {self.jwt}",
                    "Content-Type": "application/json",
                }

        passwData = {
            "current_secret": adminPassword,
            "needs_password_reset": False,
            "secret": self.password
        }

        request0 = requests.put(self.base_url + f"/api/v2/bloodhound-users/{self.user_ID}/secret", headers=headers, data=json.dumps(passwData))
        
        print(Fore.GREEN + f"[+] Changed admin password to : {self.password}" + Style.RESET_ALL)
        return


    def save(self) -> None:
        """
        Save the project object in a pickle dump
        """
        with open(self.source_directory / self.name / "project.pkl", "wb") as pkl_file:
            pickle.dump(self, pkl_file)


    def enableNTLM(self) -> None:
        """
        Enable the NTLM Post Processing Support feature (Early Access) via the BloodHound API using a PUT request
        """
        self.refreshJWT(self.password)  # Ensure we have a valid JWT token
        url = f"{self.base_url}/api/v2/features/18/toggle"
        headers = {
            "User-Agent": "bh-automation",
            "Authorization": f"Bearer {self.jwt}",
            "Accept": "application/json, text/plain, */*",
        }

        response = requests.put(url, headers=headers)
        if response.status_code == 200 or response.status_code == 204:
            print(Fore.GREEN + "[+] NTLM Post Processing Support feature (Early Access) enabled successfully" + Style.RESET_ALL)
        else:
            print(Fore.RED + f"[-] Failed to enable NTLM Post Processing Support feature. Status code: {response.status_code}\n{response.text}" + Style.RESET_ALL)


    def start(self) -> None:
        """
        Start the project and do initial tasks
        """
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
        print(f"The docker log are accessible in the {self.source_directory / self.name / 'logs.txt'} file")

        # Run docker-compose
        try:
            with open(self.source_directory / self.name / "logs.txt", "w") as output_log:
                docker_compose_bin = ["docker-compose"] if shutil.which("docker-compose") else ["docker", "compose"]
                docker_pull = subprocess.Popen(
                    [*docker_compose_bin, "pull"], cwd=self.source_directory / self.name, text=True, stdout=output_log, stderr=output_log
                    )
                docker_process = subprocess.Popen(
                    [*docker_compose_bin, "up"], cwd=self.source_directory / self.name, text=True, stdout=output_log, stderr=output_log
                    )
        except subprocess.CalledProcessError as e:
            print(Fore.RED + f"An error occurred: {e}")
            print(Style.RESET_ALL + 'Exiting...')
            exit(1)
        
        # Get the default admin password
        adminPassword = self.getAdminPassword()
        print(Fore.GREEN + f"[+] Found admin temporary password : {adminPassword}" + Style.RESET_ALL)

        # Wait for the web server to be ready
        while True:
            with open(self.source_directory / self.name / "logs.txt", "r") as logfile:
                log = logfile.read()
                if "Server started successfully" in log:
                    print(Fore.GREEN + "[+] Web server launched successfully" + Style.RESET_ALL)
                    break
        
        # Get the JWT token of the admin
        self.refreshJWT(adminPassword)
        print(Fore.GREEN + f"[+] Found JWT token : {self.jwt}" + Style.RESET_ALL)

        # Find user ID
        self.getUserID()

        # Reset the admin password
        self.resetPassword(adminPassword)

        # Enable NTLM feature
        self.enableNTLM()

        print(Fore.GREEN + 
          f"""
        #############################################################################
        #                                                                           #
        #              Your neo4j instance was successfully populated               #
        #                        and is now accessible at :                         #
        #                             localhost:{self.ports["bolt"]}{" " * (36 - len(str(self.ports["bolt"])))}#
        #                             username : neo4j                              #
        #                             password : neo5j                              # 
        #                                                                           #
        #                 The BloodHound Web GUI is accessible at :                 #
        #                         http://localhost:{self.ports["web"]}                             #
        #                     with the following credentials :                      #
        #                         username : admin                                  #
        #                         password : {self.password}{" " * (39 - len(self.password))}#
        #                                                                           #
        #############################################################################
          """ 
          + Style.RESET_ALL)
        
        self.save()
        return


    def extractZip(self, zip_file: str) -> List[str]:
        """
        Extract the zip file into a temporary directory
        """
        extract_directory = self.source_directory / self.name / ".json_tmp_storage"

        # Remove the existing directory if it exists
        if os.path.exists(extract_directory):
            shutil.rmtree(extract_directory)

        # Create the extraction directory
        os.makedirs(extract_directory)

        # Extract the contents of the zip file
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(extract_directory)
        
        file_list = os.listdir(extract_directory)
        json_files = [extract_directory / file for file in file_list if file.endswith(".json")]

        return json_files


    def uploadJSON(self, json_files: List[str]):
        """
        Upload json files into BH
        """
        self.refreshJWT(self.password)
        print(Fore.GREEN + f"[+] Refreshed JWT token : {self.jwt}" + Style.RESET_ALL)

        headers = {
                    "User-Agent": "bh-automation",
                    "Authorization": f"Bearer {self.jwt}",
                    "Content-Type": "application/json",
                }
        print(Fore.YELLOW + "[*] Starting json upload..." + Style.RESET_ALL)

        request1 = requests.post(self.base_url + "/api/v2/file-upload/start", headers=headers)
        uploadId = request1.json()["data"]["id"]
        print(Fore.GREEN + f"   [+] Started new upload batch, id : {uploadId}" + Style.RESET_ALL)

        for file in json_files:
            with open(file, "r", encoding="utf-8-sig") as f:
                data = f.read().encode("utf-8")
                request2 = requests.post(self.base_url + f"/api/v2/file-upload/{uploadId}", headers=headers, data=data)
                print(Fore.GREEN + f"   [+] Successfully uploaded {file.name}" + Style.RESET_ALL)
        
        request3 = requests.post(self.base_url + f"/api/v2/file-upload/{uploadId}/end", headers=headers)

        print(Fore.YELLOW + f"   [*] Waiting for BloodHound to ingest the data. This could take a few minutes." + Style.RESET_ALL)
        while True:
            ingest = requests.get(self.base_url + f"/api/v2/file-upload?skip=0&limit=10&sort_by=-id", headers=headers)
            status = ingest.json()["data"][0]

            if status["id"] == uploadId and status["status_message"] == "Complete":
                print(Fore.GREEN + f"[+] The JSON upload was successful" + Style.RESET_ALL)
                return
            else:
                time.sleep(5)
    

    def clear(self) -> None:
        """
        Clear the Neo4j database via BloodHound API
        """
        self.refreshJWT(self.password)
        url = f"http://localhost:{self.ports['web']}/api/v2/clear-database"
        headers = {
            "User-Agent": "bh-automation",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.jwt}"
        }

        data = {
            "deleteCollectedGraphData": True
        }

        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 204:
            print(Fore.GREEN + "[+] Neo4j database cleared successfully. You must wait a few seconds before the changes take effect." + Style.RESET_ALL)
        else:
            print(Fore.RED + f"[-] Failed to clear Neo4j database. Status code: {response.status_code}\n{response.text}" + Style.RESET_ALL)


    def delete(self) -> None:
        """
        Delete the containers and network interface
        """
        print(Fore.YELLOW + f"[*] Deleting {self.name} project..." + Style.RESET_ALL)
        # Run docker-compose
        try:
            with open(self.source_directory / self.name / "logs.txt", "a") as output_log:
                docker_compose_bin = ["docker-compose"] if shutil.which("docker-compose") else ["docker", "compose"]
                docker_process = subprocess.Popen(
                    [*docker_compose_bin, "down"], cwd=self.source_directory / self.name, text=True, stdout=output_log, stderr=output_log
                    )
        except subprocess.CalledProcessError as e:
            print(Fore.RED + f"An error occurred: {e}")
            print(Style.RESET_ALL + 'Exiting...')
            exit(1)
        # Wait for a bit
        time.sleep(10)
        # Delete project's folder
        shutil.rmtree(self.source_directory / self.name)
        print(Fore.GREEN + f"[+] The project {self.name} has been successfuly deleted" + Style.RESET_ALL)
