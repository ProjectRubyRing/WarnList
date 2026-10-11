# implementation/ — JBoss EAP 8.1 警告 13 件の対処実装

ECS (Fargate) 上の **UBI 9.8 + Red Hat build of OpenJDK 21 + JBoss EAP 8.1** コンテナで、
警告 ①〜⑬ を原因から解消するための実装一式です。EAP のサブシステム設定はすべて **jboss-cli** で行います
(ビルド時に `embed-server` で `standalone.xml` へ焼き込み、環境ごとの値は `${env.X:既定値}` 式で ECS から渡す)。

解説は `../JBossEAP81_WARN13_解説.xlsx` / `../JBossEAP81_WARN13_解説.md` を参照してください。

## 構成

```
container/
  Dockerfile                         2 段ビルド (UBI 9.8 で EAP 展開・CLI 適用 → ubi9/openjdk-21-runtime で実行)
  cli/00-system-properties.cli       ⑬ SIGTERM 時のサスペンド待ち時間
  cli/10-elytron-outbound-truststore.cli  ① TRUST_MODE=elytron のときの信頼設定 (required=true)
  cli/11-inbound-https-remove.cli    ① 使っていない 8443 一式を削除 (既定)
  cli/12-inbound-https-dedicated.cli ① 8443 を正式な鍵ストアで動かす場合
  cli/20-logging.cli                 ③④ 必要最小限の抑止 (Spring 由来の 2 種類だけ)
  cli/30-datasource-mysql-xa.cli     ⑧⑩⑪⑫ JDBC ドライバと XA データソース
  cli/31-jca-ccm.cli                 ⑧⑫⑬ 接続リーク検出の切り替え
  cli/60-undertow.cli                ⑨ X-Forwarded-* と 4xx/5xx の JSON アクセスログ
  cli/70-transactions.cli            XA の node-identifier をタスクごとに一意に
  cli/90-verify.cli                  適用結果の表示
  scripts/apply-cli.sh               embed-server で cli/ を番号順に適用
  scripts/install-ca-anchors.sh      ① CA を UBI のシステムトラストストアへ (TRUST_MODE=system)
  scripts/build-truststore.sh        ① Container_ExtraSLB_JVM_https_outbounds と同じ (TRUST_MODE=elytron)
  scripts/entrypoint.sh              起動前チェック・TX_NODE_ID・SIGTERM 中継・起動
  modules/com/mysql/main/module.xml  MySQL Connector/J のモジュール
app/                                 WAR 側の修正 (jboss-deployment-structure.xml、pom 断片、Java)
ecs/taskdef-container-fragment.json  ECS タスク定義の例
tools/                               check-warnings.sh / analyze-ij-log.py / scan-war.py / cacert-secret-args.sh
```

## ビルド

```bash
# dist/ に EAP 8.1 の配布物と JDBC ドライバを置く (コミットしない)
#   dist/jboss-eap-8.1.0.zip  dist/mysql-connector-j-26.7.0.jar
# secrets/certs/<提供元>/<証明書> に受領した CA 証明書 (ExtraSLB と同じ置き方)
DOCKER_BUILDKIT=1 docker build \
  --build-context dist=./dist \
  $(bash tools/cacert-secret-args.sh secrets/certs secrets/cacerts-bundle.tar) \
  --build-arg EAP_DIST=jboss-eap-8.1.0.zip \
  --build-arg MYSQL_DRIVER_JAR=mysql-connector-j-26.7.0.jar \
  --build-arg TRUST_MODE=system \
  --build-arg INBOUND_HTTPS_MODE=remove \
  -t iwinmichl-eap81-base:1.0.0 container/
```

| build-arg | 既定 | 意味 |
|---|---|---|
| `TRUST_MODE` | `system` | `system`: CA を UBI のシステムトラストストアへ (JDK の cacerts に入る。Elytron 設定も -D も不要) / `elytron`: ExtraSLB と同じ二層構え + `required=true` |
| `INBOUND_HTTPS_MODE` | `remove` | `remove`: 未使用の 8443 一式を削除 / `dedicated`: 起動時に渡す鍵ストアで 8443 / `keep`: EAP 既定のまま |
| `BUILD_IMAGE` / `RUNTIME_IMAGE` | `ubi9/ubi:9.8` / `ubi9/openjdk-21-runtime:latest` | 本番ではダイジェストで固定する |

フロント / バックはこのイメージを `FROM` にして WAR を `standalone/deployments/` に置くだけです。

## ECS で渡す環境変数

| 変数 | 既定 | 用途 |
|---|---|---|
| `DB_HOST` `DB_PORT` `DB_NAME` | - / 3306 / - | 接続先 (Aurora MySQL 8.4) |
| `DB_USER` `DB_PASSWORD` | - | secrets (Secrets Manager) から |
| `DB_IDLE_TIMEOUT_MIN` | 5 | ⑩⑪ 待機接続を捨てるまでの分。切られる時間 ÷ 1.5 より短く |
| `DB_TRACK_STATEMENTS` | NOWARN | ⑧⑫ 開発・検証は TRUE |
| `DB_SOCKET_TIMEOUT_MS` | 120000 | 半開き TCP で固まらない上限 (最長クエリより長く) |
| `EAP_SIGTERM_SUSPEND_TIMEOUT` | 30 | ⑬ 最長リクエスト ≦ この値 < stopTimeout |
| `JCA_CCM_DEBUG` / `JCA_CCM_ERROR` | false | 接続リークの調査時だけ true |
| `TX_NODE_ID` | (自動) | entrypoint が ECS タスク ID から作る |

- コンテナの healthCheck は管理ポート (localhost:9990) の `/health/ready` を使う (サーバ状態・サスペンド状態・デプロイ状態・起動エラーを返す)。
  ALB のヘルスチェックはアプリの URL (8080) に向ける (管理ポートは公開しない)。
- `stopTimeout` は `EAP_SIGTERM_SUSPEND_TIMEOUT` より長く (Fargate の上限は 120 秒)。ALB の deregistration delay は最長リクエスト以上。

## 運用ツール

```bash
bash tools/check-warnings.sh server.log                      # 警告 ①〜⑬ の件数
python tools/analyze-ij-log.py server.log --pkg com.example  # ⑧⑫ の作成箇所 / ⑪ の放置時間 / ⑩ の原因 / ⑬ の状況
python tools/scan-war.py iwinmichl.war --jboss-home /opt/jboss-eap   # ②③④⑤⑥⑦ の原因を WAR から特定
```

## 検証

`../verification/` で、EAP 8.1 の上流の WildFly 35.0.1 をこの Dockerfile でそのままビルドし、
修正前に 13 件すべてを再現 → 修正後に 0 件になることを確認しています。
