# syntax=docker/dockerfile:1.7
#
# JBoss EAP 8.1 on UBI 9.8 + Red Hat build of OpenJDK 21  (ECS / Fargate 用ベースイメージ)
#
#   段 1 (eap-build): UBI 9.8 + OpenJDK 21 (RPM) で EAP を展開し、jboss-cli (embed-server) で
#                     各サブシステムを設定して standalone.xml に焼き込む
#   段 2 (runtime)  : Red Hat 公式 ubi9/openjdk-21-runtime (RHEL 9.8 / OpenJDK 21 / uid 185) に
#                     設定済みの EAP と信頼設定を載せる
#
# ビルド例 (BuildKit 必須。証明書は ExtraSLB と同じ方式で 1 つのシークレットにまとめて渡す):
#   bash tools/cacert-secret-args.sh secrets/certs secrets/cacerts-bundle.tar   # → --secret 引数を出力
#   DOCKER_BUILDKIT=1 docker build \
#     --build-context dist=./dist \
#     $(bash tools/cacert-secret-args.sh secrets/certs secrets/cacerts-bundle.tar) \
#     --build-arg EAP_DIST=jboss-eap-8.1.0.zip \
#     --build-arg TRUST_MODE=system \
#     --build-arg INBOUND_HTTPS_MODE=remove \
#     -t iwinmichl-eap81-base:1.0.0 container/
#   dist/ には jboss-eap-8.1.0.zip と mysql-connector-j-<版>.jar を置く (リポジトリにはコミットしない)。
#
# ビルド引数:
#   TRUST_MODE          system (推奨: UBI のシステムトラストストアへ CA を追加)
#                       elytron (ExtraSLB 方式: cacerts のコピー + CA の p12 を Elytron default-ssl-context
#                                と -Djavax.net.ssl.trustStore の二層で参照。required=true に強化)
#   INBOUND_HTTPS_MODE  remove (推奨/既定: 未使用の 8443 一式を削除 → ① WFLYELY00023 が原因ごと消える)
#                       dedicated (ALB→タスク間も TLS: 起動時に渡す正式な鍵ストアへ差し替え)
#                       keep (EAP 既定のまま。① の警告は出続ける)
ARG BUILD_IMAGE=registry.access.redhat.com/ubi9/ubi:9.8
ARG RUNTIME_IMAGE=registry.access.redhat.com/ubi9/openjdk-21-runtime:latest

# =====================================================================
# 段 1: EAP の展開と jboss-cli による設定
# =====================================================================
FROM ${BUILD_IMAGE} AS eap-build

ARG EAP_DIST=jboss-eap-8.1.0.zip
ARG MYSQL_DRIVER_JAR=mysql-connector-j-26.7.0.jar
ARG JBOSS_HOME=/opt/jboss-eap
ARG TRUST_MODE=system
ARG INBOUND_HTTPS_MODE=remove

ENV JBOSS_HOME=${JBOSS_HOME} \
    JAVA_HOME=/usr/lib/jvm/jre-21-openjdk \
    TRUST_MODE=${TRUST_MODE} \
    INBOUND_HTTPS_MODE=${INBOUND_HTTPS_MODE}

RUN dnf -y --setopt=install_weak_deps=0 install java-21-openjdk-headless unzip tar gzip \
 && dnf clean all && rm -rf /var/cache/dnf

# EAP 本体 (zip / tar.gz のどちらでもよい。トップディレクトリ名は問わない)
COPY --from=dist ${EAP_DIST} /tmp/eap-dist
RUN set -eu; mkdir -p /tmp/eap-x; \
    if unzip -tq /tmp/eap-dist >/dev/null 2>&1; then unzip -q /tmp/eap-dist -d /tmp/eap-x; \
    else tar -xzf /tmp/eap-dist -C /tmp/eap-x; fi; \
    top="$(find /tmp/eap-x -mindepth 1 -maxdepth 1 -type d | head -n1)"; \
    mv "${top}" "${JBOSS_HOME}"; rm -rf /tmp/eap-x /tmp/eap-dist; \
    "${JBOSS_HOME}/bin/standalone.sh" --version | tail -n1
# (任意) 最新の累積アップデートを当てる: JBoss EAP 8.1『Updating Red Hat JBoss EAP』の
#   jboss-eap-installation-manager によるオフライン更新手順に従い、この位置で実行する。

# JDBC ドライバ (モジュール com.mysql)。standalone/deployments へのデプロイはしない (⑬ の一因になる)
COPY modules/ ${JBOSS_HOME}/modules/
COPY --from=dist ${MYSQL_DRIVER_JAR} ${JBOSS_HOME}/modules/com/mysql/main/mysql-connector-j.jar

COPY scripts/ /opt/app/scripts/
COPY cli/ /opt/app/cli/
RUN chmod 0755 /opt/app/scripts/*.sh

# TRUST_MODE=elytron のときだけ: cacerts のコピー + 受領した CA の PKCS12 トラストストアを作る
# (system モードは段 2 でシステムトラストストアへ入れる)
RUN --mount=type=secret,id=cacerts,target=/run/secrets/cacerts.tar,required=true \
    set -eu; mkdir -p /opt/app/security; \
    if [ "${TRUST_MODE}" = "elytron" ]; then \
        /opt/app/scripts/build-truststore.sh /run/secrets/cacerts.tar \
            /opt/app/security/extraslb-truststore.p12 changeit; \
        chmod 0444 /opt/app/security/extraslb-truststore.p12; \
    fi

# ★ 各サブシステムの設定 (jboss-cli / embed-server)。結果は standalone.xml に焼き込まれる
RUN /opt/app/scripts/apply-cli.sh /opt/app/cli

# =====================================================================
# 段 2: 実行イメージ
# =====================================================================
FROM ${RUNTIME_IMAGE} AS runtime

ARG JBOSS_HOME=/opt/jboss-eap
ARG TRUST_MODE=system
ARG INBOUND_HTTPS_MODE=remove

ENV JBOSS_HOME=${JBOSS_HOME} \
    TRUST_MODE=${TRUST_MODE} \
    INBOUND_HTTPS_MODE=${INBOUND_HTTPS_MODE} \
    LAUNCH_JBOSS_IN_BACKGROUND=true \
    EXTRASLB_TRUSTSTORE_PATH=/opt/app/security/extraslb-truststore.p12 \
    EXTRASLB_TRUSTSTORE_TYPE=PKCS12 \
    EXTRASLB_TRUSTSTORE_PASSWORD=changeit

USER root

# TRUST_MODE=system: CA を /etc/pki/ca-trust/source/anchors に置いて update-ca-trust
#   → JDK の cacerts (/etc/pki/java/cacerts) に入る。証明書ファイル自体は公開情報。
COPY --from=eap-build /opt/app/scripts/ /opt/app/scripts/
RUN --mount=type=secret,id=cacerts,target=/run/secrets/cacerts.tar,required=true \
    set -eu; \
    if [ "${TRUST_MODE}" = "system" ]; then /opt/app/scripts/install-ca-anchors.sh /run/secrets/cacerts.tar; fi

COPY --from=eap-build --chown=185:0 ${JBOSS_HOME} ${JBOSS_HOME}
COPY --from=eap-build --chown=185:0 /opt/app /opt/app
RUN chmod -R g=u ${JBOSS_HOME}/standalone /opt/app

USER 185
WORKDIR ${JBOSS_HOME}
EXPOSE 8080
ENTRYPOINT ["/opt/app/scripts/entrypoint.sh"]

# フロント / バックのイメージはこのイメージを FROM にして WAR を置くだけ:
#   FROM iwinmichl-eap81-base:1.0.0
#   COPY --chown=185:0 target/iwinmichl.war ${JBOSS_HOME}/standalone/deployments/
