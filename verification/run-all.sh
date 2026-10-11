#!/bin/bash
#
# run-all.sh — 検証シナリオを順に実行する (所要 約 20 分)
#   前提: wl-mysql (MySQL 8.4.11, wait_timeout=150) と wl-extraslb (extraslb-test) が wl-net 上で起動済み
#         イメージ wl-before:1 / wl-after-{system-remove,elytron-remove,system-dedicated}:1 がビルド済み
#         WARS=<iwinmichl-bad.war / iwinmichl-fixed.war / ws-backend.war の置き場所>
#         PKI=<make-test-pki.sh の出力先> (dedicated モード用の鍵ストア)
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
RES="${HERE}/results"; mkdir -p "${RES}"
: "${WARS:?}" "${PKI:?}"
PKI_W="$(cd "${PKI}" && { pwd -W 2>/dev/null || pwd; })"
AFTER_ENV=(-e EAP_SIGTERM_SUSPEND_TIMEOUT=30 -e DB_IDLE_TIMEOUT_MIN=1 -e DB_TRACK_STATEMENTS=TRUE)

echo "=== S0  修正前 (EAP 既定 + ExtraSLB 方式 + 修正前 WAR, SIGTERM は JVM へ中継)"
bash "${HERE}/run-scenario.sh" s0-before wl-before:1 iwinmichl-bad.war -e LAUNCH_JBOSS_IN_BACKGROUND=true

echo "=== S0n 修正前 + SIGTERM を中継しない (LAUNCH_JBOSS_IN_BACKGROUND 未設定)"
IDLE_SECONDS=5 bash "${HERE}/run-scenario.sh" s0n-before-nolaunch wl-before:1 iwinmichl-bad.war

echo "=== S1  修正後 (TRUST_MODE=system / INBOUND_HTTPS_MODE=remove + 修正後 WAR)"
LEAK_PATH=/db/fixed bash "${HERE}/run-scenario.sh" s1-after-system wl-after-system-remove:1 iwinmichl-fixed.war "${AFTER_ENV[@]}"

echo "=== S1e 修正後 (TRUST_MODE=elytron / remove)"
IDLE_SECONDS=5 LEAK_PATH=/db/fixed bash "${HERE}/run-scenario.sh" s1e-after-elytron wl-after-elytron-remove:1 iwinmichl-fixed.war "${AFTER_ENV[@]}"

echo "=== S1d 修正後 (TRUST_MODE=system / INBOUND_HTTPS_MODE=dedicated)"
IDLE_SECONDS=5 LEAK_PATH=/db/fixed bash "${HERE}/run-scenario.sh" s1d-after-dedicated wl-after-system-dedicated:1 iwinmichl-fixed.war "${AFTER_ENV[@]}" \
    -e INBOUND_KEYSTORE_PASSWORD=inboundpass -v "${PKI_W}/inbound:/opt/app/runtime-security:ro"

bash "${HERE}/run-tls-experiments.sh"
echo "=== ALL DONE"
