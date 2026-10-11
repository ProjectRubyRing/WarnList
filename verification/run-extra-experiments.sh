#!/bin/bash
#
# run-extra-experiments.sh — 追加の実測
#   E8 ④ の原因を DEBUG で確認する (修正前イメージ + 修正前 WAR、起動後に jboss-cli でロガーを DEBUG にして再デプロイ)
#   E9 ⑥ アプリ同梱の Log4j 2 は「どの除外指定で」有効になるか (除外なし / org.jboss.logmanager.log4j2 / org.apache.logging.log4j.api)
# 結果: results/extra-experiments.txt
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
RES="${HERE}/results"; OUT="${RES}/extra-experiments.txt"
: "${WARS:?}" "${L4J_JARS:?}"
WARS_W="$(cd "${WARS}" && { pwd -W 2>/dev/null || pwd; })"
L4J_W="$(cd "${L4J_JARS}" && { pwd -W 2>/dev/null || pwd; })"
SRC_W="$(cd "${HERE}/log4j-test" && { pwd -W 2>/dev/null || pwd; })"
JARS_W="$(cd "${JARS:?}" && { pwd -W 2>/dev/null || pwd; })"
DBENV=(-e DB_HOST=wl-mysql -e DB_NAME=iwinmichl -e DB_USER=app -e DB_PASSWORD=apppw)

wait_boot() {
    for i in $(seq 1 90); do
        docker logs wl-exp 2>&1 | grep -q -E "WFLYSRV0025|WFLYSRV0026" && break
        sleep 2
    done
    sleep 2
}

# ---- E9 用の WAR を 3 つ作る (UBI 9.8 + OpenJDK 21) ----
MSYS_NO_PATHCONV=1 docker run --rm -u 0 -v "${SRC_W}:/src:ro" -v "${L4J_W}:/l4j:ro" -v "${JARS_W}:/jars:ro" -v "${WARS_W}:/out" \
    registry.access.redhat.com/ubi9/ubi:9.8 bash -c '
set -euo pipefail
dnf -y -q --setopt=install_weak_deps=0 install java-21-openjdk-devel >/dev/null 2>&1
for v in none bad good; do
  r=/tmp/l4j-$v; mkdir -p $r/WEB-INF/classes $r/WEB-INF/lib
  javac --release 21 -cp "$(ls /jars/jakarta.servlet-api-*.jar):$(ls /l4j/log4j-api-*.jar)" -d $r/WEB-INF/classes $(find /src/src -name "*.java")
  cp /src/log4j2.xml $r/WEB-INF/classes/
  cp /l4j/*.jar $r/WEB-INF/lib/
  [ "$v" != none ] && cp /src/descriptors/$v.xml $r/WEB-INF/jboss-deployment-structure.xml
  (cd $r && jar --create --file /out/l4j-$v.war .)
done
ls -la /out | grep l4j'

{
echo "########## E8 ④ の原因を DEBUG で確認 (org.jboss.as.ee を DEBUG、CONSOLE ハンドラも DEBUG にして再デプロイ)"
docker rm -f wl-exp >/dev/null 2>&1
MSYS_NO_PATHCONV=1 docker run -d --name wl-exp --network wl-net "${DBENV[@]}" \
    -v "${WARS_W}/iwinmichl-bad.war:/opt/jboss-eap/standalone/deployments/iwinmichl.war:ro" wl-before:1 >/dev/null
wait_boot
MSYS_NO_PATHCONV=1 docker exec wl-exp /opt/jboss-eap/bin/jboss-cli.sh -c --commands='/subsystem=logging/logger=org.jboss.as.ee:add(level=DEBUG),/subsystem=logging/console-handler=CONSOLE:write-attribute(name=level,value=DEBUG),/deployment=iwinmichl.war:redeploy' >/dev/null 2>&1
sleep 8
docker logs wl-exp 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | grep -E "DEBUG \[org.jboss.as.ee\].*Not installing optional component" | sed 's/^.*Not installing/Not installing/' | cut -c1-330 | sort -u
docker rm -f wl-exp >/dev/null 2>&1

for v in none bad good; do
    echo; echo "########## E9 ⑥ Log4j 2 を同梱した WAR + 除外指定 = ${v}"
    case "$v" in
        none) echo "(jboss-deployment-structure.xml なし)";;
        bad)  echo "(<exclusions><module name=\"org.jboss.logmanager.log4j2\"/>)";;
        good) echo "(<exclusions><module name=\"org.apache.logging.log4j.api\"/>)";;
    esac
    MSYS_NO_PATHCONV=1 docker run -d --name wl-exp --network wl-net -p 18082:8080 "${DBENV[@]}" \
        -v "${WARS_W}/l4j-${v}.war:/opt/jboss-eap/standalone/deployments/l4j.war:ro" wl-after-system-remove:1 >/dev/null
    wait_boot
    curl -s http://localhost:18082/l4j/log
    sleep 1
    docker logs wl-exp 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | grep -E "hello-from-app-log4j2|WFLYSRV0274" | cut -c1-260
    docker rm -f wl-exp >/dev/null 2>&1
done
} > "${OUT}" 2>&1
cat "${OUT}"
