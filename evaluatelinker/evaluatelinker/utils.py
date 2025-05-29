import os
import subprocess
from enum import StrEnum, auto
from pathlib import Path

from core import (get_project_name_from_connection)

RESOURCE_PATH = Path(__file__).parent.parent.resolve() / "resources"
DATA_PATH = RESOURCE_PATH / "data"

class Result(StrEnum):
    NO_GITHUB_TAG = auto()
    NO_JAR = auto()
    NO_MAVEN = auto()
    NO_POM = auto()
    NO_RESOLVE = auto()
    NO_TEST = auto()
    NO_COMPILE = auto()
    NO_GITHUB_LINK = auto()
    UNKNOWN = auto()
    COMPATIBLE = auto()
    STATICALLY_COMPATIBLE = auto()
    STATICALLY_INCOMPATIBLE = auto()
    DYNAMICALLY_INCOMPATIBLE = auto()
    DYNAMICALLY_COMPATIBLE = auto()

def extract_value(line):
    return line.split('=')[1].strip()


class ReproducibleCentralInfo:
    """
    Class to store the info obstained from a dependency's reproducible central buildspec file.
    """
    def __init__(self, group_id: str, artifact_id: str, version: str, repo: str, tag: str):
        self.group_id = group_id
        self.artifact_id = artifact_id
        self.version = version
        self.repo = repo
        self.tag = tag


def get_buildspec_files(path_to_rc: Path) -> list[str]:
    """
    Returns a list of all .buildspec files contained in the local Reproducible Central repository
    :param path_to_rc: absolute path to the content directory in the reproducible central repository
    :return: list of .buildspec filenames (paths starting with "./", relative to reproducible-central/content)
    """
    os.chdir(path_to_rc)
    output = subprocess.run(["find", ".", "-name", "*.buildspec"], stdout=subprocess.PIPE, universal_newlines=True)
    items = output.stdout.split("\n")
    return [x for x in items if x.endswith(".buildspec")]


def parse_buildspec(path_to_buildspec: Path) -> ReproducibleCentralInfo | None:
    """
    :param path_to_buildspec: absolute path to a dependency's buildspec file
    :return: a ReproducibleCentralInfo object containing the info extracted from the buildspec file
    """
    with open(path_to_buildspec) as f:
        group_id, artifact_id, version, git_repo, git_tag = None, None, None, None, None
        for line in f.readlines():
            if line.startswith('groupId='):
                group_id = extract_value(line)
            elif line.startswith('artifactId='):
                artifact_id = extract_value(line)
            elif line.startswith('version='):
                version = extract_value(line)
            elif line.startswith('gitRepo='):
                git_repo = extract_value(line)
                if git_repo:
                    git_repo = git_repo.replace("${artifactId}", artifact_id)
                if git_repo.endswith(".git"):
                    git_repo = git_repo[:-4]
            elif line.startswith('gitTag='):
                git_tag = extract_value(line)
                git_tag = git_tag.replace("^", "")
                git_tag = git_tag.replace("${version}", version)
                git_tag = git_tag.replace("{version}", version)
                git_tag = git_tag.replace("$version", version)
                git_tag = git_tag.replace("${artifactId}", artifact_id)
                git_tag = git_tag.replace("{artifactId}", artifact_id)
                git_tag = git_tag.replace("$artifactId", artifact_id)

    if not group_id or not artifact_id or not version:
        return None
    git_repo_name = get_project_name_from_connection(git_repo)
    return ReproducibleCentralInfo(group_id, artifact_id, version, git_repo_name, git_tag)
