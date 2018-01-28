# Ubuntu sysroot builder

Helps make C++ builds reproducible by compiling against an isolated sysroot
instead of using the system libraries.

Making C++ builds reproducible and portable is hard because of variations in
developers' machine configurations. The scripts in this repo create a minimal
Ubuntu installation with locked down versions of packages that can be used to
make the process more robust.

The inspiration comes from the
[Chromium project](https://chromium.googlesource.com/chromium/src/+/lkcr/docs/linux_sysroot.md),
that uses the same method for official releases.

## Creating the sysroot

1. Fill `packages.list` with the list of packages that you want to be installed
   in the sysroot. An example is included in this repo.

2. Run `lock_versions.py` to query Ubuntu repositories, get the latest versions
   of the packages, and save them into `packages.lock`. This will ensure
   reproducibility of the creation process in the future.

3. Run `./build.py` to download an unpack the packages in `./root`.

4. Run `./pack.py` to create a tarball.

## Try with Docker

The `example/` directory contains a fractal generation C program that uses
`libpng` that I copy-pasted from
[here](http://www.labbookpages.co.uk/software/imgProc/libPNG.html). The
Dockerfile creates a minimal Ubuntu container with `clang`, and compiles the
example program using headers and libraries from the sysroot (by passing the
`--sysroot` flag). While this one flag is enough for clang, gcc seems not to
be happy with it (more information on the [clang
page](https://clang.llvm.org/docs/CrossCompilation.html)).

```
cd example
make docker-shell
# On the docker shell
make example

# Running:
root@6fe28c74d7ad:/src/example# ./example 
./example: error while loading shared libraries: libpng12.so.0: cannot open shared object file: No such file or directory
```

As expected, the program can't run because `libpng` is not installed on the
host system.

## Notes

- Packages are not _installed_ into the sysroot, but just unpacked using
`dpkg-deb`. This is simpler and works well enough for compiling things, but will
for obvious reasons not create a `chroot`-able system in the same way as, say,
`debootstrap` does.

- The sysroot only provides the headers and the libraries, but not the compiler.

- Programs compiled in the sysroot will _not_ use the sysroot libraries at
runtime, but will try to load them from standard system libraries. Backwards
compatibility _usually_ means that this works fine as long as the sysroot
system is _older_ than the runtime system.

## Dependencies

```
sudo apt-get install aria2c pxz dpkg
```
