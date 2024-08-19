import fire
import os
import zipfile
from tqdm import tqdm
from pathlib import Path
import re
import hashlib
import stat
import json
import time
import datasets
from functools import partial

def get_file_hash(file_path):
    """Calculate the MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def load_archive_info(save_dir):
    info_file = save_dir / "archive_info.json"
    if info_file.exists():
        with open(info_file, "r") as f:
            return json.load(f)
    return {}

def save_archive_info(save_dir, info):
    info_file = save_dir / "archive_info.json"
    with open(info_file, "w") as f:
        json.dump(info, f, indent=4, ensure_ascii=False)
    print(f"Saved archive info to {info_file}")
        
class ArchiveFile:
    def __init__(self, file, arcname, symlink_target, update_archive=True):
        self.file = file
        self.arcname = arcname
        self.symlink_target = symlink_target
        self.update_archive = update_archive

def iter_archive_dir(
    archive_dir: str,
    save_dir: str = None,
    num_files_per_archive: int = 10000,
    delete_original: bool = False,
    overwrite: bool = False,
    remove_duplicates: bool = False,
    recursive: bool = True,
):
    if not save_dir or not archive_dir:
        raise ValueError(f"Both archive_dir and save_dir must be provided; archive_dir: {archive_dir}, save_dir: {save_dir}")
    archive_dir = Path(archive_dir)
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)
    if not archive_dir.is_dir():
        return
    print(f"### Iterating archive_dir: {archive_dir}, Save_dir: {save_dir} ###")
    file_or_dirs = [f for f in archive_dir.iterdir()]
    file_or_dirs.sort(key=lambda x: x.stat().st_ctime)  # Sort by create time
    cur_archive_files = []
    last_archive_idx = 0
    
    archive_info = load_archive_info(save_dir)
    file_hashes = {}

    for file in tqdm(file_or_dirs, total=len(file_or_dirs), desc=f"Iterating directory: {archive_dir}"):
        if file.is_dir():
            if recursive:
                iter_archive_dir(file, save_dir / file.name, num_files_per_archive, delete_original, overwrite, remove_duplicates, recursive)
        elif file.is_file():
            file_mtime = file.stat().st_mtime
            file_path = file.name
            
            if file_path in archive_info and archive_info[file_path]["mtime"] >= file_mtime and archive_info[file_path]["size"] == file.stat().st_size:
                cur_archive_files.append(ArchiveFile(file, file_path, None, update_archive=False))
                file_hash = archive_info[file_path]["hash"]
                file_hashes[file_hash] = file_path
            else:
                file_hash = get_file_hash(file)
                if remove_duplicates:
                    match = re.match(r'.*\.(png|jpg|jpeg|gif|mp4)$', file.name)
                    if match:
                        if file_hash in file_hashes:
                            cur_archive_files.append(ArchiveFile(file, file.name, file_hashes[file_hash], update_archive=True))
                        else:
                            file_hashes[file_hash] = file.name
                            cur_archive_files.append(ArchiveFile(file, file.name, None, update_archive=True))
                    else:
                        cur_archive_files.append(ArchiveFile(file, file.name, None, update_archive=True))
                else:
                    cur_archive_files.append(ArchiveFile(file, file_path, None, update_archive=True))
                archive_info[file_path] = {"mtime": file_mtime, "size": file.stat().st_size, "hash": file_hash}

            if len(cur_archive_files) >= num_files_per_archive:
                create_archive(cur_archive_files, save_dir, last_archive_idx, overwrite, delete_original)
                last_archive_idx += len(cur_archive_files)
                cur_archive_files = []
        else:
            raise ValueError(f"Unknown file type: {file}")
    
    if cur_archive_files:
        create_archive(cur_archive_files, save_dir, last_archive_idx, overwrite, delete_original, is_last=True)

    save_archive_info(save_dir, archive_info)


def iter_archive_dir_mp(
    item: dict,
    **kwargs,
):
    return iter_archive_dir(archive_dir=item["archive_dir"], save_dir=item["save_dir"], **kwargs)

def create_archive(cur_archive_files, save_dir, last_archive_idx, overwrite, delete_original, is_last=False):
    archive_name = f"archive_{last_archive_idx}-{last_archive_idx + len(cur_archive_files)}"
    archive_name += ".last.zip" if is_last else ".zip"
    archive_file = save_dir / archive_name
    
    if len(set([archive_file.arcname for archive_file in cur_archive_files])) < len(cur_archive_files):
        for archive_file in cur_archive_files:
            print((archive_file.file, archive_file.arcname, archive_file.symlink_target, archive_file.update_archive))
        print(f"Duplicate files found in the archive. Exiting.")
        exit(1)
    
    re_archive = any([archive_file.update_archive for archive_file in cur_archive_files])
    if re_archive and is_last:
        last_zip_files = [f for f in save_dir.iterdir() if f.name.endswith(".last.zip")]
        print(f"Last zip files: {last_zip_files}")
        assert len(last_zip_files) <= 1, f"Multiple last zip files found: {last_zip_files}"
        if last_zip_files:
            for f in last_zip_files:
                f.unlink()
                print(f"Removed previous last zip file: {f}")
    re_archive = re_archive or (not archive_file.exists())
    if re_archive or overwrite:
        print(f"Creating archive {archive_file}")
        with zipfile.ZipFile(archive_file, "w") as zipf:
            for archive_file in tqdm(cur_archive_files, total=len(cur_archive_files), desc=f"Archiving {archive_name}", leave=False):
                arcname = archive_file.arcname
                symlink_target = archive_file.symlink_target
                file = archive_file.file
                if symlink_target:
                    info = zipfile.ZipInfo(arcname)
                    info.create_system = 3  # Unix
                    info.external_attr = (stat.S_IFLNK | 0o777) << 16  # symlink file type
                    zipf.writestr(info, symlink_target)
                else:
                    zipf.write(file, arcname=arcname)
    else:
        print(f"Archive {archive_file} already exists. Skipping.")

    if delete_original:
        for archive_file in cur_archive_files:
            file = archive_file.file
            os.remove(file)

def main(
    archive_dir: str,
    save_dir: str = None,
    num_files_per_archive: int = 10000,
    delete_original: bool = False,
    overwrite: bool = False,
    remove_duplicates: bool = True,
    num_proc: int = 1,
):
    """
    Archive media files in a directory to zip files according to the time of modification.
    Detects duplicate files and creates symlinks within the ZIP file.
    Handles updates to previously archived files.
    """
    archive_dir = Path(archive_dir)
    if save_dir is None:
        save_dir = Path("./archive") / archive_dir.name
    else:
        save_dir = Path(save_dir) / archive_dir.name
        
    archive_dirs = [f for f in archive_dir.iterdir() if f.is_dir()]
    save_dirs = [save_dir / f.name for f in archive_dirs]
    dataset = datasets.Dataset.from_dict({"archive_dir": list(map(str, archive_dirs)), "save_dir": list(map(str, save_dirs))})
    partial_iter_archive_dir = partial(iter_archive_dir_mp,
                                       num_files_per_archive=num_files_per_archive, 
                                       delete_original=delete_original, 
                                       overwrite=overwrite, 
                                       remove_duplicates=remove_duplicates)
    dataset.map(partial_iter_archive_dir, num_proc=num_proc)
    
    iter_archive_dir(archive_dir, save_dir, num_files_per_archive, delete_original, overwrite, remove_duplicates, recursive=False)

if __name__ == "__main__":
    fire.Fire(main)

"""
python archive_media.py {archive_dir} --save_dir {save_dir} --num_files_per_archive {num_files_per_archive} --delete_original --overwrite --remove_duplicates --num_proc {num_proc}
"""