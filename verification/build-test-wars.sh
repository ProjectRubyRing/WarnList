#!/bin/bash
#
# build-test-wars.sh <jars-dir> <out-dir>
#
# 検証用 WAR を作る (コンパイルは UBI 9.8 + Red Hat build of OpenJDK 21 のコンテナ内)。
#   iwinmichl-bad.war   … 実環境の ②③④⑤⑥⑦ (+⑧⑨⑫ 用エンドポイント) を再現する「修正前」
#   iwinmichl-fixed.war … implementation/app の是正を当てた「修正後」
#   ws-backend.war      … ③ の検証用 SOAP サービス (別デプロイ)
#
# <jars-dir> に必要な jar (Maven Central):
#   jakarta.servlet-api-6.0.0 / jakarta.annotation-api-2.1.1 / jakarta.xml.ws-api-4.0.2 /
#   jakarta.xml.soap-api-3.0.2 / jakarta.xml.bind-api-4.0.2 (以上コンパイル専用)
#   spring-{web,webmvc,core,beans,context,aop,expression,jcl}-6.2.19, micrometer-{observation,commons}-1.16.7
#   jstl-1.2.jar (修正前のみ: ⑦)、jakarta.transaction-api-2.0.1.jar (修正前のみ: ⑤)
set -euo pipefail

abspath() { ( cd "$1" && { pwd -W 2>/dev/null || pwd; } ); }
mkdir -p "${2:?out-dir}"
JARS="$(abspath "${1:?jars-dir}")"
OUT="$(abspath "$2")"
VERIF="$(abspath "$(dirname "$0")")"
IMPL="$(abspath "$(dirname "$0")/../implementation")"

MSYS_NO_PATHCONV=1 docker run --rm -u 0 \
    -v "${JARS}:/jars:ro" -v "${VERIF}:/verif:ro" -v "${IMPL}:/impl:ro" -v "${OUT}:/out" \
    registry.access.redhat.com/ubi9/ubi:9.8 bash -c '
set -euo pipefail
dnf -y -q --setopt=install_weak_deps=0 install java-21-openjdk-devel >/dev/null 2>&1
javac -version
RUNTIME_LIBS="$(ls /jars/spring-*.jar /jars/micrometer-*.jar)"
CP="$(ls /jars/jakarta.servlet-api-*.jar /jars/jakarta.annotation-api-*.jar /jars/jakarta.xml.ws-api-*.jar /jars/jakarta.xml.soap-api-*.jar /jars/jakarta.xml.bind-api-*.jar /jars/spring-*.jar /jars/micrometer-*.jar | tr "\n" ":")"

build() {  # build <name> <fixed:true|false>
    local name="$1" fixed="$2" root="/tmp/$1"
    rm -rf "${root}"; mkdir -p "${root}/WEB-INF/classes" "${root}/WEB-INF/lib"
    local srcs; srcs="$(find /verif/test-app/src -name "*.java")"
    if [ "${fixed}" = true ]; then
        srcs="${srcs} /impl/app/src/main/java/com/example/iwinmichl/web/MethodNotAllowedAdvice.java"
    fi
    javac --release 21 -parameters -encoding UTF-8 -cp "${CP}" -d "${root}/WEB-INF/classes" ${srcs}
    cp /verif/test-app/webapp/jstl.jsp /verif/test-app/webapp/jstl-fmt.jsp "${root}/"
    for j in ${RUNTIME_LIBS}; do cp "$j" "${root}/WEB-INF/lib/"; done
}

# ---- 修正前 ----
build bad false
cp /jars/jstl-1.2.jar /jars/jakarta.transaction-api-2.0.1.jar /tmp/bad/WEB-INF/lib/
cp /verif/test-app/descriptors/bad/jboss-deployment-structure.xml /tmp/bad/WEB-INF/
(cd /tmp/bad && jar --create --file /out/iwinmichl-bad.war .)

# ---- 修正後 ----
build fixed true
cp /verif/test-app/webapp/jstl-new.jsp /tmp/fixed/
cp /impl/app/src/main/webapp/WEB-INF/jboss-deployment-structure.xml /tmp/fixed/WEB-INF/
(cd /tmp/fixed && jar --create --file /out/iwinmichl-fixed.war .)

# ---- ③ 用 SOAP バックエンド ----
mkdir -p /tmp/ws/WEB-INF/classes
javac --release 21 -encoding UTF-8 -cp "${CP}" -d /tmp/ws/WEB-INF/classes $(find /verif/ws-backend/src -name "*.java")
(cd /tmp/ws && jar --create --file /out/ws-backend.war .)

ls -la /out
for w in /out/iwinmichl-bad.war /out/iwinmichl-fixed.war; do echo "== $w"; jar tf "$w" | grep -E "WEB-INF/lib/|jboss-deployment|\.jsp$" | sort; done
'
