# MaRCo toolkit

MaRCo aims to improve resolution reliability by injecting missing dependencies and replacing version pins with compatible version ranges.
It consists of two components.
The Generator can be used to compute the compatible versions for a specific GAV.
The Replacer can be used with MaRCo-generated or custom compatibility mappings to explore compatibility-aware resolution.
Both can be combined to enable Maven to resolve version conflicts by ensuring a compatible version is resolved instead of the nearest-first version.

### Structure
* `client`: contains the code related to the client-side `MaRCo Replacer` tool.
* `core`: contains shared utility code.
* `server`: contains the code related to the server-side `MaRCo Generator` tool.

Each module contains its own `README.md` containing more detailed documentation and run instructions.

### Setup
To install the full MaRCo toolkit, run:
```
pip install core
pip install server
pip install client
```

Please note that the Generator executes the test code of the GAV you give it as input.
If you do not trust the GAV, please ensure you run the Generator in a sandboxed environment.
We provide a Dockerfile and a docker compose setup to ease deployment.

### Demo: Solving Diamond Dependencies with MaRCo
See the `demo` folder for a follow-along demo on how you can use MaRCo to automatically solve diamond dependencies in your project by using the Generator to generate compatibility mappings for your dependencies, and the Replacer to replace your pinned dependencies with compatible version ranges.


### Usage

`marco-generator` invokes the Generator:
```
$  marco-generator -h

usage: marco-generator [-h] -g GROUP_ID -a ARTIFACT_ID -v VERSION_ID
                       [--max_candidates MAX_CANDIDATES] [--stop_after_n STOP_AFTER_N]
                       [--use_local]

Compatibility Mapper

options:
  -h, --help            show this help message and exit
  -g GROUP_ID, --group_id GROUP_ID
                        group id
  -a ARTIFACT_ID, --artifact_id ARTIFACT_ID
                        artifact id
  -v VERSION_ID, --version_id VERSION_ID
                        version id
  --max_candidates MAX_CANDIDATES
                        maximum number of downgrade/upgrade candidates to consider
  --stop_after_n STOP_AFTER_N
                        stop after the given number of consecutive failures
  --use_local           Flag to indicate use of local Maven repository

```

`marco-replacer` invokes the Replacer:
```
$ marco-replacer -h

usage: marco-replacer [-h] [--use_local] read_from write_to m2_path

POM Expander

positional arguments:
  read_from    /path/to/pom/to/read/from
  write_to     /path/to/write/new/pom/to
  m2_path      /path/to/m2/repository
  override     Toggle to redo already expanded POMs

options:
  -h, --help   show this help message and exit
  --use_local  Flag to indicate use of local Maven repository
```
