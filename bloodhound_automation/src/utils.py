import os
import subprocess

from pathlib import Path
from colorama import Fore, Back, Style

def createDir(directory_path: Path, project_name: Path) -> bool:
    """
    Create a directory if it doesn't already exist
    """
    if not os.path.exists(directory_path / project_name):
        try:
            os.makedirs(directory_path / project_name)
            print(Fore.YELLOW + f"[*] Created {project_name} directory" + Style.RESET_ALL)
            return True
        except OSError as e:
            print(Fore.RED + f"An error occurred while creating {directory_path} directrory: {e}")
            print(Style.RESET_ALL + 'Exiting...')
            return False
    else:
        return True

# Docker compose command with compatibility with v1 and v2 of docker compose
if subprocess.run(["docker", "compose", "version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
    command = ["docker", "compose"]
elif subprocess.run(["docker-compose", "version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
    command = ["docker-compose"]
    print(Fore.YELLOW + f"[!] WARNING : you are using the outdated v1 of docker compose. Consider installing the v2." + Style.RESET_ALL)
else:
    print(Fore.RED + f"[-] No docker version found, this tool requires docker. Please check your docker installation." + Style.RESET_ALL)
    exit(1)
