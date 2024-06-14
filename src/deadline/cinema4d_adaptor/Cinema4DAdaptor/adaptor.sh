#!/usr/bin/env bash
C4DEXE="$1"
echo "C4D Executable: ${C4DEXE}"
echo "$@"
shift
ARGS="$@"
echo "  Passed argument list: ${ARGS}"


C4DBASE=$(dirname "${C4DEXE}")
if [ -f "${C4DBASE}/setup_c4d_env" ]
then
  cd $C4DBASE
  echo "Sourcing setup_c4d_env from ${C4DBASE}/setup_c4d_env";
  source "${C4DBASE}/setup_c4d_env";
else
  echo "setup_c4d_env not found in ${C4DBASE}";
fi

echo "Executing C4D Executable with argument list after sourcing environment"
$C4DEXE ${ARGS[*]}
