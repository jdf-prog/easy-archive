import fire
import zipfile
import os
import subprocess
from pathlib import Path
from tqdm import tqdm

def unzip_file(zip_path, extract_path=None, skip_existing=False, overwrite_existing=False):
    try:
        
        command = ['unzip', str(zip_path)]
        if extract_path:
            command += ['-d', str(extract_path)]
        if overwrite_existing:
            command.insert(1, '-o')
        elif skip_existing:
            command.insert(1, '-n')
        print(f"Unzipping command: {command}")
        subprocess.run(command, check=True)
        print(f"Successfully extracted {zip_path} to {extract_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while unzipping: {e}")
    except FileNotFoundError:
        print("Error: 'unzip' command not found. Please ensure it's installed.")
        
def iter_unarchive_dir(
    archive_dir: str = "./archive",
    unarchived_dir: str = "./unarchive",
    overwrite: bool = False,
):
    print(f"### Iterating archive_dir: {archive_dir} ###")
    archive_dir = Path(archive_dir)
    file_or_dirs = [f for f in archive_dir.iterdir()]
    # Sort files by creation time
    file_or_dirs.sort(key=lambda x: x.stat().st_ctime)
    unarchived_dir = Path(unarchived_dir)
    unarchived_dir.mkdir(parents=True, exist_ok=True)
    for file in tqdm(file_or_dirs, total=len(file_or_dirs), desc=f"Iterating directory: {archive_dir}"):
        if file.is_dir():
            iter_unarchive_dir(file, unarchived_dir / file.name, overwrite)
        elif file.is_file() and zipfile.is_zipfile(file):
            # Unzip file
            unzip_file(file, unarchived_dir, skip_existing=not overwrite, overwrite_existing=overwrite)
        else:
            pass
            # print(f"File {file} is not a zip file. Skipping.")
    

def main(
    archive_dir: str = "./archive",
    unarchive_dir: str = "./unarchive",
):
    iter_unarchive_dir(archive_dir, unarchive_dir)
    
if __name__ == "__main__":
    fire.Fire(main)
