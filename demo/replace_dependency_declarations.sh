#!/bin/bash

M2_REPOSITORY="$HOME/.m2/repository"  # Please set this variable to point to your .m2 folder

# Replaces the CoreMath dependency declarations in AdvancedMath (a)
marco-replacer a/pom.xml a/marco_pom.xml "$M2_REPOSITORY" --use_local
cat a/marco_pom.xml

# Replaces the CoreMath dependency declarations in BasicMath (b)
marco-replacer b/pom.xml b/marco_pom.xml "$M2_REPOSITORY" --use_local
cat b/marco_pom.xml

printf "\n\nThe new MaRCo-enhanced POMs are located in a/marco_pom.xml and b/marco_pom.xml."