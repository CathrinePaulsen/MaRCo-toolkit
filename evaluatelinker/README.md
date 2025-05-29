# evaluatelinker
This package contains the `evaluate-linker` script which generates the data used to evaluate the algorithm that links 
a given Maven GAV to a GitHub repository and tag against the 
[Reproducible Central](https://github.com/jvm-repo-rebuild/reproducible-central) dataset as ground truth.
The generated data is found in `resources/data`.

---
## Usage
The evaluation data can be reproduced by the following steps.
1. Install the `evaluate-linker` script: `pip install path/to/evaluatelinker`
2. Download the Reproducible Central dataset into the `resources` directory by running the `download_cr.sh` script
3. Extract the relevant raw data into a csv:
```
$ evaluate-linker extract_raw
```
4. Generate results from the raw data:
```
$ evaluate-linker process_linking
$ evaluate-linker process_test_jars   # Optional, adds data on available test suites and test jars
```
For further instructions, use the `--help` flag

---

## Data files

The output of running the script can be found in `resources/data` and are as follows:

### Raw data
* `linker_raw_original.csv`:
output of `$ evaluate-linker extract_raw`

* `linker_raw.csv`:
output of manually fixing or removing malformed datapoints in `linked_raw_original.csv`, e.g. fields involving variable 
substitutions 

### Processed data
* `linker_results.csv`:
output of applying the linking algorithm to `linker_raw.csv` with `$ evaluate-linker process_linking`

* `linker_results_manual_eval.csv`:
adds the column `manual_eval` to `linked_results.csv`, with a manual evaluation of mismatches between the linking 
algorithm and Reproducible Central.
Evaluations include:
  * `SAME_REPO` / "Actual Agreement": the different Reproducible Central repository redirects to the repository found 
     by the linking algorithm.
  * `CAT1_FAIL` / "Inconclusive": The evaluation of the data point is inconclusive. The algorithm finds the tag
    that according to naming conventions logically corresponds to the GAV, however,
    Reproducible Central reports a different commit SHA not connected to any tag. For
    these failures, tag linking may not return the exact source code the artifact was built
    from.
  * `CAT2_FAIL` / "Actual Disagreement": The algorithm gives a repository and/or tag that does not equal the ground
    truth. These are actual incorrect matches that are correctly labeled as incorrect.
  * `CAT3_FAIL` / "Actual Agreement": The algorithm and ground truth give different tags, but both tags point to the
    same commit. These are actually correct matches that are falsely labeled as incorrect.
  * `CAT4_FAIL` / "Invalid": The ground truth repository or tag no longer exists so the data point cannot be
    evaluated.

### Subsets
There are four subsets of `linker_results_manual_eval.csv` stored in `resources/data/subsets`.
These files do not provide extra information, but can be used to inspect only particular subsets of the result data.
