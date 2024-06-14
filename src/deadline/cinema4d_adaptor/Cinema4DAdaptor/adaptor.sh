#!/usr/bin/env bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

set -euo pipefail
C4DEXE="$1"
echo "C4D Executable: ${C4DEXE}"
echo "$@"
shift
ARGS="$@"
echo "  Passed argument list: ${ARGS}"

C4DVERSION=""

if [[ "$C4DEXE" =~ [^/]*cinema4dr([0-9\.]+)[^/]* ]]
then
  C4DVERSION="${BASH_REMATCH[1]}"
fi

C4DBASE=$(dirname "${C4DEXE}")

echo "Manually setting LD_LIBRARY_PATH, PATH, and PYTHONPATH to Cinema4D components"
LD_LIBRARY_PATH_=${LD_LIBRARY_PATH-""}
export LD_LIBRARY_PATH="${C4DBASE}/resource/modules/python/libs/*linux64*/lib64:${C4DBASE}/resource/modules/embree.module/libs/linux64:$LD_LIBRARY_PATH_"
export PATH="${C4DBASE}:$PATH"
PYTHONPATH_=${PYTHONPATH-""}
export PYTHONPATH="${C4DBASE}/resource/modules/python/libs/*linux64*/lib/python*/lib-dynload:${C4DBASE}/resource/modules/python/libs/*linux64*/lib64/python*:$PYTHONPATH_"

if [ -f "${C4DBASE}/setup_c4d_env" ]
then
  cd $C4DBASE
  echo "Sourcing setup_c4d_env from ${C4DBASE}/setup_c4d_env";
  source "${C4DBASE}/setup_c4d_env";
  # Hacky patch to allow for libwebkit2gtk to load if C4D provides a really old version of libstdc++.so
  if (( $(echo "2024.4 > $C4DVERSION" |bc -l) )); then
    echo "Cinema 4D version $C4DVERSION is less than 2024.4."
    echo "  Patching in libstdc++.so from system"
    export LD_LIBRARY_PATH="/usr/lib64:$LD_LIBRARY_PATH"
  fi
else
  echo "setup_c4d_env not found in ${C4DBASE}";
fi

echo "Executing C4D Executable with argument list after sourcing environment"
$C4DEXE ${ARGS[*]}
