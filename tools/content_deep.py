# -*- coding: utf-8 -*-
"""①深掘り: 追加質問 Q1〜Q3 への回答と Container_ExtraSLB_JVM_https_outbounds の実装レビュー"""
from doclib import B, C, DIA, KID, NOTE, P, S, T

DEEP1 = [
    S("結論 (先に 3 行)",
      T(["質問", "答え", "根拠"], [
          ["Q1. ルート CA を入れた p12 を既定以外のディレクトリに置くと、この警告は出るのか",
           "出ない。警告はインバウンド用の applicationKS (application.keystore) のもので、自前 p12 の置き場所とは無関係。"
           "ただし自前 p12 を Elytron の key-store に登録しているので、そのパスを誤ると同じ WFLYELY00023 が「そのパス」でも出て、"
           "空のトラストストアのまま正常起動してしまう (アウトバウンド TLS が全滅)。",
           "KeyStoreService のソース / 実測 E1・E3"],
          ["Q2. standalone.sh の実行時引数でパスを渡していても出るのか",
           "出る。-Djavax.net.ssl.trustStore / keyStore は JDK (JSSE) の設定で、Elytron の key-store リソースはそれを読まない。"
           "引数で Elytron 側のパスを変えたいなら、key-store の path を ${env.X:既定値} などの式にする。",
           "実測 E2 (-Djavax.net.ssl.keyStore を渡しても同じ警告)"],
          ["Q3. どう対処するのが適切か",
           "ALB で TLS を終端し 8080 だけで受ける本構成では、使っていないインバウンド HTTPS 一式を jboss-cli で削除するのが最適。"
           "自前トラストストアは required=true にするか、さらに単純な「UBI のシステムトラストストアに CA を入れる方式」に移す。",
           "実測 E4〜E7 / 検証 S1・S1e・S1d"],
      ], widths=[3, 6, 2]),
      KID("警告は「お客さんに見せる自分の身分証の金庫」の話で、ルート CA の p12 は「信頼できる発行所の名簿」の話です。"
          "名簿をどの部屋に置いても、金庫の警告は消えません。使っていない受付 (8443) と金庫を設計図から消すのが一番すっきりします。")),
    S("Container_ExtraSLB_JVM_https_outbounds の実装 (確認した内容)",
      T(["ファイル", "やっていること"], [
          ["base/Dockerfile", "EAP 8.1 の公式イメージ (eap81-openjdk17-runtime-openshift-rhel9) を FROM。BuildKit Secrets で証明書を受け取り、"
                              "トラストストア生成 → application.keystore の事前生成 → embed-server で Elytron 設定を適用 → standalone_xml_history 削除"],
          ["base/scripts/build-truststore.sh", "JDK の cacerts を PKCS12 に変換してコピーし、受領した証明書 (PEM/DER/PKCS#7) を <提供元>-ca-<n> として追加。"
                                               "/opt/app/security/extraslb-truststore.p12 (パスワード changeit、0444)"],
          ["base/jboss-cli/configure-outbound-tls.cli", "key-store=extraslb-trust-store (path は ${env.EXTRASLB_TRUSTSTORE_PATH:...} の式、required 指定なし)、"
                                                         "trust-manager、client-ssl-context (TLSv1.3/1.2)、default-ssl-context に登録"],
          ["base/scripts/entrypoint.sh", "起動前チェック、(必要なら) embed-server、履歴の正規化、application.keystore の補完、"
                                         "exec standalone.sh -Djavax.net.ssl.trustStore=... -Djavax.net.ssl.trustStorePassword=... -Djavax.net.ssl.trustStoreType=..."],
          ["base/scripts/provision-application-keystore.sh", "applicationKS と同じ形 (alias=server, CN=localhost, RSA2048, 3650 日, JKS, パスワード password) の鍵ストアを keytool で事前生成"],
          ["docs/wflyely00023-application-keystore.md", "警告は applicationKS 由来でアウトバウンドとは無関係、と分析。対処として事前生成を採用、削除案は却下"],
      ], widths=[2, 6])),
    S("評価: 正しい点",
      B("警告の出どころの判定 (applicationKS 由来でアウトバウンドとは無関係) は正しい。ソース (KeyStoreService / elytron-app feature group) と実測 E1・E2 で確認。",
        "cacerts を土台に CA を追加する設計は正しい。パブリック CA 宛 (AWS SDK 等) の通信を壊さない (実測: Google 宛も 3 種類のクライアントで成功)。",
        "「Elytron の default-ssl-context」と「-Djavax.net.ssl.trustStore」の二層構えは必要。Apache CXF は TLS パラメータ未指定時に "
        "javax.net.ssl.trustStore / trustStoreType / trustStorePassword を自分で読んで SSLContext を作り、Elytron の default-ssl-context は使わない (CXF の jsse SSLUtils で確認)。",
        "BuildKit Secrets で証明書をイメージ層に残さない、CLI をビルド時に適用して起動時の embed-server をなくす、standalone_xml_history を消す、"
        "起動前チェックで理由を出して止める、はいずれも良い実装。")),
    S("評価: 改善した方がよい点",
      T(["現状", "問題", "改善 (本書の実装)"], [
          ["1. application.keystore を事前生成 (provision)", "既知のパスワード (password) の秘密鍵 (CN=localhost) を全タスクで共有し、使っていない 8443 が待ち受け続ける (実測 E5: 8443 で CN=localhost を返す)",
           "11-inbound-https-remove.cli で 8443 一式を削除 (実測 E6: 待ち受けなし、警告 0)。ALB→タスクも暗号化するなら 12-inbound-https-dedicated.cli"],
          ["2. extraslb-trust-store に required が無い (既定 false)", "パスを誤ると WFLYELY00023 (WARN) だけで正常起動し、既定 SSLContext 経由の HTTPS がパブリック CA 宛も含めて全滅 (実測 E3)",
           "required=true (実測 E4: WFLYELY00022 で起動時に必ず失敗が見える) + entrypoint の事前チェック"],
          ["3. ベースイメージが OpenJDK 17 の OpenShift 用 EAP イメージ", "EAP 8.1 で OpenJDK 17 の OpenShift イメージは非推奨 (8.2 で削除予定)。実環境は OpenJDK 21",
           "UBI 9.8 + Red Hat build of OpenJDK 21 (ubi9/openjdk-21-runtime) を実行ベースに"],
          ["4. cacerts をコピーして Elytron に読ませる", "ビルド時点のスナップショットで OS の CA 更新に追随しない。期限切れのルートがあると Elytron が WFLYELY00024 を出す",
           "TRUST_MODE=system: CA を /etc/pki/ca-trust/source/anchors に置いて update-ca-trust。JDK の cacerts に入る (実測 E7)。-D も Elytron 設定も不要"],
          ["5. -Djavax.net.ssl.trustStorePassword を引数で渡す", "プロセス引数 (ps / /proc/<pid>/cmdline) に出る (中身は公開証明書なので実害は小さい)", "system モードなら不要"],
          ["6. entrypoint で LAUNCH_JBOSS_IN_BACKGROUND を設定していない", "standalone.sh が PID 1 だと SIGTERM が JVM に届かず、停止処理が走らない (⑬ に関係)", "entrypoint で export LAUNCH_JBOSS_IN_BACKGROUND=true"],
      ], widths=[3, 4, 4])),
    S("信頼設定 (アウトバウンド) の 2 方式の比較",
      T(["観点", "TRUST_MODE=system (推奨)", "TRUST_MODE=elytron (ExtraSLB 方式を強化)"], [
          ["CA の置き場所", "/etc/pki/ca-trust/source/anchors/<提供元>-ca-<n>.pem → update-ca-trust → JDK の cacerts", "/opt/app/security/extraslb-truststore.p12 (cacerts のコピー + CA)"],
          ["SSLContext.getDefault()", "JSSE 既定 (cacerts。CA 入り)", "Elytron の DelegatingSSLContext (p12)"],
          ["CXF 等の自前 SSLContext", "cacerts (javax.net.ssl.trustStore 未指定)", "-Djavax.net.ssl.trustStore の p12"],
          ["必要な設定", "Dockerfile の 1 ステップだけ", "Elytron の 4 リソース + standalone.sh の -D 引数 3 つ"],
          ["OS の CA 更新への追随", "する (イメージ更新で ca-certificates と一緒に)", "しない (ビルド時点のコピー)"],
          ["WFLYELY00024 (期限切れの警告)", "出ない (Elytron は cacerts を読まない)", "cacerts に期限切れのルートがあれば出る"],
          ["OS のツール (curl 等)", "同じ CA を信頼する", "信頼しない"],
          ["向いている場合", "コンテナ全体で同じ CA を信頼してよい (通常これ)", "宛先ごとに信頼を分けたい / Elytron の authentication-client で使い分けたい"],
      ], widths=[2, 4, 4]),
      T(["クライアント (検証で実測)", "参照する設定", "system", "elytron", "現行 (修正前)"], [
          ["A HttpsURLConnection (既定)", "SSLContext.getDefault()", "OK", "OK", "OK"],
          ["B java.net.http.HttpClient (既定)", "SSLContext.getDefault()", "OK", "OK", "OK"],
          ["C new SSLContext(TLS).init(null,...) / CXF 等", "JSSE 既定の TrustManagerFactory (javax.net.ssl.trustStore → 無ければ cacerts)", "OK", "OK", "OK"],
          ["参考: 自前 p12 のパスを誤った場合 (E3)", "-", "-", "起動時に失敗 (required=true)", "A・B はパブリック CA 宛も NG、C は自己署名 CA 宛のみ NG"],
      ], widths=[4, 5, 1, 2, 4]),
      NOTE("C の「パスを誤った場合」で自己署名 CA 宛だけ失敗しパブリック CA 宛は成功したのは、存在しない javax.net.ssl.trustStore を指定すると "
           "JDK が既定の cacerts に戻るため (実測)。一部の宛先だけが失敗するので、気づきにくい壊れ方になります。")),
    S("インバウンド HTTPS (8443) の扱い 4 方式の実測",
      T(["方式", "WFLYELY00023 / 01084", "8443", "設定", "評価"], [
          ["keep (EAP 既定)", "出る / 出る", "初回接続時に CN=localhost の自己署名を生成して待ち受け", "なし", "△"],
          ["provision (ExtraSLB 現行)", "出ない / 出ない", "CN=localhost (イメージに焼いた鍵) で待ち受け", "keytool で事前生成", "○ 不要な鍵と口が残る"],
          ["remove ★", "出ない / 出ない", "待ち受けなし", "11-inbound-https-remove.cli", "◎ 本構成に最適"],
          ["dedicated", "出ない / 出ない", "起動時に渡した証明書 (CN=iwinmichl.internal) で待ち受け", "12-inbound-https-dedicated.cli + Secrets", "○ ALB→タスクも暗号化する場合"],
      ], widths=[2, 2, 4, 3, 2])),
    S("推奨構成と移行手順",
      B("1) Dockerfile を implementation/container/Dockerfile に置き換える (ビルド段 UBI 9.8、実行段 ubi9/openjdk-21-runtime)。"
        "証明書の受け渡し (cacert-secret-args.sh と BuildKit Secrets) は ExtraSLB と同じ。",
        "2) TRUST_MODE=system でビルドし、アウトバウンド HTTPS を確認する (自己署名 CA 宛とパブリック CA 宛)。"
        "問題があれば TRUST_MODE=elytron で ExtraSLB と同じ二層構え (required=true 付き) に戻せる。",
        "3) INBOUND_HTTPS_MODE=remove でビルドし、ALB のターゲットグループが HTTP:8080 であることを確認する。",
        "4) ExtraSLB の entrypoint.sh を使い続ける場合は、export LAUNCH_JBOSS_IN_BACKGROUND=true を追加し、"
        "EXTRASLB_APP_KEYSTORE_MODE=skip にする (事前生成が不要になるため)。",
        "5) 起動ログで WFLYELY00023 / 01084 が 0 件、/subsystem=elytron:read-attribute(name=default-ssl-context) が "
        "undefined (system モード) であることを確認する。")),
    S("実測の記録 (要約)",
      T(["実験", "条件", "結果"], [
          ["E1", "現行 (修正前イメージ)", "application.keystore について WFLYELY00023・01084。アウトバウンドは 3 クライアントとも OK。8443 は CN=localhost"],
          ["E2", "-Djavax.net.ssl.keyStore も渡す", "WFLYELY00023 は変わらず出る"],
          ["E3", "自前 p12 のパスを誤る (required=false)", "そのパスでも WFLYELY00023。正常起動するが A・B は全宛先 NG、C は自己署名 CA 宛 NG"],
          ["E4", "同じ誤り + required=true", "WFLYELY00022 → サービス起動失敗 → started (with errors)。entrypoint 経由なら起動前に FATAL"],
          ["E5", "ExtraSLB の事前生成", "警告 0、8443 で CN=localhost"],
          ["E6", "remove / dedicated", "remove: 警告 0、8443 なし。dedicated: 警告 0、8443 で正式な証明書。鍵ストア渡し忘れは entrypoint が FATAL"],
          ["E7", "system モード", "JDK の cacerts (/etc/pki/ca-trust/extracted/java/cacerts) に extraslbtestrootca が trustedCertEntry として入る"],
      ], widths=[1, 3, 8])),
]
