# Demo: solving diamond dependencies with MaRCo

The goal of MaRCo is to provide a more reliable dependency resolution process that minimizes dependency-related issues.
Diamond dependencies are one such issue.

This demo shows how MaRCo prevents diamond dependencies from occurring, saving developers time that otherwise would've 
been spent manually figuring out how to fix their dependencies.

## Setup
Imagine we are working on a project with the following dependencies:
```
            project
           /       \
 AdvancedMath:1    BasicMath:1
          |         |
     CoreMath:2    CoreMath:1
```
Here, `project` is a simple application which performs some calculations by calling methods from the `AdvancedMath` and
`BasicMath` libraries and prints the result.

Using the regular Maven dependency resolver, Maven will resolve version 2 of `CoreMath` which causes our project to break
because version 1 and 2 are not compatible.

To see the output of trying to run the project, run `install.sh` followed by `run_broken.sh`:
```shell
[INFO] --- exec:3.5.0:java (default-cli) @ project ---
This is a demo project! Performing calculations...
Addition (2 + 3): 5
[WARNING]
java.lang.Exception: The specified mainClass doesn't contain a main method with appropriate signature.
    at org.codehaus.mojo.exec.ExecJavaMojo.lambda$execute$0 (ExecJavaMojo.java:291)
    at java.lang.Thread.run (Thread.java:840)
Caused by: java.lang.NoSuchMethodError: 'int marco.demo.c.CoreMath.subtract(int, int)'
    at marco.demo.b.BasicMath.minus (BasicMath.java:13)
    at marco.demo.project.Project.main (Project.java:13)
    at org.codehaus.mojo.exec.ExecJavaMojo.doMain (ExecJavaMojo.java:375)
    at org.codehaus.mojo.exec.ExecJavaMojo.doExec (ExecJavaMojo.java:364)
    at org.codehaus.mojo.exec.ExecJavaMojo.lambda$execute$0 (ExecJavaMojo.java:286)
    at java.lang.Thread.run (Thread.java:840)
[INFO] ------------------------------------------------------------------------
[INFO] BUILD FAILURE
[INFO] ------------------------------------------------------------------------
```
---

## Solving the issue manually
If this happens in a real-world scenario, it would be up to us to manually override Maven's dependency resolution to 
find a dependency set that works.

To do this, we may have to scour through the change logs of `CoreMath` to figure out *which* breaking changes are 
introduced *when* and based on this find a version that is compatible with both `AdvancedMath:1` and `BasicMath:1`.
After manually evaluating the code changes, we determine that `CoreMath:1` and `CoreMath:2` are neither forwards nor backwards compatible.
However, we see that `CoreMath:3` adds backwards compatibility to `CoreMath:1`, so we manually override our project's 
POM to resolve `CoreMath:3` by adding the following:
```
<!-- Manual fix overriding the resolved version of CoreMath -->
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>marco.demo</groupId>
            <artifactId>c</artifactId>
            <version>3</version>
        </dependency>
    </dependencies>
</dependencyManagement>
```

To see the output of running the project after manually overriding the version, run `run_manual.sh`:
```
[INFO] --- exec:3.5.0:java (default-cli) @ project ---
This is a demo project! Performing calculations...
Addition (2 + 3): 5
Subtraction (5 - 3): 2
Multiplication (2 * 3): 6
Division (6 / 2): 3
[INFO] ------------------------------------------------------------------------
[INFO] BUILD SUCCESS
[INFO] ------------------------------------------------------------------------
```

Dependency issues like this can be complicated and time-consuming to manually figure out and detangle, which is where 
MaRCo comes in.

---
## Solving the issue automatically with MaRCo
MaRCo provides a more reliable resolution process by modifying the dependency declaration with additional compatibility 
information.
It does this by replacing the previously pinned versions with compatible version ranges.
The compatible version ranges ensure that a compatible version is resolved, or resolution fails altogether.

### Step 0: Setting up the server
To set up the local Maven Repository and Compatibility Store used for the demo, please execute the script `setup_server.sh` 
in a separate shell.

### Step 1: Generating the compatibility mappings
To obtain the compatible version ranges, MaRCo generates compatibility mappings for each dependency using 
cross-version testing and bytecode differencing.

To generate the compatibility mappings for `CoreMath`, execute the script `generate_compatibility_mappings.sh`,
which results in the following compatibility mappings stored in `server/resources/compatibilities_demo.json`:
```
{
    "marco.demo:c:1": ["3","1"],
    "marco.demo:c:2": ["3","2"],
    "marco.demo:c:3": ["3"]
}
```

The mappings show that both `CoreMath:1` and `CoreMath:2` are behaviorally compatible with `CoreMath:3`,
without having to manually scour version change logs ourselves.

### Step 2: Replacing pinned versions with version ranges
MaRCo replaces pinned versions with version ranges constructed from the compatibility mappings.

To replace the pinned `CoreMath` version, execute the script `replace_dependency_declarations.sh`.
The new MaRCo-enhanced POMs are located in `a/marco_pom.xml` and `b/marco_pom.xml`, and look like the following:
```
$ cat a/marco_pom.xml
<?xml version='1.0' encoding='UTF-8'?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://www.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>marco.demo</groupId>
    <artifactId>a</artifactId>
    <version>1</version>

    <dependencies>
        <!-- Dependency C: Core Math -->
        <dependency>
            <groupId>marco.demo</groupId>
            <artifactId>c</artifactId>
            <version replaced_value="2">[2,3]</version>
        </dependency>
    </dependencies>
</project>

$ cat b/marco_pom.xml
<?xml version='1.0' encoding='UTF-8'?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://www.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>marco.demo</groupId>
    <artifactId>b</artifactId>
    <version>1</version>

    <dependencies>
        <!-- Dependency C: Core Math -->
        <dependency>
            <groupId>marco.demo</groupId>
            <artifactId>c</artifactId>
            <version replaced_value="1">[1],[3]</version>
        </dependency>
    </dependencies>
</project>
```

You can see that MaRCo has replaced the version declarations of `CoreMath` with their compatible version ranges.

To check whether this MaRCo fix has solved our diamond dependency issue, we re-run our project with the MaRCo-applied fix
using `run_marco.sh`:
```
[INFO] --- exec:3.5.0:java (default-cli) @ project ---
This is a demo project! Performing calculations...
Addition (2 + 3): 5
Subtraction (5 - 3): 2
Multiplication (2 * 3): 6
Division (6 / 2): 3
[INFO] ------------------------------------------------------------------------
[INFO] BUILD SUCCESS
[INFO] ------------------------------------------------------------------------
```

As we can see, re-running the project the MaRCo-enhanced POMs solves the diamond dependency issue automatically.

