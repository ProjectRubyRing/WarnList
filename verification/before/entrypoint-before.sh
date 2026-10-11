#!/bin/bash
# 検証用「修正前」entrypoint: Container_ExtraSLB_JVM_https_outbounds の entrypoint.sh の起動部分と同じ引数で起動する
#   (embed-server はビルド時に適用済みのため起動時は実行しない)
set -euo pipefail
JBOSS_HOME="${JBOSS_HOME:-/opt/jboss-eap}"
exec "${JBOSS_HOME}/bin/standalone.sh" \
    -b "${JBOSS_BIND_ADDRESS:-0.0.0.0}" \
    -c "${SERVER_CONFIG:-standalone.xml}" \
    -Djavax.net.ssl.trustStore="${EXTRASLB_TRUSTSTORE_PATH}" \
    -Djavax.net.ssl.trustStorePassword="${EXTRASLB_TRUSTSTORE_PASSWORD}" \
    -Djavax.net.ssl.trustStoreType="${EXTRASLB_TRUSTSTORE_TYPE}" \
    "$@"
