> DISCLAIMER: Work in progress

# PyFV3

PyFV3 is a Python version of the [FV3 dynamical core](https://github.com/GEOS-ESM/FVdycoreCubed_GridComp). PyFV3 is based on [GridTools GT4Py](https://github.com/GridTools/gt4py/) and offers CPU and GPU backend options.
This repository includes infrastructure to run regression tests against serialized output from original the Fortran model. Serialization data was captured with [Serialbox](https://github.com/GridTools/serialbox).

## QuickStart

1. Ensure you have docker installed and working. Be sure to complete any required post-installation instructions (e.g. for [Linux systems](https://docs.docker.com/engine/install/linux-postinstall/)) such that you can run docker without being `root`.
2. You can build the image, download the data, and run the tests using:

```shell
make build savepoint_tests savepoint_tests_mpi
```

If you want to develop code, you should also install the linting requirements and git hooks locally

```shell
pip install -c constraints.txt -r requirements/requirements_lint.txt
pre-commit install
```

> TODO: where did linting move to?

## Getting started, in more detail

If you want to build the main PyFV3 docker image, run

```shell
make build
```

If you want to download test data run

```shell
make get_test_data
```

and the c12_6ranks_standard data will be download into the `test_data` directory.

MPI parallel tests (that run that way to exercise halo updates in the model) can be run with:

```shell
make savepoint_tests_mpi
```

## Running tests interactively inside a container

If you to prefer to work interactively inside the fv3core container, get the test data and build the docker image (see above):

```shell
make get_test_data
make build
```

Testing can be run with this data from `/port_dev` inside the container:

```shell
make dev
```

Then inside the container:

```shell
pytest -v -s --data_path=/test_data/ /port_dev/tests --which_modules=<stencil name>
```

The `<stencil name>` can be determined from the associated `Translate<Stencil>` class. e.g. `TranslateXPPM` is a test class that translate data serialized from a run of the fortran model, and `XPPM` is the name you can use with `--which_modules`.

### Test options

All of the make endpoints involved running tests can be prefixed with the `TEST_ARGS` environment variable to set test options or pytest CLI args (see below) when running inside the container.

* `--which_modules <modules to run tests for>` - comma separated list of which modules to test (defaults to running all of them).

* `--print_failures` - if your test fails, it will only report the first datapoint. If you want all the nonmatching regression data to print out (so you can see if there are patterns, e.g. just incorrect for the first 'i' or whatever), this will print out for every failing test all the non-matching data.

* `--failure_stride` - when printing failures, print every n failures only.

* `--data_path` - path to where you have the `Generator*.dat` and `*.json` serialization regression data. Defaults to current directory.

* `--backend` - which backend to use for the computation. Options: `[numpy, gt:cpu_ifirst, gt:cpu_first, gt:gpu, cuda]`. Defaults to `numpy`.
* `--python_regression` - Run the tests that have Python based regression data. Only applies to running parallel tests (savepoint_tests_mpi)

Pytest provides a lot of options, which you can see by `pytest --help`. Here are some common options for our tests, which you can add to `TEST_ARGS`:

* `-r` - is used to report test types other than failure. It can be provided `s` for skipped (e.g. tests which were not run because earlier tests of the same stencil failed), `x` for "expected failure" (short "xfail") tests (like tests with no translate class), or `p` for pass. For example, to report skipped and xfail tests you would use `-rsx`.

* `--disable-warnings` - will stop all warnings from being printed at the end of the tests, for example warnings that translate classes are not yet implemented.

* `-v` - will increase test verbosity, while `-q` will decrease it.

* `-s` - will let stdout print directly to console instead of capturing the output and printing it when a test fails only. Note that logger lines will always be printed both during (by setting log_cli in our `pytest.ini` file) and after tests.

* `-m` - will let you run only certain groups of tests. For example, `-m=parallel` will run only parallel stencils, while `-m=sequential` will run only stencils that operate on one rank at a time.

* `--threshold_overrides_file` - will read a yaml file with error thresholds specified for specific backend and platform (docker or metal) configurations, overriding the max_error thresholds defined in the Translate classes. Format of the yaml file is described [here](tests/savepoint/translate/overrides/README.md).

* `--dperiodic` - run tests on a doubly-periodic domain. Will look for only one tile's worth of test data and parallel tests will be run with a TileCommunicator instead of a CubedSphereCommunicator.

**NOTE:** FV3 is current assumed to be by default in a "development mode", where stencils are checked each time they execute for code changes (which can trigger regeneration). This process is somewhat expensive, so there is an option to put FV3 in a performance mode by telling it that stencils should not automatically be rebuilt:

```shell
$ export FV3_STENCIL_REBUILD_FLAG=False
```

> Question: Is this env variable still alive? I can't find any usage inside this repo...

## Porting a new stencil

1. Find the location in the fv3gfs-fortran repo code where the save-point is to be added, e.g. using

```shell
$ git grep <stencil_name> <checkout of fv3gfs-fortran>
```

2. Create a `translate` class from the serialized save-point data to a call to the stencil or function that calls the relevant stencil(s).

These are usually named `tests/savepoint/translate/translate_<lowercase name>`

Import this class in the `tests/savepoint/translate/__init__.py` file

3. Write a Python function wrapper that the translate function (created above) calls.

By convention, we name these `fv3core/stencils/<lower case stencil name>.py`

4. Run the test, either with one name or a comma-separated list

```shell
$ make dev_tests TEST_ARGS="-–which_modules=<stencil name(s)>"
```

**Please also review the [Porting conventions](#porting-conventions) section for additional explanation**

## Installation

### Docker Image

To build the PyFV3 image with required dependencies for running the Python code, run

```shell
make build
```

## Relevant repositories

- https://github.com/GridTools/serialbox -
  Serialbox generates serialized data when the Fortran model runs and has bindings to manage data from Python

- https://github.com/GEOS-ESM/FVdycoreCubed_GridComp -
  This is the existing Fortran model decorated with serialization statements from which the test data is generated

- https://github.com/GridTools/gt4py -
  Python package for the DSL language

## License

PyFV3 is provided under the terms of the [GPLv3](https://www.gnu.org/licenses/gpl-3.0.en.html) license.

# Development guidelines

## File structure / conventions

The main functionality of the FV3 dynamical core, which has been ported from the Fortran version in the fv3gfs-fortran repo, is defined using GT4py stencils and python 'compute' functions in fv3core/stencils. The core is comprised of units of calculations defined for regression testing. These were initially generally separated into distinct files in fv3core/stencils with corresponding files in `tests/savepoint/translate/translate_<unit>.py` defining the translation of variables from Fortran to Python. Exceptions exist in cases where topical and logical grouping allowed for code reuse. As refactors optimize the model, these units may be merged to occupy the same files and even methods/stencils, but the units should still be tested separately, unless determined to be redundant.

The core has most of its calculations happening in GT4py stencils, but there are still several instances of operations happening in Python directly, which will need to be replaced with GT4py code for optimal performance.

The namelist and grid are global variables defined in `pyFV3/_config.py`. The namelist is 'flattened' so that the grouping name of the option is not required to access the data (we may want to change this).

The grid variables are mostly 2d variables and are 'global' to the model thread per mpi rank. The grid object also contains domain and layout information relevant to the current rank being operated on.

Utility functions in `pyFV3/utils/` include:

* `functional_validation.py` utility functions to generate subset functions.

The `tests/` directory currently includes a framework for translating fields serialized (using Serialbox from GridTools) from a Fortran run into gt4py storages that can be inputs to fv3core unit computations, and compares the results of the ported code to serialized data following a unit computation.

The build system uses the `Makefile`.

## Model Interface

The top level functions `fv_dynamics` and `fv_sugridz` can currently only be run in parallel using mpi with a minimum of 6 ranks (there are a few other units that also require this, e.g. whenever there is a halo update involved in a unit). These are the interface to the rest of the model and currently have different conventions than the rest of the model.

* A 'state' object (currently a SimpleNamespace) stores pointers to the allocated data fields
* Most functions within dyn_core can be run sequentially per rank
* Currently a list of ArgSpecs must decorate an interface function, where each ArgSpec provides useful information about the argument, e.g.: `@state_inputs( ArgSpec("qvapor", "specific_humidity", "kg/kg", intent="inout")`
  * The format is (fortran_name, long_name, units, intent)
  * We currently provide a duplicate of most of the metadata in the specification of the unit test, but that may be removed eventually.
* Then the function itself, e.g. fv_dynamics, has arguments of 'state', 'comm' (the communicator) and all of the scalar parameters being provided.

### Porting conventions

Generation of regression data occurs in the fv3gfs-fortran repo (https://github.com/VulcanClimateModeling/fv3gfs-fortran) with serialization statements and a build procedure defined in `tests/serialized_test_data_generation`. The version of data this repo currently tests against is defined in `FORTRAN_SERIALIZED_DATA_VERSION` in this repo's `docker/Makefile.image_names`. Fields serialized are defined in Fortran code with serialization comment statements such as:

```shell
    !$ser savepoint C_SW-In
    !$ser data delpcd=delpc delpd=delp ptcd=ptc
```

where the name being assigned is the name the fv3core uses to identify the variable in the test code. When this name is not equal to the name of the variable, this was usually done to avoid conflicts with other parts of the code where the same name is used to reference a differently sized field.

The majority of the logic for translating from data serialized from Fortran to something that can be used by Python, and the comparison of the results, is encompassed by the main Translate class in the tests/savepoint/translate/translate.py file. Any units not involving a halo update can be run using this framework, while those that need to be run in parallel can look to the ParallelTranslate class as the parent class in tests/savepoint/translate/parallel_translate.py. These parent classes provide generally useful operations for translating serialized data between Fortran and Python specifications, and for applying regression tests.

A new unit test can be defined as a new child class of one of these, with a naming convention of `Translate<Savepoint Name>` where `Savepoint Name` is the name used in the serialization statements in the Fortran code, without the `-In` and `-Out` part of the name. A translate class can usually be minimally specify the input and output fields. Then, in cases where the parent compute function is insuffient to handle the complexity of either the data translation or the compute function, the appropriate methods can be overridden.

For Translate objects
  - The init function establishes the assumed translation setup for the class, which can be dynamically overridden as needed.
  - the parent compute function does:
    - Makes gt4py storages of the max shape (grid.npx+1, grid.npy+1, grid.npz+1) aligning the data based on the start indices specified. (gt4py requires data fields have the same shape, so in this model we have buffer points so all calculations can be done easily without worrying about shape matching).
    - runs the compute function (defined in self.compute_func) on the input data storages
    - slices the computed Python fields to be compared to fortran regression data
  - The unit test then uses a modified relative error metric to determine whether the unit passes
  - The init method for a Translate class:
    - The input (self.in_vars["data_vars"]) and output(self.out_vars) variables are specified in dictionaries, where the keys are the name of the variable used in the model and the values are dictionaries specifying metadata for translation of serialized data to gt4py storages. The metadata that can be specied to override defaults are:
    - Indices to line up data arrays into gt4py storages (which all get created as the max possible size needed by all operations, for simplicity): "istart", "iend", "jstart", "jend", "kstart", "kend". These should be set using the 'grid' object available to the Translate object, using equivalent index names as in the declaration of variables in the Fortran code, e.g. real:: cx(bd%is:bd%ie+1,bd%jsd:bd%jed ) means we should assign. Example:

```python
      self.in_vars["data_vars"]["cx"] = {"istart": self.is\_, "iend": self.ie + 1,
                                         "jstart": self.jsd, "jend": self.jed,}
```
  - There is only a limited set of Fortran shapes declared, so abstractions defined in the grid can also be used,
    e.g.: `self.out_vars["cx"] = self.grid.x3d_compute_domain_y_dict()`. Note that the variables, e.g. `grid.is\_` and `grid.ie` specify the 'compute' domain in the x direction of the current tile, equivalent to `bd%is` and `bd%ie` in the Fortran model EXCEPT that the Python variables are local to the current MPI rank (a subset of the tile face), while the Fortran values are global to the tile face. This is because these indices are used to slice into fields, which in Python is 0-based, and in Fortran is based on however the variables are declared. But, for the purposes of aligning data for computations and comparisons, we can match them in this framework. Shapes need to be defined in a dictionary per variable including `"istart"`, `"iend"`, `"jstart"`, `"jend"`, `"kstart"`, `"kend"` that represent the shape of that variable as defined in the Fortran code. The default shape assumed if a variable is specified with an empty dictionary is `isd:ied, jsd:jed, 0:npz - 1` inclusive, and variables that aren't that shape in the Fortran code need to have the 'start' indices specified for the in_vars dictionary , and 'start' and 'end' for the out_vars.
    - `"serialname"` can be used to specify a name used in the Fortran code declaration if we'd like the model to use a different name
    - `"kaxis"`: which dimension is the vertical direction. For most variables this is '2' and does not need to be specified. For Fortran variables that assign the vertical dimension to a different axis, this can be set to ensure we end up with 3d storages that have the vertical dimension where it is expected by GT4py.
    - `"dummy_axes"`: If set this will set of the storage to have singleton dimensions in the axes defined. This is to enable testing stencils where the full 3d data has not been collected and we want to run stencil tests on the data for a particular slice.
    - `"names_4d"`: If a 4d variable is being serialized, this can be set to specify the names of each 3d field. By default this is the list of tracers.
    - input variables that are scalars should be added to `self.in_vars["parameters"]`
    - `self.compute_func` is the name of the model function that should be run by the compute method in the translate class
    - `self.max_error` overrides the parent classes relative error threshold. This should only be changed when the reasons for non-bit reproducibility are understood.
    - `self.max_shape` sets the size of the gt4py storage created for testing
    - `self.ignore_near_zero_errors[<varname>] = True`: This is an option to let some fields pass with higher relative error if the absolute error is very small
    - `self.skip_test`: This is an option to jump over the test case, to be used in the override file for temporary deactivation of tests.

For `ParallelTranslate` objects:
  - Inputs and outputs are defined at the class level, and these include metadata such as the "name" (e.g. understandable name for the symbol), dimensions, units and n_halo(numb er of halo lines)
  - Both `compute_sequential` and `compute_parallel` methods may be defined, where a mock communicator is used in the `compute_sequential` case
  - The parent assumes a state object for tracking fields and methods exist for translating from inputs to a state object and extracting the output variables from the state. It is assumed that Quantity objects are needed in the model method in order to do halo updates.
  - `ParallelTranslate2Py` is a slight variation of this used for many of the parallel units that do not yet utilize a state object and relies on the specification of the same index metadata of the Translate classes
  - `ParallelTranslateBaseSlicing` makes use of the state but relies on the Translate object of self._base, a Translate class object, to align the data before making quantities, computing and comparing.

### Debugging Tests

Pytest can be configured to give you a pdb session when a test fails. To route this properly through docker, you can run:

```bash
TEST_ARGS="-v -s --pdb" RUN_FLAGS="--rm -it" make tests
```

This can be done with any pytest target, such as `make savepoint_tests` and `make savepoint_tests_mpi`.

### GEOS API

The `GeosDycoreWrapper` class provides an API to run the dynamical core in a Python component of a GEOS model run. A `GeosDycoreWrapper` object is initialized with a namelist, communicator, and backend, which creates the communicators, partitioners, dycore state, and dycore object required to run the Pace dycore. A wrapper object takes numpy arrays of `u, v, w, delz, pt, delp, q, ps, pe, pk, peln, pkz, phis, q_con, omga, ua, va, uc, vc, mfxd, mfyd, cxd, cyd,` and `diss_estd` and returns a dictionary containing numpy arrays of those same variables. Wrapper objects contain a `timer` attrubite that tracks the amount of time moving input data to the dycore state, running the dynamical core, and retrieving the data from the state.
