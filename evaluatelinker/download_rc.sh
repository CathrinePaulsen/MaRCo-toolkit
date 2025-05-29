#!/bin/bash

# Run this script to download the Reproducible Central dataset used by the evaluation of the Github linking algorithm
# NB: this script may fail in the future in case the Reproducible Central repository is (re)moved

REPO="git@github.com:jvm-repo-rebuild/reproducible-central.git"
COMMIT="e5e03d8d9337c1f99a889431cf6a294bb3fd0387"
TARGET_DIR="resources/reproducible-central"

# Clone the repository at the specified commit
git clone --no-checkout $REPO $TARGET_DIR
cd $TARGET_DIR || { echo "Failed to change directory to $TARGET_DIR"; exit 1; }
git checkout $COMMIT

echo "Repository successfully downloaded at commit $COMMIT in $TARGET_DIR"