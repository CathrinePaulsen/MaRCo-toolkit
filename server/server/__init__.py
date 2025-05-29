"""Given a Maven coordinate, generate its compatible versions and store them in the compatibility store."""
import argparse
import json
from collections import defaultdict
from typing import Optional

from core import get_available_versions, scrape_available_versions, MavenMetadataNotFound
from server.config import COMPATIBILITY_STORE
from server.dynamic import dynamically_compatible
from server.exceptions import (BaseJarNotFoundException, CandidateJarNotFoundException,
                               CandidateMavenCompileTimeout, CandidateMavenTestTimeout, MavenNoPomInDirectoryException,
                               MavenResolutionFailedException, MavenCompileFailedException,
                               MavenSurefireTestFailedException, GithubRepoNotFoundException,
                               GithubTagNotFoundException)
from server.static import statically_compatible
from server.template.base_template import BaseTemplate


class CompatibilityResult:
    def __init__(self, group_id, artifact_id, v_base, v_cand, statically_compatible, dynamically_compatible, err=""):
        self.group_id = group_id
        self.artifact_id = artifact_id
        self.v_base = v_base
        self.v_cand = v_cand
        self.statically_compatible = statically_compatible
        self.dynamically_compatible = dynamically_compatible
        self.err = err

    def __repr__(self):
        return f"CompatibilityResult({self.group_id}:{self.artifact_id}:{self.v_base} => {self.v_cand}," \
               f" static={self.statically_compatible}, dynamic={self.dynamically_compatible}, err={self.err}"


def load_compatibility_store() -> defaultdict[str, set]:
    try:
        with open(COMPATIBILITY_STORE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return defaultdict(set)


def save_compatibility_store(compatibility_store: dict[str, set], write_to_path=COMPATIBILITY_STORE):
    with open(write_to_path, 'w') as f:
        return json.dump(compatibility_store, f, indent=4, default=set_default)


def set_default(obj):
    if isinstance(obj, set):
        return list(obj)
    raise TypeError


def get_compatibility_set(g: str, a: str, v: str, cv_versions: list[str], max_fail=None, use_local=False):
    """Given a GAV and a set of candidate versions, it returns the set of compatible candidates."""
    gav = f"{g}:{a}:{v}"
    compatibility_set = {v}  # A GAV is always compatible with itself

    # Prepare base for dynamic test: create persistent folder base_templates/g:a:v which contains
    # target/test-classes, target/generates-test-sources and target/surefire-report_BASE
    base_template = BaseTemplate(g, a, v, use_local=use_local)

    # Split versions into upgrades and downgrades relative to v
    # The cv_versions list is sorted in descending order of versions, so newer => older versions.
    idx_base = cv_versions.index(v)
    # Ascending upgrades to v, starting closest to v so most recent upgrade *last*
    upgrades = cv_versions[:idx_base][::-1]
    # Descending downgrades to v, starting closest to v so most recent downgrade *first*
    downgrades = cv_versions[idx_base + 1:]
    assert v not in upgrades and v not in downgrades

    # Run static and dynamic compatibility checks
    compat_store: defaultdict[str, set] = load_compatibility_store()

    # TODO: refactor the for-loops, they are near duplicate
    up_fails = 0
    for cv in upgrades:
        if max_fail is not None and up_fails >= max_fail:
            # If max_fail is set, stop after max_fail consecutive fails
            break

        try:
            if statically_compatible(g, a, v, cv):
                if dynamically_compatible(base_template, cv, use_local=use_local):
                    compatibility_set.add(cv)
                else:
                    up_fails += 1
            else:
                up_fails += 1
        except BaseJarNotFoundException:
            # Quit comparison if the base version cannot be found
            raise BaseJarNotFoundException(f"Could not find jar of the base version for compatibility comparison: "
                                           f"{gav}")
        except CandidateJarNotFoundException:
            continue  # Move on to next available candidate version

    down_fails = 0
    for cv in downgrades:
        if max_fail is not None and down_fails >= max_fail:
            # If max_fail is set, stop after max_fail consecutive fails
            break

        try:
            if statically_compatible(g, a, v, cv):
                if dynamically_compatible(base_template, cv, use_local=use_local):
                    compatibility_set.add(cv)
                else:
                    down_fails += 1
            else:
                down_fails += 1
        except BaseJarNotFoundException:
            # Quit comparison if the base version cannot be found
            raise BaseJarNotFoundException(f"Could not find jar of the base version for compatibility comparison: "
                                           f"{gav}")
        except CandidateJarNotFoundException:
            continue  # Move on to next available candidate version

    # Add compatibility mapping to JSON store
    stored_set = set(compat_store.get(gav, set()))
    stored_set.update(compatibility_set)
    compat_store[gav] = stored_set
    save_compatibility_store(compat_store)
    return stored_set


def get_compatibility_results_helper(g: str, a: str, v: str, cv_versions: list[str],
                                     base_template: BaseTemplate, static_only=False) -> list[CompatibilityResult]:
    compatibility_results = []
    max_consecutive_fails = 3   # Give up search after a certain number of incompatible versions in a row
    fails = 0
    # Run static and dynamic compatibility checks
    for i, cv in enumerate(cv_versions):
        if fails < max_consecutive_fails and i < 50:  # Don't do more than 100 versions or more than max fails
            try:
                if statically_compatible(g, a, v, cv):
                    try:
                        if static_only:
                            # A version pair being statically compatible tells us nothing of its dynamic compatibility
                            result = CompatibilityResult(g, a, v, cv, True, None)
                            fails = 0
                        else:
                            if dynamically_compatible(base_template, cv):
                                result = CompatibilityResult(g, a, v, cv, True, True)
                                fails = 0
                            else:
                                result = CompatibilityResult(g, a, v, cv, True, False)
                                fails += 1
                    except GithubRepoNotFoundException as e:
                        print(e)
                        result = CompatibilityResult(g, a, v, cv, True, False, err="NO_GITHUB")
                        fails += 1
                    except GithubTagNotFoundException as e:
                        print(e)
                        result = CompatibilityResult(g, a, v, cv, True, False, err="NO_TAG")
                        fails += 1
                    except CandidateMavenCompileTimeout as e:
                        print(e)
                        result = CompatibilityResult(g, a, v, cv, True, False, err="CAND_COMPILE_TIMEOUT")
                        fails += 1
                    except CandidateMavenTestTimeout as e:
                        print(e)
                        result = CompatibilityResult(g, a, v, cv, True, False, err="CAND_TEST_TIMEOUT")
                        fails += 1
                    except MavenNoPomInDirectoryException as e:
                        print(e)
                        result = CompatibilityResult(g, a, v, cv, True, False, err="NO_POM")
                        fails += 1
                    except MavenResolutionFailedException as e:
                        print(e)
                        result = CompatibilityResult(g, a, v, cv, True, False, err="NO_RESOLVE")
                        fails += 1
                    except MavenCompileFailedException as e:
                        print(e)
                        result = CompatibilityResult(g, a, v, cv, True, False, err="NO_COMPILE")
                        fails += 1
                    except MavenSurefireTestFailedException as e:
                        print(e)
                        result = CompatibilityResult(g, a, v, cv, True, False, err="NO_TEST")
                        fails += 1
                else:
                    # If two versions aren't statically compatible, then they also aren't dynamically compatible
                    result = CompatibilityResult(g, a, v, cv, False, False)
                    fails += 1
            except (BaseJarNotFoundException, CandidateJarNotFoundException):
                # Quit comparison if the base version cannot be found
                # If two versions aren't statically compatible, then they also aren't dynamically compatible
                result = CompatibilityResult(g, a, v, cv, False, False, err="NO_JAR")
            if result:
                compatibility_results.append(result)
    return compatibility_results


def get_compatibility_results(g: str, a: str, v: str, cv_versions: list[str], github_link=None,
                              static_only=False) -> list[CompatibilityResult]:
    """Given a GAV and a set of candidate versions, it returns the list of compatible candidates."""
    idx_split = cv_versions.index(v)
    # Versions list should be ordered by newest first (as it appears on maven repo)
    cv_versions_upper = cv_versions[:idx_split]
    cv_versions_lower = cv_versions[(idx_split+1):]
    cv_versions_upper.reverse()  # Reverse the upper so versions are evaluated going away from v

    # Prepare base for dynamic test: create persistent folder base_templates/g:a:v which contains
    # target/test-classes, target/generates-test-sources and target/surefire-report_BASE
    base_template = None if static_only else BaseTemplate(g, a, v, repo_name=github_link)

    compatible_lower = get_compatibility_results_helper(g, a, v, cv_versions_lower, base_template,
                                                        static_only=static_only)
    compatible_upper = get_compatibility_results_helper(g, a, v, cv_versions_upper, base_template,
                                                        static_only=static_only)
    compatibility_results = compatible_lower + compatible_upper

    return compatibility_results


def find_compatibility_results(g: str, a: str, v: str, max_num=None, silent=False, github_link=None,
                               static_only=False) -> Optional[list[CompatibilityResult]]:
    try:
        candidate_versions = get_available_versions(g, a, max_num=max_num)
        if v not in candidate_versions:
            # If we cannot find ourselves in available candidates, the maven-metadata.xml is out of date
            # Make a last ditch-effort by scraping
            candidate_versions = scrape_available_versions(g, a)
            if v not in candidate_versions:
                raise MavenMetadataNotFound(f"Could not find the base version for {g}:{a}:{v}")
    except MavenMetadataNotFound as e:
        print(e)
        candidate_versions = scrape_available_versions(g, a)
        if v not in candidate_versions:
            raise MavenMetadataNotFound(f"Could not find the base version for {g}:{a}:{v}")

    if not silent:
        print(f"Calculating compatibility set for {g}:{a}:{v} with candidates: {candidate_versions}")

    compatibility_results = get_compatibility_results(g, a, v, candidate_versions,
                                                      github_link=github_link, static_only=static_only)

    if not silent:
        print(f"Result:\n {g}:{a}:{v} has compatibility results {compatibility_results} "
              f"out of candidate versions {candidate_versions}")

    return compatibility_results


def find_compatible_versions(g: str, a: str, v: str, max_num=None, max_fail=None, silent=False, use_local=False):
    candidate_versions = get_available_versions(g, a, use_remote=use_local)

    if max_num is not None:
        idx_base_version = candidate_versions.index(v)
        upgrade_candidates = candidate_versions[max(0, idx_base_version - max_num):idx_base_version]
        downgrade_candidates = candidate_versions[idx_base_version+1 : idx_base_version+1+max_num]
        candidate_versions = upgrade_candidates + [v] + downgrade_candidates

    if not silent:
        print(f"Calculating compatibility set for {g}:{a}:{v} with candidates: {candidate_versions}")
        confirm = input('Confirm (y/n)?: ')
        if confirm != "y":
            print(f"Aborted.")
            return

    compatible_versions = get_compatibility_set(g, a, v, candidate_versions, max_fail=max_fail, use_local=use_local)

    if not silent:
        print(f"Result:\n {g}:{a}:{v} has compatible versions {compatible_versions} "
              f"out of candidate versions {candidate_versions}")

    return compatible_versions


def main():
    """
    Example: server-example -g com.fasterxml.jackson.core -a jackson-databind -v 2.16.0 --max_candidates 5
    """
    cli = argparse.ArgumentParser(description='Compatibility Mapper')
    cli.add_argument('-g', '--group_id', type=str, required=True, help='group id')
    cli.add_argument('-a', '--artifact_id', type=str, required=True, help='artifact id')
    cli.add_argument('-v', '--version_id', type=str, required=True, help='version id')
    cli.add_argument('--max_candidates', type=int, default=None, help='maximum number of downgrade/upgrade candidates to consider')
    cli.add_argument('--stop_after_n', type=int, default=None, help='stop after the given number of consecutive failures')
    cli.add_argument('--use_local', action='store_true', default=False,
                     help='Flag to indicate use of local Maven repository')

    args = cli.parse_args()
    g = args.group_id
    a = args.artifact_id
    v = args.version_id

    find_compatible_versions(g, a, v,
                             max_num=args.max_candidates, max_fail=args.stop_after_n, use_local=args.use_local)
