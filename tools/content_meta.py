# -*- coding: utf-8 -*-
"""表紙・一覧・基礎知識・年表・用語集・前提と版・出典"""
from doclib import B, C, DIA, KID, NOTE, P, S, T

TITLE = "JBoss EAP 8.1 警告 13 件 徹底解説と jboss-cli による対処実装"
SUBTITLE = ("ECS タスク上の UBI 9.8 + Red Hat build of OpenJDK 21 + JBoss EAP 8.1 コンテナ / "
            "サブシステム設定はすべて jboss-cli で実施 / 作成日 2026-10-11")

ENV_ROWS = [
    ["実行基盤", "Amazon ECS (Fargate を主対象)。ALB で TLS を終端し、コンテナは 8080 (HTTP) で受ける"],
    ["コンテナ", "UBI 9.8 + Red Hat build of OpenJDK 21 + JBoss EAP 8.1 (standalone, JBOSS_HOME=/opt/jboss-eap)"],
    ["設定方式", "各サブシステムは jboss-cli (.cli) で設定し、イメージのビルド時に embed-server で standalone.xml へ焼き込む。"
                "環境ごとの値は ${env.変数名:既定値} 式で ECS タスク定義から渡す"],
    ["DB", "Aurora MySQL 8.4 互換 (ログの productVersion=8.4.7)。XA データソース MIF02JA_JDS (java:/jdbc/MIF02JA_JDS)"],
    ["アプリ", "iwinmichl.war (Spring MVC / JSP・JSTL / Apache CXF クライアント / jboss-deployment-structure.xml あり)"],
    ["関連プロジェクト", "Container_ExtraSLB_JVM_https_outbounds (自己署名ルート CA を信頼するアウトバウンド HTTPS 実装)"],
]

LEGEND_ROWS = [
    ["A", "障害 (要求の失敗・処理の中断) に直結しうる。早急に対処する"],
    ["B", "今は動くが、設定やコードの誤りを示している / 将来の更新で壊れうる。計画的に対処する"],
    ["C", "それ自体は無害。ただしログを汚し、本当に見るべき警告を埋もれさせる。原因を理解したうえで整理する"],
]

HOW_TO_READ = [
    "各警告のシートは「ひとことで (小学生向け)」→「メッセージの正体」→「動作原理」→「動作イメージ」→"
    "「歴史・背景」→「この環境での原因と切り分け」→「影響度」→「対処方針の比較」→「実装」→「確認方法」→"
    "「検証結果」→「出典」の順に並んでいます。",
    "小学生向けの説明は、たとえ話と「たとえ ⇔ 本当の仕組み」の対応表のセットです。技術者向けの説明は、"
    "WildFly / IronJacamar / Spring などのソースコード (EAP 8.1 の上流版) で確認した事実に基づいています。",
    "実装はすべて implementation/ フォルダに実ファイルとして置いてあり、「実装コード」シートと md に全文を載せています。",
    "「検証結果」は、UBI 9.8 + OpenJDK 21 + WildFly 35.0.1 (EAP 8.1 の上流) + MySQL 8.4 のコンテナで、"
    "修正前に 13 件すべてを再現し、修正後に消えることを実際に動かして確かめた記録です。",
]

# ---------------------------------------------------------------------
# 一覧 (検証件数は build_docs.py が results から埋める)
# ---------------------------------------------------------------------
SUMMARY_HEADER = ["No", "警告", "出す場所 (ロガー)", "いつ出る", "ひとことで", "この環境での本当の原因",
                  "危険度", "主な対処", "対処の場所", "検証 (修正前→修正後)"]
SUMMARY_WIDTHS = [5, 16, 24, 12, 30, 40, 6, 42, 14, 14]
SUMMARY = [
    ["①", "WFLYELY00023", "org.wildfly.extension.elytron", "ブート時",
     "使っていない HTTPS 受付用の鍵の金庫 (application.keystore) が無いので空で代用した",
     "EAP 標準のインバウンド HTTPS (8443) 用 applicationKS。自前の p12 の置き場所や -D 引数とは無関係",
     "C", "未使用の 8443 一式 (https-listener→SSC→KM→KS) を jboss-cli で削除。自前トラストストアは required=true",
     "jboss-cli", "W01"],
    ["②", "WFLYSRV0058", "org.jboss.as.server.deployment", "デプロイ時",
     "荷物リストに書いた段ボール (testClasses) が荷物に入っていなかった",
     "jboss-deployment-structure.xml に WAR に無い resource-root (WEB-INF/classes/testClasses) が残っている",
     "C", "記述を削除。ビルド時に scan-war.py で検査", "WAR", "W02"],
    ["③", "WFLYSRV0018", "org.jboss.as.dependency.private", "デプロイ時",
     "図書館の職員専用の棚 (private モジュール) の本を借りた",
     "jboss-deployment-structure.xml の org.apache.cxf.impl 依存 (+ spring-core の MANIFEST が宣言する org.jboss.vfs)",
     "B", "依存を削除し、SOAP のタイムアウトは標準プロパティ jakarta.xml.ws.client.*Timeout で設定。org.jboss.vfs は 1 行だけ絞って抑止",
     "WAR / jboss-cli", "W03"],
    ["④", "WFLYEE0007", "org.jboss.as.ee", "デプロイ時",
     "Spring の見張り番 (AsyncListener) に道具を配ろうとしたが、作り方が特殊で作れなかった",
     "Weld 無効の WAR で、Spring の AsyncListener 実装 6 クラスに引数なしコンストラクタが無い (WFLYEE0048)",
     "C", "DEBUG で WFLYEE0048 を確認したうえで、Spring のクラス分だけをログフィルタで抑止 (動作影響なし)",
     "jboss-cli", "W04"],
    ["⑤", "WFLYWELD0013", "org.jboss.weld.deployer", "デプロイ時",
     "CDI のシールは見つかったが、名簿 (Bean アーカイブ) を作るきっかけが無い",
     "WAR に同梱された jakarta.transaction-api の TransactionScoped に @NormalScope が付いている (+ jsf 除外で Weld 無効)",
     "B", "EE API jar を provided にして同梱をやめる。CDI 不使用なので weld も jsf と一緒に除外", "WAR", "W05"],
    ["⑥", "WFLYSRV0274", "org.jboss.as.server.deployment", "デプロイ時 (最後)",
     "受け取り拒否リストに書いた相手から、そもそも荷物が来る予定がなかった (空振り)",
     "org.jboss.logmanager.log4j2 はデプロイの依存に直接入らないモジュール。除外しても何も起きていない",
     "B", "除外を削除して EAP のログに乗せる (推奨)。自前 Log4j 2 を使うなら除外すべきは org.apache.logging.log4j.api",
     "WAR / jboss-cli", "W06"],
    ["⑦", "Failed to define class javax.*", "org.jboss.modules.define", "デプロイ時",
     "昔の教科書 (javax) の付録が、新しい教科書 (jakarta) しかない学校で読めなかった",
     "WAR に Java EE 時代の jstl-1.2.jar が残り、その TLD の validator クラスを読み込もうとして失敗",
     "B", "javax 版 JSTL を削除し、EAP 提供の Jakarta JSTL 3.0 を使う。enforcer で javax.* の混入を止める", "WAR", "W07"],
    ["⑧", "IJ030040", "org.jboss.jca.adapters.jdbc.WrappedConnection", "リクエスト処理中",
     "借りた本の中のメモ用紙 (Statement) を片付けずに本を返した",
     "アプリが Statement を閉じずに Connection だけ閉じている (track-statements=true で検出)",
     "B", "try-with-resources / JdbcTemplate で必ず閉じる。本番は修正後に NOWARN", "WAR", "W08"],
    ["⑨", "Resolved [HttpRequestMethodNotSupportedException]", "org.springframework.web.servlet.mvc.support.DefaultHandlerExceptionResolver",
     "リクエスト処理中", "「見るだけ」の窓口に「置かせて」と来た人を断った",
     "GET 専用 URL に POST が届いた (送信元・URL はログに出ない)",
     "B", "4xx/5xx の JSON アクセスログ (jboss-cli) と 405 詳細ログ (@ControllerAdvice) で送信元を特定して直す",
     "jboss-cli / WAR", "W09"],
    ["⑩", "IJ030027", "org.jboss.jca.adapters.jdbc.xa.XAManagedConnectionFactory", "リクエスト処理中 (貸出前の検証)",
     "長く止めていたタクシーのエンジンがかからなかったので廃車にした",
     "プールで待機中の接続が DB 側 (wait_timeout) や経路のアイドル切断で既に切られていた",
     "B", "idle-timeout-minutes を切断時間より短く。exception-sorter 追加、TCP keepalive。原因は Caused by で判別",
     "jboss-cli / ECS", "W10"],
    ["⑪", "IJ000621", "org.jboss.jca.core.connectionmanager.pool.strategy.OnePool", "リクエスト処理中 (貸出前の検証)",
     "点検に通らなかった車を配車係が廃車にして、別の車を出した",
     "⑩ と同じ接続のプール側の記録 (validate-on-match=true の貸出時検証で検出)",
     "B", "⑩ と同じ。ログ時刻 - lastReturned で放置時間を測って idle-timeout を決める", "jboss-cli / ECS", "W11"],
    ["⑫", "IJ030042", "org.jboss.jca.adapters.jdbc.WrappedConnection", "リクエスト処理中",
     "メモ用紙に書いた答えのプリント (ResultSet) も出しっぱなしだった",
     "アプリが ResultSet を閉じていない (⑧ と同じ箇所のことが多い)",
     "B", "⑧ と同じ。analyze-ij-log.py で作った場所を特定", "WAR", "W12"],
    ["⑬", "IJ000615", "org.jboss.jca.core.connectionmanager.pool.strategy.OnePool", "停止時 (SIGTERM 等)",
     "閉店のとき、お客さんがレジを使っている途中なのにレジを片付けた",
     "SIGTERM 時のサスペンド待ち時間が既定の 0 秒。処理中の要求ごと DB 接続が破棄された",
     "A", "org.wildfly.sigterm.suspend.timeout (jboss-cli) + LAUNCH_JBOSS_IN_BACKGROUND + ECS stopTimeout を一貫させる",
     "jboss-cli / ECS", "W13"],
]

# ---------------------------------------------------------------------
# 基礎知識
# ---------------------------------------------------------------------
BASICS = [
    S("1. JBoss EAP ってなに？",
      KID("JBoss EAP は「Java で作ったお店 (Web アプリ) を入居させる大きなビル」です。ビルには、受付係・警備室・"
          "図書館・タクシー会社・日記係など、たくさんの係 (サブシステム) がいて、入居したお店のために働きます。"
          "係たちは毎日「日記 (ログ)」を書いていて、気になることがあると「WARN (注意)」として書きます。"
          "今回の 13 件は、この日記に書かれた「注意」です。"),
      T(["たとえ", "本当の仕組み"], [
          ["ビル", "JBoss EAP 8.1 (Jakarta EE 10 準拠のアプリケーションサーバ。上流は WildFly / WildFly Core)"],
          ["入居するお店", "WAR ファイル (iwinmichl.war)"],
          ["係 (部署)", "サブシステム: elytron (セキュリティ)、undertow (Web)、datasources/jca (DB 接続)、logging、weld (CDI)、ee、webservices、transactions など"],
          ["ビルの設計図", "standalone.xml (各サブシステムの設定。jboss-cli で書き換える)"],
          ["日記", "サーバログ (コンソール = CloudWatch Logs、server.log)"],
      ], widths=[1, 3]),
      P("JBoss EAP 8.1 は 2025-09-02 に一般提供 (GA) となった Jakarta EE 10 のアプリケーションサーバです。"
        "上流のオープンソース版は WildFly で、EAP 8.1 は WildFly Core 27.1 系をベースにしています "
        "(Red Hat のセキュリティアドバイザリで WildFly Core 27.1.x の更新が確認できる)。2026-10 時点の最新は 8.1.8 (Update 8, 2026-09-22) です。"
        "OpenJDK 21 / RHEL 9 の組み合わせがサポートされ、OpenJDK 17 の OpenShift 用イメージは 8.1 で非推奨 (8.2 で削除予定) になっています。")),
    S("2. JBoss Modules (図書館と貸出カード)",
      KID("ビルの中には大きな図書館 (JBoss Modules) があり、本 (ライブラリ) は棚 (モジュール) ごとに分けて置かれています。"
          "お店は「貸出カード」に書いた棚の本しか読めません。図書館は気をきかせて、よく使う本の棚を最初からカードに"
          "書いてくれます (暗黙の依存)。お店が自分で棚を書き足すこともできます (明示の依存)。"
          "棚には「どなたでもどうぞ (public)」と「職員専用 (private)」の札が付いています。"),
      T(["用語", "意味"], [
          ["モジュール", "$JBOSS_HOME/modules/... の module.xml で定義された部品 (例: org.apache.cxf, org.apache.cxf.impl)"],
          ["デプロイのモジュール", "WAR ごとに deployment.iwinmichl.war という名前のモジュールが作られる。WEB-INF/classes と WEB-INF/lib/*.jar がその中身 (リソースルート)"],
          ["暗黙の依存", "サブシステムが自動で付ける依存 (logging は org.apache.logging.log4j.api 等、webservices は JAX-WS 一式 等)"],
          ["明示の依存", "jboss-deployment-structure.xml の <dependencies>、MANIFEST.MF の Dependencies: ヘッダ (WEB-INF/lib の jar の MANIFEST も対象)"],
          ["除外", "jboss-deployment-structure.xml の <exclusions> / <exclude-subsystems>"],
          ["jboss.api", "module.xml の <property name=\"jboss.api\" value=\"private\"/> 等。public / private / unsupported / deprecated"],
          ["読み込みの優先順位", "暗黙の依存 → 明示の依存 → WAR 自身 (WEB-INF/classes, lib) → 他デプロイ。同じクラスがあればサーバ側が先に見つかる"],
      ], widths=[1, 3]),
      NOTE("JBoss Modules は JBoss AS 7 (2011) で導入された「モジュール単位で見える範囲を区切る」クラスローダです。"
           "それ以前 (AS 5/6) は階層型のクラスローダで、アプリとサーバのライブラリが混ざって衝突しやすかったため、"
           "見える範囲を明示的に宣言する方式に変わりました。②③⑥⑦ はこの仕組みに関係する警告です。")),
    S("3. デプロイの流れ (引っ越しの手順)",
      KID("お店がビルに入居するときは、決まった順番で作業が進みます。荷物を開ける → 中身を調べる → 必要な本の貸出カードを作る → "
          "部屋を整える → 道具を配置する → 最後に片付け。それぞれの作業の途中で、係が気づいたことを日記に書きます。"),
      DIA("""デプロイのフェーズ (Phase) と、そこで出る警告
 STRUCTURE ─ jboss-deployment-structure.xml を読む ............ ② WFLYSRV0058 (リソースルートが無い)
 PARSE     ─ web.xml / TLD / アノテーション索引 (Jandex) を作る
 DEPENDENCIES ─ 暗黙・明示の依存を組み立てる (logging, webservices, weld ...)
 CONFIGURE_MODULE ─ モジュールを作る .............................. ③ WFLYSRV0018 (private モジュール)
 POST_MODULE ─ CDI / JSF の判定 ................................... ⑤ WFLYWELD0013
 INSTALL   ─ EE コンポーネント (サーブレット・リスナ等) を構成 ...... ④ WFLYEE0007 / ⑦ Failed to define class
 CLEANUP   ─ 後片付け・設定の検算 .................................. ⑥ WFLYSRV0274 (除外の空振り)""",
          "図: デプロイのフェーズと警告"),
      P("① はデプロイではなく「サーバのブート時 (サブシステムの起動)」、⑧〜⑫ は「リクエスト処理中」、⑬ は「停止時」に出ます。")),
    S("4. Elytron (警備室: 身分証と信頼リスト)",
      KID("警備室 (Elytron) は 2 種類の大事なものを管理しています。ひとつは「自分の身分証と、それを証明する秘密のハンコ」"
          "(キーストア)。お客さんに「本物のビルです」と見せるのに使います。もうひとつは「信頼できる発行所の名簿」"
          "(トラストストア)。よそのビルを訪ねたとき、相手の身分証が本物かを確かめるのに使います。"
          "① の警告は前者 (自分の身分証の金庫) の話で、ルート CA を入れた p12 は後者 (名簿) の話です。"),
      T(["Elytron のリソース", "役割", "今回の例"], [
          ["key-store", "鍵・証明書の入れ物 (ファイル)", "applicationKS (application.keystore) / extraslb-trust-store (p12)"],
          ["key-manager", "「自分の証明書」を出す係 (サーバ側 TLS)", "applicationKM (自己署名の自動生成機能付き)"],
          ["trust-manager", "「相手の証明書」を検証する係 (クライアント側 TLS)", "extraslb-trust-manager"],
          ["server-ssl-context", "受け付ける側の TLS 設定", "applicationSSC (https-listener 8443 が使う)"],
          ["client-ssl-context", "接続しに行く側の TLS 設定", "extraslb-client-ssl-context"],
          ["default-ssl-context", "JVM 既定の SSLContext を差し替える", "SSLContext.getDefault() が Elytron の DelegatingSSLContext になる"],
      ], widths=[1, 2, 2]),
      NOTE("-Djavax.net.ssl.trustStore / keyStore は JDK (JSSE) の設定で、Elytron の key-store リソースはこれを読みません。"
           "2 つは別の仕組みです (① で実測)。")),
    S("5. IronJacamar (タクシー会社: DB 接続のプール)",
      KID("DB と話すための回線 (接続) を毎回つなぐのは時間がかかるので、タクシー会社 (接続プール) が車 (接続) を何台か"
          "待機させておき、お客さん (リクエスト) に貸し出します。返してもらった車は駐車場で待機します。"
          "長く駐車した車はバッテリーが上がっていることがあるので、貸す前に点検 (検証) します。"),
      T(["用語", "意味", "関係する警告"], [
          ["プール", "接続を使い回す仕組み (IronJacamar)。データソース MIF02JA_JDS ごとに 1 つ", "⑩⑪⑬"],
          ["validate-on-match", "貸し出す直前に接続を検証する (ping)。失敗した接続は捨てる", "⑩⑪"],
          ["background-validation", "別スレッドで定期的に検証する (validate-on-match と併用しない)", "⑩"],
          ["valid-connection-checker", "検証方法 (MySQL なら MySQLValidConnectionChecker = ping)", "⑩"],
          ["exception-sorter", "使用中に起きた例外が「接続が壊れた」ものか判定し、壊れた接続をプールに戻さない", "⑩"],
          ["idle-timeout-minutes", "待機がこの時間を超えた接続を捨てる (既定 30 分。半分の間隔で点検)", "⑩⑪"],
          ["track-statements", "Statement / ResultSet の閉じ忘れを追跡 (FALSE / TRUE / NOWARN。既定 NOWARN)", "⑧⑫"],
          ["CCM (cached-connection-manager)", "要求の終わりに閉じ忘れた接続を見つける", "⑬ (補助)"],
      ], widths=[2, 4, 1])),
    S("6. ECS タスクの起動と停止 (お店の開店と閉店)",
      KID("新しいお店 (タスク) が開店して準備ができると、案内係 (ALB) がお客さんを案内し始めます。"
          "閉店するときは、まず案内係が新しいお客さんを案内しなくなり (登録解除)、少し待ってから"
          "「閉店してください」の合図 (SIGTERM) が届きます。決められた時間 (stopTimeout) が過ぎても閉まらないと、"
          "強制的に電気を落とされます (SIGKILL)。"),
      DIA("""ECS のタスク停止 (ローリングデプロイ・スケールイン)
  ALB: ターゲットの登録解除 → 新規リクエストを送らない (deregistration delay の間は既存接続を待つ。既定 300 秒)
    ↓
  ECS: コンテナの PID 1 に SIGTERM
    ↓  standalone.sh が LAUNCH_JBOSS_IN_BACKGROUND=true なら JVM へ中継 (未設定なら JVM に届かない)
  JVM: シャットダウンフック → サスペンド (新規要求を 503 で断り、処理中の要求を待つ)
         待ち時間 = org.wildfly.sigterm.suspend.timeout 秒 (既定 0 = 待たない)  ← ⑬
       → サービス停止 (データソースのプールを閉じる。使用中の接続があれば IJ000615)
    ↓
  ECS: stopTimeout (既定 30 秒 / Fargate 最大 120 秒) を過ぎたら SIGKILL""",
          "図: ECS の停止シーケンスと EAP")),
    S("7. ログ 1 行の読み方",
      C("05:33:57,567 WARN  [org.jboss.jca.core.connectionmanager.pool.strategy.OnePool] (ServerService Thread Pool -- 119) IJ000615: Destroying active connection in pool: MIF02JA_JDS (...)",
        "text", "例"),
      T(["部分", "意味"], [
          ["05:33:57,567", "時刻 (コンテナの TZ。既定は UTC)"],
          ["WARN", "レベル (ERROR > WARN > INFO > DEBUG > TRACE)"],
          ["[org.jboss.jca...OnePool]", "ロガーカテゴリ (だれが書いたか)。logging サブシステムで、このカテゴリごとにレベルやフィルタを設定できる"],
          ["(ServerService Thread Pool -- 119)", "スレッド名。default task-N = HTTP 要求の処理、MSC service thread = サービスの起動・停止"],
          ["IJ000615", "メッセージ ID。接頭辞で出どころが分かる: WFLYELY=Elytron、WFLYSRV=サーバ本体、WFLYEE=EE、WFLYWELD=Weld、"
                       "IJ=IronJacamar。ID が無いものは JBoss Modules (⑦) や Spring (⑨) など"],
      ], widths=[1, 3]),
      NOTE("メッセージ ID の接頭辞 (WFLY...) は WildFly 9 (2015) で JBAS から変わったものです。"
           "日本語ロケールでは本文が翻訳されますが ID は同じなので、検索や集計は ID で行います (check-warnings.sh)。")),
    S("8. jboss-cli で設定する理由とやり方",
      KID("ビルの設計図 (standalone.xml) を手で書き換えると、書き間違いに気づきにくく、何をどう変えたかも残りません。"
          "jboss-cli は「設計図を正しい手順で書き換える専用の道具」で、書き換えの手順書 (.cli ファイル) がそのまま記録になります。"),
      B("イメージのビルド時に embed-server (サーバを外部公開せずに管理用だけで起動するモード) で .cli を適用し、standalone.xml に焼き込む",
        "環境ごとに変わる値は ${env.DB_HOST} のような式で書き、起動時に ECS タスク定義の environment / secrets から解決させる",
        "if (outcome != success) of ...:read-resource で「無ければ追加」にして、何度流しても同じ結果になるようにする (冪等)",
        "最後に read-resource で結果を表示して確認する (90-verify.cli)。属性名は EAP 8.1 / WildFly 35 のモデルで実在を確認したものだけを使う",
        "起動時に embed-server を動かさない (動かすと設定ブートが 2 回になり、standalone_xml_history の扱いで ECS だけ失敗する事例がある)")),
]

# ---------------------------------------------------------------------
# 年表
# ---------------------------------------------------------------------
TIMELINE_HEADER = ["年月", "出来事", "関係する警告"]
TIMELINE = [
    ["1999", "HTTP/1.1 (RFC 2616) に 405 Method Not Allowed と Allow ヘッダ", "⑨"],
    ["2006", "JSTL 1.2 (Java EE 5)。javax.servlet.jsp.jstl パッケージ、検証用 TagLibraryValidator (PermittedTaglibsTLV 等)", "⑦"],
    ["2007", "Spring 2.5: アノテーションによる @RequestMapping", "⑨"],
    ["2009-12", "Java EE 6: Servlet 3.0 (非同期処理と AsyncListener)、CDI 1.0", "④⑤"],
    ["2009-12", "Spring 3.0: DefaultHandlerExceptionResolver", "⑨"],
    ["2011-07", "JBoss AS 7.0: JBoss Modules、jboss-deployment-structure.xml、IronJacamar", "②③⑥⑦⑧⑩⑪⑫⑬"],
    ["2013", "Java EE 7: CDI 1.1 で暗黙的 Bean アーカイブ (bean-discovery-mode) を導入", "⑤"],
    ["2013-07", "WFLY-924: オプションコンポーネントの失敗を WARN 1 行 + DEBUG に要約 (WFLYEE0007 の形)", "④"],
    ["2015-07", "WildFly 9: メッセージ ID が JBAS → WFLY 系に。サスペンド / グレースフルシャットダウン導入", "全般 / ⑬"],
    ["2015-10", "WFCORE-1090: module.xml に jboss.api=private を付与 (private モジュールの明示)", "③"],
    ["2016-06", "WFCORE-1576: 初回利用時に自己署名証明書を自動生成 (レガシーセキュリティ)。「SSL out of the box」", "①"],
    ["2017", "WildFly 11 / EAP 7.1: Elytron 導入。Spring 5.0: リアクティブ対応 (spring-web にサーブレット用アダプタ)", "① / ④"],
    ["2018-09", "Spring 5.1: 例外解決ログが \"Resolved [...]\" 形式に", "⑨"],
    ["2018-12", "WFCORE-4233 / 4234: 存在しないサブシステム・依存の除外を WARN (WFLYSRV0273 / 0274)", "⑥"],
    ["2020-11", "WFCORE-5095: Elytron でも自己署名証明書の自動生成。既定構成に applicationKS/KM/SSC", "①"],
    ["2020-12", "Jakarta EE 9: javax.* → jakarta.* の名前空間変更", "⑦"],
    ["2021", "MySQL 8.0.24: wait_timeout 切断時にエラー 4031 を通知。WildFly 25: レガシーセキュリティ削除", "⑩ / ①"],
    ["2022", "Jakarta EE 10 (CDI 4.0、Jakarta Tags 3.0 で jakarta.tags.* URN)、Spring 6.0、RFC 9110", "⑤⑦⑨"],
    ["2023-08", "ECS on Fargate で systemControls (sysctl。TCP keepalive 等) が利用可能に", "⑩⑪"],
    ["2024-02", "JBoss EAP 8.0 GA (Jakarta EE 10、Elytron に一本化)", "全般"],
    ["2024-04", "MySQL 8.4 LTS", "⑩⑪"],
    ["2024-09", "NLB の TCP アイドルタイムアウトが 60〜6000 秒で変更可能に (既定 350 秒のまま)", "⑩"],
    ["2025-04 / 09", "JBoss EAP 8.1 ベータ (04-28) / GA (09-02)", "全般"],
    ["2026-05", "Aurora MySQL 8.4 GA (最初のマイナー 8.4.7。ログの productVersion=8.4.7 と一致)", "⑩⑪"],
    ["2026-09", "JBoss EAP 8.1.8 (Update 8)", "全般"],
]

# ---------------------------------------------------------------------
# 用語集
# ---------------------------------------------------------------------
GLOSSARY_HEADER = ["用語", "小学生向けのひとこと", "技術的な意味"]
GLOSSARY = [
    ["JBoss EAP", "お店 (アプリ) が入る大きなビル", "Red Hat の Jakarta EE アプリケーションサーバ。上流は WildFly"],
    ["サブシステム", "ビルの中の係 (部署)", "elytron, undertow, datasources 等の機能単位。standalone.xml に設定"],
    ["jboss-cli", "設計図を正しい手順で書き換える道具", "管理 CLI。.cli ファイルで手順を記録・再実行できる"],
    ["embed-server", "お客さんを入れずに設計図だけ直すモード", "jboss-cli 内でサーバを管理専用に起動するモード (ビルド時の設定適用に使う)"],
    ["JBoss Modules", "図書館の棚と貸出カード", "モジュール単位でクラスの見える範囲を区切るクラスローダ"],
    ["private モジュール", "職員専用の棚", "jboss.api=private。アプリが直接使うと将来壊れても保証されない"],
    ["jboss-deployment-structure.xml", "引っ越しの荷物リスト", "WAR の依存・除外・追加リソースルートを宣言する記述子"],
    ["Elytron", "警備室", "WildFly / EAP のセキュリティ基盤 (認証・TLS・鍵管理)"],
    ["キーストア", "自分の身分証とハンコの金庫", "自分の証明書と秘密鍵を入れるファイル (サーバ側 TLS で使う)"],
    ["トラストストア", "信頼できる発行所の名簿", "信頼する CA 証明書の一覧 (相手の証明書の検証に使う)"],
    ["ルート CA (自己署名)", "名簿のいちばん上の発行所", "自分で自分に署名した CA 証明書。名簿に入れないと信頼されない"],
    ["cacerts", "JDK に最初から付いている名簿", "JDK 既定のトラストストア。UBI の RPM 版 OpenJDK ではシステムトラストストアへのリンク"],
    ["update-ca-trust", "名簿を作り直す係", "RHEL / UBI で CA を追加・反映するコマンド (/etc/pki/ca-trust/source/anchors に置いて実行)"],
    ["Undertow", "受付係", "EAP の Web サーバ (HTTP/HTTPS リスナ、サーブレットコンテナ)"],
    ["Weld / CDI", "名簿係", "CDI (Jakarta Contexts and Dependency Injection) の実装。Bean を管理する"],
    ["Bean アーカイブ", "名簿に載る道具箱", "CDI が Bean を探す単位 (beans.xml や Bean 定義アノテーションで決まる)"],
    ["AsyncListener", "非同期の見張り番", "サーブレットの非同期処理の完了・タイムアウト等を受け取るインタフェース"],
    ["Jakarta EE / javax", "新しい教科書 / 昔の教科書", "Jakarta EE 9 で API のパッケージ名が javax.* から jakarta.* に変わった"],
    ["JSTL / TLD", "JSP 用の便利な道具とその説明書", "JSP 標準タグライブラリと、その定義ファイル (タグライブラリ記述子)"],
    ["IronJacamar", "タクシー会社", "EAP の JCA 実装。JDBC データソースの接続プールを提供"],
    ["XA データソース", "2 つ以上の店で同時に会計する仕組みに参加できるレジ", "分散トランザクション (2 相コミット) に参加できるデータソース"],
    ["wait_timeout", "長く黙っているお客さんの電話を切る時間", "MySQL が無操作の接続を切るまでの秒数 (既定 28800)"],
    ["TCP keepalive", "黙っていても時々「もしもし」と言う", "無通信の TCP 接続に定期的に確認パケットを送る仕組み"],
    ["SIGTERM / SIGKILL", "「閉店してください」/ 強制停電", "終了要求シグナル (後片付けできる) / 強制終了 (後片付けできない)"],
    ["サスペンド", "新しいお客さんを断り、今のお客さんを待つ", "EAP のグレースフルシャットダウンの前段 (要求の受付停止と完了待ち)"],
    ["ALB / NLB", "案内係", "AWS のロードバランサ (L7 / L4)"],
    ["Fargate", "お店の建物を AWS が用意してくれる方式", "サーバ管理不要で ECS タスクを動かす実行環境"],
]

# ---------------------------------------------------------------------
# 前提と版
# ---------------------------------------------------------------------
VERSIONS_HEADER = ["項目", "本書の前提 (実環境)", "検証に使った版"]
VERSIONS = [
    ["アプリケーションサーバ", "JBoss EAP 8.1 (最新 8.1.8 / Update 8, 2026-09-22)", "WildFly 35.0.1.Final (EAP 8.1 の上流。WildFly Core 27.0.1。EAP 8.1 は 27.1.x)"],
    ["Elytron", "EAP 8.1 同梱版", "wildfly-elytron 2.6.0.Final"],
    ["Undertow", "EAP 8.1 同梱版", "Undertow 2.3.18.Final"],
    ["IronJacamar", "EAP 8.1 同梱版 (3.0.x 系)", "IronJacamar 3.0.10.Final"],
    ["Weld", "EAP 8.1 同梱版 (5.1.x 系)", "Weld 5.1.4.Final"],
    ["JBossWS-CXF / Apache CXF", "EAP 8.1 同梱版", "JBossWS-CXF 7.3.1.Final / Apache CXF 4.0.6"],
    ["JBoss Modules / jboss-logmanager", "EAP 8.1 同梱版", "JBoss Modules 2.1.6.Final / jboss-logmanager 2.1.19.Final"],
    ["OS / JDK", "UBI 9.8 + Red Hat build of OpenJDK 21", "RHEL 9.8 UBI、java-21-openjdk-headless 21.0.12.1 (2026-08-18)、ubi9/openjdk-21-runtime 1.24"],
    ["DB", "Aurora MySQL 8.4 互換 (8.4.7)", "MySQL 8.4.11 (検証のため wait_timeout=150 秒)"],
    ["JDBC ドライバ", "MySQL Connector/J (com.mysql.cj)", "Connector/J 26.7.0 (2026-07。9.7.0 の次の版)"],
    ["Spring Framework", "6.x (Spring MVC)", "Spring Framework 6.2.19 / Micrometer 1.16.7"],
    ["実行基盤", "Amazon ECS (Fargate)", "Docker Desktop 29.8.1 (Windows 11) 上のコンテナで再現"],
]
ASSUMPTIONS = [
    "jboss-deployment-structure.xml は jsf サブシステムを除外していると推定した (④ と ⑤ が同時に出るのはこの条件。除外しないと spring-web の PhaseListener 実装で JSF が有効化され、Weld デプロイになって ④⑤ が出ない。検証で確認)。",
    "⑤ の「CDI アノテーション」の出どころは jakarta.transaction-api の同梱を想定した。実際の WAR では scan-war.py で特定できる。",
    "データソースは validate-on-match=true + MySQLValidConnectionChecker、track-statements=true と推定した (⑪ がリクエスト処理スレッドで出ている、⑧⑫ が出ている、Ping failed の文言から)。",
    "⑬ はタスク停止時 (SIGTERM) に出たと推定した (スレッド ServerService Thread Pool はサービス停止の実行スレッド)。デプロイ・リロード時でも同じ警告になる。",
]
TO_CONFIRM = [
    "実際の jboss-deployment-structure.xml の全文 (exclude-subsystems の内容)",
    "Spring Framework・Apache CXF の利用箇所 (org.apache.cxf.impl を必要としていた理由)",
    "データソースの現在の設定値 (/subsystem=datasources/xa-data-source=MIF02JA_JDS:read-resource)",
    "Aurora のパラメータグループの wait_timeout / interactive_timeout、DB への経路 (NAT / NLB / Transit Gateway の有無)",
    "⑪ のログ行そのものの時刻 (「ログ時刻 - lastReturned」で放置時間を出すため)",
    "ECS タスク定義の stopTimeout、ALB ターゲットグループの deregistration delay、最長リクエストの処理時間",
    "LAUNCH_JBOSS_IN_BACKGROUND がイメージのどこかで設定されているか (⑬ の IJ000615 が出ている = SIGTERM は JVM に届いている可能性が高い)",
]

# ---------------------------------------------------------------------
# 出典
# ---------------------------------------------------------------------
REFS_HEADER = ["区分", "資料", "URL"]
REFS = [
    ["Red Hat", "JBoss EAP 8.1 Release notes", "https://docs.redhat.com/en/documentation/red_hat_jboss_enterprise_application_platform/8.1/html-single/release_notes_for_red_hat_jboss_enterprise_application_platform_8.1/index"],
    ["Red Hat", "JBoss EAP 8.1 Configuration Guide (サスペンドと OS シグナルによる正常シャットダウン)", "https://docs.redhat.com/en/documentation/red_hat_jboss_enterprise_application_platform/8.1/html-single/configuration_guide/index"],
    ["Red Hat", "Configuring SSL/TLS in JBoss EAP 8.1", "https://docs.redhat.com/en/documentation/red_hat_jboss_enterprise_application_platform/8.1/html-single/configuring_ssltls_in_jboss_eap/index"],
    ["Red Hat", "Updating Red Hat JBoss EAP 8.1", "https://docs.redhat.com/en/documentation/red_hat_jboss_enterprise_application_platform/8.1/html-single/updating_red_hat_jboss_enterprise_application_platform/index"],
    ["Red Hat", "JBoss EAP 8 Included Modules (public / private の分類)", "https://access.redhat.com/node/7142689"],
    ["Red Hat", "EAP 6/7/8 JDBC datasource not fault tolerant ... needs connection validation enabled", "https://access.redhat.com/solutions/156103"],
    ["Red Hat", "JBoss EAP 8.1 GA (Red Hat Developers, 2025-09-02)", "https://developers.redhat.com/blog/2025/09/02/jboss-eap-81-modernizing-enterprise-java-applications"],
    ["Red Hat", "RHSA-2026:70230 (JBoss EAP 8.1.8)", "https://access.redhat.com/errata/RHSA-2026:70230"],
    ["WildFly", "WFCORE-5095 Elytron の自己署名証明書の自動生成 (設計提案)", "https://docs.wildfly.org/wildfly-proposals/elytron/WFCORE-5095-automatic-self-signed-certificate-generation.html"],
    ["ソース", "KeyStoreService (WFLYELY00022/00023/00024)", "https://github.com/wildfly/wildfly-core/blob/27.0.1.Final/elytron/src/main/java/org/wildfly/extension/elytron/KeyStoreService.java"],
    ["ソース", "elytron-app feature group (applicationKS/KM/SSC の既定構成)", "https://github.com/wildfly/wildfly-core/blob/27.0.1.Final/core-feature-pack/galleon-common/src/main/resources/feature_groups/elytron-app.xml"],
    ["ソース", "ServerLogger (WFLYSRV0018/0058/0211/0220/0272/0273/0274)", "https://github.com/wildfly/wildfly-core/blob/27.0.1.Final/server/src/main/java/org/jboss/as/server/logging/ServerLogger.java"],
    ["ソース", "DeploymentStructureDescriptorParser (②)", "https://github.com/wildfly/wildfly-core/blob/27.0.1.Final/server/src/main/java/org/jboss/as/server/deployment/module/descriptor/DeploymentStructureDescriptorParser.java"],
    ["ソース", "ModuleLoadService (③ の判定: ユーザー指定の依存だけ)", "https://github.com/wildfly/wildfly-core/blob/27.0.1.Final/server/src/main/java/org/jboss/as/server/moduleservice/ModuleLoadService.java"],
    ["ソース", "ModuleSpecification#getFictitiousExcludedDependencies (⑥)", "https://github.com/wildfly/wildfly-core/blob/27.0.1.Final/server/src/main/java/org/jboss/as/server/deployment/module/ModuleSpecification.java"],
    ["ソース", "LoggingModuleDependency (logging の暗黙依存一覧)", "https://github.com/wildfly/wildfly-core/blob/27.0.1.Final/logging/src/main/java/org/jboss/as/logging/LoggingModuleDependency.java"],
    ["ソース", "BootstrapImpl (org.wildfly.sigterm.suspend.timeout)", "https://github.com/wildfly/wildfly-core/blob/27.0.1.Final/server/src/main/java/org/jboss/as/server/BootstrapImpl.java"],
    ["ソース", "standalone.sh (LAUNCH_JBOSS_IN_BACKGROUND とシグナル中継)", "https://github.com/wildfly/wildfly-core/blob/27.0.1.Final/core-feature-pack/common/src/main/resources/content/bin/standalone.sh"],
    ["ソース", "WebComponentProcessor (AsyncListener / TLD validator のコンポーネント化)", "https://github.com/wildfly/wildfly/blob/35.0.1.Final/undertow/src/main/java/org/wildfly/extension/undertow/deployment/WebComponentProcessor.java"],
    ["ソース", "EEModuleConfigurationProcessor (WFLYEE0007)", "https://github.com/wildfly/wildfly/blob/35.0.1.Final/ee/src/main/java/org/jboss/as/ee/component/deployers/EEModuleConfigurationProcessor.java"],
    ["ソース", "DefaultInterceptorConfigurator (WFLYEE0048)", "https://github.com/wildfly/wildfly/blob/35.0.1.Final/ee/src/main/java/org/jboss/as/ee/component/DefaultInterceptorConfigurator.java"],
    ["ソース", "CdiAnnotations / WeldDeploymentProcessor (WFLYWELD0013)", "https://github.com/wildfly/wildfly/blob/35.0.1.Final/weld/subsystem/src/main/java/org/jboss/as/weld/CdiAnnotations.java"],
    ["ソース", "JSFVersionProcessor (JSF 有効化で Weld デプロイにする)", "https://github.com/wildfly/wildfly/blob/35.0.1.Final/jsf/subsystem/src/main/java/org/jboss/as/jsf/deployment/JSFVersionProcessor.java"],
    ["ソース", "EventLoggerHttpHandler (console-access-log の predicate は応答完了後に評価)", "https://github.com/wildfly/wildfly/blob/35.0.1.Final/undertow/src/main/java/org/wildfly/extension/undertow/EventLoggerHttpHandler.java"],
    ["ソース", "JDKModuleLogger (Failed to define class / org.jboss.modules.define)", "https://github.com/jboss-modules/jboss-modules/blob/2.1.6.Final/src/main/java/org/jboss/modules/log/JDKModuleLogger.java"],
    ["ソース", "jboss-logmanager RegexFilter (match は整形後メッセージに部分一致)", "https://github.com/jboss-logging/jboss-logmanager/blob/2.1.19.Final/src/main/java/org/jboss/logmanager/filters/RegexFilter.java"],
    ["ソース", "IronJacamar AdaptersLogger (IJ030027/030040/030042)", "https://github.com/ironjacamar/ironjacamar/blob/3.0.10.Final/adapters/src/main/java/org/jboss/jca/adapters/AdaptersLogger.java"],
    ["ソース", "IronJacamar MySQLValidConnectionChecker", "https://github.com/ironjacamar/ironjacamar/blob/3.0.10.Final/adapters/src/main/java/org/jboss/jca/adapters/jdbc/extensions/mysql/MySQLValidConnectionChecker.java"],
    ["ソース", "IronJacamar SemaphoreConcurrentLinkedDequeManagedConnectionPool (IJ000615/000621)", "https://github.com/ironjacamar/ironjacamar/blob/3.0.10.Final/core/impl/src/main/java/org/jboss/jca/core/connectionmanager/pool/mcp/SemaphoreConcurrentLinkedDequeManagedConnectionPool.java"],
    ["ソース", "IronJacamar Defaults (track-statements=NOWARN 等)", "https://github.com/ironjacamar/ironjacamar/blob/3.0.10.Final/common/api/src/main/java/org/jboss/jca/common/api/metadata/Defaults.java"],
    ["ソース", "Spring DefaultHandlerExceptionResolver (v6.2)", "https://github.com/spring-projects/spring-framework/blob/v6.2.11/spring-webmvc/src/main/java/org/springframework/web/servlet/mvc/support/DefaultHandlerExceptionResolver.java"],
    ["ソース", "Spring ServletServerHttpResponse (ResponseAsyncListener は非 static 内部クラス)", "https://github.com/spring-projects/spring-framework/blob/v6.2.11/spring-web/src/main/java/org/springframework/http/server/reactive/ServletServerHttpResponse.java"],
    ["ソース", "Apache CXF Message (jakarta.xml.ws.client.connectionTimeout / receiveTimeout)", "https://github.com/apache/cxf/blob/cxf-4.0.6/core/src/main/java/org/apache/cxf/message/Message.java"],
    ["ソース", "Apache CXF jsse SSLUtils (javax.net.ssl.trustStore を自分で読む)", "https://github.com/apache/cxf/blob/cxf-4.0.6/core/src/main/java/org/apache/cxf/configuration/jsse/SSLUtils.java"],
    ["仕様", "Jakarta Standard Tag Library 3.0", "https://jakarta.ee/specifications/tags/3.0/"],
    ["仕様", "RFC 9110 HTTP Semantics (405 / Allow)", "https://www.rfc-editor.org/rfc/rfc9110"],
    ["MySQL", "WL#12999 wait_timeout 切断時のエラー通知 (4031)", "https://dev.mysql.com/worklog/task/?id=12999"],
    ["AWS", "Aurora MySQL version 8.4", "https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraMySQL.MySQL84.html"],
    ["AWS", "NAT ゲートウェイの接続トラブルシューティング (350 秒のアイドルタイムアウト)", "https://repost.aws/knowledge-center/vpc-troubleshoot-nat-gateway-connection"],
    ["AWS", "NLB の TCP アイドルタイムアウトの変更", "https://docs.aws.amazon.com/elasticloadbalancing/latest/network/update-idle-timeout.html"],
    ["AWS", "Fargate の追加 Linux 制御 (systemControls, 2023-08-09)", "https://aws.amazon.com/blogs/containers/announcing-additional-linux-controls-for-amazon-ecs-tasks-on-aws-fargate/"],
    ["AWS", "ECS TaskDefinition SystemControl (Fargate はプラットフォーム 1.4.0 以降)", "https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-properties-ecs-taskdefinition-systemcontrol.html"],
    ["AWS", "ContainerDefinition stopTimeout (既定 30 秒、Fargate 最大 120 秒)", "https://docs.aws.amazon.com/sdk-for-kotlin/api/latest/ecs/aws.sdk.kotlin.services.ecs.model/-container-definition/stop-timeout.html"],
    ["AWS", "ALB はターゲットの証明書を検証しない (re:Post)", "https://www.repost.aws/questions/QU97HoG_YMQxO1LXTj76ui-w/traffic-between-alb-and-backend-ec2-instance-needs-to-be-encrypted"],
]

REF_KEYS = ['eap-rn', 'eap-cfg', 'eap-tls', 'eap-upd', 'eap-mods', 'kb-ds', 'eap-ga', 'rhsa', 'wfcore5095', 'src-ksservice', 'src-elyapp', 'src-serverlogger', 'src-dsparser', 'src-moduleload', 'src-modspec', 'src-logdeps', 'src-bootstrap', 'src-standalone', 'src-webcomp', 'src-eemodcfg', 'src-defintercept', 'src-cdi', 'src-jsf', 'src-eventlogger', 'src-jbm', 'src-regex', 'src-ij-adapters', 'src-ij-mysqlvcc', 'src-ij-pool', 'src-ij-defaults', 'src-spring-dher', 'src-spring-sshr', 'src-cxf-msg', 'src-cxf-ssl', 'spec-tags', 'rfc9110', 'mysql-4031', 'aws-aurora84', 'aws-natgw', 'aws-nlb', 'aws-fargate-sysctl', 'aws-cfn-sysctl', 'aws-stoptimeout', 'aws-alb-cert']
assert len(REF_KEYS) == len(REFS), (len(REF_KEYS), len(REFS))
REF_BY_KEY = dict(zip(REF_KEYS, REFS))
