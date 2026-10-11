# 【Deep Research 依頼】JBoss EAP 8.1（Amazon ECS／UBI 9.8／Red Hat build of OpenJDK 21）で出ている警告 13 件の徹底解説と、jboss-cli による対処実装

（本日：2026 年 10 月 11 日。この時点の最新情報で調査すること）

## 0. 依頼の要旨

あなたは Red Hat JBoss EAP／WildFly（WildFly Core、Elytron、Undertow、Weld、IronJacamar、JBoss Modules）、Jakarta EE、Spring Framework、MySQL、AWS（ECS、Fargate、Elastic Load Balancing）に精通したシニアエンジニアです。同時に、難しい技術を小学生にも正しく伝えられる教育者でもあります。

「2. 調査対象の警告」の ①〜⑬ それぞれについて、次の 4 点を調べ、日本語のレポートにまとめてください。説明は深く、詳しく、わかりやすく、明確にしてください。

1. 小学生にもわかる説明
2. 動作原理と動作イメージ（内部で何が、どの順番で起きているか）
3. 登場の歴史・背景・必要になった経緯
4. 「1. 前提環境」で極めて適切に対処するための実装例（JBoss EAP 8.1 のサブシステム設定は jboss-cli で行う前提）

① については、4 章の追加質問 Q1〜Q3 への回答と、付録 A の現行実装のレビューも必須です。

### 依頼原文（そのまま掲載）

> 以下の①～⑬として列挙した各警告について、極めて深く詳しくわかりやすく明確に、最新の情報を踏まえて、動作原理と動作イメージに深堀しながら、登場の歴史と背景と必要になった経緯も絡めて小学生にもわかるように説明してください。また、各警告内容に対して極めて適切に対処する実装を、ECSタスク上で動作するUBI9.8のOpenJDK21のRedHatBuild並びにJBossEAP8.1の動作コンテナで、JBossEAP8.1のセットアップはjboss cliによる操作で各サブシステムの設定を行うことにした場合に必要な実装をし、それを実装例として記載してください。

警告①に付いていた注記（原文のまま）：

> ただし、本警告についてはルートCAの自己署名証明書を追加する実装をしている。この追加する実装をしている際に、デフォルトのkeystoreの配置場所ではなく、他ディレクトリにp12ファイルを配置するような実装にする場合に、このような警告が起きてしまうのか、standalone.shの実行時引数にkeystoreのパスを渡している場合でもこのような警告は発生してしまうのか、この場合、どのように対処するのが適切なのかを極めて詳しく合わせて説明してください。実際の実装箇所は、Container_ExtraSLB_JVM_https_outboundsのプロジェクトフォルダの実装内容を確認して、警告の対処法として適切な内容を説明してください。

※ Container_ExtraSLB_JVM_https_outbounds は社内プロジェクトで Web 上には存在しないため、要点を付録 A に転記した。

## 1. 前提環境（固定条件）

| 項目 | 内容 |
|---|---|
| 実行基盤 | Amazon ECS タスク。Fargate を主な対象とし、EC2 起動タイプで挙動や設定が変わる点は併記すること |
| コンテナ | UBI 9.8 ベース＋Red Hat build of OpenJDK 21＋Red Hat JBoss EAP 8.1。standalone モード（standalone.xml）。JBOSS_HOME は /opt/jboss-eap（警告①のパスより） |
| 設定方式 | EAP の各サブシステム設定は jboss-cli（.cli スクリプト）で行い、standalone.xml は手で編集しない。現行はイメージのビルド時に `embed-server` で適用して standalone.xml に焼き込み、環境ごとに変わる値は `${env.変数名:既定値}` 式にして ECS タスク定義の environment／secrets から渡している |
| 前段 | ALB で TLS を終端し、コンテナは 8080（HTTP）で受ける。インバウンドの 8443（HTTPS）は使っていない |
| アウトバウンド | アプリから外部へ HTTPS の REST 通信を行う。相手は、自己署名ルート CA の証明書を使う extraslb、その他の提供元、パブリック CA のサーバ |
| DB | MySQL 8.4.7（ログの productVersion より）。社内の別資料では Amazon Aurora MySQL（8.4 互換、Serverless v2）と MySQL Connector/J 9.7.0 を前提にしている。RDS for MySQL の場合と違いがあれば併記すること。XA データソース（プール名 MIF02JA_JDS、JNDI 名 java:/jdbc/MIF02JA_JDS）。接続検証は、過去に background-validation=true（background-validation-millis=60000）と validate-on-match=true を併用していた時期がある（現在の値は未確定） |
| アプリ | iwinmichl.war。Spring Framework（Spring MVC）ベースで、JSP/JSTL、Apache CXF 関連の依存、jboss-deployment-structure.xml を含む。Spring と各ライブラリの正確な版は未確定 |
| ログ | コンソール出力は awslogs で CloudWatch Logs へ送る。server.log を EFS 上に出力する構成もある |
| ファイルシステム | 現行は readonlyRootFilesystem=false。将来 true にする可能性があるので、両方で成り立つ実装が望ましい |
| 構成 | フロントとバックの 2 種類の EAP コンテナがあり、どちらも共通のベースイメージを継承して WAR を配置する |

不明な点（Spring・Connector/J・CXF の版、jboss-deployment-structure.xml の全文、データソースの現在の設定値など）は、置いた仮定を明示して回答し、仮定が違う場合の分岐も示すこと。

## 2. 調査対象の警告（ユーザー環境のログ。日本語ロケールの出力をそのまま転記）

```
①WFLYELY00023: keystoreファイル /opt/jboss-eap/standalone/configuration/application.keystoreは存在しない。空白を使用しました。
②WFLYSRV0058: jboss-deployment-structure.xmlで追加されたリソースルート/content/iwinmichl.war/WEB-INF/classes/testClassesは存在しません。
③WFLYSRV0018:デプロイメント"deployment.iwinmichl.warはプライベートモジュール"org.apache.cxf.impl"を使っていますが、このモジュールは今後のバージョンで予告なく削除される可能性があります。
④WFLY0007: 例外が原因でオプションのコンポーネント org.springframework.http.server.reactive.ServletServerHttpResponse$ResponseAsyncListenerをインストールしていません（DEBUGレベルを有効にして、原因を確認してください）
⑤WFLYWELD0013: デプロイメント iwinmichl.warにはJakarta Contexts and Dependency Injectionアノテーションが含まれますが、Beanアーカイブは見つかりませんでした(beans.xmlおよびBeanを定義するアノテーションを持つクラスがありません）
⑥WFLYSRV0274: jboss-deployment-structure.xmlを介して除外された依存関係.org.jboss.logmanager.log4j2は存在しません。
⑦Failed to define class javax.servlet.jsp.jstl.tlv.Permitted.TaglibsTLV in Module "deployment.iwinmichl.war" from Service Module Loader: java.lang.NoClassDefFound Error: Failed to link javax/servlet/jsp/jstl/tlv/PermittedTaglibsTLVModule "deployment.iwinmichl.war" from Service Module Loader javax/servlet/jsp/tagext/TaglibraryValidator
⑧IJ030040: Closing a statement you left open please do your own housekeeping for: java/jdbc/MIF02JA_JDS - java.lang.Throwable: STACKTRACE
⑨Resolved ( org.springframework.web.HttpRequestMethodNotSupportedException: RequestMethod 'POST' is not supported'
⑩org.jboss.jca.adapters.jdbc.xa.XAManagedConnectionFactory default task-7 IJ030027: Destroying connection that is not valid, due to the following exception: com.mysql.cj.jdbc.ConnectionWrapper@752a69a6: java.sql.SQLException: Ping failed: java.lang.reflect.InvocationTargetException
⑪org.jboss.jca.core.connectionmanager.pool.strategy.OnePool default-task-7 IJ000621: Destroying connection that could not be validated: org.jboss.jca.core.connectionmanager.listener.TxConnectionListener@384d5be6[state=NORMAL managed connection=org.jboss.jca.adapters.jdbc.xa.XAManagedConnection@c24620c connection handles=0 lastReturned=1788828592947 lastValidated=1788827437514 lastCheckedOut=1788828592692 trackByTx=false pool=org.jboss.jca.core.connectionmanager.pool.strategy.OnePool@4a8f027f mcp=SemaphoreConcurrentLinkedDequeManagedConnectionPool@4a9fc932[pool=MIF02JA_JDS] xaResource=XAResourceWrapperImpl@5ece3ccd[xaResource=org.jboss.jca.adapters.jdbc.xa.XAManagedConnection@c24620c pad=false overrideRmValue=false productName=MySQL productVersion=8.4.7 jndiName=java:/jdbc/MIF02JA_JDS] txSync=null]
⑫org.jboss.jca.adapters.jdbc.WrappedConnection default-task-7 IJ030042: Closing a result set you left open please do your own housekeeping for: com.mysql.cj.jdbc.result.ResultSetImpl@46f61974:java.lang.Throwable: STACKTRACE
⑬org.jboss.jca.core.connectionmanager.pool.strategy.OnePool ServerService Thread Pool -- 80) IJ000615: Destroying active connection in pool: MIF02JA_JDS (org.jboss.jca.adapters.jdbc.xa.XAManagedConnection@6c1a1d2)
```

転記時の表記ゆれと補足（調査で正しい英語原文とメッセージ ID を確定させること）:

- ④の「WFLY0007」は、EE サブシステムの `WFLYEE0007`（Not installing optional component ... due to an exception ...）である可能性が高い。
- ⑦は転記時に崩れている。正しくは `javax.servlet.jsp.jstl.tlv.PermittedTaglibsTLV` と `java.lang.NoClassDefFoundError: Failed to link javax/servlet/jsp/jstl/tlv/PermittedTaglibsTLV (Module "deployment.iwinmichl.war" from Service Module Loader): javax/servlet/jsp/tagext/TagLibraryValidator` だと推定される。
- ⑨は Spring の `Resolved [org.springframework.web.HttpRequestMethodNotSupportedException: Request method 'POST' is not supported]` だと推定される。
- ⑪のエポックミリ秒を日本時間に直すと、lastValidated＝2026-09-08 09:30:37.514、lastCheckedOut＝09:49:52.692、lastReturned＝09:49:52.947。lastReturned と lastValidated の差は約 19 分 15 秒、lastReturned と lastCheckedOut の差は 255 ミリ秒。ログ行そのものの出力時刻は手元にないので、「ログ時刻 − lastReturned」で放置時間を求める手順も示すこと。
- ⑧⑩⑪⑫ は同じデータソース（MIF02JA_JDS）で、⑩⑪⑫ は同じリクエスト処理スレッド（default task-7）で出ている。これらの関係も分析すること。

## 3. 各警告に共通する回答テンプレート（13 件すべてを同じ深さで）

警告ごとに、次の見出しをこの順番ですべて埋めること。後半の警告ほど説明が薄くなることがないよう、分量を均等に配分すること。

1. **ひとことで（小学生向け）**：身近なたとえ話で 3〜5 文。たとえ話のどの部分が実際の仕組みのどれに当たるかを対応表で示す。たとえ話が技術的な誤解を生まないようにすること。
2. **メッセージの正体**：英語原文、メッセージ ID、ログレベル、ロガーカテゴリ、出力元（サブシステム・ライブラリ・クラス名）、出るタイミング（ビルド時の embed-server／ブート時／デプロイ時／リクエスト処理時／停止時）。
3. **動作原理**：内部で何がどの順番で起き、どの条件判定でこのメッセージに至るのか。できる限りソースコード（クラス名・メソッド名）と設定属性に基づいて説明する。
4. **動作イメージ**：時系列のシーケンス図（Mermaid またはテキスト図）。正常時と警告が出るときの違いがわかるようにする。
5. **歴史・背景・必要になった経緯**：その仕組みとメッセージが、いつ（どの製品バージョン・仕様バージョン・Issue で）、なぜ導入されたか。それ以前は何が困っていたのか。
6. **この環境での原因候補と切り分け**：原因候補を列挙し、どのログ・コマンド・jboss-cli 操作で確定できるかを、具体的なコマンド付きで示す。
7. **影響度と放置した場合のリスク**：「無害」「是正が必要」「障害の予兆」のどれに当たるかと、その根拠。
8. **対処方針の比較**：根本対処と抑止（ログ設定）の区別。サーバ設定（jboss-cli）、アプリ修正（WAR）、ECS 設定のどれで直すべきか。推奨案とその理由。
9. **実装例**：その警告に対応する部分のコードとコメント。完全版は出力の 4 章（統合実装例）にまとめ、ここからは参照してよい。
10. **対処後の確認方法**：CLI の read-resource／read-attribute、ログで確認すべき行、簡単なテスト手順。
11. **出典**：根拠にした一次情報の URL。

## 4. 警告ごとの重点調査ポイント（リサーチプランに必ず含めること）

### ① WFLYELY00023（application.keystore が存在しない）

- EAP 8.1 の既定の standalone.xml にある `applicationKS`（key-store）、`applicationKM`（key-manager。`generate-self-signed-certificate-host` 属性）、`applicationSSC`（server-ssl-context）、Undertow の `https-listener` の関係。どのリソースのどの処理がこの警告を出すのか。自己署名証明書の自動生成を予告するメッセージ（WFLYELY01084 等）との関係。key-store サービスは、誰からも参照されていなくてもブート時に起動するのか。
- key-store の `required` 属性と `path`／`relative-to` の挙動。ファイルが無いとき「空（blank）のキーストア」で起動するとはどういうことか。
- 歴史：旧来のセキュリティレルム（ApplicationRealm の SSL 設定と自己署名証明書の自動生成）から Elytron への移行、EAP 8 でのレガシーセキュリティ削除までの経緯。正確なバージョンは一次情報で確認すること。
- **追加質問（必須。Q&A 形式で、結論 → 理由 → 根拠の順に回答）**
  - **Q1.** ルート CA（自己署名）の証明書を取り込んだ p12 を、既定の configuration ディレクトリではなく別のディレクトリ（現行実装では /opt/app/security/extraslb-truststore.p12）に置く実装にすると、この警告は出るのか。この警告が「自前の p12 のパス」で出るのはどんな場合か。p12 の置き場所のベストプラクティス（configuration 配下か専用ディレクトリか、readonlyRootFilesystem、権限、所有者）も示すこと。
  - **Q2.** standalone.sh の実行時引数でパスを渡している場合でも、この警告は出るのか。現行実装が渡しているのは `-Djavax.net.ssl.trustStore` などの JSSE システムプロパティである（ユーザーは「keystore のパス」と表現しているが、実際に渡しているのは trustStore。キーストアとトラストストアの違いも小学生向けに説明すること）。JSSE のシステムプロパティと Elytron の key-store リソースはどう関係するのか（あるいは関係しないのか）。逆に、起動引数で Elytron 側のパスを切り替えたい場合の正しい方法（`${...}` 式など）も示すこと。
  - **Q3.** この場合、どう対処するのが適切か。少なくとも次の案を比較し、本環境（ALB 終端、8080 受信、8443 未使用、ECS）での推奨を示すこと。
    - (a) 使っていないインバウンド HTTPS 一式（https-listener → applicationSSC → applicationKM → applicationKS）を、jboss-cli で安全な順序で削除する
    - (b) EAP が自動生成するはずのキーストアをビルド時に事前生成し、イメージに入れる（現行実装）
    - (c) 正式な鍵ストアを用意して applicationKS を差し替える（ALB からターゲットまでも暗号化する場合。ALB がターゲットの証明書を検証するかどうかも踏まえる）
    - (d) ログレベルやフィルタで抑止する
    - (e) これら以外に、より良い方法があればそれも
- **付録 A の現行実装のレビュー**：正しい点、誤りやリスク、改善版のコード（そのまま置き換えられる形）を示すこと。少なくとも次の観点で評価すること。
  1. 警告の発生源の判定（applicationKS 由来であり、自前の p12 の置き場所や -D 引数とは関係ない）は正しいか。
  2. 事前生成方式の評価。セキュリティ面（既知のパスワードの秘密鍵をイメージに同梱する、全タスクが同じ鍵を持つ、使っていない 8443 が待ち受けたままになる、など）と運用面の両方。
  3. 自前トラストストアの key-store に `required=true` を付けるべきか。パスを誤ったときに空のトラストストアで起動し、default-ssl-context 経由のアウトバウンド TLS が全部失敗する事故を防げるか。
  4. 「Elytron の default-ssl-context」と「javax.net.ssl.* システムプロパティ」の二層構えは妥当か。次のクライアントがそれぞれどちらの設定を参照するかを表にすること：HttpsURLConnection、java.net.http.HttpClient、Apache HttpClient 4.x／5.x、Spring の RestTemplate／RestClient／WebClient、RESTEasy（JAX-RS Client）、Apache CXF の JAX-WS クライアント、AWS SDK for Java v2、MySQL Connector/J（TLS 接続時）。
  5. 代替案として、UBI のシステムトラストストア（/etc/pki/ca-trust/source/anchors/ に置いて update-ca-trust を実行）に CA を追加する方式との比較。RPM 版の Red Hat build of OpenJDK の cacerts がシステムトラストストアから作られる仕組みと、利点・欠点。
  6. cacerts のコピーを Elytron の key-store として読み込むことで出る WFLYELY00024（期限切れ証明書の警告）の扱い。
  7. トラストストアのパスワードの扱い（standalone.xml の式、-D 引数によるプロセス引数への露出、Elytron credential-store が必要かどうか）。
  8. ベースイメージの違い。付録 A の参照実装は Red Hat 公式の EAP 8.1 イメージ（OpenJDK 17 版、JBOSS_HOME=/opt/server）を FROM にしているが、実環境は UBI 9.8＋OpenJDK 21＋EAP 8.1（JBOSS_HOME=/opt/jboss-eap）である。実環境向けの実装として示すこと。

### ② WFLYSRV0058（存在しないリソースルート）

- jboss-deployment-structure.xml の `<resources><resource-root path="..."/>` は何をするのか（JBoss Modules のリソースローダー、VFS の /content/... というパスの意味）。WEB-INF/classes の下のディレクトリを追加のリソースルートにすると何が起きるか（パッケージ階層のずれ、二重ロードなど）。
- ディレクトリが無いときの挙動（無視されるだけなのか）と、testClasses のような開発用の設定が本番 WAR に混ざる典型パターン。
- 歴史：JBoss AS 7（JBoss Modules によるモジュール型クラスローディング）で jboss-deployment-structure.xml が導入された経緯と、それ以前（AS 5/6 の階層型クラスローダー、jboss-classloading.xml など）の問題。
- 対処：記述子の修正、Maven プロファイルなどで環境ごとに記述子を切り替える方法、ビルド時の検査（WAR 内に実在するかのチェック）。

### ③ WFLYSRV0018（private モジュールの使用）

- module.xml の `jboss.api` プロパティ（private、unsupported、deprecated など）の意味。どの条件で警告が出るのか。ユーザーが jboss-deployment-structure.xml や MANIFEST.MF の Dependencies で明示した依存だけが対象で、サブシステムが暗黙に付ける依存は対象外なのか。兄弟メッセージとロガーカテゴリ。
- `org.apache.cxf.impl`、`org.apache.cxf`、`org.jboss.ws.cxf.jbossws-cxf-client` などの関係。EAP 8.1 で、アプリが CXF 固有の API（インターセプター、HTTPConduit、タイムアウト設定など）を使いたい場合に、Red Hat がサポートする依存の書き方。
- アプリが何のために org.apache.cxf.impl を必要としているかを特定する方法（WAR 内クラスの参照解析、jdeps など）。
- 対処の比較：依存の削除、公開モジュールへの置き換え、Jakarta XML Web Services 標準 API への置き換え、CXF を WAR に同梱して webservices サブシステムを除外する案の是非。webservices サブシステムの jboss-cli 設定（クライアント設定、エンドポイント設定、ALB の背後での WSDL アドレス書き換えに関わる属性など）で代わりにできることの整理。

### ④ WFLYEE0007（オプションのコンポーネントをインストールしていない）

- 正しいメッセージ ID。EE サブシステムでいう「オプションのコンポーネント」とは何か。WildFly／Undertow が WAR 内の `jakarta.servlet.AsyncListener` 実装クラスなどを、リソース注入の対象になる Web コンポーネントとして登録する仕組み（どの処理が、なぜそうするのか）。
- `org.springframework.http.server.reactive.ServletServerHttpResponse$ResponseAsyncListener` のクラス構造（内部クラスかどうか、コンストラクタの形）と、インストールに失敗する理由。DEBUG で出てくる可能性のある原因（たとえば WFLYEE0048「Could not find default constructor」や、依存クラスの欠落による NoClassDefFoundError など）と、それぞれの見分け方。Weld（CDI）が有効なデプロイかどうかで挙動が変わるか。同じ理由で警告になる Spring の他のクラスはあるか。
- Spring の非同期処理（DeferredResult、Callable、SSE など）の動作に実害があるか。
- 対処：DEBUG で原因を確かめる jboss-cli の手順（ロガーとハンドラのレベル、確認後の戻し方）。無害と確定した場合に、この警告だけを狙って抑止する方法（logging サブシステムの filter-spec。`match` がフォーマット前とフォーマット後のどちらのメッセージに効くのか、正確な構文）と、抑止しすぎない設計。

### ⑤ WFLYWELD0013（CDI アノテーションはあるが Bean アーカイブが無い）

- WildFly は何を「CDI アノテーション」と判定するのか（対象アノテーションの一覧と判定処理）。Bean アーカイブの判定（beans.xml、bean-discovery-mode、Bean 定義アノテーション）。CDI 1.1 で導入された暗黙的 Bean アーカイブ、CDI 4.0（Jakarta EE 10）での空の beans.xml の扱いの変更。weld サブシステムの属性（require-bean-descriptor、non-portable-mode、development-mode、legacy-empty-beans-xml-treatment など）の意味。
- Spring アプリでこの警告が出る典型的な原因の候補（@Inject や @Named の利用、jakarta.transaction-api などの EE API jar の WAR 同梱、ライブラリ内のアノテーション、jsf など CDI に依存するサブシステムを除外している場合など）と、切り分け方法。
- 対処：CDI を使わないなら jboss-deployment-structure.xml で weld を除外する（同時に除外が必要になるサブシステムがあるか、副作用は何か）。EE API を provided にする。beans.xml を置く案の是非。

### ⑥ WFLYSRV0274（除外を指定したモジュールが存在しない）

- jboss-deployment-structure.xml の `<exclusions>` の仕組み。存在しないモジュール名を指定したときの挙動（除外が空振りして、意図した除外が効いていない可能性）。
- `org.jboss.logmanager.log4j2` モジュールが存在した時期と、廃止または改名の経緯。EAP 8.1 での Log4j 2 関連モジュールの構成（`org.apache.logging.log4j.api` など）。logging サブシステムがデプロイに暗黙で追加するログ API の一覧。
- 対処の比較：
  - (A) アプリに同梱した Log4j 2 を使う場合の正しい除外指定。あるいは logging サブシステムの `add-logging-api-dependencies=false`／`use-deployment-logging-config` を CLI で設定する方法（サーバ全体に効く点の評価を含む）。
  - (B) EAP の logging サブシステムに寄せ（log4j-core を同梱しない）、CloudWatch Logs に向いた出力形式（JSON フォーマッターなど）にする方法。
  - ECS（awslogs）でのログ収集の設計まで含めて推奨を示すこと。

### ⑦ Failed to define class javax.servlet.jsp.jstl.tlv.PermittedTaglibsTLV

- JBoss Modules の「Failed to define class」の意味（ロガーカテゴリ、ログレベル）と、「NoClassDefFoundError: Failed to link」の意味（スーパークラスやインターフェースを解決できなかった）。
- なぜ javax.* のクラスを読み込もうとするのか。WAR に同梱された javax 版 JSTL（jstl-1.2.jar など）の TLD（permittedTaglibs.tld や scriptfree.tld の `<validator>`）が TLD スキャンで読まれ、javax.servlet.jsp.tagext.TagLibraryValidator を親に持つクラスのロードが試みられる仕組み。Jakarta EE 9 での javax から jakarta への名前空間変更の歴史と経緯、EAP 8 への影響。
- 実害の有無。JSP が壊れるケースと壊れないケース。Jastow のタグプラグインなどのおかげで動いているように見える場合の注意点。
- Jakarta Standard Tag Library 3.0 の新しい URI（jakarta.tags.core など）と、旧 URI（http://java.sun.com/jsp/jstl/core など）の互換性。EAP 8.1 が提供する JSTL 実装とモジュール。
- 対処：javax 版 JSTL を取り除き、EAP が提供する Jakarta 版を使う（Maven 依存のスコープ、enforcer プラグインによる javax.* の混入防止）。Migration Toolkit for Applications（MTA）や Eclipse Transformer による移行チェック。JSP の taglib 宣言を更新する必要があるか。

### ⑧ IJ030040 と ⑫ IJ030042（Statement と ResultSet の閉じ忘れ）

- IronJacamar の WrappedConnection が Statement と ResultSet を追跡する仕組み（データソースの `track-statements` 属性：false／true／nowarn と既定値）。接続を返却したときに閉じられて警告が出る流れ。`java.lang.Throwable: STACKTRACE` の読み方（生成した場所のスタック）。
- 典型的な原因（アプリコードの close 漏れ、Spring JdbcTemplate／MyBatis／JPA で起きるパターン）。
- 対処：try-with-resources などによるアプリ修正の例。`track-statements` を環境ごとにどう設定するか（開発・検証は true、本番は nowarn などの是非）。cached-connection-manager（debug／error）による接続リークの検出や、spy ロギングなどの jboss-cli 設定。
- 歴史：JBoss AS 時代の JBossJCA から IronJacamar への移行と、この機能が必要になった経緯（プール環境でのリソースリーク）。

### ⑨ Resolved [HttpRequestMethodNotSupportedException: Request method 'POST' is not supported]

- 出力元（Spring MVC の DefaultHandlerExceptionResolver／AbstractHandlerExceptionResolver と warnLogCategory）。返る HTTP 応答（405 と Allow ヘッダ）。Spring のバージョンによる文言やログレベルの違い。ログにリクエストの URL が出ない理由。
- 原因候補：GET 専用のハンドラーへの POST、エラーページへフォワードするときにメソッドが POST のまま維持されるケース（Servlet のエラーディスパッチ）、フォームの送信先の誤り、セッション切れのあとの再送信、ALB のヘルスチェックや外部のスキャナー・ボット、HiddenHttpMethodFilter など。
- 切り分け：Undertow のアクセスログを jboss-cli で有効にする方法（access-log／console-access-log などの選択肢、標準出力への出力、X-Forwarded-For を含むパターン、http-listener の proxy-address-forwarding）。ALB のアクセスログとの突き合わせ。Spring 側でメソッドと URL を記録する方法。
- 対処：マッピングの修正、@ControllerAdvice などで 405 を詳しく記録する実装、ログレベルの見直し。
- 歴史：HTTP メソッドと 405（RFC 9110）、Spring MVC のアノテーション駆動のマッピングと例外リゾルバーの経緯。

### ⑩ IJ030027 と ⑪ IJ000621（検証に失敗した接続の破棄）

- 接続検証の仕組み。validate-on-match と background-validation（background-validation-millis）。valid-connection-checker（メッセージの「Ping failed: java.lang.reflect.InvocationTargetException」から、ping をリフレクションで呼ぶ MySQLValidConnectionChecker のようなチェッカーと推定される。これを確認し、根本原因が InvocationTargetException に包まれて見えにくくなる理由と、根本原因を出す方法を示すこと）。JDBC4 の isValid や check-valid-connection-sql との違い。exception-sorter、stale-connection-checker、flush-strategy、idle-timeout-minutes。
- ⑪のログの各フィールド（state、connection handles、lastReturned、lastValidated、lastCheckedOut、trackByTx、pad、overrideRmValue など）の意味と読み方。リクエスト処理スレッド（default task-7）で出ていることから、どの検証方式で検出されたと読めるか。
- 原因候補：MySQL の wait_timeout／interactive_timeout。AWS の経路上のアイドル切断（NAT Gateway や NLB などのアイドルタイムアウト。最新の既定値と変更できるかを確認すること）。Aurora／RDS のフェイルオーバーやメンテナンス、Aurora Serverless v2 の自動一時停止やスケーリング、RDS Proxy、DB 側での接続の kill など。
- 対処：MySQL 8.4（Aurora MySQL 8.4 互換）向けの XA データソースの推奨設定を jboss-cli で示すこと。具体的には、JDBC ドライバーのモジュール登録と jdbc-driver の定義、xa-data-source の作成、プールサイズ、idle-timeout-minutes とアイドル切断時間の関係、検証方式の選び方、exception-sorter、Connector/J の接続プロパティ（tcpKeepAlive、connectTimeout、socketTimeout など）、資格情報の渡し方（ECS secrets や Elytron credential-store）。ECS タスク定義の systemControls で TCP keepalive（net.ipv4.tcp_keepalive_*）を設定できるか（Fargate で可能か、制約は何か）。XA を使うときに必要な関連設定（MySQL の XA 固有の注意点、ECS で複数のタスクが動くときに transactions サブシステムの node-identifier を一意にする方法、リカバリー）。
- 歴史：プールした接続が「死んでいる」問題と、検証機能が導入された経緯。

### ⑬ IJ000615（使用中の接続をプールから破棄）

- どの操作で出るか（サーバの停止、アンデプロイや再デプロイ、データソースの無効化やリロード、flush 操作、flush-strategy による一斉フラッシュなど）。スレッド名「ServerService Thread Pool -- 80」から何が読み取れるか。他の原因との見分け方。
- ECS のタスク停止の流れ（ALB の登録解除の遅延 → SIGTERM → stopTimeout → SIGKILL。それぞれの既定値と Fargate での上限）。standalone.sh、PID 1、シグナルの中継（LAUNCH_JBOSS_IN_BACKGROUND）、initProcessEnabled の効果と限界。付録 A の entrypoint.sh が `exec standalone.sh ...` で起動している点も踏まえること。
- EAP のグレースフルシャットダウン（suspend）。SIGTERM を受けたときに処理中のリクエストの完了を待たせる、EAP 8.1 での公式な方法（たとえばシステムプロパティ org.wildfly.sigterm.suspend.timeout が存在するか、既定値、サポート状況）と、shutdown 操作の suspend-timeout。
- 対処：entrypoint、jboss-cli、ECS タスク定義（stopTimeout）、ALB（deregistration delay）を一貫させた設計と実装。接続リークが原因だった場合の検出方法。

## 5. 実装例の共通要件

- **jboss-cli**
  - サブシステムごとに番号付きのスクリプトに分けること（例：00-common、10-elytron、20-logging、30-datasource、40-webservices、50-ee-weld、60-undertow、70-transactions、90-verify）。各スクリプトの冒頭コメントに、どの警告への対処かを明記すること。
  - イメージのビルド時に `embed-server --server-config=standalone.xml --std-out=echo` で適用する方式を基本とし、起動時に変える必要がある値は `${env.変数名:既定値}` 式で外に出すこと。起動時に再適用が必要なものがあれば、その理由と方法を示すこと。
  - 冪等にすること（`if (outcome != success) of ...:read-resource` など）。複数の操作は batch でまとめること。
  - 属性名・操作名・値は、EAP 8.1（および上流に当たる WildFly のモデルリファレンス wildscribe）で実在を確認したものだけを使うこと。EAP 8.1 で非推奨・削除になったものは使わないこと。バージョンによる違いがあれば注記すること。
  - 適用結果を確かめる検証用の CLI（read-resource／read-attribute）も付けること。
- **コンテナ**：UBI 9.8＋Red Hat build of OpenJDK 21＋EAP 8.1 の Dockerfile（マルチステージ可、非 root 実行、JDBC ドライバーのモジュール登録、CLI のビルド時適用、ベースイメージのダイジェスト固定）と、シグナル処理を含む entrypoint.sh。
- **ECS**：タスク定義（コンテナ定義）の JSON 抜粋。environment／secrets、stopTimeout、healthCheck、systemControls、logConfiguration、readonlyRootFilesystem=true にする場合に必要な書き込み先。
- **アプリ（WAR）側**：サーバ設定で直すべきでないもの（②③⑤⑥⑦⑧⑨⑫ など）は、WAR 側の修正として明確に分けて示すこと（jboss-deployment-structure.xml の修正版、pom.xml の依存とスコープの修正、Java コードの例）。
- **抑止は最終手段**：ログレベルやフィルタで警告を消す方法は、根本対処ができない場合か、無害と確定した場合に限ること。その場合は、抑止の範囲（本当に見たい警告まで消えないか）と根拠を明記すること。
- **運用**：本当に危険な警告（⑩⑪⑬ など）を CloudWatch Logs のメトリクスフィルタとアラームで監視する例を示すこと。
- コードは省略記号（...）で端折らず、そのまま使える完全な形で書き、各行の意図をコメントで説明すること。説明が重複しないよう、共通事項は出力の 1 章と 4 章にまとめ、各警告からは参照すること。

## 6. 調査方法と情報源の条件

- 検索は英語の一次情報を中心に行い、レポートは日本語で書くこと。
- 情報源の優先順位：
  1. Red Hat 公式ドキュメント（JBoss EAP 8.1 の構成ガイド、セキュリティ（Elytron）、データソース、開発ガイド、移行ガイド、リリースノート）と、Red Hat Customer Portal のナレッジ（閲覧できる範囲）
  2. ソースコードと Issue（GitHub の wildfly/wildfly、wildfly/wildfly-core、wildfly-security/wildfly-elytron、ironjacamar、jboss-modules、undertow、weld、spring-projects/spring-framework、issues.redhat.com の WFLY／WFCORE／ELY／JBEAP／JBJCA など）。メッセージの英語原文と ID は、ロガーインターフェース（*Logger や *Messages）の定義で確認すること。
  3. 仕様（Jakarta Servlet 6.0、Jakarta Pages 3.1、Jakarta Standard Tag Library 3.0、Jakarta CDI 4.0、RFC 9110）
  4. MySQL（Server 8.4、Connector/J）と AWS（ECS、Fargate、ELB、NAT Gateway、RDS／Aurora）の公式ドキュメント
  5. 上記で確認できない場合に限り、信頼できる技術ブログや Q&A（その場合はそう明記する）
- 2026 年 10 月時点の最新情報を優先すること。EAP 8.1 の最新アップデート、UBI 9.8、OpenJDK 21 の最新版で挙動が変わった点があれば明記すること。EAP 6/7 や javax 時代の情報は「歴史」の説明に限って使い、現行との違いを明示すること。
- 一次情報で確認できた事実には出典を付けること。推測や一般論には「推測」、確認できなかったことには「未確認」と明記すること。存在しない属性名・CLI 操作・メッセージ ID・システムプロパティを作らないこと。
- 付録 A のコードは社内プロジェクトの抜粋で、Web 上には存在しない。検索の対象ではなく、レビューの対象として扱うこと（実ファイルが添付されている場合はそちらを正とする）。

### 調査の進め方（リサーチプランの指針）

1. 13 件それぞれについて、メッセージを出しているソースコード上の場所と英語原文を特定する。
2. EAP 8.1 の公式ドキュメントで、関係するサブシステムの属性、既定値、推奨設定を確認する。
3. 各機能が導入された経緯（製品バージョン、Issue、仕様）を確認する。
4. ECS／Fargate、ALB、Aurora／MySQL 8.4、UBI 9.8、OpenJDK 21 といった環境側の要因を確認する。
5. 付録 A を読み、①の Q1〜Q3 とレビュー観点に答える。
6. 実装例を組み立て、使った属性と操作が実在するかをモデルリファレンスで照合する。

## 7. 出力の構成

0. **エグゼクティブサマリー**：一覧表（No、メッセージ ID、出力元、発生タイミング、重要度、原因（候補）、推奨対処、対処する場所（jboss-cli／WAR／ECS））と、優先して対処すべき順番。前提にしたバージョンの要約も載せる。
1. **共通の基礎知識**（小学生向けのたとえ話 → 技術的な説明の順）：EAP とサブシステム、JBoss Modules とクラスローディング、デプロイの流れ、Elytron（キーストアとトラストストア）、IronJacamar（接続プール）、ECS タスクの起動と停止。
2. **警告①〜⑬の解説**（3 章のテンプレートどおり）。
3. **① の追加質問への回答**（Q1〜Q3）と、**付録 A の現行実装のレビュー**（改善版のコード付き）。
4. **統合実装例**：すべての jboss-cli スクリプト、Dockerfile、entrypoint.sh、ECS タスク定義、WAR 側の修正を、それぞれ完全な形で。
5. **適用後の検証チェックリスト**：どの警告が何件になれば成功か。
6. **年表**：JBoss AS → WildFly → EAP、Java EE → Jakarta EE、関連する仕様、各警告に関わる機能が登場した時点。
7. **用語集**：小学生向けのひとこと説明付き。
8. **前提にしたバージョンの一覧**（EAP 8.1 のアップデート、WildFly Core、Elytron、Undertow、Weld、IronJacamar、Spring Framework、MySQL Connector/J など）と、**追加で確認すべき情報のリスト**。
9. **参考文献**（URL の一覧）。

- 図は Mermaid（sequenceDiagram や flowchart）かテキスト図で示すこと。
- 専門用語は初めて出たときに英語を併記し、ひとことで意味を添えること。
- 「小学生向けの説明」と「技術者向けの深掘り」は見出しを分け、両方を必ず書くこと。

---

## 付録 A：現行実装（社内プロジェクト Container_ExtraSLB_JVM_https_outbounds）の要点

（Web 上に存在しないため、レビューに必要な部分を転記した）

### A-1. 目的と構成

- ECS 上の EAP 8.1 コンテナ（フロントとバック）から、自己署名ルート CA の証明書を使う extraslb を含む複数の提供元へ、アウトバウンドの HTTPS 通信を行うための実装。
- 受け取った証明書（ルート CA、中間 CA、サーバ証明書。PEM／DER／PKCS#7 のいずれも可）を BuildKit Secrets でビルド時だけ渡す。JDK の cacerts（RPM 版 OpenJDK では、update-ca-trust が管理するシステムトラストストアへのシンボリックリンク）を PKCS12 形式に変換してコピーし、そこへ受け取った証明書を追加して `/opt/app/security/extraslb-truststore.p12`（パスワード changeit、権限 0444）を作る。証明書の別名は `<提供元名>-ca-<連番>`。
- これらは共通のベースイメージで行い、フロントとバックは WAR を COPY するだけ。
- 信頼設定は次の二層構えで、どちらも同じ p12 を参照する。

| 層 | 設定する場所 | 狙い |
|---|---|---|
| Elytron の default-ssl-context | jboss-cli（ビルド時に embed-server で適用） | SSLContext.getDefault() を使う実装全般 |
| javax.net.ssl.trustStore などのシステムプロパティ | entrypoint.sh が standalone.sh の引数として付ける | システムプロパティから自分で SSLContext を組み立てるライブラリ |

### A-2. jboss-cli（configure-outbound-tls.cli。ビルド時に embed-server で適用）

```
if (outcome != success) of /subsystem=elytron/key-store=extraslb-trust-store:read-resource
    /subsystem=elytron/key-store=extraslb-trust-store:add( \
        path="${env.EXTRASLB_TRUSTSTORE_PATH:/opt/app/security/extraslb-truststore.p12}", \
        type="${env.EXTRASLB_TRUSTSTORE_TYPE:PKCS12}", \
        credential-reference={clear-text="${env.EXTRASLB_TRUSTSTORE_PASSWORD:changeit}"} \
    )
end-if

if (outcome != success) of /subsystem=elytron/trust-manager=extraslb-trust-manager:read-resource
    /subsystem=elytron/trust-manager=extraslb-trust-manager:add(key-store=extraslb-trust-store)
end-if

if (outcome != success) of /subsystem=elytron/client-ssl-context=extraslb-client-ssl-context:read-resource
    /subsystem=elytron/client-ssl-context=extraslb-client-ssl-context:add( \
        trust-manager=extraslb-trust-manager, \
        protocols=["TLSv1.3","TLSv1.2"] \
    )
end-if

/subsystem=elytron:write-attribute(name=default-ssl-context, value=extraslb-client-ssl-context)
```

key-store の `required` 属性は指定していない。

### A-3. entrypoint.sh（起動部分）

```bash
exec "${JBOSS_HOME}/bin/standalone.sh" \
    -b "${JBOSS_BIND_ADDRESS}" \
    -c "${SERVER_CONFIG}" \
    -Djavax.net.ssl.trustStore="${EXTRASLB_TRUSTSTORE_PATH}" \
    -Djavax.net.ssl.trustStorePassword="${EXTRASLB_TRUSTSTORE_PASSWORD}" \
    -Djavax.net.ssl.trustStoreType="${EXTRASLB_TRUSTSTORE_TYPE}" \
    "$@"
```

- 起動前に次を行う：ビルド時に設定済みでなければ embed-server で A-2 を適用する（既定は「設定済みならスキップ」）、standalone_xml_history を正規化する、application.keystore を補完する（A-4）。
- entrypoint.sh の中では LAUNCH_JBOSS_IN_BACKGROUND を設定していない。

### A-4. WFLYELY00023 への現行の対処（application.keystore の事前生成）

現行の見解（プロジェクトのドキュメントより。検証の対象として扱うこと）：

- 警告は EAP 標準の applicationKS（インバウンド 8443 用）が出しており、自前のアウトバウンド設定とは関係ない。application.keystore は配布物に含まれず、最初のインバウンド HTTPS ハンドシェイクのときに遅延生成される。一方で key-store サービスは、参照されているかどうかに関係なくブートのたびに起動するため、ファイルが無い間は毎回この警告が出る。
- 上流の WildFly（36 系）での実測：
  - 標準設定のままブート → 出る
  - https-listener だけを削除 → 出る
  - default-ssl-context の設定の有無 → 影響しない
  - embed-server → 出る
  - application.keystore を事前に置く → 出ない
  - 警告が出ている同じブート上で、自己署名ルート CA が発行したサーバと、パブリック CA のサーバへのアウトバウンド HTTPS は、どちらも成功した（SSLContext.getDefault() は Elytron の DelegatingSSLContext だった）
- readonlyRootFilesystem=true だと遅延生成に失敗し、8443 のハンドシェイクが失敗しうる。

現行の実装：ビルド時（Dockerfile）と起動時（entrypoint.sh。ファイルが無い場合だけ）に provision-application-keystore.sh を実行し、EAP の遅延生成と同じ形の鍵ストアを作る。実際の値は standalone.xml から読み取る。以下は標準設定のときに実行されるコマンドの例。

```bash
keytool -genkeypair -alias server -keyalg RSA -keysize 2048 -sigalg SHA256withRSA -validity 3650 \
  -dname "CN=localhost" \
  -keystore "${JBOSS_HOME}/standalone/configuration/application.keystore" \
  -storetype JKS -storepass password -keypass password
```

- 対象にするのは、standalone.xml を解析して次の条件をすべて満たす key-store だけ：relative-to が jboss.server.config.dir、パスが単純なファイル名、ファイルがまだ無い、パスワードがリテラル、generate-self-signed-certificate-host を持つ key-manager から参照されている。

現行が採用しなかった案と、その理由：

| 案 | 採用しなかった理由 |
|---|---|
| ログレベルの変更 | 同じカテゴリの重要な警告まで消える |
| applicationKS／KM／SSC を CLI で削除 | https-listener が参照しているので、順序を誤るとブートに失敗する。将来 8443 を使う構成に移れなくなる。得られるのは警告 1 行の削除だけ |
| https-listener ごと削除 | 8443 を使うかどうかはアプリの要件であり、ベースイメージが決めることではない |
| 毎回の起動時に生成 | 無駄が多く、タスクごとに証明書が変わる |

- WFLYELY00024（cacerts に由来する期限切れのルート証明書の警告）には対処していない。トラストアンカーを外すと、既存の検証経路を壊すおそれがあるため。

### A-5. ビルド時の処理順（base/Dockerfile の要点）

1. `FROM registry.redhat.io/jboss-eap-8/eap81-openjdk17-runtime-openshift-rhel9:latest`（参照実装。実環境は UBI 9.8＋OpenJDK 21＋EAP 8.1 で、JBOSS_HOME=/opt/jboss-eap）
2. `RUN --mount=type=secret,id=cacerts,target=/run/secrets/cacerts.tar,required=true build-truststore.sh ...`（トラストストアの生成）
3. application.keystore の事前生成（A-4）
4. embed-server で A-2 を適用し、standalone_xml_history を削除して、configuration の所有者を実行ユーザー（uid 185、gid 0）にする
5. `USER 185`、`ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]`
