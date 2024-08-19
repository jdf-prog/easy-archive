import fire
import os
from .archive import main as archive
from .unarchive import main as unarchive


class EasyArchiveCLI:
    def __init__(self):
        self.archive = archive
        self.unarchive = unarchive
    
    def __call__(self, *args, **kwds):
        return self.archive(*args, **kwds)

def main():
    fire.Fire(EasyArchiveCLI)

if __name__ == "__main__":
    main()