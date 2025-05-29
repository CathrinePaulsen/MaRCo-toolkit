#!/bin/bash

cd project || exit
mvn exec:java -Dexec.mainClass="marco.demo.project.Project" -f manually_fixed_pom.xml
