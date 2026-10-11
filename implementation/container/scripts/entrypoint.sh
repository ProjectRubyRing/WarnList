#!/bin/bash
#
# entrypoint.sh — JBoss EAP 8.1 コンテナの起動スクリプト (ECS タスク用)
#
#   1. 起動前チェック (足りない設定があれば、EAP を起動する前に理由を出して止める)
#   2. XA 用のノード ID (TX_NODE_ID) をタスクごとに一意に決める
#   3. SIGTERM を JVM に中継させる (LAUNCH_JBOSS_IN_BACKGROUND=true) … ⑬ の前提
#   4. standalone.sh を exec で起動
#
# サブシステム設定はビルド時に jboss-cli で standalone.xml へ適用済み (apply-cli.sh)。
# 起動時に jboss-cli (embed-server) は実行しない。
set -euo pipefail

JBOSS_HOME="${JBOSS_HOME:-/opt/jboss-eap}"
TRUST_MODE="${TRUST_MODE:-system}"
INBOUND_HTTPS_MODE="${INBOUND_HTTPS_MODE:-remove}"

say() { echo "==> [entrypoint] $*"; }
die() { echo "==> [entrypoint] FATAL: $*" >&2; exit 1; }

# ---------------------------------------------------------------
# 1. 起動前チェック
# ---------------------------------------------------------------
# データソース (30-datasource-mysql-xa.cli) が使う環境変数。既定値の無い式は未設定だと起動時に解決できない。
for v in DB_HOST DB_NAME DB_USER DB_PASSWORD; do
    [[ -n "${!v:-}" ]] || die "環境変数 ${v} が未設定です (ECS タスク定義の environment / secrets を確認)"
done

if [[ "${TRUST_MODE}" == elytron ]]; then
    # 10-elytron-outbound-truststore.cli は required=true。ここでも先に確かめて分かりやすく止める。
    [[ -r "${EXTRASLB_TRUSTSTORE_PATH:-}" ]] || die "トラストストアが読めません: ${EXTRASLB_TRUSTSTORE_PATH:-(未設定)}"
fi

if [[ "${INBOUND_HTTPS_MODE}" == dedicated ]]; then
    [[ -r "${INBOUND_KEYSTORE_PATH:-/opt/app/runtime-security/inbound-server.p12}" ]] \
        || die "インバウンド用鍵ストアがありません: ${INBOUND_KEYSTORE_PATH:-/opt/app/runtime-security/inbound-server.p12}"
    [[ -n "${INBOUND_KEYSTORE_PASSWORD:-}" ]] || die "INBOUND_KEYSTORE_PASSWORD が未設定です"
fi

# ---------------------------------------------------------------
# 2. TX_NODE_ID (70-transactions.cli が参照。23 バイト以内・タスクごとに一意)
#    ECS のタスクメタデータ (v4) の TaskARN 末尾 = タスク ID (32 桁の 16 進) を使う。
# ---------------------------------------------------------------
if [[ -z "${TX_NODE_ID:-}" ]]; then
    TASK_ID=""
    if [[ -n "${ECS_CONTAINER_METADATA_URI_V4:-}" ]]; then
        TASK_ARN="$(curl -fsS --max-time 2 "${ECS_CONTAINER_METADATA_URI_V4}/task" 2>/dev/null \
                    | sed -n 's/.*"TaskARN"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' || true)"
        TASK_ID="${TASK_ARN##*/}"
    fi
    [[ -n "${TASK_ID}" ]] || TASK_ID="${HOSTNAME:-$(cat /proc/sys/kernel/hostname 2>/dev/null || echo node)}"
    TX_NODE_ID="$(printf '%s' "${TASK_ID}" | LC_ALL=C tr -cd 'A-Za-z0-9' | cut -c1-23)"
    export TX_NODE_ID
fi
say "TX_NODE_ID=${TX_NODE_ID}"

# ---------------------------------------------------------------
# 3. SIGTERM の中継 (⑬)
#    standalone.sh は LAUNCH_JBOSS_IN_BACKGROUND が設定されているときだけ、受けた TERM/INT を
#    JVM へ kill で中継し、JVM の終了を wait する。未設定だと PID 1 のシェルが SIGTERM を
#    受けても JVM に届かず、stopTimeout 後の SIGKILL で強制終了になる (停止処理が一切走らない)。
#    ECS の initProcessEnabled (tini) はゾンビ回収用で、これの代わりにはならない。
# ---------------------------------------------------------------
export LAUNCH_JBOSS_IN_BACKGROUND=true

# ---------------------------------------------------------------
# 4. 起動
# ---------------------------------------------------------------
ARGS=(-b "${JBOSS_BIND_ADDRESS:-0.0.0.0}" -c "${SERVER_CONFIG:-standalone.xml}")
if [[ "${TRUST_MODE}" == elytron ]]; then
    # Apache CXF の HTTPConduit 等、SSLContext を自前で組み立てるライブラリは
    # Elytron の default-ssl-context ではなく javax.net.ssl.trustStore* を読む (二層構え)。
    ARGS+=("-Djavax.net.ssl.trustStore=${EXTRASLB_TRUSTSTORE_PATH}"
           "-Djavax.net.ssl.trustStoreType=${EXTRASLB_TRUSTSTORE_TYPE:-PKCS12}"
           "-Djavax.net.ssl.trustStorePassword=${EXTRASLB_TRUSTSTORE_PASSWORD:-changeit}")
fi
say "TRUST_MODE=${TRUST_MODE} INBOUND_HTTPS_MODE=${INBOUND_HTTPS_MODE} EAP_SIGTERM_SUSPEND_TIMEOUT=${EAP_SIGTERM_SUSPEND_TIMEOUT:-30}"
exec "${JBOSS_HOME}/bin/standalone.sh" "${ARGS[@]}" "$@"
