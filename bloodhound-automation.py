import argparse
import pickle

from pathlib import Path

from src.list import listProjects
from src.project import Project
    

if __name__=="__main__":
    parser = argparse.ArgumentParser(description="Automatically deploy a bloodhound instance and populate it with the SharpHound data")
    subparsers = parser.add_subparsers(dest='subparser', help="Action to run")

    # List
    parser_list = subparsers.add_parser('list', help="List existing projects")

    # Start
    parser_start = subparsers.add_parser('start', help="Create a new project or start an existing one")
    parser_start.add_argument('project', type=str, help="")
    parser_start.add_argument('-bp', '--bolt-port', type=int, required=False, default=7687, help="The custom port for the bolt connection")
    parser_start.add_argument('-np', '--neo4j-port', type=int, required=False, default=7474, help="The custom port for the neo4j connection")
    parser_start.add_argument('-wp', '--web-port', type=int, required=False, default=8080, help="The custom port for the web app (default: 8080)")
    parser_start.add_argument('-p', '--password', type=str, required=False, default="Chien2Sang<3", help="Custom password for the web interface (12 chars min. & all types of characters)")
    
    # Data
    parser_data = subparsers.add_parser('data', help="Feed data into an existing project")
    parser_data.add_argument('project', type=str, help="")
    parser_data.add_argument('-z', '--zip', type=str, required=True, help="The zip file from SharpHound containing the json extracts")

    # Stop
    parser_stop = subparsers.add_parser('stop', help="Stop a running project")

    # Delete
    parser_delete = subparsers.add_parser('delete', help="Delete a project")

    args = parser.parse_args()

    PROJECT_DIR = Path(__file__).parent / "projects"

    if args.subparser == "start":
        project = Project(name = args.project,
                          source_directory = PROJECT_DIR,
                          ports = {"neo4j": args.neo4j_port, "bolt": args.bolt_port, "web": args.web_port},
                          password = args.password)
        project.start()
        
    if args.subparser == "data":
        with open(PROJECT_DIR / args.project / "project.pkl", "rb") as pikl_file:
            project = pickle.load(pikl_file)
        jsons = project.extractZip(args.zip)
        project.uploadJSON(jsons)

