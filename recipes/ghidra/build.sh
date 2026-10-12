#!/bin/bash
set -euxo pipefail
dest="${PREFIX}/share/ghidra"
mkdir -p "${dest}" "${PREFIX}/bin"
cp -a ./* "${dest}/"
find "${dest}" -name '*.bat' -delete
for tool in ghidraRun:ghidraRun analyzeHeadless:support/analyzeHeadless pyghidraRun:support/pyghidraRun; do
  name="${tool%%:*}"; rel="${tool#*:}"
  [ -e "${dest}/${rel}" ] || continue
  cat > "${PREFIX}/bin/${name}" <<WRAP
#!/bin/bash
# conda wrapper: run Ghidra with the environment's openjdk
here="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
export JAVA_HOME="\${JAVA_HOME:-\$(cd "\${here}/.." && pwd)/lib/jvm}"
[ -x "\${JAVA_HOME}/bin/java" ] || export JAVA_HOME="\$(cd "\${here}/.." && pwd)"
exec "\${here}/../share/ghidra/${rel}" "\$@"
WRAP
  chmod +x "${PREFIX}/bin/${name}"
done
