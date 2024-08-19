from setuptools import setup, find_packages

setup(
    name='easy-archive',
    version='0.0.1',
    description='Easy Archive is a tool to archive and compress files and directories, especially for large a lot of files.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Dongfu Jiang',
    author_email='dongfu.jiang@uwaterloo.ca',
    packages=find_packages(),
    url='https://github.com/jdf-prog/easy-archive',
    entry_points={"console_scripts": [
        "easy-archive = src.cli:main",
        "earc = src.cli:main",
        ]},
    install_requires=[
        "datasets",
        "fire",
        "matplotlib",
        "pandas",
        "tqdm",
    ],
)



# [build-system]
# python setup.py sdist bdist_wheel
# twine upload dist/*