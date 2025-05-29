import pandas as pd
import requests

from core import HTTP_headers
from evaluatelinker.utils import DATA_PATH


def add_subparser(subparsers):
    parser = subparsers.add_parser('process_test_jars',
                                   help='Checks for test jars on Maven Central and stores the result')

    parser.add_argument(
        '--save_as',
        type=str,
        default='linker_results.csv',
        help='Output file name (default: linker_results.csv)'
    )

    return parser


def process_test_jars(override=False, filename='linker_results.csv'):
    """
    For each GAV in the input dataset, checks whether it has a test jar on Maven Central.
    Returns True if a test jar is found, otherwise False
    """
    READ_FROM = DATA_PATH / "linker_results.csv"
    WRITE_TO = DATA_PATH/ filename

    input(f"Reading data from {READ_FROM} and storing the results in {WRITE_TO}. Press any key to continue.")

    df = pd.read_csv(READ_FROM)

    total = len(df)
    count = 0

    try:
        for index, row in df.iterrows():
            count += 1
            print(f"\nPROGRESS {count}/{total} ({int(count/total*100)}%)")

            if not override:
                if not pd.isnull(row['has_tests_jar']):
                    print(f"\nSKIPPING {count}/{total} ({int(count/total*100)}%)")
                    continue

            g, a = row['ga'].split(":")
            version = row['version']
            base_url = "https://repo1.maven.org/maven2"
            query = f"{base_url}/{g.replace('.', '/')}/{a}/{version}/{a}-{version}-tests.jar"
            response = requests.get(query, headers=HTTP_headers)
            has_tests_jar = True if response.status_code == 200 else False
            print(f"has_tests_jar={has_tests_jar}")

            df.at[index, 'has_tests_jar'] = has_tests_jar

    except KeyboardInterrupt as e:
        print(e)
        pass

    df.to_csv(WRITE_TO, index=False)
    print(f"The processed data has been written to {WRITE_TO}.")
