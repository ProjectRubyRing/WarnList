#!/bin/bash
#
# run-scenario.sh <label> <image> <war-file-name> [extra docker run args...]
#
# 検証シナリオを 1 本実行する (MySQL wl-mysql と HTTPS テストサーバ extraslb-test は起動済みの前提)。
#   1. ブート + デプロイ (①〜⑦ はここで出る)
#   2. 機能確認: JSP(⑦) / 405(⑨) / 非同期(④) / アウトバウンド TLS(①) / SOAP タイムアウト(③) / DB(⑧⑫)
#   3. 170 秒放置して DB 接続を MySQL の wait_timeout(150 秒) で切らせ、再利用 (⑩⑪)
#   4. 15 秒かかる DB 処理の最中に docker stop (SIGTERM) (⑬)
# 結果: results/<label>-server.log, results/<label>-http.txt, results/<label>-warnings.txt
#
# 環境変数: WARS (WAR の置き場所), IDLE_SECONDS (既定 170), LEAK_PATH (既定 /db/leak)
set -uo pipefail

LABEL="${1:?label}"; IMAGE="${2:?image}"; WAR="${3:?war}"; shift 3
HERE="$(cd "$(dirname "$0")" && pwd)"
RES="${HERE}/results"; mkdir -p "${RES}"
WARS_W="$(cd "${WARS:?set WARS}" && { pwd -W 2>/dev/null || pwd; })"
IDLE_SECONDS="${IDLE_SECONDS:-170}"
LEAK_PATH="${LEAK_PATH:-/db/leak}"
HTTP="${RES}/${LABEL}-http.txt"
BASE="http://localhost:18080"

docker rm -f wl-app >/dev/null 2>&1
MSYS_NO_PATHCONV=1 docker run -d --name wl-app --network wl-net -p 18080:8080 \
    -e DB_HOST=wl-mysql -e DB_NAME=iwinmichl -e DB_USER=app -e DB_PASSWORD=apppw \
    -v "${WARS_W}/${WAR}:/opt/jboss-eap/standalone/deployments/iwinmichl.war:ro" \
    -v "${WARS_W}/ws-backend.war:/opt/jboss-eap/standalone/deployments/ws-backend.war:ro" \
    "$@" "${IMAGE}" >/dev/null

for i in $(seq 1 120); do
    docker logs wl-app 2>&1 | grep -q -E "WFLYSRV0025|WFLYSRV0026|WFLYSRV0024" && break
    sleep 2
done
sleep 3

{
echo "### label=${LABEL} image=${IMAGE} war=${WAR} args=$*"
echo "### boot line"; docker logs wl-app 2>&1 | grep -E "WFLYSRV0025|WFLYSRV0026|WFLYSRV0024" | sed 's/\x1b\[[0-9;]*m//g' | tail -1
for p in /iwinmichl/jstl.jsp /iwinmichl/jstl-fmt.jsp /iwinmichl/jstl-new.jsp; do
    echo "### GET ${p} (⑦)"; curl -s -H 'Accept-Language: ja-JP' -w '  (HTTP %{http_code})\n' "${BASE}${p}"
done
echo "### POST /iwinmichl/api/hello (⑨)"; curl -s -i -X POST "${BASE}/iwinmichl/api/hello" | grep -E "^HTTP|^Allow" | tr -d '\r'
echo "### GET /iwinmichl/api/async (④: Spring の非同期処理)"; curl -s -w '  (HTTP %{http_code})\n' "${BASE}/iwinmichl/api/async"
echo "### GET /iwinmichl/tls?url=https://extraslb-test/ (①: 自己署名ルート CA)"; curl -s "${BASE}/iwinmichl/tls?url=https://extraslb-test/"
echo "### GET /iwinmichl/tls?url=https://www.google.com/ (①: パブリック CA)"; curl -s "${BASE}/iwinmichl/tls?url=https://www.google.com/"
echo "### GET /iwinmichl/soap?sleepMs=3000&timeoutMs=1000 (③: 標準プロパティでタイムアウト)"; curl -s "${BASE}/iwinmichl/soap?sleepMs=3000&timeoutMs=1000"
echo "### GET /iwinmichl/soap?sleepMs=200&timeoutMs=3000 (③: 正常応答)"; curl -s "${BASE}/iwinmichl/soap?sleepMs=200&timeoutMs=3000"
echo "### GET /iwinmichl/db/ok"; curl -s -w '  (HTTP %{http_code})\n' "${BASE}/iwinmichl/db/ok"
echo "### GET /iwinmichl${LEAK_PATH} (⑧⑫)"; curl -s -w '  (HTTP %{http_code})\n' "${BASE}/iwinmichl${LEAK_PATH}"
echo "### ${IDLE_SECONDS} 秒放置 (MySQL wait_timeout=150 を超える) → 再利用 (⑩⑪)"
} > "${HTTP}" 2>&1

sleep "${IDLE_SECONDS}"

{
echo "### GET /iwinmichl/db/ok (放置後)"; curl -s -w '  (HTTP %{http_code})\n' "${BASE}/iwinmichl/db/ok"
echo "### ⑬: /db/slow?sec=15 の実行中 (3 秒後) に docker stop -t 90 (SIGTERM)"
( curl -s -m 60 -w '  (HTTP %{http_code})\n' "${BASE}/iwinmichl/db/slow?sec=15" > "${RES}/${LABEL}-slow.txt" 2>&1 ) &
CURL_PID=$!
sleep 3
T0=$(date +%s); docker stop -t 90 wl-app >/dev/null; T1=$(date +%s)
wait "${CURL_PID}" 2>/dev/null
echo "docker stop 所要: $((T1 - T0)) 秒 / コンテナ終了コード: $(docker inspect -f '{{.State.ExitCode}}' wl-app)"
echo "slow の応答: $(tr -d '\n' < "${RES}/${LABEL}-slow.txt")"
} >> "${HTTP}" 2>&1

docker logs wl-app > "${RES}/${LABEL}-server.log" 2>&1
sed -i 's/\x1b\[[0-9;]*m//g' "${RES}/${LABEL}-server.log"
bash "${HERE}/../implementation/tools/check-warnings.sh" "${RES}/${LABEL}-server.log" > "${RES}/${LABEL}-warnings.txt"
cat "${HTTP}"; echo; cat "${RES}/${LABEL}-warnings.txt"
