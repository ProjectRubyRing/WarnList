#!/bin/bash
#
# run-tls-experiments.sh — ① の追加質問 (Q1/Q2) と対処方式の比較を実測する
#   E1 修正前イメージ: ExtraSLB の p12 を別ディレクトリに置き -D で渡している状態 (= 現行) のブート警告
#   E2 修正前イメージ: Q2 の確認として -Djavax.net.ssl.keyStore も渡す → applicationKS の警告は変わるか
#   E3 修正前イメージ: 自前トラストストアのパスを誤った場合 (required=false の現行設定) → 何が起きるか
#   E4 修正後 (elytron, required=true) でパスを誤った場合 → 何が起きるか (entrypoint の事前チェックを外して観察)
#   E5 修正前イメージ + ExtraSLB の provision-application-keystore.sh (事前生成方式) → 警告と 8443 の状態
#   E6 inbound HTTPS 3 方式 (remove / dedicated / provision) の 8443 の状態
# 結果: results/tls-experiments.txt と results/e*-server.log
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
RES="${HERE}/results"; OUT="${RES}/tls-experiments.txt"
: "${WARS:?}" "${PKI:?}"
WARS_W="$(cd "${WARS}" && { pwd -W 2>/dev/null || pwd; })"
PKI_W="$(cd "${PKI}" && { pwd -W 2>/dev/null || pwd; })"
EXTRA_W="$(cd "${HERE}/../../Container_ExtraSLB_JVM_https_outbounds/base/scripts" && { pwd -W 2>/dev/null || pwd; })"
DBENV=(-e DB_HOST=wl-mysql -e DB_NAME=iwinmichl -e DB_USER=app -e DB_PASSWORD=apppw)
WARMOUNT=(-v "${WARS_W}/iwinmichl-fixed.war:/opt/jboss-eap/standalone/deployments/iwinmichl.war:ro")

boot() {  # boot <name> <docker run args...>
    local name="$1"; shift
    docker rm -f wl-exp >/dev/null 2>&1
    MSYS_NO_PATHCONV=1 docker run -d --name wl-exp --network wl-net -p 18081:8080 "$@" >/dev/null
    for i in $(seq 1 90); do
        docker logs wl-exp 2>&1 | grep -q -E "WFLYSRV0025|WFLYSRV0026|WFLYSRV0024" && break
        if [ "$(docker inspect -f '{{.State.Running}}' wl-exp 2>/dev/null)" != "true" ]; then break; fi
        sleep 2
    done
    sleep 2
    docker logs wl-exp 2>&1 | sed 's/\x1b\[[0-9;]*m//g' > "${RES}/${name}-server.log"
}
show() {  # show <name> — 関連するログ行を要約表示
    echo "--- ${1}: boot result / keystore 関連 / サービス失敗"
    grep -E "WFLYSRV0025|WFLYSRV0026|WFLYSRV0024|WFLYELY000(22|23|24)|WFLYELY0108|WFLYCTL0186|WFLYCTL0412|WFLYCTL0448|Services with missing|FATAL" "${RES}/${1}-server.log" | cut -c1-260
}
tls() { echo "--- outbound TLS probe (${1})"; curl -s "http://localhost:18081/iwinmichl/tls?url=${1}"; }
p8443() {  # 8443 の待ち受けと証明書の主体を見る
    echo "--- 8443: $(MSYS_NO_PATHCONV=1 docker run --rm --network wl-net registry.access.redhat.com/ubi9/ubi:9.8 bash -c \
        'timeout 5 openssl s_client -connect wl-exp:8443 </dev/null 2>/dev/null | openssl x509 -noout -subject 2>/dev/null || echo "接続できない (待ち受けなし)"' 2>/dev/null)"
}

{
echo "########## E1 現行 (修正前イメージ): p12 は /opt/app/security、-Djavax.net.ssl.trustStore* を standalone.sh 引数で渡す"
boot e1-current "${DBENV[@]}" "${WARMOUNT[@]}" wl-before:1
show e1-current; tls https://extraslb-test/; p8443

echo; echo "########## E2 Q2: 引数で -Djavax.net.ssl.keyStore=<p12> も渡す"
boot e2-keystore-arg "${DBENV[@]}" "${WARMOUNT[@]}" wl-before:1 -Djavax.net.ssl.keyStore=/opt/app/security/extraslb-truststore.p12 -Djavax.net.ssl.keyStorePassword=changeit
show e2-keystore-arg

echo; echo "########## E3 現行設定 (required=false) で自前トラストストアのパスを誤る"
boot e3-wrongpath-current "${DBENV[@]}" "${WARMOUNT[@]}" -e EXTRASLB_TRUSTSTORE_PATH=/opt/app/security/NOT-EXIST.p12 wl-before:1
show e3-wrongpath-current; tls https://extraslb-test/; tls https://www.google.com/

echo; echo "########## E4 修正後 elytron (required=true) で自前トラストストアのパスを誤る (entrypoint の事前チェックを迂回)"
boot e4-wrongpath-required "${DBENV[@]}" "${WARMOUNT[@]}" -e EXTRASLB_TRUSTSTORE_PATH=/opt/app/security/NOT-EXIST.p12 \
    --entrypoint /opt/jboss-eap/bin/standalone.sh wl-after-elytron-remove:1 -b 0.0.0.0
show e4-wrongpath-required; tls https://extraslb-test/
echo "--- 参考: entrypoint 経由なら起動前に止まる"
MSYS_NO_PATHCONV=1 docker run --rm "${DBENV[@]}" -e EXTRASLB_TRUSTSTORE_PATH=/opt/app/security/NOT-EXIST.p12 wl-after-elytron-remove:1 2>&1 | tail -2

echo; echo "########## E5 ExtraSLB の事前生成方式 (provision-application-keystore.sh を起動前に実行)"
boot e5-provision "${DBENV[@]}" "${WARMOUNT[@]}" -v "${EXTRA_W}/provision-application-keystore.sh:/tmp/provision.sh:ro" \
    --entrypoint bash wl-before:1 -c '/tmp/provision.sh /opt/jboss-eap/standalone/configuration/standalone.xml && exec /usr/local/bin/entrypoint.sh'
show e5-provision; p8443

echo; echo "########## E6 remove / dedicated の 8443"
boot e6-remove "${DBENV[@]}" "${WARMOUNT[@]}" wl-after-system-remove:1
show e6-remove; p8443
boot e6-dedicated "${DBENV[@]}" "${WARMOUNT[@]}" -e INBOUND_KEYSTORE_PASSWORD=inboundpass -v "${PKI_W}/inbound:/opt/app/runtime-security:ro" wl-after-system-dedicated:1
show e6-dedicated; p8443
echo "--- 参考: dedicated で鍵ストアを渡し忘れた場合 (entrypoint)"
MSYS_NO_PATHCONV=1 docker run --rm "${DBENV[@]}" -e INBOUND_KEYSTORE_PASSWORD=x wl-after-system-dedicated:1 2>&1 | tail -1

echo; echo "########## E7 TRUST_MODE=system: JDK cacerts に CA が入っていること / -D なし"
MSYS_NO_PATHCONV=1 docker run --rm --entrypoint bash wl-after-system-remove:1 -c \
  'readlink -f $JAVA_HOME/lib/security/cacerts; keytool -list -keystore $JAVA_HOME/lib/security/cacerts -storepass changeit 2>/dev/null | grep -i -A1 "extraslb" | head -4; ls /etc/pki/ca-trust/source/anchors/'
} > "${OUT}" 2>&1
docker rm -f wl-exp >/dev/null 2>&1
cat "${OUT}"
