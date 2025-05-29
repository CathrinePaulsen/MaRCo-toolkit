from pathlib import Path

import pandas as pd

from evaluatelinker.utils import get_buildspec_files, parse_buildspec, DATA_PATH, RESOURCE_PATH


def add_subparser(subparsers):
    parser = subparsers.add_parser('extract_raw',
                                   help='Extract the raw data from the Reproducible Central buildspec'
                                        'files and convert them into usable datapoints stored in csv format')

    parser.add_argument(
        '--save_as',
        type=str,
        default='linker_raw.csv',
        help='Output file name (default: linker_raw.csv)'
    )

    return parser


def extract_raw(filename="linker_raw_original.csv") -> None:
    """
    Converts the buildspec files in resources/reproducible-central/content into usable datapoints stored in a csv

    :param filename: the extracted datapoints will be stored in resources/<filename>, defaults to linker_raw.csv

    The data extracted for each datapoint include:
    - ga: the groupId and artifactId of the dependency
    - version: the version of the dependency, which together with the GA forms a dependency's unique GAV
    - groundtruth_repo: the GitHub repository of the GAV given by ReproducibleCentral
    - groundtruth_tag: the GitHub tag corresponding to the GAV given by ReproducibleCentral (NB: may be a commit hash)

    The following empty columns are added to store the results of the Linker:
    - repo: the GitHub repository of the dependency given by the Linker
    - commit: the commit corresponding to GAV given by the Linker
    - tag: the tag corresponding to the GAV given by the Linker
    - commit: the commit corresponding to the GAV given by the Linker
    - exact_match: whether the tag was found by exact string matching (True/False)
    - has_tests: whether the repo+tag given by the Linker contains a test suite (True/False)
    - has_tests_jar: whether the GAV has a test jar available on Maven Central (True/False)
    - err: indicates the reason for unsuccessful Links, possible errors include:
        - no_github_link: found no link in the GAV's POM to a valid GitHub repository
        - no_github_tag: a GitHub repository was found, but no tag could be found that corresponds to the version
        - no_pom: the GAV's POM could not be found on Maven Central

    :return: None
    """
    WRITE_TO = DATA_PATH / filename
    BUILDSPEC_PATH = RESOURCE_PATH / "reproducible-central" / "content"
    input(f"Reading data from {BUILDSPEC_PATH} and storing the results in {WRITE_TO}. Press any key to continue.")

    rows = []

    try:
        buildspec_files = get_buildspec_files(BUILDSPEC_PATH)
        n_total = len(buildspec_files)

        for i, filename in enumerate(buildspec_files):
            print(f"\nPROGRESS {i+1}/{n_total} ({int((i+1)/n_total*100)}%)")
            print(f"Processing {Path.joinpath(BUILDSPEC_PATH, filename[2:])}")

            gt = parse_buildspec(Path.joinpath(BUILDSPEC_PATH, filename[2:]))  # ground truth info
            if not gt:
                print(f"Skipping malformed datapoint: {Path.joinpath(BUILDSPEC_PATH, filename[2:])}")
                continue
            print("groupId:", gt.group_id)
            print("artifactId:", gt.artifact_id)
            print("version:", gt.version)
            print("gitRepoName:", gt.repo)
            print("gitTag:", gt.tag)

            row = {
                'ga': f"{gt.group_id}:{gt.artifact_id}", 'version': gt.version, 'groundtruth_repo': gt.repo,
                'groundtruth_tag': gt.tag, 'repo': None, 'tag': None, 'commit': None, 'exact_match': None,
                'has_tests': None, 'has_tests_jar': None, 'err': None,
            }
            rows.append(row)

    except KeyboardInterrupt as e:
        print(e)
        pass

    df = pd.DataFrame(rows)
    df.to_csv(WRITE_TO, index=False)
    print(f"The raw data has been extracted and written to {WRITE_TO}.")
