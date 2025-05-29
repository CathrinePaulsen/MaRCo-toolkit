#!/bin/bash

# Generate the mappings for each version of the marco.demo:c dependency
marco-generator -g marco.demo -a c -v 1 --use_local
marco-generator -g marco.demo -a c -v 2 --use_local
marco-generator -g marco.demo -a c -v 3 --use_local

echo "MaRCo generated the following compatibility mappings:"
cat ../server/resources/compatibilities_demo.json