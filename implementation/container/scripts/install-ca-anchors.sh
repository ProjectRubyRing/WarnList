#!/bin/bash
#
# install-ca-anchors.sh <cacert-archive.tar | cacert-dir>
#
# TRUST_MODE=system (推奨) 用。受領した CA 証明書 (ルート CA / 中間 CA / サーバ証明書) を
# UBI (RHEL) のシステムトラストストアへ追加する。
#
#   /etc/pki/ca-trust/source/anchors/<提供元>-ca-<n>.pem  に置いて  update-ca-trust extract
#     → /etc/pki/ca-trust/extracted/java/cacerts (JKS) が再生成される
#     → Red Hat build of OpenJDK (RPM) の $JAVA_HOME/lib/security/cacerts は
#        /etc/pki/java/cacerts → /etc/pki/ca-trust/extracted/java/cacerts へのシンボリックリンク
#        なので、JVM 既定のトラストストアに自動で入る (UBI 9.8 / OpenJDK 21.0.12 で確認)
#
# 効果: SSLContext.getDefault() を使うクライアントも、自前で SSLContext を作るクライアント
#       (Apache CXF の HTTPConduit 等。javax.net.ssl.trustStore 未指定なら cacerts を使う) も、
#       追加設定なしで同じ CA を信頼する。Elytron の key-store / default-ssl-context も、
#       standalone.sh の -Djavax.net.ssl.trustStore* も不要。cacerts のコピーを Elytron に
#       読ませないので WFLYELY00024 (期限切れ証明書の警告) も出ない。
#
# 入力レイアウトは Container_ExtraSLB_JVM_https_outbounds の cacert-secret-args.sh と同じ:
#   <name>/<任意のファイル名>  (PEM / DER / PKCS#7、チェーン連結も可。拡張子は見ない)
set -euo pipefail

INPUT="${1:?usage: install-ca-anchors.sh <cacert-archive.tar|cacert-dir>}"
ANCHORS=/etc/pki/ca-trust/source/anchors
JAVA_CACERTS=/etc/pki/ca-trust/extracted/java/cacerts

command -v update-ca-trust >/dev/null || { echo "ERROR: update-ca-trust が無い (ca-certificates / p11-kit-trust 未導入)" >&2; exit 1; }
command -v keytool >/dev/null         || { echo "ERROR: keytool が無い (JDK 未導入)" >&2; exit 1; }

WORK="$(mktemp -d)"
trap 'rm -rf "${WORK}"' EXIT

if [[ -f "${INPUT}" && "$(LC_ALL=C dd if="${INPUT}" bs=1 skip=257 count=5 2>/dev/null)" == "ustar" ]]; then
    mkdir -p "${WORK}/in" && tar -xf "${INPUT}" -C "${WORK}/in"
    INPUT="${WORK}/in"
fi
[[ -d "${INPUT}" ]] || { echo "ERROR: 入力が見つからない: ${INPUT}" >&2; exit 1; }

sanitize() { printf '%s' "$1" | LC_ALL=C tr 'A-Z' 'a-z' | LC_ALL=C tr -c 'a-z0-9._-' '-'; }

mkdir -p "${ANCHORS}"
TOTAL=0
FPS=()
for SRC_DIR in "${INPUT}"/*/; do
    NAME="$(sanitize "$(basename "${SRC_DIR}")")"
    SEQ=0
    for F in "${SRC_DIR}"*; do
        [[ -f "${F}" && -s "${F}" ]] || continue
        # PEM / DER / PKCS#7 をすべて PEM に正規化 (keytool -printcert -rfc は全証明書を出力する)
        PEM="${WORK}/norm.pem"
        if ! keytool -J-Duser.language=en -printcert -rfc -file "${F}" > "${PEM}" 2>/dev/null \
           || ! grep -q -- '-----BEGIN CERTIFICATE-----' "${PEM}"; then
            echo "WARN: 証明書ではないため読み飛ばし: ${NAME}/$(basename "${F}")" >&2
            continue
        fi
        # 1 枚ずつに分割して anchors へ置く
        rm -f "${WORK}"/one-*
        awk -v d="${WORK}" '/-----BEGIN CERTIFICATE-----/{n++; w=1} w{print > sprintf("%s/one-%03d", d, n)} /-----END CERTIFICATE-----/{w=0}' "${PEM}"
        for ONE in "${WORK}"/one-*; do
            SEQ=$((SEQ + 1))
            DEST="${ANCHORS}/${NAME}-ca-${SEQ}.pem"
            cp "${ONE}" "${DEST}"
            chmod 0644 "${DEST}"
            INFO="$(keytool -J-Duser.language=en -printcert -file "${ONE}")"
            FP="$(sed -n 's/^[[:space:]]*SHA256: //p' <<<"${INFO}" | head -n1)"
            FPS+=("${FP}")
            echo "==> anchor ${DEST}"
            sed -n '/^Owner:/p; /^Issuer:/p; /^Valid from:/p' <<<"${INFO}"
            TOTAL=$((TOTAL + 1))
        done
    done
done
[[ "${TOTAL}" -gt 0 ]] || { echo "ERROR: 取り込む証明書が 1 枚も無い" >&2; exit 1; }

update-ca-trust extract

# JVM 既定トラストストア (cacerts) に入ったことを指紋で確認する
LIST="$(keytool -J-Duser.language=en -list -v -keystore "${JAVA_CACERTS}" -storepass changeit 2>/dev/null)"
for FP in "${FPS[@]}"; do
    if grep -q -- "${FP}" <<<"${LIST}"; then
        echo "==> OK: cacerts に登録済み SHA256 ${FP}"
    else
        echo "ERROR: cacerts に見つからない SHA256 ${FP}" >&2
        exit 1
    fi
done
echo "==> ${TOTAL} certificate(s) installed into the system trust store (${JAVA_CACERTS})"
