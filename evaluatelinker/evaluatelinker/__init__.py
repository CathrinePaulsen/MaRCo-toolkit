import argparse

import evaluatelinker.extract_raw as extract_raw
import evaluatelinker.process_linking as process_linking
import evaluatelinker.process_test_jars as process_test_jars


def main():
    parser = argparse.ArgumentParser(description='Console script for the Maven-Github linker')
    subparsers = parser.add_subparsers(dest='command', help='commands')
    extract_raw.add_subparser(subparsers)
    process_linking.add_subparser(subparsers)
    process_test_jars.add_subparser(subparsers)
    args = parser.parse_args()

    match args.command:
        case 'extract_raw':
            extract_raw.extract_raw(args.save_as)
        case 'process_linking':
            process_linking.process_linking()
        case 'process_test_jars':
            process_test_jars.process_test_jars()
        case _:
            parser.print_help()

