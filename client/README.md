## MaRCo (client-side)
This package contains the client-side code of MaRCo.
This includes all code related to expanding Maven POMs which requires access to
the compatibility mappings which are stored and served server-side.

### Installing the package
The client package requires the core package.
To install the client package, first install the core package:
```
$ pip install path/to/core/package
$ pip install path/to/client/package
```

#### External dependencies
Requires Jython 2.7.3, maven-artifact-3.0-alpha-1.jar
