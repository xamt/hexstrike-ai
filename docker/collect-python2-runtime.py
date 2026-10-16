"""Collect the fixed Python 2 runtime without copying its build toolchain."""

from __future__ import print_function

import os
import re
import shutil
import subprocess
import sys


GLIBC_LIBRARIES = re.compile(
    r"^(?:ld-linux.*|lib(?:c|m|pthread|dl|rt|util|resolv|anl))\.so(?:\..*)?$"
)


def shared_dependencies(path):
    """Return resolved non-glibc dependencies, rejecting unresolved libraries."""
    process = subprocess.Popen(["ldd", path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()
    output = output.decode("utf-8")
    if "not found" in output:
        raise RuntimeError("Unresolved runtime library: " + output)
    if process.returncode:
        message = output + error.decode("utf-8")
        if "not a dynamic executable" in message or "statically linked" in message:
            return []
        raise RuntimeError("Cannot inspect runtime library: " + message)
    result = []
    for line in output.splitlines():
        match = re.search(r"=> (/\S+)", line)
        if match and not GLIBC_LIBRARIES.match(os.path.basename(match.group(1))):
            result.append(match.group(1))
    return result


def collect(source, destination):
    """Copy Python and recursively collect external shared libraries."""
    shutil.copytree(source, destination, symlinks=False)
    compatibility = os.path.join(destination, "lib", "compat")
    os.makedirs(compatibility)
    pending = []
    for directory, _, files in os.walk(source):
        for filename in files:
            path = os.path.join(directory, filename)
            with open(path, "rb") as stream:
                if stream.read(4) == b"\x7fELF":
                    pending.append(path)
    visited = set()
    while pending:
        path = pending.pop()
        if path in visited:
            continue
        visited.add(path)
        for dependency in shared_dependencies(path):
            if not dependency.startswith(source + os.sep):
                target = os.path.join(compatibility, os.path.basename(dependency))
                if os.path.exists(target):
                    with open(dependency, "rb") as left, open(target, "rb") as right:
                        if left.read() != right.read():
                            raise RuntimeError("Conflicting library: " + target)
                else:
                    shutil.copy2(dependency, target)
            pending.append(dependency)


if __name__ == "__main__":
    collect(sys.argv[1], sys.argv[2])
