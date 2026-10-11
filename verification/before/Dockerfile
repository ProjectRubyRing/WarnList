# syntax=docker/dockerfile:1.7
#
# 検証用「修正前」イメージ: 実環境 (UBI 9.8 + Red Hat build of OpenJDK 21 + EAP 8.1, JBOSS_HOME=/opt/jboss-eap)
# を、EAP 8.1 の上流である WildFly 35.0.1.Final で模したもの。
#   - Container_ExtraSLB_JVM_https_outbounds と同じ信頼設定 (cacerts コピー + CA の p12、
#     Elytron default-ssl-context、-Djavax.net.ssl.trustStore*)
#   - EAP 標準のインバウンド HTTPS 設定 (applicationKS 等) はそのまま → ①
#   - データソースは 30-datasource-before.cli (⑧⑩⑪⑫ の再現用)
#   - org.wildfly.sigterm.suspend.timeout 無し (既定 0) → ⑬
FROM registry.access.redhat.com/ubi9/ubi:9.8

ARG EAP_DIST=wildfly-dist-35.0.1.Final.tar.gz
ARG MYSQL_DRIVER_JAR=mysql-connector-j-26.7.0.jar
ENV JBOSS_HOME=/opt/jboss-eap \
    JAVA_HOME=/usr/lib/jvm/jre-21-openjdk \
    EXTRASLB_TRUSTSTORE_PATH=/opt/app/security/extraslb-truststore.p12 \
    EXTRASLB_TRUSTSTORE_PASSWORD=changeit \
    EXTRASLB_TRUSTSTORE_TYPE=PKCS12

RUN dnf -y --setopt=install_weak_deps=0 install java-21-openjdk-headless unzip tar gzip \
 && dnf clean all && rm -rf /var/cache/dnf \
 && useradd -u 185 -g 0 -M -d /opt/jboss-eap jboss

COPY --from=dist ${EAP_DIST} /tmp/eap-dist
RUN set -eu; mkdir -p /tmp/eap-x; tar -xzf /tmp/eap-dist -C /tmp/eap-x; \
    mv "$(find /tmp/eap-x -mindepth 1 -maxdepth 1 -type d | head -n1)" "${JBOSS_HOME}"; rm -rf /tmp/eap-x /tmp/eap-dist

COPY --from=impl modules/ ${JBOSS_HOME}/modules/
COPY --from=dist ${MYSQL_DRIVER_JAR} ${JBOSS_HOME}/modules/com/mysql/main/mysql-connector-j.jar
COPY --from=impl scripts/build-truststore.sh /usr/local/bin/build-truststore.sh
COPY cli/ /opt/app/cli/
COPY entrypoint-before.sh /usr/local/bin/entrypoint.sh

RUN --mount=type=secret,id=cacerts,target=/run/secrets/cacerts.tar,required=true \
    set -eu; chmod 0755 /usr/local/bin/*.sh; \
    /usr/local/bin/build-truststore.sh /run/secrets/cacerts.tar "${EXTRASLB_TRUSTSTORE_PATH}" "${EXTRASLB_TRUSTSTORE_PASSWORD}" >/tmp/truststore.log 2>&1 || { cat /tmp/truststore.log; exit 1; }; \
    tail -n 6 /tmp/truststore.log; chmod 0444 "${EXTRASLB_TRUSTSTORE_PATH}"

RUN set -eu; { echo "embed-server --server-config=standalone.xml --std-out=echo"; \
      cat /opt/app/cli/10-configure-outbound-tls.cli; echo; cat /opt/app/cli/30-datasource-before.cli; echo; \
      echo "stop-embedded-server"; } > /tmp/before.cli; \
    "${JBOSS_HOME}/bin/jboss-cli.sh" --file=/tmp/before.cli; rm -f /tmp/before.cli; \
    rm -rf "${JBOSS_HOME}/standalone/configuration/standalone_xml_history"; \
    chown -R 185:0 "${JBOSS_HOME}" /opt/app; chmod -R g=u "${JBOSS_HOME}/standalone"

USER 185
EXPOSE 8080 8443
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
