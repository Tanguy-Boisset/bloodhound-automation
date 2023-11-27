import argparse
import pickle
import os

from pathlib import Path
from colorama import Fore, Back, Style

from src.project import Project
    

if __name__=="__main__":
    parser = argparse.ArgumentParser(description="Automatically deploy a bloodhound instance and populate it with the SharpHound data")
    subparsers = parser.add_subparsers(dest='subparser', help="Action to run")

    # List
    parser_list = subparsers.add_parser('list', help="List existing projects")

    # Start
    parser_start = subparsers.add_parser('start', help="Create a new project or start an existing one")
    parser_start.add_argument('project', type=str, help="The project name")
    parser_start.add_argument('-bp', '--bolt-port', type=int, required=False, default=7687, help="The custom port for the bolt connection")
    parser_start.add_argument('-np', '--neo4j-port', type=int, required=False, default=7474, help="The custom port for the neo4j connection")
    parser_start.add_argument('-wp', '--web-port', type=int, required=False, default=8080, help="The custom port for the web app (default: 8080)")
    parser_start.add_argument('-p', '--password', type=str, required=False, default="Chien2Sang<3", help="Custom password for the web interface (12 chars min. & all types of characters)")
    
    # Data
    parser_data = subparsers.add_parser('data', help="Feed data into an existing project")
    parser_data.add_argument('project', type=str, help="The project name")
    parser_data.add_argument('-z', '--zip', type=str, required=True, help="The zip file from SharpHound containing the json extracts")

    # Stop
    parser_stop = subparsers.add_parser('stop', help="Stop a running project (WIP)")

    # Delete
    parser_delete = subparsers.add_parser('delete', help="Delete a project (WIP)")

    args = parser.parse_args()

    PROJECT_DIR = Path(__file__).parent / "projects"

    if args.subparser == "list":
        # List existing projects
        projects = []
        for root, dirs, files in os.walk(PROJECT_DIR):
            if 'project.pkl' in files:
                with open(root + "/project.pkl", "rb") as pkl_file:
                    projects.append(pickle.load(pkl_file))
        # Print project details
        if len(projects) == 0:
            print(Fore.YELLOW + "[*] No project yet" + Style.RESET_ALL)
        c = 1
        for project in projects:
            print(Fore.GREEN + f"[{c}] {project.name}" + Style.RESET_ALL)
            print(Fore.YELLOW + f"   * name: {project.name}" + Style.RESET_ALL)
            print(Fore.YELLOW + f"   * bolt port: {project.ports['bolt']}" + Style.RESET_ALL)
            print(Fore.YELLOW + f"   * neo4j port: {project.ports['neo4j']}" + Style.RESET_ALL)
            print(Fore.YELLOW + f"   * web port: {project.ports['web']}" + Style.RESET_ALL)
            print(Fore.YELLOW + f"   * password: {project.password}" + Style.RESET_ALL)
            c += 1
        

    if args.subparser == "start":
        project = Project(name = args.project,
                          source_directory = PROJECT_DIR,
                          ports = {"neo4j": args.neo4j_port, "bolt": args.bolt_port, "web": args.web_port},
                          password = args.password)
        project.start()
        
    if args.subparser == "data":
        with open(PROJECT_DIR / args.project / "project.pkl", "rb") as pkl_file:
            project = pickle.load(pkl_file)
        jsons = project.extractZip(args.zip)
        project.uploadJSON(jsons)

