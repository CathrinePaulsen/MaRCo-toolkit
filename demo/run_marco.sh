#!/bin/bash

# Dependencies b and a are re-installed as a convenient way to
# put the new MaRCo-enhanced POM files in the correct .m2 folder for the demo
cd b || exit
mvn clean install -f marco_pom.xml -DskipTests && cd ..

cd a || exit
mvn clean install -f marco_pom.xml -DskipTests && cd ..

cd project || exit
mvn exec:java -Dexec.mainClass="marco.demo.project.Project"
