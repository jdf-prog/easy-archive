import fire
import zipfile
import os
from pathlib import Path
from tqdm import tqdm

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
            with zipfile.ZipFile(file, "r") as zipf:
                zipf_files = zipf.namelist()
                for f in tqdm(zipf_files, total=len(zipf_files), desc=f"Extracting {file}"):
                    f_path = unarchived_dir / f
                    if f_path.exists() and not overwrite:
                        pass
                        # print(f"File {f_path} already exists. Skipping.")
                    else:
                        # print(f"Extracting {f} to {f_path}")
                        zipf.extract(f, unarchived_dir)
        else:
            print(f"File {file} is not a zip file. Skipping.")
    

def main(
    archived_dir: str = "./archive",
    unarchived_dir: str = "./unarchive",
):
    iter_unarchive_dir(archived_dir, unarchived_dir)
    
if __name__ == "__main__":
    fire.Fire(main)