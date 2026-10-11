# -*- coding: utf-8 -*-
"""警告 ①〜④ の原稿"""
from doclib import B, C, DIA, KID, NOTE, P, S, T

# =====================================================================
# ① WFLYELY00023
# =====================================================================
W01 = {
    "key": "W01", "no": "①", "sheet": "①WFLYELY00023", "id": "WFLYELY00023", "severity": "C",
    "title": "① WFLYELY00023: keystore ファイル application.keystore が存在しない (空で代用した)",
    "user_log": "WFLYELY00023: keystoreファイル /opt/jboss-eap/standalone/configuration/application.keystoreは存在しない。空白を使用しました。",
    "verify_labels": ["WFLYELY00023 keystore file does not exist", "WFLYELY01084 self-signed will be generated",
                      "WFLYELY00022 does not exist and required"],
    "sections": [
        S("ひとことで (小学生向け)",
          KID("EAP というビルの設計図 (standalone.xml) には、最初から「HTTPS のお客さん用の受付 (8443 番の窓口)」と、"
              "そこで見せる「ビルの身分証と秘密のハンコを入れる金庫 (application.keystore)」が書いてあります。\n"
              "でも引っ越してきたとき、金庫は実際には置かれていません。最初の HTTPS のお客さんが来たときに、"
              "警備室がその場で身分証を作って金庫に入れる約束になっているからです。\n"
              "警備室 (Elytron) は毎朝の点検で「設計図にある金庫が見当たらないので、とりあえず空っぽの箱を置きます」"
              "と日記に書きます。これがこの警告です。\n"
              "あなたが別の部屋に置いた「信頼できる発行所の名簿 (ルート CA を入れた p12)」とは、まったく別の物の話です。"),
          T(["たとえ", "本当の仕組み"], [
              ["ビルの設計図", "standalone.xml の elytron サブシステム"],
              ["身分証とハンコの金庫", "key-store=applicationKS → standalone/configuration/application.keystore (サーバ証明書と秘密鍵)"],
              ["HTTPS の受付 (8443)", "Undertow の https-listener=https (ssl-context=applicationSSC)"],
              ["その場で身分証を作る約束", "key-manager=applicationKM の generate-self-signed-certificate-host=localhost (初回接続時に自己署名証明書を生成)"],
              ["毎朝の点検", "ブート時に key-store サービスが起動する (誰も使っていなくても起動する)"],
              ["空っぽの箱で代用", "空のキーストアで起動を続ける (Used blank)"],
              ["信頼できる発行所の名簿", "トラストストア (extraslb-truststore.p12)。相手の証明書を確かめる用。今回の警告とは無関係"],
          ], widths=[1, 3])),
        S("メッセージの正体",
          T(["項目", "内容"], [
              ["英語原文", "WFLYELY00023: KeyStore file '%s' does not exist. Used blank."],
              ["ID / レベル", "WFLYELY00023 / WARN"],
              ["ロガー", "org.wildfly.extension.elytron"],
              ["出す場所", "org.wildfly.extension.elytron.KeyStoreService#start (ElytronSubsystemMessages#keyStoreFileNotExistsButIgnored)"],
              ["タイミング", "サーバのブート時 (MSC service thread)。ビルド時の embed-server でも同じく出る"],
              ["一緒に出るもの", "WFLYELY01084: KeyStore ... not found, it will be auto-generated on first use with a self-signed certificate for host localhost"],
              ["兄弟", "WFLYELY00022 (required=true でファイルが無い → 起動失敗) / WFLYELY01085 (自己署名を生成した) / WFLYELY00024 (証明書の期限切れ)"],
          ], widths=[1, 4])),
        S("動作原理",
          B("EAP 8.1 の既定構成 (Galleon の feature group「elytron-app」) は、次の 3 つを Elytron に作る: "
            "key-store=applicationKS (path=application.keystore, relative-to=jboss.server.config.dir, type=JKS, パスワード password)、"
            "key-manager=applicationKM (generate-self-signed-certificate-host=localhost)、server-ssl-context=applicationSSC。"
            "Undertow の https-listener=https (8443) が applicationSSC を参照する。",
            "KeyStoreDefinition は key-store ごとに KeyStoreService を Mode.ACTIVE でインストールする。"
            "このため、https-listener が使っているかどうかに関係なく、ブート時に必ず start() が呼ばれる。",
            "start() は path を relative-to で解決し、ファイルが無いとき required (既定 false) を見る。"
            "true なら WFLYELY00022 で StartException、false なら WFLYELY00023 を WARN で出して空の KeyStore を読み込んだ状態で続行する。",
            "applicationKM は generate-self-signed-certificate-host を持つので、ファイルが無いと WFLYELY01084 (予告) を出す。"
            "最初の HTTPS ハンドシェイクの時点で RSA 2048 / SHA256withRSA / 有効 10 年 / CN=localhost / 別名 server の自己署名証明書を作り、"
            "application.keystore に保存する (WFLYELY01085)。",
            "コンテナは毎回イメージの初期状態から起動するので、ファイルは毎回無い → 毎回この警告が出る。"
            "readonlyRootFilesystem=true だと生成した鍵の保存にも失敗する。")),
        S("動作イメージ",
          DIA("""[ブート]
 standalone.xml を読む
  ├ elytron key-store=applicationKS (application.keystore) …… Mode.ACTIVE なので必ず起動
  │    ├ ファイルあり → 読み込む (期限切れの証明書があれば WFLYELY00024)
  │    └ ファイルなし ─┬ required=true  → WFLYELY00022 (サービス起動失敗)
  │                     └ required=false → WFLYELY00023「空で代用」(WARN) ★今回
  ├ elytron key-manager=applicationKM (generate-self-signed-certificate-host=localhost)
  │    └ ファイルなし → WFLYELY01084「初回利用時に自己署名証明書を作ります」(WARN)
  └ undertow https-listener (8443) → applicationSSC → applicationKM → applicationKS
[最初の HTTPS 接続 (8443)]
  → 自己署名証明書 (CN=localhost) を生成して application.keystore に保存 (WFLYELY01085)

[アウトバウンド HTTPS (別系統。applicationKS は一切通らない)]
  アプリ → HttpsURLConnection / java.net.http → SSLContext.getDefault()
          → (Elytron default-ssl-context) extraslb-client-ssl-context → trust-manager → extraslb-trust-store (p12)
  アプリ → Apache CXF / 自前の SSLContext → JSSE 既定の TrustManagerFactory → -Djavax.net.ssl.trustStore (同じ p12)""",
              "図: インバウンド用の鍵 (警告の対象) と、アウトバウンド用の信頼リスト (ExtraSLB の実装) は別の経路")),
        S("歴史・背景・必要になった経緯",
          B("2016-06 WFCORE-1576: レガシーのセキュリティレルム (ApplicationRealm) に「初回利用時に自己署名証明書を自動生成」が入った。"
            "インストール直後から HTTPS を試せるように (SSL out of the box) するための機能で、"
            "このとき「application.keystore は同梱せず、必要になったら作る」設計になった。",
            "2017 WildFly 11 / EAP 7.1: 新しいセキュリティ基盤 Elytron が導入される。",
            "2020-11 WFCORE-5095 (EAP7-1545): Elytron にも同じ自動生成 (generate-self-signed-certificate-host) が入り、"
            "既定構成に applicationKS / applicationKM / applicationSSC が加わった。",
            "2021 WildFly 25: レガシーセキュリティが削除され、2024 年の EAP 8.0 で Elytron に一本化。既定の https-listener は applicationSSC を参照する。",
            "結果として「ファイルは同梱しない + key-store サービスは常に起動する」組み合わせになり、"
            "毎回まっさらな状態で起動するコンテナでは、ブートのたびにこの警告が出るようになった。"),
          NOTE("「起動のたびに出る」こと自体は、設計どおりの挙動です。サーバ単体で使い続ける環境では、"
               "初回の HTTPS 接続でファイルができるので 2 回目以降は出ません。コンテナではそれが毎回リセットされます。")),
        S("この環境での原因と切り分け",
          P("原因は EAP 標準の applicationKS です。警告のパスが application.keystore であることがその証拠で、"
            "Container_ExtraSLB_JVM_https_outbounds の実装 (ルート CA を入れた p12 を /opt/app/security に置き、"
            "standalone.sh に -Djavax.net.ssl.trustStore* を渡す) とは関係ありません。下の実測で確かめました。"),
          T(["実験", "条件", "結果"], [
              ["E1", "現行 (p12 は /opt/app/security、-D で trustStore を渡す)", "application.keystore について WFLYELY00023 と WFLYELY01084 が 1 件ずつ。アウトバウンド HTTPS は自己署名 CA 宛・パブリック CA 宛とも 3 種類のクライアントで成功"],
              ["E2", "Q2 の確認: -Djavax.net.ssl.keyStore=<p12> も渡す", "WFLYELY00023 は変わらず出る (Elytron の key-store は -D を読まない)"],
              ["E3", "自前 p12 のパスを誤る (現行の required=false)", "WFLYELY00023 が「そのパス」でも出て、サーバは正常起動 (WFLYSRV0025)。しかし既定 SSLContext 経由の HTTPS はパブリック CA 宛も含めて全滅 (trustAnchors parameter must be non-empty)"],
              ["E4", "同じ誤りで required=true", "WFLYELY00022 でサービス起動失敗 → started (with errors) (ERROR)。entrypoint の事前チェックなら起動前に FATAL で止まる"],
          ], widths=[1, 3, 6]),
          C("""# 実機での確認 (起動中のコンテナで)
/opt/jboss-eap/bin/jboss-cli.sh -c '/subsystem=elytron/key-store=applicationKS:read-resource'
/opt/jboss-eap/bin/jboss-cli.sh -c '/subsystem=undertow/server=default-server:read-children-names(child-type=https-listener)'
# ALB のターゲットグループが HTTP:8080 なら 8443 は使われていない
aws elbv2 describe-target-groups --names <tg-name> --query 'TargetGroups[].{p:Protocol,port:Port}'""", "bash", "確認コマンド")),
        S("影響度と放置した場合のリスク",
          P("危険度 C (無害だが整理すべき)。アウトバウンド HTTPS には影響しません (E1 で実測)。ただし次の点は放置しない方がよいです。"),
          B("使っていない 8443 が待ち受けている (E1: 8443 に接続すると CN=localhost の自己署名証明書が返る)。不要な口は攻撃面になる。",
            "readonlyRootFilesystem=true にすると、初回接続時の自己署名証明書の保存が失敗する。",
            "毎回の WARN が、本当に見るべき警告 (証明書の期限切れ WFLYELY00024 など) を埋もれさせる。")),
        S("対処方針の比較",
          T(["方式", "やること", "警告", "8443", "イメージ内の秘密鍵", "評価"], [
              ["(a) 削除 remove ★推奨", "jboss-cli で https-listener → applicationSSC → applicationKM → applicationKS の順に削除",
               "消える (E6)", "待ち受けなし", "なし", "◎ ALB 終端・8080 受信の本構成に最適"],
              ["(b) 事前生成 provision (ExtraSLB 現行)", "ビルド時に keytool で application.keystore を作って同梱",
               "消える (E5)", "CN=localhost で待ち受け", "既知パスワードの鍵を全タスクで共有", "○ 動くが、不要な鍵と口が残る"],
              ["(c) 正式な鍵ストア dedicated", "起動時に渡す鍵ストアに差し替え (required=true、自動生成を止める)",
               "消える (E6)", "正式な証明書で待ち受け", "なし (実行時に注入)", "○ ALB→タスク間も暗号化したい場合"],
              ["(d) ログ抑止", "ロガーのレベルやフィルタで隠す", "見えなくなるだけ", "そのまま", "-", "× 同じカテゴリの重要な警告まで隠れる"],
              ["(e) 何もしない keep", "-", "出続ける", "自己署名を遅延生成", "実行時に生成", "△"],
          ], widths=[3, 5, 2, 2, 3, 4]),
          NOTE("ALB はターゲットの証明書を検証しないため、ALB → タスク間を暗号化するだけなら自己署名でも通信できます。"
               "その場合でも鍵はイメージに焼かず、(c) のように実行時に渡すのが安全です。"
               "Q1〜Q3 の詳しい回答と、ExtraSLB の実装の評価は「①深掘り」シートにまとめています。")),
        S("実装 (jboss-cli)",
          C("""# 11-inbound-https-remove.cli (抜粋。全文は「実装コード」シート)
if (outcome == success) of /subsystem=undertow/server=default-server/https-listener=https:read-resource
    /subsystem=undertow/server=default-server/https-listener=https:remove
end-if
if (outcome == success) of /subsystem=elytron/server-ssl-context=applicationSSC:read-resource
    /subsystem=elytron/server-ssl-context=applicationSSC:remove
end-if
if (outcome == success) of /subsystem=elytron/key-manager=applicationKM:read-resource
    /subsystem=elytron/key-manager=applicationKM:remove
end-if
if (outcome == success) of /subsystem=elytron/key-store=applicationKS:read-resource
    /subsystem=elytron/key-store=applicationKS:remove
end-if""", "text", "インバウンド HTTPS 一式の削除 (参照する側から順に)"),
          C("""# 10-elytron-outbound-truststore.cli (TRUST_MODE=elytron の場合。抜粋)
/subsystem=elytron/key-store=extraslb-trust-store:write-attribute(name=required, value=true)""", "text",
            "自前トラストストアは required=true (パス誤りを起動時に必ず見えるようにする)"),
          P("TRUST_MODE=system (推奨) の場合は、CA を UBI のシステムトラストストアへ入れる (install-ca-anchors.sh) ので、"
            "Elytron のトラストストア設定も -D 引数も不要になります。詳しくは「①深掘り」。")),
        S("確認方法",
          C("""/opt/jboss-eap/bin/jboss-cli.sh -c '/subsystem=elytron:read-children-names(child-type=key-store)'
# → applicationKS が無いこと (remove モード)
/opt/jboss-eap/bin/jboss-cli.sh -c '/subsystem=undertow/server=default-server:read-children-names(child-type=https-listener)'
# → [] (https-listener が無いこと)
grep -c WFLYELY00023 server.log   # → 0""", "bash")),
    ],
    "refs": ["eap-tls", "wfcore5095", "src-ksservice", "src-elyapp", "aws-alb-cert"],
}

# =====================================================================
# ② WFLYSRV0058
# =====================================================================
W02 = {
    "key": "W02", "no": "②", "sheet": "②WFLYSRV0058", "id": "WFLYSRV0058", "severity": "C",
    "title": "② WFLYSRV0058: jboss-deployment-structure.xml で追加したリソースルートが存在しない",
    "user_log": "WFLYSRV0058: jboss-deployment-structure.xmlで追加されたリソースルート/content/iwinmichl.war/WEB-INF/classes/testClassesは存在しません。",
    "verify_labels": ["WFLYSRV0058 resource root does not exist"],
    "sections": [
        S("ひとことで (小学生向け)",
          KID("お店がビルに引っ越すとき、「荷物リスト (jboss-deployment-structure.xml)」に"
              "「testClasses という段ボールも本棚に並べてね」と書いてありました。\n"
              "ところが、その段ボールは荷物の中に入っていませんでした。引っ越し係は「リストにある段ボールが見つからないので、"
              "飛ばします」と日記に書きました。お店はちゃんと開店できますが、リストが古いままだということです。"),
          T(["たとえ", "本当の仕組み"], [
              ["荷物リスト", "WEB-INF/jboss-deployment-structure.xml"],
              ["本棚に並べる段ボール", "<resources><resource-root path=\"...\"/> (追加のリソースルート = クラスを探す場所)"],
              ["荷物", "iwinmichl.war の中身 (サーバ内では VFS の /content/iwinmichl.war/... に見える)"],
              ["飛ばす", "その resource-root を登録しない (デプロイは続行)"],
          ], widths=[1, 3])),
        S("メッセージの正体",
          T(["項目", "内容"], [
              ["英語原文", "WFLYSRV0058: Additional resource root %s added via jboss-deployment-structure.xml does not exist"],
              ["ID / レベル", "WFLYSRV0058 / WARN"],
              ["ロガー", "org.jboss.as.server.deployment"],
              ["出す場所", "DeploymentStructureDescriptorParser (ServerLogger#additionalResourceRootDoesNotExist)"],
              ["タイミング", "デプロイの STRUCTURE フェーズ (記述子を読んだ直後)"],
          ], widths=[1, 4])),
        S("動作原理",
          B("デプロイされた WAR は、JBoss Modules の 1 モジュール (deployment.iwinmichl.war) になり、"
            "WEB-INF/classes と WEB-INF/lib/*.jar が「リソースルート (クラスやリソースを探す場所)」として登録される。"
            "中身は VFS で /content/iwinmichl.war/... にマウントされる (警告に出ている /content/... はこの仮想パス)。",
            "jboss-deployment-structure.xml の <resources><resource-root path=\"X\"/> は、標準以外の場所を追加のリソースルートにする指定。"
            "path は WAR のルートからの相対パス。",
            "パーサは X が存在するかを確かめ、無ければ WFLYSRV0058 を出して登録しない。あれば RESOURCE_ROOTS に加え、"
            "アノテーション索引 (Jandex) を作り、モジュールのルートとして扱う。",
            "もし WEB-INF/classes/testClasses が実在していたら、その下の com/example/Foo.class が com.example.Foo として"
            "読み込めるようになる (パッケージの起点がずれる)。テスト用クラスが本番で読み込まれる危険がある。")),
        S("動作イメージ",
          DIA("""[STRUCTURE フェーズ]
 WAR を VFS にマウント (/content/iwinmichl.war)
  ├ 標準のリソースルート: WEB-INF/classes, WEB-INF/lib/*.jar
  └ jboss-deployment-structure.xml の <resource-root path="WEB-INF/classes/testClasses"/>
        ├ 実在する → 追加のリソースルートとして登録・索引化
        └ 実在しない → WFLYSRV0058 (WARN) を出して読み飛ばす ★今回 → デプロイは続行""")),
        S("歴史・背景・必要になった経緯",
          B("JBoss AS 5/6 (〜2010) は VFS と階層型クラスローダで、アプリとサーバのライブラリが混ざりやすく、"
            "jboss-classloading.xml などで調整していた。",
            "2011 年の JBoss AS 7.0 で JBoss Modules (モジュール単位で見える範囲を区切る方式) に切り替わり、"
            "デプロイごとの依存・除外・追加リソースルートを宣言する jboss-deployment-structure.xml が導入された。",
            "WildFly 9 (2015) でメッセージ ID が JBAS から WFLYSRV 等に変わり、現在の形になった。")),
        S("この環境での原因と切り分け",
          P("jboss-deployment-structure.xml に、WAR に存在しない WEB-INF/classes/testClasses が残っています。"
            "開発時のテスト用設定の名残か、別プロジェクトからの複写と考えられます。本番 WAR にテストクラスが入っていないこと自体は正しい状態です。"),
          C("""# WAR の中身と記述子を突き合わせる (implementation/tools/scan-war.py)
python scan-war.py iwinmichl.war
## ② resource-root (jboss-deployment-structure.xml)
  NG  WEB-INF/classes/testClasses  ← WAR に無い: WFLYSRV0058 の原因。記述を削除する""", "text", "検証用 WAR での実行結果")),
        S("影響度と放置した場合のリスク",
          P("危険度 C。指定は無視されるだけで、動作には影響しません。ただし、将来ビルド設定が変わって testClasses が WAR に入ると、"
            "テスト用クラスが本番で読み込まれるようになります。記述子と WAR の中身がずれているサインとして直しておきます。")),
        S("対処方針の比較",
          T(["方式", "内容", "評価"], [
              ["記述を削除 ★推奨", "<resource-root path=\"WEB-INF/classes/testClasses\"/> を消す。WEB-INF/classes は最初からリソースルート", "◎"],
              ["環境ごとに記述子を切り替え", "Maven プロファイルで開発用だけ追加", "△ 本番で不要なら複雑になるだけ"],
              ["ビルド時の検査", "scan-war.py をビルドの最後に実行し、NG があれば止める", "◎ 再発防止"],
          ], widths=[2, 5, 1])),
        S("実装 (WAR 側)",
          C("""<!-- WEB-INF/jboss-deployment-structure.xml (修正後の抜粋) -->
<jboss-deployment-structure xmlns="urn:jboss:deployment-structure:1.3">
    <deployment>
        <!-- <resources><resource-root path="WEB-INF/classes/testClasses"/></resources> は削除 -->
    </deployment>
</jboss-deployment-structure>""", "xml"),
          C("""<!-- pom.xml: 念のため testClasses を WAR に入れない -->
<plugin>
  <groupId>org.apache.maven.plugins</groupId>
  <artifactId>maven-war-plugin</artifactId>
  <configuration>
    <packagingExcludes>WEB-INF/classes/testClasses/**</packagingExcludes>
  </configuration>
</plugin>""", "xml")),
        S("確認方法",
          C("""python scan-war.py iwinmichl.war    # ② が OK になること
grep -c WFLYSRV0058 server.log        # → 0""", "bash")),
    ],
    "refs": ["src-serverlogger", "src-dsparser"],
}

# =====================================================================
# ③ WFLYSRV0018
# =====================================================================
W03 = {
    "key": "W03", "no": "③", "sheet": "③WFLYSRV0018", "id": "WFLYSRV0018", "severity": "B",
    "title": "③ WFLYSRV0018: デプロイが private モジュール org.apache.cxf.impl を使っている",
    "user_log": "WFLYSRV0018:デプロイメント\"deployment.iwinmichl.warはプライベートモジュール\"org.apache.cxf.impl\"を使っていますが、このモジュールは今後のバージョンで予告なく削除される可能性があります。",
    "verify_labels": ["WFLYSRV0018 private module used", "  of which org.apache.cxf.impl", "  of which org.jboss.vfs (spring-core)"],
    "sections": [
        S("ひとことで (小学生向け)",
          KID("ビルの図書館の本棚には「どなたでもどうぞ (public)」の棚と「職員専用 (private)」の棚があります。\n"
              "iwinmichl のお店は、貸出カードに職員専用の棚 (org.apache.cxf.impl) を自分で書き込みました。\n"
              "司書さんは本を貸してくれますが、「職員用の本は予告なく入れ替えることがあるので、ある日突然使えなくなっても知りませんよ」"
              "と日記に書きました。"),
          T(["たとえ", "本当の仕組み"], [
              ["図書館の棚", "JBoss Modules のモジュール ($JBOSS_HOME/modules/... の module.xml)"],
              ["職員専用の札", "module.xml の <property name=\"jboss.api\" value=\"private\"/>"],
              ["貸出カードに自分で書く", "jboss-deployment-structure.xml の <dependencies> や MANIFEST.MF の Dependencies: (ユーザー指定の依存)"],
              ["司書が気をきかせて付ける本", "サブシステムが自動で付ける暗黙の依存 (こちらは private でも警告しない)"],
          ], widths=[1, 3])),
        S("メッセージの正体",
          T(["項目", "内容"], [
              ["英語原文", "WFLYSRV0018: Deployment \"%s\" is using a private module (\"%s\") which may be changed or removed in future versions without notice."],
              ["ID / レベル", "WFLYSRV0018 / WARN"],
              ["ロガー", "org.jboss.as.dependency.private (unsupported は org.jboss.as.dependency.unsupported、deprecated は ...deprecated)"],
              ["出す場所", "ModuleLoadService#start (デプロイのモジュールを読み込むとき)"],
              ["兄弟", "WFLYSRV0019 (unsupported モジュール) / WFLYSRV0221 (deprecated モジュール)"],
          ], widths=[1, 4])),
        S("動作原理",
          B("モジュールの module.xml には jboss.api プロパティで公開区分が書かれている: public (既定) / private / unsupported / deprecated。"
            "Red Hat は「JBoss EAP 8 Included Modules」で一覧を公開しており、org.apache.cxf は PUBLIC、"
            "org.apache.cxf.impl・org.jboss.vfs・org.jboss.logmanager.log4j2 は PRIVATE。",
            "デプロイのモジュールを読み込む ModuleLoadService は、依存のうち isUserSpecified() が true のもの"
            "(jboss-deployment-structure.xml の <dependencies>、WAR や WEB-INF/lib の jar の MANIFEST.MF の Dependencies:) だけについて、"
            "相手の jboss.api を調べ、private なら WFLYSRV0018 を出す。",
            "webservices サブシステムが JAX-WS のために自動で付ける CXF の依存は「暗黙の依存」なので、private でも警告しない。"
            "つまりこの警告は「アプリ自身が private モジュールを指名した」ことを示す。",
            "org.apache.cxf.impl には CXF の実装 (cxf-rt-frontend-jaxws、cxf-rt-transports-http = HTTPConduit / HTTPClientPolicy、"
            "WS-Security など) が入っている。CXF の HTTPConduit を直接触ってタイムアウトや TLS を設定するコードがあると、この依存が必要になる。",
            "検証で見つかったもう 1 件: spring-core-6.2.19.jar の MANIFEST.MF に「Dependencies: jdk.unsupported,org.jboss.vfs」が書かれており"
            "(Spring が JBoss の VFS 上でクラスパスを走査するため)、Spring を使う WAR では org.jboss.vfs についても WFLYSRV0018 が必ず出る。")),
        S("動作イメージ",
          DIA("""[デプロイのモジュールを読み込む]
 依存の一覧
  ├ 暗黙の依存 (logging, webservices, ee ...)            → チェックしない
  └ ユーザー指定の依存
       ├ jboss-deployment-structure.xml: org.apache.cxf.impl → jboss.api=private → WFLYSRV0018 ★今回
       └ spring-core.jar の MANIFEST.MF: jdk.unsupported, org.jboss.vfs → org.jboss.vfs は private → WFLYSRV0018""")),
        S("歴史・背景・必要になった経緯",
          B("2015-10 WFCORE-1090、2015-12 WFLY-5804: module.xml に jboss.api=private を付けて「内部用」を明示するようになった (WildFly 10 / EAP 7 系)。",
            "目的は、サポートする API (public) と内部実装 (private) を分けること。内部ライブラリ (CXF など) はメジャー更新で中身が大きく変わるので、"
            "アプリが内部実装に依存すると EAP の更新で壊れる。それを事前に知らせるのがこの警告。",
            "EAP 8.1 のリリースノートにも「ActiveMQ Artemis の内部モジュールを private にし、公開用の org.apache.activemq.artemis.client を新設」"
            "という変更があり、private 化は現在も進んでいる。")),
        S("この環境での原因と切り分け",
          P("jboss-deployment-structure.xml に <module name=\"org.apache.cxf.impl\"/> があります。アプリが CXF の実装クラスを直接使っているか、"
            "以前の対処の名残です。まず実際に使っているかを確かめます。"),
          C("""# WAR のクラスが CXF 実装クラスを参照しているか (JDK の jdeps)
jdeps -verbose:class -cp 'WEB-INF/lib/*' WEB-INF/classes | grep -E 'org\\.apache\\.cxf\\.(transport|transports|jaxws|configuration\\.jsse)'
# 明示依存の一覧 (記述子 + 各 jar の MANIFEST)
python scan-war.py iwinmichl.war   # ## ③ に org.apache.cxf.impl / org.jboss.vfs が出る""", "bash"),
          T(["よくある使い方", "必要なクラス (所属モジュール)", "private 依存なしの代替"], [
              ["SOAP の接続/応答タイムアウト", "HTTPConduit, HTTPClientPolicy (org.apache.cxf.impl)", "BindingProvider のリクエストコンテキストに jakarta.xml.ws.client.connectionTimeout / receiveTimeout (CXF 4 が読む。検証で動作確認)"],
              ["TLS の信頼設定", "TLSClientParameters (org.apache.cxf.impl)", "JVM 既定のトラストストアに CA を入れる (TRUST_MODE=system) か -Djavax.net.ssl.trustStore。CXF は TLS パラメータ未指定時に javax.net.ssl.trustStore → cacerts を読む"],
              ["CXF の Bus やインターセプタ", "org.apache.cxf (cxf-core。public)", "public な org.jboss.ws.cxf.jbossws-cxf-client (services=\"import\") に依存する"],
          ], widths=[2, 3, 5])),
        S("影響度と放置した場合のリスク",
          P("危険度 B。今は動きますが、EAP のアップデートやマイナーバージョンアップで CXF の実装が入れ替わると、"
            "コンパイル済みのアプリが実行時に壊れる可能性があり、Red Hat のサポート対象外の使い方でもあります。"
            "org.jboss.vfs の 1 件は Spring 自身の宣言によるもので、アプリ側では消せない (無害)。")),
        S("対処方針の比較",
          T(["方式", "内容", "評価"], [
              ["依存を削除し標準 API で書く ★推奨", "タイムアウトは jakarta.xml.ws.client.*Timeout、TLS は JVM 既定のトラストストア", "◎ private 依存ゼロ"],
              ["public モジュールに置き換え", "org.jboss.ws.cxf.jbossws-cxf-client (services=\"import\")。CXF の公開 API の範囲で使う", "○"],
              ["CXF を WAR に同梱し webservices を除外", "アプリが CXF の版を自分で管理する", "△ 更新・脆弱性対応を自分で負う"],
              ["そのまま使い続ける", "private と承知でテストを厚くする", "△ 警告は残る"],
              ["org.jboss.vfs (Spring 由来)", "logging で WFLYSRV0018 のうち org.jboss.vfs の行だけをフィルタ (20-logging.cli)", "○ Spring の jar を改変するよりよい"],
          ], widths=[2, 5, 2])),
        S("実装",
          C("""// implementation/app/.../ws/SoapClientTimeouts.java (標準 API だけでタイムアウトを設定)
Map<String, Object> ctx = ((BindingProvider) port).getRequestContext();
ctx.put("jakarta.xml.ws.client.connectionTimeout", 5000);   // ms
ctx.put("jakarta.xml.ws.client.receiveTimeout", 30000);     // ms""", "java", "アプリ側 (org.apache.cxf.impl 不要)"),
          C("""<!-- jboss-deployment-structure.xml: <module name="org.apache.cxf.impl"/> を削除。
     CXF の公開 API が本当に必要なときだけ: -->
<dependencies>
    <module name="org.jboss.ws.cxf.jbossws-cxf-client" services="import"/>
</dependencies>""", "xml"),
          C("""# 20-logging.cli (抜粋): spring-core 由来の org.jboss.vfs の 1 行だけを抑止
/subsystem=logging/logger=org.jboss.as.dependency.private:add(filter-spec="not(match(\\"WFLYSRV0018: .*org.jboss.vfs\\"))")""",
            "text", "サーバ側 (jboss-cli)")),
        S("確認方法",
          C("""grep WFLYSRV0018 server.log    # → org.apache.cxf.impl の行が無いこと
# SOAP のタイムアウトが効くこと (検証: 応答 3 秒のサービスに receiveTimeout=1000ms → 約 1.2 秒で SocketTimeoutException)""", "bash")),
    ],
    "refs": ["eap-rn", "eap-mods", "src-serverlogger", "src-moduleload", "src-cxf-msg", "src-cxf-ssl"],
}

# =====================================================================
# ④ WFLYEE0007
# =====================================================================
W04 = {
    "key": "W04", "no": "④", "sheet": "④WFLYEE0007", "id": "WFLYEE0007", "severity": "C",
    "title": "④ WFLYEE0007: 例外のためオプションのコンポーネント ...ServletServerHttpResponse$ResponseAsyncListener をインストールしていない",
    "user_log": "WFLY0007: 例外が原因でオプションのコンポーネント org.springframework.http.server.reactive.ServletServerHttpResponse$ResponseAsyncListenerをインストールしていません（DEBUGレベルを有効にして、原因を確認してください）",
    "verify_labels": ["WFLYEE0007 optional component not installed", "  of which org.springframework.*",
                      "  of which javax.servlet.jsp.jstl.* (=⑦)"],
    "sections": [
        S("ひとことで (小学生向け)",
          KID("ビルには「お店に入ってきた道具に、必要な物を配ってあげる親切な係 (EE サブシステム)」がいます。\n"
              "Spring の道具箱の中に「非同期の見張り番 (AsyncListener)」という道具が 6 つ入っていたので、係は配る準備をしようとしました。\n"
              "でもその道具は「親 (外側のクラス) と一緒でないと作れない」作りだったので、係は作れませんでした。"
              "これは「やってもやらなくてもよい仕事 (オプション)」だったので、係は「飛ばしました。理由は DEBUG で」とメモしました。\n"
              "Spring は見張り番を自分でちゃんと作って使うので、お店は何も困りません。"),
          T(["たとえ", "本当の仕組み"], [
              ["親切な係", "EE サブシステム (EEModuleConfigurationProcessor)"],
              ["配る準備をする道具", "Undertow が「注入対象の Web コンポーネント」として登録したクラス (AsyncListener 実装など)"],
              ["親と一緒でないと作れない", "引数なしコンストラクタが無い (非 static の内部クラス等) → WFLYEE0048"],
              ["やってもやらなくてもよい仕事", "オプションのコンポーネント (失敗しても WARN を出して続行)"],
              ["Spring が自分で作る", "Spring は new ResponseAsyncListener() を自分で生成し、AsyncContext#addListener(インスタンス) で登録する"],
          ], widths=[1, 3])),
        S("メッセージの正体",
          T(["項目", "内容"], [
              ["英語原文", "WFLYEE0007: Not installing optional component %s due to an exception (enable DEBUG log level to see the cause)"],
              ["ID / レベル", "WFLYEE0007 / WARN  (ユーザーのログの「WFLY0007」は EE サブシステムの WFLYEE0007)"],
              ["ロガー", "org.jboss.as.ee"],
              ["出す場所", "EEModuleConfigurationProcessor (WFLY-924 で「WARN 1 行 + 原因は DEBUG」に要約)"],
              ["DEBUG で出る原因 (実測)", "WFLYEE0048: Could not find default constructor for class org.springframework...ResponseAsyncListener"],
              ["同じ理由で出る Spring のクラス (実測 6 件)", "ServletServerHttpResponse$ResponseAsyncListener / ServletServerHttpRequest$RequestAsyncListener / "
                                            "ServletHttpHandlerAdapter$HttpHandlerAsyncListener / ServletServerHttpAsyncRequestControl / "
                                            "StandardServletAsyncWebRequest / ServerHttpObservationFilter$ObservationAsyncListener"],
          ], widths=[1, 4])),
        S("動作原理",
          B("Servlet 仕様では、AsyncContext#createListener(Class) で作られる AsyncListener もリソース注入の対象になる。"
            "そのため WildFly の Undertow 連携 (WebComponentProcessor) は、デプロイのアノテーション索引から jakarta.servlet.AsyncListener を実装する"
            "具象クラスを全部探し、サーブレット・フィルタ・リスナ・TLD のタグ/バリデータと同じく「Web コンポーネント (オプション)」として登録する。",
            "EE サブシステムはコンポーネントごとにインスタンスの作り方を決める。Weld (CDI) が有効なデプロイなら Weld に作らせる "
            "(WeldComponentIntegrationProcessor が WeldManagedReferenceFactory を設定)。Weld が無効なら引数なしコンストラクタで作る "
            "(DefaultInterceptorConfigurator)。",
            "Spring の 6 クラスは非 static の内部クラスなど、引数なしコンストラクタを持たないため WFLYEE0048 になり、オプション扱いなので "
            "WFLYEE0007 を出して登録をやめる (デプロイは成功)。",
            "④ と ⑤ の関係: 既定では spring-web に含まれる DelegatingPhaseListenerMulticaster (jakarta.faces.event.PhaseListener の実装) を見て "
            "JSF サブシステムが有効になり、Faces 4 は CDI 必須なのでデプロイが Weld デプロイになる → ④ は出ない。"
            "jboss-deployment-structure.xml で jsf を除外していると Weld デプロイにならず、④ (と ⑤) が出る。検証で両方を確認した。",
            "⑦ の javax 版 JSTL の TLD バリデータ (PermittedTaglibsTLV / ScriptFreeTLV) も同じ仕組みでコンポーネント登録され、"
            "クラスが読めずに WFLYEE0007 になる (こちらは ⑦ で対処)。")),
        S("動作イメージ",
          DIA("""[デプロイ: INSTALL フェーズ]
 Undertow: 索引から AsyncListener の実装クラスを列挙 → 6 クラスを「オプションの Web コンポーネント」として登録
 EE: 各コンポーネントの作り方を決める
   ├ Weld デプロイ (JSF 有効 / beans.xml あり 等) → Weld が作る → 問題なし
   └ Weld デプロイでない (jsf・weld を除外 等)    → 引数なしコンストラクタで作る
         └ コンストラクタが無い → WFLYEE0048 → オプションなので WFLYEE0007 (WARN) ★今回 → 登録だけやめる
[実行時]
 Spring: new ResponseAsyncListener() を自分で作り、asyncContext.addListener(インスタンス) → コンテナの注入は不要
         → 非同期処理は正常 (検証: /api/async が "async-ok on MvcAsync1")""")),
        S("歴史・背景・必要になった経緯",
          B("2009 Servlet 3.0 (Java EE 6): 非同期処理と AsyncListener、createListener による注入対象のリスナが導入された。",
            "JBoss AS 7 / WildFly: 注入をサポートするため、AsyncListener 実装をすべてコンポーネント化する実装になった。",
            "2013 WFLY-924: オプションのコンポーネントの失敗は大量の例外を出さず、WARN 1 行 + DEBUG に要約する形 (現在の WFLYEE0007) に。",
            "2017 Spring 5.0: リアクティブ対応 (spring-web にサーブレット上でリアクティブを動かすアダプタ類) が入り、"
            "Spring MVC だけを使うアプリの jar にも AsyncListener 実装クラスが含まれるようになった。")),
        S("この環境での原因と切り分け",
          P("原因は「Weld 無効の WAR で、Spring の AsyncListener 実装に引数なしコンストラクタが無い」こと。"
            "推測でなく DEBUG で確かめてから対処します (下の手順。検証では 6 クラスとも WFLYEE0048 を確認)。"),
          C("""# 起動中のコンテナで一時的に DEBUG にして再デプロイ
/opt/jboss-eap/bin/jboss-cli.sh -c --commands='/subsystem=logging/logger=org.jboss.as.ee:add(level=DEBUG),/subsystem=logging/console-handler=CONSOLE:write-attribute(name=level,value=DEBUG),/deployment=iwinmichl.war:redeploy'
# → DEBUG [org.jboss.as.ee] Not installing optional component ...ResponseAsyncListener due to an exception:
#      ... WFLYEE0048: Could not find default constructor for class ...ResponseAsyncListener
# 確認後に戻す
/opt/jboss-eap/bin/jboss-cli.sh -c --commands='/subsystem=logging/console-handler=CONSOLE:write-attribute(name=level,value=INFO),/subsystem=logging/logger=org.jboss.as.ee:remove'""",
            "bash", "原因の確認 (ECS Exec などで)"),
          C("python scan-war.py iwinmichl.war   # ## ④ に「引数なしコンストラクタ無し」のクラスが一覧される", "bash")),
        S("影響度と放置した場合のリスク",
          P("危険度 C (無害)。Spring の非同期処理 (DeferredResult / Callable / SSE) は影響を受けません (検証で確認)。"
            "ただしデプロイのたびに 6 行の WARN が出て、本当に見るべき WFLYEE0007 (自分のクラスの注入失敗など) が埋もれます。")),
        S("対処方針の比較",
          T(["方式", "内容", "評価"], [
              ["原因確認のうえ Spring の分だけ抑止 ★推奨", "org.jboss.as.ee ロガーに filter-spec を付け、\"WFLYEE0007: Not installing optional component org.springframework.\" で始まる行だけ捨てる", "◎ 他の WFLYEE0007 は出る"],
              ["Weld を有効にする", "WEB-INF/beans.xml (bean-discovery-mode=\"annotated\") で Weld デプロイにする", "△ 警告は消えるが、使わない CDI を動かすことになる"],
              ["jsf の除外をやめる", "spring-web の PhaseListener で JSF + Weld が有効になる", "× JSF を使わないのに有効化される"],
              ["ロガーのレベルを ERROR にする", "org.jboss.as.ee 全体を黙らせる", "× 範囲が広すぎる"],
          ], widths=[2, 5, 2])),
        S("実装 (jboss-cli)",
          C("""# 20-logging.cli (抜粋)
if (outcome != success) of /subsystem=logging/logger=org.jboss.as.ee:read-resource
    /subsystem=logging/logger=org.jboss.as.ee:add(filter-spec="not(match(\\"WFLYEE0007: Not installing optional component org.springframework.\\"))")
end-if""", "text"),
          NOTE("jboss-logmanager の match() は「整形後のメッセージ」に対する部分一致 (RegexFilter#isLoggable が getFormattedMessage を使う)。"
               "メッセージ ID を含む文頭で絞ることで、Spring 以外のクラスの WFLYEE0007 は残ります。")),
        S("確認方法",
          C("""grep -c 'WFLYEE0007.*org.springframework' server.log   # → 0
curl http://localhost:8080/iwinmichl/api/async                 # Spring の非同期処理が動くこと""", "bash")),
    ],
    "refs": ["src-webcomp", "src-eemodcfg", "src-defintercept", "src-cdi", "src-jsf", "src-regex", "src-spring-sshr"],
}
