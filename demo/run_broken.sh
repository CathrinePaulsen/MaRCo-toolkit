#!/bin/bash

cd project || exit
mvn exec:java -Dexec.mainClass="marco.demo.project.Project"
ll