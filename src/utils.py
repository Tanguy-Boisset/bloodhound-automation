import os

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