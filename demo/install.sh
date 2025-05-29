#!/bin/bash

cd c1 || exit
mvn clean install && cd ..

cd c2 || exit
mvn clean install && cd ..

cd c3 || exit
mvn clean install && cd ..

cd b || exit
mvn clean install && cd ..

cd a || exit
mvn clean install && cd ..

cd project || exit
mvn clean install && cd ..