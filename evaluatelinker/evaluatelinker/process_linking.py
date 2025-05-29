import pandas as pd
from github import Repository

from core import (get_github_repo_and_tag,
                  PomNotFoundException)
from evaluatelinker.utils import DATA_PATH, Result


def add_subparser(subparsers):
    parser = subparsers.add_parser('process_linking',
                                   help='Apply the Maven-GitHub linking algorithm for each datapoint in linker_raw.csv'
                                        ', and store the results in linker_results.csv')

    parser.add_argument(
        '--save_as',
        type=str,
        default='linker_results.csv',
        help='Output file name (default: linker_results.csv)'
    )

    return parser


def has_tests(repo: Repository, commit_sha: str) -> bool:
    """
    Look for files that match: Test*.java, *Test.java, *Tests.java, *TestCase.java (from Maven surefire spec)
    :param repo: the GitHub repository to evaluate
    :param commit_sha: the commit sha at which to evaluate the repo
    :return: True if the given repo has tests, False otherwise
    """

    tree = repo.get_git_tree(commit_sha, recursive=True)
    for obj in tree.tree:
        end = obj.path.split("/")[-1]
        if end.endswith(".java"):
            filename = end.split(".")[0]
            if filename.endswith("Test") or filename.endswith("Tests") or filename.endswith("TestCase") or filename.startswith("Test"):
                print(f"Found tests ({obj.path}) for {repo.full_name}")
                return True

    print(f"Found no tests for {repo.full_name}.")
    return False


def process_linking(override=False, filename='linker_results.csv'):
    # READ_FROM = Path(__file__).parent.resolve() / "linker_results.csv"  # to continue
    READ_FROM = DATA_PATH / "linker_raw.csv"  # to redo from scratch
    WRITE_TO = DATA_PATH / filename

    input(f"Reading data from {READ_FROM} and storing the results in {WRITE_TO}. Press any key to continue.")

    df = pd.read_csv(READ_FROM)

    total = len(df)
    count = 0

    try:
        # Iterate through the DataFrame row by row
        for index, row in df.iterrows():
            count += 1
            print(f"\nPROGRESS {count}/{total} ({int((count)/total*100)}%)")
            ga = row['ga']
            g, a = ga.split(":")
            version = row['version']
            print(f"Processing {ga}:{version}")
            if not override:
                if not pd.isnull(row['repo']) or not pd.isnull(row['err']):
                    print(f"\nSKIPPING {count}/{total} ({int((count)/total*100)}%)")
                    continue

            repo, repo_name, tag, tag_name, tag_commit, exact_match, repo_has_tests, err = None, None, None, None, None, None, None, None
            try:
                repo, tag = get_github_repo_and_tag(g, a, version)
                if repo is None:
                    err = Result.NO_GITHUB_LINK
                elif tag is None:
                    repo_name = repo.full_name
                    err = Result.NO_GITHUB_TAG
                else:
                    repo_name = repo.full_name
                    tag_name = tag.name
                    tag_commit = tag.commit
                    exact_match = tag.exact_match
                    repo_has_tests = has_tests(repo, tag.commit)
            except PomNotFoundException as e:
                print(e)
                err = Result.NO_POM

            df.at[index, 'repo'] = repo_name
            df.at[index, 'tag'] = tag_name
            df.at[index, 'tag'] = tag_name
            df.at[index, 'commit'] = tag_commit
            df.at[index, 'exact_match'] = exact_match
            df.at[index, 'has_tests'] = repo_has_tests
            df.at[index, 'err'] = err

    except KeyboardInterrupt as e:
        print(e)
        pass

    df.to_csv(WRITE_TO, index=False)
    print(f"The processed data has been written to {WRITE_TO}.")
