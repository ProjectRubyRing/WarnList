#!/bin/bash
#
# apply-cli.sh [cli-dir]
#
# イメージのビルド時に jboss-cli の組み込みサーバ (embed-server, admin-only) を 1 回だけ起動し、
# cli/ 配下の .cli を番号順に適用して standalone.xml に焼き込む。
#   - ${env.*} 式はこの時点では解決されず、式のまま standalone.xml に保存される
#     (起動時に ECS タスク定義の環境変数から解決される)
#   - 起動時に embed-server を動かさないので、コンテナ 1 起動あたりの設定ブートは 1 回で済む
#     (Container_ExtraSLB_JVM_https_outbounds の docs/standalone-xml-history-ecs-vs-compose.md 参照)
#
# 選択適用:
#   10-elytron-outbound-truststore.cli … TRUST_MODE=elytron のときだけ
#   11-inbound-https-remove.cli        … INBOUND_HTTPS_MODE=remove (既定) のときだけ
#   12-inbound-https-dedicated.cli     … INBOUND_HTTPS_MODE=dedicated のときだけ
#   90-verify.cli                      … 最後に必ず実行 (結果の表示のみ)
set -euo pipefail

JBOSS_HOME="${JBOSS_HOME:?JBOSS_HOME is not set}"
CLI_DIR="${1:-/opt/app/cli}"
TRUST_MODE="${TRUST_MODE:-system}"
INBOUND_HTTPS_MODE="${INBOUND_HTTPS_MODE:-remove}"
SERVER_CONFIG="${SERVER_CONFIG:-standalone.xml}"

case "${TRUST_MODE}" in system|elytron) ;; *) echo "[apply-cli] FATAL: TRUST_MODE=${TRUST_MODE} (system|elytron)" >&2; exit 1 ;; esac
case "${INBOUND_HTTPS_MODE}" in remove|dedicated|keep) ;; *) echo "[apply-cli] FATAL: INBOUND_HTTPS_MODE=${INBOUND_HTTPS_MODE} (remove|dedicated|keep)" >&2; exit 1 ;; esac

BATCH="$(mktemp /tmp/apply-cli.XXXXXX.cli)"
trap 'rm -f "${BATCH}"' EXIT

{
    echo "embed-server --server-config=${SERVER_CONFIG} --std-out=echo"
    for f in "${CLI_DIR}"/[0-8]*.cli; do
        name="$(basename "${f}")"
        case "${name}" in
            10-elytron-outbound-truststore.cli) [[ "${TRUST_MODE}" == elytron ]] || continue ;;
            11-inbound-https-remove.cli)        [[ "${INBOUND_HTTPS_MODE}" == remove ]] || continue ;;
            12-inbound-https-dedicated.cli)     [[ "${INBOUND_HTTPS_MODE}" == dedicated ]] || continue ;;
        esac
        echo "echo ===== [apply] ${name}"
        cat "${f}"
        echo
    done
    cat "${CLI_DIR}/90-verify.cli"
    echo
    echo "stop-embedded-server"
} > "${BATCH}"

echo "[apply-cli] TRUST_MODE=${TRUST_MODE} INBOUND_HTTPS_MODE=${INBOUND_HTTPS_MODE} SERVER_CONFIG=${SERVER_CONFIG}"
"${JBOSS_HOME}/bin/jboss-cli.sh" --file="${BATCH}"

# embed-server が作った履歴をイメージに残さない
# (overlayfs の下位レイヤに standalone_xml_history/current が残ると、起動時の rename が失敗し得る)
rm -rf "${JBOSS_HOME}/standalone/configuration/standalone_xml_history"
echo "[apply-cli] done"
