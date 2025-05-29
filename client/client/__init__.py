"""Given a Maven project, expand its pom twice:
first with undeclared used dependencies, second expand SoftVers with ranges."""
import argparse
import os.path
import subprocess
from pathlib import Path
import shutil

import requests
from lxml import etree as ET

import core
from core import get_available_versions, namespace, dependencies_are_equal, get_text_of_child, GAV

RANGE_CONVERSION_SCRIPT = Path(__file__).parent.resolve() / "range_converter.py"
SERVER_URL = "http://127.0.0.1:5000"
# SERVER_URL = "http://marco-server:5000"


def get_parent_gav(pom: ET.Element, properties: dict) -> GAV | None:
    """
    Given a parsed pom, return the GAV of its parent if it exists, otherwise None
    """
    parent_tag = pom.find("./maven:parent", namespace)
    if parent_tag is not None:
        try:
            group_id = parent_tag.find("./maven:groupId", namespace).text
            artifact_id = parent_tag.find("./maven:artifactId", namespace).text
            version = parent_tag.find("./maven:version", namespace).text
            # If the version is a property, replace by its value
            if properties:
                version = properties.get(version, version)
            return GAV(group_id=group_id, artifact_id=artifact_id, version=version)
        except AttributeError:
            # If there is no groupId/artifactId/version, the parent is malformed, so we skip it
            pass
    return None


def get_import_gavs(pom: ET.Element, properties: dict) -> list[GAV]:
    """
    Given a parsed pom, return the list of the GAVS of its imported poms
    """
    gavs = []
    dependency_management_tag = pom.find(".//maven:dependencyManagement", namespace)
    if dependency_management_tag is not None:
        dependency_tags = dependency_management_tag.findall(".//maven:dependency", namespace)
        if dependency_tags is not None:
            for dependency_tag in dependency_tags:
                group_id = get_text_of_child(dependency_tag, "groupId")
                artifact_id = get_text_of_child(dependency_tag, "artifactId")
                version = get_text_of_child(dependency_tag, "version")
                # If the version is a property, replace by its value
                if properties:
                    version = properties.get(version, version)
                typ = get_text_of_child(dependency_tag, "type")
                scope = get_text_of_child(dependency_tag, "scope")
                if group_id and artifact_id and version and typ == "pom" and scope == "import":
                    gavs.append(GAV(group_id=group_id, artifact_id=artifact_id, version=version,
                                    typ=typ, scope=scope))
    return gavs


def convert_compat_list_to_range(g: str, a: str, compatible_versions: list[str], use_local=False):
    """Calls the range converter which uses Maven's ComparableVersion via Jython."""
    available_versions = get_available_versions(g, a, use_remote=use_local)
    # Need to call range converter via subprocess as it uses a different python environment (Python 2)
    output = subprocess.run(["jython", RANGE_CONVERSION_SCRIPT, "-a"] + available_versions +
                            ["-c"] + compatible_versions, stdout=subprocess.PIPE)
    print(output)
    return output.stdout


def is_softver(v: str) -> bool:
    range_characters = ["[", "]", "(", ")", ","]
    for char in range_characters:
        if char in v:
            return False
    return True


def version_is_property(version: str):
    """
    Returns True if the text in a version tag references a property eg <version>${junit.version}</version>
    """
    if version[:2] == "${" and version[-1] == "}":
        return True
    return False


def parse_properties_to_dict(tree: ET.Element):
    """
    Parses the list of <properties></properties> in the POM and stores the result in a dict where the key is the
    tag name and the value is the tag contents.
    """
    properties = tree.find(".//maven:properties", namespace)
    project_info = tree.find(".//maven:project", namespace)
    dict = {}
    # ${project.version} is sometimes used to declare versions, which does not occur in <properties> but <project>
    if project_info is not None:
        project_version = get_text_of_child(project_info, "version")
        if project_version is not None:
            dict["${project.version}"] = project_version
    dict = {}
    if properties is not None:
        for property in properties:
            if property.tag is ET.Comment:
                continue  # Skip comment nodes
            name = f"${{{ET.QName(property).localname}}}"
            dict[name] = property.text
    return dict


def replace_property(pom: ET.Element, replace_by: str, property: str, properties: dict) -> str:
    """Given a parsed POM, replace the given property value with the replace_by value."""
    property_name = property[2:-1]
    property_tag = pom.find(f".//maven:properties", namespace).find(f"maven:{property_name}", namespace)
    if property_tag is not None and property_tag.text is not None:
        previous_value = property_tag.text
        if properties[property] != previous_value:
            # We already replaced this property
            # TODO: get union of what is was previously replaced by, and what we want to replace it with now
            return properties[property]
        property_tag.text = replace_by
        property_tag.set("replaced_value", previous_value)
        return previous_value


def replace_dep(soft_dep: ET.Element, range: str, pom: ET.Element, properties: dict, write_to=None) -> bool:
    """Given a <dependency>-element, a range, and a pom, replace the content of the <version> subtag with the range."""
    replaced = False

    dependencies = pom.findall(".//maven:dependency", namespaces=namespace)
    for dep in dependencies:
        if dependencies_are_equal(dep, soft_dep):
            version_tag = dep.find(f".//maven:version", namespaces=namespace)
            # Commented out because putting a range in a property is not supported by Maven 3.9.6,
            # so we replace the property reference by the range directly instead
            # if version_is_property(version_tag.text):
            #     replaced_value = replace_property(pom, range, version_tag.text, properties)
            # else:
            #     replaced_value = version_tag.text
            #     version_tag.text = range
            replaced_value = version_tag.text
            version_tag.text = range
            if replaced_value:
                version_tag.set("replaced_value", replaced_value)
            else:
                version_tag.set("replaced_value", "unknown")
            replaced = True

    if write_to:  # To make testing easier
        pom.write(write_to, encoding='utf-8')

    return replaced


def get_compatible_version_list(g: str, a: str, v: str):
    """Query server for, and return, the pre-calculated compatible versions of GAV"""
    query = f"{SERVER_URL}/compatibilities/{g}:{a}:{v}"
    response = requests.get(query)
    if response.status_code == 200:
        return response.json()['compatible_versions']
    else:
        return None


def get_compatible_version_range(dep: ET.Element, properties: dict, use_local=False):
    """Given a <dependency>-element, query the server for the list of compatible versions, convert the list
    into a valid Maven range spec and return it."""
    g = get_text_of_child(dep, "groupId")
    a = get_text_of_child(dep, "artifactId")
    v = get_text_of_child(dep, "version")
    if version_is_property(v) and properties:
        v = properties.get(v, "")
    if not v:
        return None
    compatible_versions = get_compatible_version_list(g, a, v)
    if not compatible_versions:
        return None
    return convert_compat_list_to_range(g, a, compatible_versions, use_local=use_local).decode('utf-8')


def get_softver_deps(pom: ET.Element, effective_pom: ET.Element) -> (list[ET.Element], dict):
    """Returns a list of <dependency>-elements which have a <version>-tag that is a soft constraint."""
    dependencies = pom.findall(".//maven:dependency", namespace)
    properties = parse_properties_to_dict(effective_pom)
    softvers = []
    for dep in dependencies:
        v = get_text_of_child(dep, "version")
        scope = get_text_of_child(dep, "scope")
        scope = scope if scope else "compile"  # Non-specified scope defaults to "compile"
        if scope != "compile" and scope != "runtime":
            continue  # We only replace compile/runtime dependencies
        if version_is_property(v) and properties:
            v = properties.get(v, "")
        if v and is_softver(v):
            softvers.append(dep)
    return softvers, properties


def replace_softvers(pom: ET.Element, effective_pom: ET.Element, write_to=None, use_local=False):
    """Replaces all declared soft version constraints with their compatible ranges."""
    soft_deps, properties = get_softver_deps(pom, effective_pom)
    num_replaced = 0
    for dep in soft_deps:
        g = get_text_of_child(dep, "groupId")
        a = get_text_of_child(dep, "artifactId")
        v = get_text_of_child(dep, "version")
        if a == "plexus-utils":
            # Do not replace plexus-utils due to maven plugins relying on it
            continue
        if g == "commons-collections" and a == "commons-collections":
            # Do not replace commons-collections due to maven plugins relying on it
            continue
        if g == "org.apache.velocity" and a == "velocity":
            # Do not replace velocity due to maven plugins relying on it
            continue

        range = get_compatible_version_range(dep, properties, use_local=use_local)
        if not range:
            continue
        range = range.replace("\n", "")
        if not range:
            continue
        replaced = replace_dep(dep, range, pom, properties)
        print(f"Replaced {g}:{a}:{v} with {g}:{a}:{range}")
        num_replaced += 1 if replaced else 0

    if write_to:  # To make testing easier
        pom.write(write_to, encoding='utf-8')

    return num_replaced


def insert_deps(deps: list[ET.Element], pom: ET.Element, write_to=None):
    """Append the given dependencies to the pom's <dependencies> tag."""
    num_inserted = 0
    dependencies_tag = pom.find('./maven:dependencies', namespace)
    if dependencies_tag is None:
        # No dependencies to replace
        raise NotImplementedError("Top-level <dependencies> tag not found in the XML.")
    for dep in deps:
        version_tag = dep.find("version")  # Does not have namespace
        version_tag.set("inserted", "true")
        dependencies_tag.append(dep)
        num_inserted += 1

    if write_to:  # To make testing easier
        ET.indent(pom, space="  ", level=0)
        pom.write(write_to, encoding='utf-8')

    return num_inserted


def parse_missing(output: subprocess.CompletedProcess) -> list[ET.Element]:
    """Returns the XML Element representing the missing dependencies."""
    start = f"[INFO] Add the following to your pom to correct the missing dependencies:"
    grab_line = False
    # Need to wrap the missing dependencies in parent tag <dependencies></dependencies> otherwise XML parsing fails
    xml_strings = ["<dependencies>"]

    for line in output.stdout.splitlines():
        if line.startswith(start):
            grab_line = True

        elif grab_line:
            if line.startswith("[INFO]"):
                continue
            else:
                xml_strings.append(line)

    xml_strings.append("</dependencies>")

    root = ET.fromstringlist(xml_strings)

    missing_deps = []
    for dep in root.findall("dependency"):
        scope_tag = dep.find("scope")
        scope = scope_tag.text if scope_tag is not None and scope_tag.text is not None else "compile"
        if scope == "compile" or scope == "runtime":
            # Will only insert missing compile or runtime dependencies
            missing_deps.append(dep)

    return missing_deps


def expand_pom(project: Path, pom: ET.Element, pom_path=None, write_to=None):
    old_dir = os.getcwd()
    os.chdir(project)
    if pom_path:
        commands = ["mvn", "dependency:analyze-only", "-DoutputXML", "-f", pom_path]
    else:
        commands = ["mvn", "dependency:analyze-only", "-DoutputXML"]
    output = subprocess.run(commands, stdout=subprocess.PIPE, universal_newlines=True)
    missing_deps: list[ET.Element] = parse_missing(output)
    num_expansions = 0 if len(missing_deps) == 0 else insert_deps(missing_deps, pom, write_to=write_to)
    os.chdir(old_dir)
    return num_expansions


def clean_effective_pom(effective_pom_file: Path):
    # Clean effective pom from unwanted generated input, only keep the xml bit (content between first < and last >)
    with open(effective_pom_file, 'r') as f:
        xml_content = f.read()
    # Find the index of the first '<' character
    start_index = xml_content.find('<')

    # Find the index of the last '>' character
    end_index = xml_content.rfind('>')

    # Extract the substring between the first '<' and last '>'
    filtered_xml = xml_content[start_index:end_index+1]

    # Write filtered XML content back to the file
    with open(effective_pom_file, "w") as file:
        file.write(filtered_xml)


def expand_and_replace(read_from: Path, write_to: Path, m2_path: Path, write_to_copy=None, override=False, visited=None, injection=True, use_local=False):
    """
    Expand and replace the <read_from> POM and write new POM to <write_to>
    :param injection: if False, does not perform injection; useful for library POMs.
    :param read_from: POM to read from.
    :param write_to: POM to write the replacement to.
    :param m2_path: path to m2 folder used by Maven
    :param override: If True, do nothing if write_to already exists
    :param visited: None, or a set of already replaced <read_from>s
                        to avoid infinite recursion in case of circular imports
    """
    # Unless we are overriding, to nothing if <write_to> already exists
    if not override and Path.is_file(write_to):
        return 0, 0

    if visited is None:
        visited = set()
    if read_from in visited:
        # If we've already visited this <read_from>, return immediately
        print(f"Skipping already visited POM: {read_from}")
        return 0, 0
    visited.add(read_from)

    project_directory = read_from.parent
    assert Path.is_dir(project_directory)
    assert Path.is_file(read_from)
    assert read_from.parent == write_to.parent

    # TODO: remove this later.
    # Only execute this code when doing pass 2 of static_recursive (generating static_recursive_p2 library poms)
    # NB: I don't think this optimization is working anyway
    skip_me = project_directory / f"static_recursive_p3_{read_from.stem}.pom"
    if Path.is_file(skip_me):
        return 0, 0

    # 1. Generate effective pom.
    effective_pom_path = project_directory / "effective_pom.xml"
    try:
        # Generate the effective pom based on <read_from>
        if not Path.is_file(effective_pom_path):
            # Don't generate if we already have it, which is fine because MaRCo doesn't replace in properties,
            # nor does it replace pom-types (parents, imports), so no changes are expected for the properties
            subprocess.run(["mvn", "help:effective-pom", "-N", "-f",
                            read_from, f"-Doutput={effective_pom_path}"]).check_returncode()
            # Clean effective pom from unwanted generated input, only keep the XML (content between first < and last >)
            clean_effective_pom(effective_pom_path)
    except subprocess.CalledProcessError as e:
        print(e)
        # If we for some reason cannot generate the effective-pom, then use the <read_from> pom instead
        # e.g. where this error happens: org.eclipse.sisu:org.eclipse.sisu.plexus:0.3.0.M1
        effective_pom_path = read_from
    effective_pom = ET.parse(effective_pom_path)

    # 2. Do insertion
    # mvn dependency:analyze doesn't always report all used undeclared dependencies at first,
    # so we do multiple insertion rounds
    total_num_expansions = 0
    if injection:
        no_used_undeclared = False
        limit = 5
        count = 0
        while not no_used_undeclared and count < limit:
            count += 1
            pom = ET.parse(read_from)
            num_expansions = expand_pom(project_directory, pom)
            total_num_expansions += num_expansions
            if num_expansions > 0:
                ET.indent(pom, space="  ", level=0)  # Fix indentation, will remove whitespace from file however
                pom.write(write_to, encoding='utf-8')
                read_from = write_to  # The intermediate results in <write_to> becomes <read_from>
            else:
                no_used_undeclared = True
        print(f"Ran {count} rounds of dependency injection (limit={limit})")
    else:
        print(f"Injection is disabled.")

    # 3. Do replacement
    pom = ET.parse(read_from)
    try:
        num_replacements = replace_softvers(pom, effective_pom, use_local=use_local)
    except core.MavenMetadataNotFound as e:
        # Could not replace soft constraints due to missing metadata
        # (happens for net.jcip:jcip-annotations)
        num_replacements = 0
        print(e)
        pass
    if num_replacements > 0:
        pom.write(write_to, encoding='utf-8', xml_declaration=True)
        read_from = write_to  # The intermediate results in <write_to> becomes <read_from>
        if write_to_copy:
            pom.write(write_to_copy, encoding='utf-8', xml_declaration=True)

    # 4. Replace imported poms and parent poms
    pom = ET.parse(read_from)
    properties = parse_properties_to_dict(effective_pom)
    parent_gav = get_parent_gav(pom, properties)
    imported_gavs = get_import_gavs(pom, properties)
    print(f"Found parent={parent_gav}, and {len(imported_gavs)} imported poms")
    if parent_gav:
        imported_gavs.append(parent_gav)
    for gav in imported_gavs:
        dependency_path = m2_path / gav.group_id.replace(".", "/") / gav.artifact_id / gav.version
        dependency_pom_path = dependency_path / f"{gav.artifact_id}-{gav.version}.pom"
        dependency_pom_backup_path = dependency_path / f"original_{gav.artifact_id}-{gav.version}.pom"
        dep_copy = dependency_path / f"static_recursive_{gav.artifact_id}-{gav.version}.pom"  # TODO: set name
        if not override and Path.is_file(dep_copy):
            print(f"Skipping already replaced dependency {dep_copy}")
            continue
        print(f"Expanding pom of {dependency_path}")
        if not Path.is_file(dependency_pom_path):
            print(f"\n== Could not expand POM of {dependency_path}, does not exist")
            continue
        if Path.is_file(dependency_pom_backup_path):
            if override:
                # If overriding, restore original pom from backup
                shutil.copy(dependency_pom_backup_path, dependency_pom_path)
            # else:
            #     continue  # To avoid re-replacing dependencies we've already done
        else:
            # Backup pom if it hasn't been backed up already
            shutil.copy(dependency_pom_path, dependency_pom_backup_path)
        expansions, replacements = expand_and_replace(read_from=dependency_pom_path, write_to=dependency_pom_path,
                                                      m2_path=m2_path, write_to_copy=dep_copy, override=override, visited=visited,
                                                      injection=False)  # Disable injection for libraries, it rarely applies
        visited.add(dependency_pom_path)
        print(f"Made {expansions} expansions and {replacements} replacements in imported POM: {dependency_path}")

    return total_num_expansions, num_replacements


def main():
    """
    Example: client-example path/to/maven/project
    """
    parser = argparse.ArgumentParser(description='POM Expander')
    parser.add_argument('read_from', type=str, help='/path/to/pom/to/read/from')
    parser.add_argument('write_to', type=str, help='/path/to/write/new/pom/to')
    parser.add_argument('m2_path', type=str, help='/path/to/m2/repository')
    parser.add_argument('override', action='store_true', help='Toggle to redo already expanded POMs')
    parser.add_argument('--use_local', action='store_true', default=False,
                        help='Flag to indicate use of local Maven repository')

    args = parser.parse_args()
    read_from = Path(args.read_from).resolve()
    write_to = Path(args.write_to).resolve()
    m2_path = Path(args.m2_path).resolve()

    print(f"Performing POM expansion on {read_from}, writing to {write_to}, using m2_path={m2_path}")
    confirm = input('Confirm (y/n)?: ')
    if confirm == "y":
        expansions, replacements = expand_and_replace(read_from=read_from, write_to=write_to,
                                                      m2_path=m2_path, override=args.override, use_local=args.use_local)
        print(f"Made {expansions} expansions, and {replacements} replacements")
    else:
        print(f"Aborted.")

