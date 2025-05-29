## MaRCo (server-side)
This package contains the server-side code of MaRCo.
This includes all code related to generating and serving compatibility mappings.

### Installing the package
The server package requires the core package.
To install the server package, first install the core package:
```
$ pip install path/to/core/package
$ pip install path/to/server/package
```

### Serving compatibility mappings
To start the server that serves the compatibility mappings, run `docker compose up` if using Docker or
run `run_server.sh` otherwise.
