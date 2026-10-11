#!/bin/bash
#
# make-test-pki.sh <out-dir>
#
# 検証用の PKI を作る (UBI 9.8 コンテナ内の openssl を使う)。
#   <out-dir>/ca/rootCA.pem, rootCA.key     … 「extraslb」の自己署名ルート CA を模したもの
#   <out-dir>/server/server.crt, server.key  … extraslb-test (HTTPS テストサーバ) の証明書 (上の CA が発行)
#   <out-dir>/certs/extraslb/cacert.crt      … ビルドへ渡す受領証明書 (= ルート CA)。ExtraSLB と同じ配置
#   <out-dir>/inbound/inbound-server.p12     … ① dedicated モード検証用の正式な (と見なす) 鍵ストア
set -euo pipefail
OUT="${1:?out-dir}"
mkdir -p "${OUT}"
OUT_W="$(cd "${OUT}" && { pwd -W 2>/dev/null || pwd; })"

MSYS_NO_PATHCONV=1 docker run --rm -v "${OUT_W}:/out" registry.access.redhat.com/ubi9/ubi:9.8 bash -c '
set -euo pipefail
dnf -y -q install openssl java-21-openjdk-headless >/dev/null 2>&1
cd /out
mkdir -p ca server certs/extraslb inbound
openssl req -x509 -newkey rsa:2048 -nodes -sha256 -days 3650 \
  -subj "/O=ExtraSLB Test/CN=ExtraSLB Test Root CA" \
  -addext "basicConstraints=critical,CA:true" -addext "keyUsage=critical,keyCertSign,cRLSign" \
  -keyout ca/rootCA.key -out ca/rootCA.pem 2>/dev/null
openssl req -newkey rsa:2048 -nodes -sha256 -subj "/CN=extraslb-test" -keyout server/server.key -out server/server.csr 2>/dev/null
printf "subjectAltName=DNS:extraslb-test\nextendedKeyUsage=serverAuth\nbasicConstraints=CA:false\n" > server/ext.cnf
openssl x509 -req -in server/server.csr -CA ca/rootCA.pem -CAkey ca/rootCA.key -CAcreateserial \
  -days 825 -sha256 -extfile server/ext.cnf -out server/server.crt 2>/dev/null
cp ca/rootCA.pem certs/extraslb/cacert.crt
keytool -genkeypair -alias server -keyalg RSA -keysize 2048 -validity 825 \
  -dname "CN=iwinmichl.internal, O=Verification" -ext SAN=dns:iwinmichl.internal \
  -keystore inbound/inbound-server.p12 -storetype PKCS12 -storepass inboundpass -keypass inboundpass >/dev/null 2>&1
chmod -R a+rX /out
openssl x509 -in ca/rootCA.pem -noout -subject -enddate
openssl x509 -in server/server.crt -noout -subject -issuer -ext subjectAltName
'
ls -R "${OUT}"
