import argparse
import os
import subprocess

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
            ofile.write(ifile.read().replace("7687", str(args.port)))


if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, required=True)
    parser.add_argument('-j', '--json', type=str, required=True)
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
        docker_process = subprocess.run(["docker-compose", "up"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        docker_output = docker_process.stdout
        print(docker_output)
    except subprocess.CalledProcessError as e:
        print(Fore.RED + f"An error occurred: {e}")
        print(Style.RESET_ALL + 'Exiting...')
        exit(1)