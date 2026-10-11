# verification/ — 修正前の再現と修正後の解消の実測

JBoss EAP 8.1 のバイナリは Red Hat の認証が必要なため、上流の **WildFly 35.0.1.Final**
(WildFly Core 27.0.1 / Elytron 2.6.0 / Undertow 2.3.18 / IronJacamar 3.0.10 / Weld 5.1.4 / JBossWS-CXF 7.3.1)
で検証しました。`../implementation/container/Dockerfile` に EAP の zip の代わりに WildFly の配布物を渡し、そのままビルドしています。

- OS / JDK: UBI 9.8、Red Hat build of OpenJDK 21.0.12.1 (java-21-openjdk-headless)、ubi9/openjdk-21-runtime 1.24
- DB: MySQL 8.4.11 (`wait_timeout=150` 秒にして、待機接続の切断を短時間で再現)
- アプリ: Spring Framework 6.2.19 の検証用 WAR (`test-app/`)、SOAP バックエンド (`ws-backend/`)、Log4j 2.26.1 の検証用 WAR (`log4j-test/`)
- TLS: 自己署名ルート CA が発行した証明書の HTTPS サーバ (nginx, `infra/`)

## シナリオ

| 記号 | 内容 | 結果 (①〜⑬ の合計) |
|---|---|---|
| S0 | 修正前 (EAP 既定 + ExtraSLB 方式 + 修正前 WAR + 修正前データソース、SIGTERM 中継あり) | 24 件 (13 種すべて再現) |
| S0n | S0 で LAUNCH_JBOSS_IN_BACKGROUND 未設定 | 停止に 91 秒、終了コード 137 (SIGKILL) |
| S1 | 修正後 (TRUST_MODE=system / INBOUND_HTTPS_MODE=remove + 修正後 WAR) | 0 件 |
| S1e | 修正後 (TRUST_MODE=elytron) | 0 件 |
| S1d | 修正後 (INBOUND_HTTPS_MODE=dedicated) | 0 件 |
| E1〜E7 | ① の追加質問 (p12 の置き場所・-D 引数・パス誤り・required・4 方式) | `results/tls-experiments.txt` |
| E8 / E9 | ④ の原因 (DEBUG で WFLYEE0048) / ⑥ の除外指定 3 パターン | `results/extra-experiments.txt` |

## ファイル

```
test-app/          検証用 iwinmichl.war のソース (JSP、Spring MVC、DB、TLS、SOAP の確認用)
ws-backend/        ③ の SOAP タイムアウト確認用サービス
log4j-test/        ⑥ の確認用 (アプリ同梱の Log4j 2)
before/            「修正前」イメージ (ExtraSLB と同じ信頼設定 + 推定した現行データソース)
infra/             テスト用 PKI と HTTPS サーバの設定
build-test-wars.sh 修正前 / 修正後の WAR を作る
run-scenario.sh    1 シナリオ (ブート → 機能確認 → 170 秒放置 → 処理中に docker stop)
run-all.sh         全シナリオと ① の実験
run-tls-experiments.sh / run-extra-experiments.sh
results/           すべてのログと集計 (*-server.log / *-http.txt / *-warnings.txt / build-*.log)
```

## 再現 (Git Bash)

```bash
export MSYS_NO_PATHCONV=1
bash infra/make-test-pki.sh <pki>
bash build-test-wars.sh <jars> <wars>
# イメージ (wl-before:1 / wl-after-{system-remove,elytron-remove,system-dedicated}:1) をビルド
# MySQL 8.4 (wait_timeout=150) と extraslb-test を docker ネットワーク wl-net 上に起動
WARS=<wars> PKI=<pki> bash run-all.sh
WARS=<wars> L4J_JARS=<log4j jars> JARS=<jars> bash run-extra-experiments.sh
```
