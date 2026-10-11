# JBoss EAP 8.1 警告 13 件 徹底解説と jboss-cli による対処実装

ECS タスク上の UBI 9.8 + Red Hat build of OpenJDK 21 + JBoss EAP 8.1 コンテナ / サブシステム設定はすべて jboss-cli で実施 / 作成日 2026-10-11

## 目次

- [対象環境と読み方](#対象環境と読み方)
- [一覧](#一覧)
- [基礎知識](#基礎知識)
- [① WFLYELY00023: keystore ファイル application.keystore が存在しない (空で代用した)](#①-wflyely00023-keystore-ファイル-applicationkeystore-が存在しない-空で代用した)
- [② WFLYSRV0058: jboss-deployment-structure.xml で追加したリソースルートが存在しない](#②-wflysrv0058-jboss-deployment-structurexml-で追加したリソースルートが存在しない)
- [③ WFLYSRV0018: デプロイが private モジュール org.apache.cxf.impl を使っている](#③-wflysrv0018-デプロイが-private-モジュール-orgapachecxfimpl-を使っている)
- [④ WFLYEE0007: 例外のためオプションのコンポーネント ...ServletServerHttpResponse$ResponseAsyncListener をインストールしていない](#④-wflyee0007-例外のためオプションのコンポーネント-servletserverhttpresponseresponseasynclistener-をインストールしていない)
- [⑤ WFLYWELD0013: CDI アノテーションはあるが Bean アーカイブが見つからない](#⑤-wflyweld0013-cdi-アノテーションはあるが-bean-アーカイブが見つからない)
- [⑥ WFLYSRV0274: jboss-deployment-structure.xml で除外した依存 org.jboss.logmanager.log4j2 が存在しない](#⑥-wflysrv0274-jboss-deployment-structurexml-で除外した依存-orgjbosslogmanagerlog4j2-が存在しない)
- [⑦ Failed to define class javax.servlet.jsp.jstl.tlv.PermittedTaglibsTLV (NoClassDefFoundError: Failed to link)](#⑦-failed-to-define-class-javaxservletjspjstltlvpermittedtaglibstlv-noclassdeffounderror-failed-to-link)
- [⑧ IJ030040: 開いたままの Statement を閉じた (自分で後片付けしてください)](#⑧-ij030040-開いたままの-statement-を閉じた-自分で後片付けしてください)
- [⑨ Resolved [HttpRequestMethodNotSupportedException: Request method 'POST' is not supported]](#⑨-resolved-httprequestmethodnotsupportedexception-request-method-post-is-not-supported)
- [⑩ IJ030027: 有効でない接続を破棄する (Ping failed: java.lang.reflect.InvocationTargetException)](#⑩-ij030027-有効でない接続を破棄する-ping-failed-javalangreflectinvocationtargetexception)
- [⑪ IJ000621: 検証できなかった接続を破棄する (プール側の記録)](#⑪-ij000621-検証できなかった接続を破棄する-プール側の記録)
- [⑫ IJ030042: 開いたままの ResultSet を閉じた (自分で後片付けしてください)](#⑫-ij030042-開いたままの-resultset-を閉じた-自分で後片付けしてください)
- [⑬ IJ000615: 使用中の接続をプールで破棄した (停止時)](#⑬-ij000615-使用中の接続をプールで破棄した-停止時)
- [①深掘り: 追加質問と ExtraSLB 実装レビュー](#①深掘り-追加質問と-extraslb-実装レビュー)
- [実装](#実装)
- [検証結果](#検証結果)
- [年表](#年表)
- [用語集](#用語集)
- [前提・版](#前提版)
- [出典](#出典)

## 対象環境と読み方

| 項目 | 内容 |
|---|---|
| 実行基盤 | Amazon ECS (Fargate を主対象)。ALB で TLS を終端し、コンテナは 8080 (HTTP) で受ける |
| コンテナ | UBI 9.8 + Red Hat build of OpenJDK 21 + JBoss EAP 8.1 (standalone, JBOSS_HOME=/opt/jboss-eap) |
| 設定方式 | 各サブシステムは jboss-cli (.cli) で設定し、イメージのビルド時に embed-server で standalone.xml へ焼き込む。環境ごとの値は ${env.変数名:既定値} 式で ECS タスク定義から渡す |
| DB | Aurora MySQL 8.4 互換 (ログの productVersion=8.4.7)。XA データソース MIF02JA_JDS (java:/jdbc/MIF02JA_JDS) |
| アプリ | iwinmichl.war (Spring MVC / JSP・JSTL / Apache CXF クライアント / jboss-deployment-structure.xml あり) |
| 関連プロジェクト | Container_ExtraSLB_JVM_https_outbounds (自己署名ルート CA を信頼するアウトバウンド HTTPS 実装) |

| 危険度 | 意味 |
|---|---|
| A | 障害 (要求の失敗・処理の中断) に直結しうる。早急に対処する |
| B | 今は動くが、設定やコードの誤りを示している / 将来の更新で壊れうる。計画的に対処する |
| C | それ自体は無害。ただしログを汚し、本当に見るべき警告を埋もれさせる。原因を理解したうえで整理する |

- 各警告のシートは「ひとことで (小学生向け)」→「メッセージの正体」→「動作原理」→「動作イメージ」→「歴史・背景」→「この環境での原因と切り分け」→「影響度」→「対処方針の比較」→「実装」→「確認方法」→「検証結果」→「出典」の順に並んでいます。
- 小学生向けの説明は、たとえ話と「たとえ ⇔ 本当の仕組み」の対応表のセットです。技術者向けの説明は、WildFly / IronJacamar / Spring などのソースコード (EAP 8.1 の上流版) で確認した事実に基づいています。
- 実装はすべて implementation/ フォルダに実ファイルとして置いてあり、「実装コード」シートと md に全文を載せています。
- 「検証結果」は、UBI 9.8 + OpenJDK 21 + WildFly 35.0.1 (EAP 8.1 の上流) + MySQL 8.4 のコンテナで、修正前に 13 件すべてを再現し、修正後に消えることを実際に動かして確かめた記録です。

## 一覧

| No | 警告 | 出す場所 (ロガー) | いつ出る | ひとことで | この環境での本当の原因 | 危険度 | 主な対処 | 対処の場所 | 検証 (修正前→修正後) |
|---|---|---|---|---|---|---|---|---|---|
| ① | WFLYELY00023 | org.wildfly.extension.elytron | ブート時 | 使っていない HTTPS 受付用の鍵の金庫 (application.keystore) が無いので空で代用した | EAP 標準のインバウンド HTTPS (8443) 用 applicationKS。自前の p12 の置き場所や -D 引数とは無関係 | C | 未使用の 8443 一式 (https-listener→SSC→KM→KS) を jboss-cli で削除。自前トラストストアは required=true | jboss-cli | 1 → 0 |
| ② | WFLYSRV0058 | org.jboss.as.server.deployment | デプロイ時 | 荷物リストに書いた段ボール (testClasses) が荷物に入っていなかった | jboss-deployment-structure.xml に WAR に無い resource-root (WEB-INF/classes/testClasses) が残っている | C | 記述を削除。ビルド時に scan-war.py で検査 | WAR | 1 → 0 |
| ③ | WFLYSRV0018 | org.jboss.as.dependency.private | デプロイ時 | 図書館の職員専用の棚 (private モジュール) の本を借りた | jboss-deployment-structure.xml の org.apache.cxf.impl 依存 (+ spring-core の MANIFEST が宣言する org.jboss.vfs) | B | 依存を削除し、SOAP のタイムアウトは標準プロパティ jakarta.xml.ws.client.*Timeout で設定。org.jboss.vfs は 1 行だけ絞って抑止 | WAR / jboss-cli | 2 → 0 |
| ④ | WFLYEE0007 | org.jboss.as.ee | デプロイ時 | Spring の見張り番 (AsyncListener) に道具を配ろうとしたが、作り方が特殊で作れなかった | Weld 無効の WAR で、Spring の AsyncListener 実装 6 クラスに引数なしコンストラクタが無い (WFLYEE0048) | C | DEBUG で WFLYEE0048 を確認したうえで、Spring のクラス分だけをログフィルタで抑止 (動作影響なし) | jboss-cli | 8 → 0 |
| ⑤ | WFLYWELD0013 | org.jboss.weld.deployer | デプロイ時 | CDI のシールは見つかったが、名簿 (Bean アーカイブ) を作るきっかけが無い | WAR に同梱された jakarta.transaction-api の TransactionScoped に @NormalScope が付いている (+ jsf 除外で Weld 無効) | B | EE API jar を provided にして同梱をやめる。CDI 不使用なので weld も jsf と一緒に除外 | WAR | 1 → 0 |
| ⑥ | WFLYSRV0274 | org.jboss.as.server.deployment | デプロイ時 (最後) | 受け取り拒否リストに書いた相手から、そもそも荷物が来る予定がなかった (空振り) | org.jboss.logmanager.log4j2 はデプロイの依存に直接入らないモジュール。除外しても何も起きていない | B | 除外を削除して EAP のログに乗せる (推奨)。自前 Log4j 2 を使うなら除外すべきは org.apache.logging.log4j.api | WAR / jboss-cli | 1 → 0 |
| ⑦ | Failed to define class javax.* | org.jboss.modules.define | デプロイ時 | 昔の教科書 (javax) の付録が、新しい教科書 (jakarta) しかない学校で読めなかった | WAR に Java EE 時代の jstl-1.2.jar が残り、その TLD の validator クラスを読み込もうとして失敗 | B | javax 版 JSTL を削除し、EAP 提供の Jakarta JSTL 3.0 を使う。enforcer で javax.* の混入を止める | WAR | 4 → 0 |
| ⑧ | IJ030040 | org.jboss.jca.adapters.jdbc.WrappedConnection | リクエスト処理中 | 借りた本の中のメモ用紙 (Statement) を片付けずに本を返した | アプリが Statement を閉じずに Connection だけ閉じている (track-statements=true で検出) | B | try-with-resources / JdbcTemplate で必ず閉じる。本番は修正後に NOWARN | WAR | 1 → 0 |
| ⑨ | Resolved [HttpRequestMethodNotSupportedException] | org.springframework.web.servlet.mvc.support.DefaultHandlerExceptionResolver | リクエスト処理中 | 「見るだけ」の窓口に「置かせて」と来た人を断った | GET 専用 URL に POST が届いた (送信元・URL はログに出ない) | B | 4xx/5xx の JSON アクセスログ (jboss-cli) と 405 詳細ログ (@ControllerAdvice) で送信元を特定して直す | jboss-cli / WAR | 1 → 0 |
| ⑩ | IJ030027 | org.jboss.jca.adapters.jdbc.xa.XAManagedConnectionFactory | リクエスト処理中 (貸出前の検証) | 長く止めていたタクシーのエンジンがかからなかったので廃車にした | プールで待機中の接続が DB 側 (wait_timeout) や経路のアイドル切断で既に切られていた | B | idle-timeout-minutes を切断時間より短く。exception-sorter 追加、TCP keepalive。原因は Caused by で判別 | jboss-cli / ECS | 1 → 0 |
| ⑪ | IJ000621 | org.jboss.jca.core.connectionmanager.pool.strategy.OnePool | リクエスト処理中 (貸出前の検証) | 点検に通らなかった車を配車係が廃車にして、別の車を出した | ⑩ と同じ接続のプール側の記録 (validate-on-match=true の貸出時検証で検出) | B | ⑩ と同じ。ログ時刻 - lastReturned で放置時間を測って idle-timeout を決める | jboss-cli / ECS | 1 → 0 |
| ⑫ | IJ030042 | org.jboss.jca.adapters.jdbc.WrappedConnection | リクエスト処理中 | メモ用紙に書いた答えのプリント (ResultSet) も出しっぱなしだった | アプリが ResultSet を閉じていない (⑧ と同じ箇所のことが多い) | B | ⑧ と同じ。analyze-ij-log.py で作った場所を特定 | WAR | 1 → 0 |
| ⑬ | IJ000615 | org.jboss.jca.core.connectionmanager.pool.strategy.OnePool | 停止時 (SIGTERM 等) | 閉店のとき、お客さんがレジを使っている途中なのにレジを片付けた | SIGTERM 時のサスペンド待ち時間が既定の 0 秒。処理中の要求ごと DB 接続が破棄された | A | org.wildfly.sigterm.suspend.timeout (jboss-cli) + LAUNCH_JBOSS_IN_BACKGROUND + ECS stopTimeout を一貫させる | jboss-cli / ECS | 1 → 0 |

## 基礎知識

### 1. JBoss EAP ってなに？

> **【小学生にもわかる説明】**  
> JBoss EAP は「Java で作ったお店 (Web アプリ) を入居させる大きなビル」です。ビルには、受付係・警備室・図書館・タクシー会社・日記係など、たくさんの係 (サブシステム) がいて、入居したお店のために働きます。係たちは毎日「日記 (ログ)」を書いていて、気になることがあると「WARN (注意)」として書きます。今回の 13 件は、この日記に書かれた「注意」です。

| たとえ | 本当の仕組み |
|---|---|
| ビル | JBoss EAP 8.1 (Jakarta EE 10 準拠のアプリケーションサーバ。上流は WildFly / WildFly Core) |
| 入居するお店 | WAR ファイル (iwinmichl.war) |
| 係 (部署) | サブシステム: elytron (セキュリティ)、undertow (Web)、datasources/jca (DB 接続)、logging、weld (CDI)、ee、webservices、transactions など |
| ビルの設計図 | standalone.xml (各サブシステムの設定。jboss-cli で書き換える) |
| 日記 | サーバログ (コンソール = CloudWatch Logs、server.log) |

JBoss EAP 8.1 は 2025-09-02 に一般提供 (GA) となった Jakarta EE 10 のアプリケーションサーバです。上流のオープンソース版は WildFly で、EAP 8.1 は WildFly Core 27.1 系をベースにしています (Red Hat のセキュリティアドバイザリで WildFly Core 27.1.x の更新が確認できる)。2026-10 時点の最新は 8.1.8 (Update 8, 2026-09-22) です。OpenJDK 21 / RHEL 9 の組み合わせがサポートされ、OpenJDK 17 の OpenShift 用イメージは 8.1 で非推奨 (8.2 で削除予定) になっています。

### 2. JBoss Modules (図書館と貸出カード)

> **【小学生にもわかる説明】**  
> ビルの中には大きな図書館 (JBoss Modules) があり、本 (ライブラリ) は棚 (モジュール) ごとに分けて置かれています。お店は「貸出カード」に書いた棚の本しか読めません。図書館は気をきかせて、よく使う本の棚を最初からカードに書いてくれます (暗黙の依存)。お店が自分で棚を書き足すこともできます (明示の依存)。棚には「どなたでもどうぞ (public)」と「職員専用 (private)」の札が付いています。

| 用語 | 意味 |
|---|---|
| モジュール | $JBOSS_HOME/modules/... の module.xml で定義された部品 (例: org.apache.cxf, org.apache.cxf.impl) |
| デプロイのモジュール | WAR ごとに deployment.iwinmichl.war という名前のモジュールが作られる。WEB-INF/classes と WEB-INF/lib/*.jar がその中身 (リソースルート) |
| 暗黙の依存 | サブシステムが自動で付ける依存 (logging は org.apache.logging.log4j.api 等、webservices は JAX-WS 一式 等) |
| 明示の依存 | jboss-deployment-structure.xml の <dependencies>、MANIFEST.MF の Dependencies: ヘッダ (WEB-INF/lib の jar の MANIFEST も対象) |
| 除外 | jboss-deployment-structure.xml の <exclusions> / <exclude-subsystems> |
| jboss.api | module.xml の <property name="jboss.api" value="private"/> 等。public / private / unsupported / deprecated |
| 読み込みの優先順位 | 暗黙の依存 → 明示の依存 → WAR 自身 (WEB-INF/classes, lib) → 他デプロイ。同じクラスがあればサーバ側が先に見つかる |

> **【注意・補足】**  
> JBoss Modules は JBoss AS 7 (2011) で導入された「モジュール単位で見える範囲を区切る」クラスローダです。それ以前 (AS 5/6) は階層型のクラスローダで、アプリとサーバのライブラリが混ざって衝突しやすかったため、見える範囲を明示的に宣言する方式に変わりました。②③⑥⑦ はこの仕組みに関係する警告です。

### 3. デプロイの流れ (引っ越しの手順)

> **【小学生にもわかる説明】**  
> お店がビルに入居するときは、決まった順番で作業が進みます。荷物を開ける → 中身を調べる → 必要な本の貸出カードを作る → 部屋を整える → 道具を配置する → 最後に片付け。それぞれの作業の途中で、係が気づいたことを日記に書きます。

**図: デプロイのフェーズと警告**

```text
デプロイのフェーズ (Phase) と、そこで出る警告
 STRUCTURE ─ jboss-deployment-structure.xml を読む ............ ② WFLYSRV0058 (リソースルートが無い)
 PARSE     ─ web.xml / TLD / アノテーション索引 (Jandex) を作る
 DEPENDENCIES ─ 暗黙・明示の依存を組み立てる (logging, webservices, weld ...)
 CONFIGURE_MODULE ─ モジュールを作る .............................. ③ WFLYSRV0018 (private モジュール)
 POST_MODULE ─ CDI / JSF の判定 ................................... ⑤ WFLYWELD0013
 INSTALL   ─ EE コンポーネント (サーブレット・リスナ等) を構成 ...... ④ WFLYEE0007 / ⑦ Failed to define class
 CLEANUP   ─ 後片付け・設定の検算 .................................. ⑥ WFLYSRV0274 (除外の空振り)
```

① はデプロイではなく「サーバのブート時 (サブシステムの起動)」、⑧〜⑫ は「リクエスト処理中」、⑬ は「停止時」に出ます。

### 4. Elytron (警備室: 身分証と信頼リスト)

> **【小学生にもわかる説明】**  
> 警備室 (Elytron) は 2 種類の大事なものを管理しています。ひとつは「自分の身分証と、それを証明する秘密のハンコ」(キーストア)。お客さんに「本物のビルです」と見せるのに使います。もうひとつは「信頼できる発行所の名簿」(トラストストア)。よそのビルを訪ねたとき、相手の身分証が本物かを確かめるのに使います。① の警告は前者 (自分の身分証の金庫) の話で、ルート CA を入れた p12 は後者 (名簿) の話です。

| Elytron のリソース | 役割 | 今回の例 |
|---|---|---|
| key-store | 鍵・証明書の入れ物 (ファイル) | applicationKS (application.keystore) / extraslb-trust-store (p12) |
| key-manager | 「自分の証明書」を出す係 (サーバ側 TLS) | applicationKM (自己署名の自動生成機能付き) |
| trust-manager | 「相手の証明書」を検証する係 (クライアント側 TLS) | extraslb-trust-manager |
| server-ssl-context | 受け付ける側の TLS 設定 | applicationSSC (https-listener 8443 が使う) |
| client-ssl-context | 接続しに行く側の TLS 設定 | extraslb-client-ssl-context |
| default-ssl-context | JVM 既定の SSLContext を差し替える | SSLContext.getDefault() が Elytron の DelegatingSSLContext になる |

> **【注意・補足】**  
> -Djavax.net.ssl.trustStore / keyStore は JDK (JSSE) の設定で、Elytron の key-store リソースはこれを読みません。2 つは別の仕組みです (① で実測)。

### 5. IronJacamar (タクシー会社: DB 接続のプール)

> **【小学生にもわかる説明】**  
> DB と話すための回線 (接続) を毎回つなぐのは時間がかかるので、タクシー会社 (接続プール) が車 (接続) を何台か待機させておき、お客さん (リクエスト) に貸し出します。返してもらった車は駐車場で待機します。長く駐車した車はバッテリーが上がっていることがあるので、貸す前に点検 (検証) します。

| 用語 | 意味 | 関係する警告 |
|---|---|---|
| プール | 接続を使い回す仕組み (IronJacamar)。データソース MIF02JA_JDS ごとに 1 つ | ⑩⑪⑬ |
| validate-on-match | 貸し出す直前に接続を検証する (ping)。失敗した接続は捨てる | ⑩⑪ |
| background-validation | 別スレッドで定期的に検証する (validate-on-match と併用しない) | ⑩ |
| valid-connection-checker | 検証方法 (MySQL なら MySQLValidConnectionChecker = ping) | ⑩ |
| exception-sorter | 使用中に起きた例外が「接続が壊れた」ものか判定し、壊れた接続をプールに戻さない | ⑩ |
| idle-timeout-minutes | 待機がこの時間を超えた接続を捨てる (既定 30 分。半分の間隔で点検) | ⑩⑪ |
| track-statements | Statement / ResultSet の閉じ忘れを追跡 (FALSE / TRUE / NOWARN。既定 NOWARN) | ⑧⑫ |
| CCM (cached-connection-manager) | 要求の終わりに閉じ忘れた接続を見つける | ⑬ (補助) |

### 6. ECS タスクの起動と停止 (お店の開店と閉店)

> **【小学生にもわかる説明】**  
> 新しいお店 (タスク) が開店して準備ができると、案内係 (ALB) がお客さんを案内し始めます。閉店するときは、まず案内係が新しいお客さんを案内しなくなり (登録解除)、少し待ってから「閉店してください」の合図 (SIGTERM) が届きます。決められた時間 (stopTimeout) が過ぎても閉まらないと、強制的に電気を落とされます (SIGKILL)。

**図: ECS の停止シーケンスと EAP**

```text
ECS のタスク停止 (ローリングデプロイ・スケールイン)
  ALB: ターゲットの登録解除 → 新規リクエストを送らない (deregistration delay の間は既存接続を待つ。既定 300 秒)
    ↓
  ECS: コンテナの PID 1 に SIGTERM
    ↓  standalone.sh が LAUNCH_JBOSS_IN_BACKGROUND=true なら JVM へ中継 (未設定なら JVM に届かない)
  JVM: シャットダウンフック → サスペンド (新規要求を 503 で断り、処理中の要求を待つ)
         待ち時間 = org.wildfly.sigterm.suspend.timeout 秒 (既定 0 = 待たない)  ← ⑬
       → サービス停止 (データソースのプールを閉じる。使用中の接続があれば IJ000615)
    ↓
  ECS: stopTimeout (既定 30 秒 / Fargate 最大 120 秒) を過ぎたら SIGKILL
```

### 7. ログ 1 行の読み方

**例**

```text
05:33:57,567 WARN  [org.jboss.jca.core.connectionmanager.pool.strategy.OnePool] (ServerService Thread Pool -- 119) IJ000615: Destroying active connection in pool: MIF02JA_JDS (...)
```

| 部分 | 意味 |
|---|---|
| 05:33:57,567 | 時刻 (コンテナの TZ。既定は UTC) |
| WARN | レベル (ERROR > WARN > INFO > DEBUG > TRACE) |
| [org.jboss.jca...OnePool] | ロガーカテゴリ (だれが書いたか)。logging サブシステムで、このカテゴリごとにレベルやフィルタを設定できる |
| (ServerService Thread Pool -- 119) | スレッド名。default task-N = HTTP 要求の処理、MSC service thread = サービスの起動・停止 |
| IJ000615 | メッセージ ID。接頭辞で出どころが分かる: WFLYELY=Elytron、WFLYSRV=サーバ本体、WFLYEE=EE、WFLYWELD=Weld、IJ=IronJacamar。ID が無いものは JBoss Modules (⑦) や Spring (⑨) など |

> **【注意・補足】**  
> メッセージ ID の接頭辞 (WFLY...) は WildFly 9 (2015) で JBAS から変わったものです。日本語ロケールでは本文が翻訳されますが ID は同じなので、検索や集計は ID で行います (check-warnings.sh)。

### 8. jboss-cli で設定する理由とやり方

> **【小学生にもわかる説明】**  
> ビルの設計図 (standalone.xml) を手で書き換えると、書き間違いに気づきにくく、何をどう変えたかも残りません。jboss-cli は「設計図を正しい手順で書き換える専用の道具」で、書き換えの手順書 (.cli ファイル) がそのまま記録になります。

- イメージのビルド時に embed-server (サーバを外部公開せずに管理用だけで起動するモード) で .cli を適用し、standalone.xml に焼き込む
- 環境ごとに変わる値は ${env.DB_HOST} のような式で書き、起動時に ECS タスク定義の environment / secrets から解決させる
- if (outcome != success) of ...:read-resource で「無ければ追加」にして、何度流しても同じ結果になるようにする (冪等)
- 最後に read-resource で結果を表示して確認する (90-verify.cli)。属性名は EAP 8.1 / WildFly 35 のモデルで実在を確認したものだけを使う
- 起動時に embed-server を動かさない (動かすと設定ブートが 2 回になり、standalone_xml_history の扱いで ECS だけ失敗する事例がある)

## ① WFLYELY00023: keystore ファイル application.keystore が存在しない (空で代用した)

**危険度 C**

**ユーザー環境のログ (原文)**

```text
WFLYELY00023: keystoreファイル /opt/jboss-eap/standalone/configuration/application.keystoreは存在しない。空白を使用しました。
```

### ひとことで (小学生向け)

> **【小学生にもわかる説明】**  
> EAP というビルの設計図 (standalone.xml) には、最初から「HTTPS のお客さん用の受付 (8443 番の窓口)」と、そこで見せる「ビルの身分証と秘密のハンコを入れる金庫 (application.keystore)」が書いてあります。
> でも引っ越してきたとき、金庫は実際には置かれていません。最初の HTTPS のお客さんが来たときに、警備室がその場で身分証を作って金庫に入れる約束になっているからです。
> 警備室 (Elytron) は毎朝の点検で「設計図にある金庫が見当たらないので、とりあえず空っぽの箱を置きます」と日記に書きます。これがこの警告です。
> あなたが別の部屋に置いた「信頼できる発行所の名簿 (ルート CA を入れた p12)」とは、まったく別の物の話です。

| たとえ | 本当の仕組み |
|---|---|
| ビルの設計図 | standalone.xml の elytron サブシステム |
| 身分証とハンコの金庫 | key-store=applicationKS → standalone/configuration/application.keystore (サーバ証明書と秘密鍵) |
| HTTPS の受付 (8443) | Undertow の https-listener=https (ssl-context=applicationSSC) |
| その場で身分証を作る約束 | key-manager=applicationKM の generate-self-signed-certificate-host=localhost (初回接続時に自己署名証明書を生成) |
| 毎朝の点検 | ブート時に key-store サービスが起動する (誰も使っていなくても起動する) |
| 空っぽの箱で代用 | 空のキーストアで起動を続ける (Used blank) |
| 信頼できる発行所の名簿 | トラストストア (extraslb-truststore.p12)。相手の証明書を確かめる用。今回の警告とは無関係 |

### メッセージの正体

| 項目 | 内容 |
|---|---|
| 英語原文 | WFLYELY00023: KeyStore file '%s' does not exist. Used blank. |
| ID / レベル | WFLYELY00023 / WARN |
| ロガー | org.wildfly.extension.elytron |
| 出す場所 | org.wildfly.extension.elytron.KeyStoreService#start (ElytronSubsystemMessages#keyStoreFileNotExistsButIgnored) |
| タイミング | サーバのブート時 (MSC service thread)。ビルド時の embed-server でも同じく出る |
| 一緒に出るもの | WFLYELY01084: KeyStore ... not found, it will be auto-generated on first use with a self-signed certificate for host localhost |
| 兄弟 | WFLYELY00022 (required=true でファイルが無い → 起動失敗) / WFLYELY01085 (自己署名を生成した) / WFLYELY00024 (証明書の期限切れ) |

### 動作原理

- EAP 8.1 の既定構成 (Galleon の feature group「elytron-app」) は、次の 3 つを Elytron に作る: key-store=applicationKS (path=application.keystore, relative-to=jboss.server.config.dir, type=JKS, パスワード password)、key-manager=applicationKM (generate-self-signed-certificate-host=localhost)、server-ssl-context=applicationSSC。Undertow の https-listener=https (8443) が applicationSSC を参照する。
- KeyStoreDefinition は key-store ごとに KeyStoreService を Mode.ACTIVE でインストールする。このため、https-listener が使っているかどうかに関係なく、ブート時に必ず start() が呼ばれる。
- start() は path を relative-to で解決し、ファイルが無いとき required (既定 false) を見る。true なら WFLYELY00022 で StartException、false なら WFLYELY00023 を WARN で出して空の KeyStore を読み込んだ状態で続行する。
- applicationKM は generate-self-signed-certificate-host を持つので、ファイルが無いと WFLYELY01084 (予告) を出す。最初の HTTPS ハンドシェイクの時点で RSA 2048 / SHA256withRSA / 有効 10 年 / CN=localhost / 別名 server の自己署名証明書を作り、application.keystore に保存する (WFLYELY01085)。
- コンテナは毎回イメージの初期状態から起動するので、ファイルは毎回無い → 毎回この警告が出る。readonlyRootFilesystem=true だと生成した鍵の保存にも失敗する。

### 動作イメージ

**図: インバウンド用の鍵 (警告の対象) と、アウトバウンド用の信頼リスト (ExtraSLB の実装) は別の経路**

```text
[ブート]
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
  アプリ → Apache CXF / 自前の SSLContext → JSSE 既定の TrustManagerFactory → -Djavax.net.ssl.trustStore (同じ p12)
```

### 歴史・背景・必要になった経緯

- 2016-06 WFCORE-1576: レガシーのセキュリティレルム (ApplicationRealm) に「初回利用時に自己署名証明書を自動生成」が入った。インストール直後から HTTPS を試せるように (SSL out of the box) するための機能で、このとき「application.keystore は同梱せず、必要になったら作る」設計になった。
- 2017 WildFly 11 / EAP 7.1: 新しいセキュリティ基盤 Elytron が導入される。
- 2020-11 WFCORE-5095 (EAP7-1545): Elytron にも同じ自動生成 (generate-self-signed-certificate-host) が入り、既定構成に applicationKS / applicationKM / applicationSSC が加わった。
- 2021 WildFly 25: レガシーセキュリティが削除され、2024 年の EAP 8.0 で Elytron に一本化。既定の https-listener は applicationSSC を参照する。
- 結果として「ファイルは同梱しない + key-store サービスは常に起動する」組み合わせになり、毎回まっさらな状態で起動するコンテナでは、ブートのたびにこの警告が出るようになった。

> **【注意・補足】**  
> 「起動のたびに出る」こと自体は、設計どおりの挙動です。サーバ単体で使い続ける環境では、初回の HTTPS 接続でファイルができるので 2 回目以降は出ません。コンテナではそれが毎回リセットされます。

### この環境での原因と切り分け

原因は EAP 標準の applicationKS です。警告のパスが application.keystore であることがその証拠で、Container_ExtraSLB_JVM_https_outbounds の実装 (ルート CA を入れた p12 を /opt/app/security に置き、standalone.sh に -Djavax.net.ssl.trustStore* を渡す) とは関係ありません。下の実測で確かめました。

| 実験 | 条件 | 結果 |
|---|---|---|
| E1 | 現行 (p12 は /opt/app/security、-D で trustStore を渡す) | application.keystore について WFLYELY00023 と WFLYELY01084 が 1 件ずつ。アウトバウンド HTTPS は自己署名 CA 宛・パブリック CA 宛とも 3 種類のクライアントで成功 |
| E2 | Q2 の確認: -Djavax.net.ssl.keyStore=<p12> も渡す | WFLYELY00023 は変わらず出る (Elytron の key-store は -D を読まない) |
| E3 | 自前 p12 のパスを誤る (現行の required=false) | WFLYELY00023 が「そのパス」でも出て、サーバは正常起動 (WFLYSRV0025)。しかし既定 SSLContext 経由の HTTPS はパブリック CA 宛も含めて全滅 (trustAnchors parameter must be non-empty) |
| E4 | 同じ誤りで required=true | WFLYELY00022 でサービス起動失敗 → started (with errors) (ERROR)。entrypoint の事前チェックなら起動前に FATAL で止まる |

**確認コマンド**

```bash
# 実機での確認 (起動中のコンテナで)
/opt/jboss-eap/bin/jboss-cli.sh -c '/subsystem=elytron/key-store=applicationKS:read-resource'
/opt/jboss-eap/bin/jboss-cli.sh -c '/subsystem=undertow/server=default-server:read-children-names(child-type=https-listener)'
# ALB のターゲットグループが HTTP:8080 なら 8443 は使われていない
aws elbv2 describe-target-groups --names <tg-name> --query 'TargetGroups[].{p:Protocol,port:Port}'
```

### 影響度と放置した場合のリスク

危険度 C (無害だが整理すべき)。アウトバウンド HTTPS には影響しません (E1 で実測)。ただし次の点は放置しない方がよいです。

- 使っていない 8443 が待ち受けている (E1: 8443 に接続すると CN=localhost の自己署名証明書が返る)。不要な口は攻撃面になる。
- readonlyRootFilesystem=true にすると、初回接続時の自己署名証明書の保存が失敗する。
- 毎回の WARN が、本当に見るべき警告 (証明書の期限切れ WFLYELY00024 など) を埋もれさせる。

### 対処方針の比較

| 方式 | やること | 警告 | 8443 | イメージ内の秘密鍵 | 評価 |
|---|---|---|---|---|---|
| (a) 削除 remove ★推奨 | jboss-cli で https-listener → applicationSSC → applicationKM → applicationKS の順に削除 | 消える (E6) | 待ち受けなし | なし | ◎ ALB 終端・8080 受信の本構成に最適 |
| (b) 事前生成 provision (ExtraSLB 現行) | ビルド時に keytool で application.keystore を作って同梱 | 消える (E5) | CN=localhost で待ち受け | 既知パスワードの鍵を全タスクで共有 | ○ 動くが、不要な鍵と口が残る |
| (c) 正式な鍵ストア dedicated | 起動時に渡す鍵ストアに差し替え (required=true、自動生成を止める) | 消える (E6) | 正式な証明書で待ち受け | なし (実行時に注入) | ○ ALB→タスク間も暗号化したい場合 |
| (d) ログ抑止 | ロガーのレベルやフィルタで隠す | 見えなくなるだけ | そのまま | - | × 同じカテゴリの重要な警告まで隠れる |
| (e) 何もしない keep | - | 出続ける | 自己署名を遅延生成 | 実行時に生成 | △ |

> **【注意・補足】**  
> ALB はターゲットの証明書を検証しないため、ALB → タスク間を暗号化するだけなら自己署名でも通信できます。その場合でも鍵はイメージに焼かず、(c) のように実行時に渡すのが安全です。Q1〜Q3 の詳しい回答と、ExtraSLB の実装の評価は「①深掘り」シートにまとめています。

### 実装 (jboss-cli)

**インバウンド HTTPS 一式の削除 (参照する側から順に)**

```text
# 11-inbound-https-remove.cli (抜粋。全文は「実装コード」シート)
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
end-if
```

**自前トラストストアは required=true (パス誤りを起動時に必ず見えるようにする)**

```text
# 10-elytron-outbound-truststore.cli (TRUST_MODE=elytron の場合。抜粋)
/subsystem=elytron/key-store=extraslb-trust-store:write-attribute(name=required, value=true)
```

TRUST_MODE=system (推奨) の場合は、CA を UBI のシステムトラストストアへ入れる (install-ca-anchors.sh) ので、Elytron のトラストストア設定も -D 引数も不要になります。詳しくは「①深掘り」。

### 確認方法

```bash
/opt/jboss-eap/bin/jboss-cli.sh -c '/subsystem=elytron:read-children-names(child-type=key-store)'
# → applicationKS が無いこと (remove モード)
/opt/jboss-eap/bin/jboss-cli.sh -c '/subsystem=undertow/server=default-server:read-children-names(child-type=https-listener)'
# → [] (https-listener が無いこと)
grep -c WFLYELY00023 server.log   # → 0
```

### 検証結果 (実測)

| 集計項目 (check-warnings.sh) | S0 修正前 | S1 修正後 (system/remove) | S1e 修正後 (elytron) | S1d 修正後 (dedicated) |
|---|---|---|---|---|
| WFLYELY00023 keystore file does not exist | 1 | 0 | 0 | 0 |
| WFLYELY01084 self-signed will be generated | 1 | 0 | 0 | 0 |
| WFLYELY00022 does not exist and required | 0 | 0 | 0 | 0 |

S0 = 修正前を再現した状態、S1 系 = 本書の実装を適用した状態。シナリオの詳細と全ログは「検証結果」シート (md では「検証結果」章)。

### 出典

- [Configuring SSL/TLS in JBoss EAP 8.1](https://docs.redhat.com/en/documentation/red_hat_jboss_enterprise_application_platform/8.1/html-single/configuring_ssltls_in_jboss_eap/index)
- [WFCORE-5095 Elytron の自己署名証明書の自動生成 (設計提案)](https://docs.wildfly.org/wildfly-proposals/elytron/WFCORE-5095-automatic-self-signed-certificate-generation.html)
- [KeyStoreService (WFLYELY00022/00023/00024)](https://github.com/wildfly/wildfly-core/blob/27.0.1.Final/elytron/src/main/java/org/wildfly/extension/elytron/KeyStoreService.java)
- [elytron-app feature group (applicationKS/KM/SSC の既定構成)](https://github.com/wildfly/wildfly-core/blob/27.0.1.Final/core-feature-pack/galleon-common/src/main/resources/feature_groups/elytron-app.xml)
- [ALB はターゲットの証明書を検証しない (re:Post)](https://www.repost.aws/questions/QU97HoG_YMQxO1LXTj76ui-w/traffic-between-alb-and-backend-ec2-instance-needs-to-be-encrypted)

## ② WFLYSRV0058: jboss-deployment-structure.xml で追加したリソースルートが存在しない

**危険度 C**

**ユーザー環境のログ (原文)**

```text
WFLYSRV0058: jboss-deployment-structure.xmlで追加されたリソースルート/content/iwinmichl.war/WEB-INF/classes/testClassesは存在しません。
```

### ひとことで (小学生向け)

> **【小学生にもわかる説明】**  
> お店がビルに引っ越すとき、「荷物リスト (jboss-deployment-structure.xml)」に「testClasses という段ボールも本棚に並べてね」と書いてありました。
> ところが、その段ボールは荷物の中に入っていませんでした。引っ越し係は「リストにある段ボールが見つからないので、飛ばします」と日記に書きました。お店はちゃんと開店できますが、リストが古いままだということです。

| たとえ | 本当の仕組み |
|---|---|
| 荷物リスト | WEB-INF/jboss-deployment-structure.xml |
| 本棚に並べる段ボール | <resources><resource-root path="..."/> (追加のリソースルート = クラスを探す場所) |
| 荷物 | iwinmichl.war の中身 (サーバ内では VFS の /content/iwinmichl.war/... に見える) |
| 飛ばす | その resource-root を登録しない (デプロイは続行) |

### メッセージの正体

| 項目 | 内容 |
|---|---|
| 英語原文 | WFLYSRV0058: Additional resource root %s added via jboss-deployment-structure.xml does not exist |
| ID / レベル | WFLYSRV0058 / WARN |
| ロガー | org.jboss.as.server.deployment |
| 出す場所 | DeploymentStructureDescriptorParser (ServerLogger#additionalResourceRootDoesNotExist) |
| タイミング | デプロイの STRUCTURE フェーズ (記述子を読んだ直後) |

### 動作原理

- デプロイされた WAR は、JBoss Modules の 1 モジュール (deployment.iwinmichl.war) になり、WEB-INF/classes と WEB-INF/lib/*.jar が「リソースルート (クラスやリソースを探す場所)」として登録される。中身は VFS で /content/iwinmichl.war/... にマウントされる (警告に出ている /content/... はこの仮想パス)。
- jboss-deployment-structure.xml の <resources><resource-root path="X"/> は、標準以外の場所を追加のリソースルートにする指定。path は WAR のルートからの相対パス。
- パーサは X が存在するかを確かめ、無ければ WFLYSRV0058 を出して登録しない。あれば RESOURCE_ROOTS に加え、アノテーション索引 (Jandex) を作り、モジュールのルートとして扱う。
- もし WEB-INF/classes/testClasses が実在していたら、その下の com/example/Foo.class が com.example.Foo として読み込めるようになる (パッケージの起点がずれる)。テスト用クラスが本番で読み込まれる危険がある。

### 動作イメージ

```text
[STRUCTURE フェーズ]
 WAR を VFS にマウント (/content/iwinmichl.war)
  ├ 標準のリソースルート: WEB-INF/classes, WEB-INF/lib/*.jar
  └ jboss-deployment-structure.xml の <resource-root path="WEB-INF/classes/testClasses"/>
        ├ 実在する → 追加のリソースルートとして登録・索引化
        └ 実在しない → WFLYSRV0058 (WARN) を出して読み飛ばす ★今回 → デプロイは続行
```

### 歴史・背景・必要になった経緯

- JBoss AS 5/6 (〜2010) は VFS と階層型クラスローダで、アプリとサーバのライブラリが混ざりやすく、jboss-classloading.xml などで調整していた。
- 2011 年の JBoss AS 7.0 で JBoss Modules (モジュール単位で見える範囲を区切る方式) に切り替わり、デプロイごとの依存・除外・追加リソースルートを宣言する jboss-deployment-structure.xml が導入された。
- WildFly 9 (2015) でメッセージ ID が JBAS から WFLYSRV 等に変わり、現在の形になった。

### この環境での原因と切り分け

jboss-deployment-structure.xml に、WAR に存在しない WEB-INF/classes/testClasses が残っています。開発時のテスト用設定の名残か、別プロジェクトからの複写と考えられます。本番 WAR にテストクラスが入っていないこと自体は正しい状態です。

**検証用 WAR での実行結果**

```text
# WAR の中身と記述子を突き合わせる (implementation/tools/scan-war.py)
python scan-war.py iwinmichl.war
## ② resource-root (jboss-deployment-structure.xml)
  NG  WEB-INF/classes/testClasses  ← WAR に無い: WFLYSRV0058 の原因。記述を削除する
```

### 影響度と放置した場合のリスク

危険度 C。指定は無視されるだけで、動作には影響しません。ただし、将来ビルド設定が変わって testClasses が WAR に入ると、テスト用クラスが本番で読み込まれるようになります。記述子と WAR の中身がずれているサインとして直しておきます。

### 対処方針の比較

| 方式 | 内容 | 評価 |
|---|---|---|
| 記述を削除 ★推奨 | <resource-root path="WEB-INF/classes/testClasses"/> を消す。WEB-INF/classes は最初からリソースルート | ◎ |
| 環境ごとに記述子を切り替え | Maven プロファイルで開発用だけ追加 | △ 本番で不要なら複雑になるだけ |
| ビルド時の検査 | scan-war.py をビルドの最後に実行し、NG があれば止める | ◎ 再発防止 |

### 実装 (WAR 側)

```xml
<!-- WEB-INF/jboss-deployment-structure.xml (修正後の抜粋) -->
<jboss-deployment-structure xmlns="urn:jboss:deployment-structure:1.3">
    <deployment>
        <!-- <resources><resource-root path="WEB-INF/classes/testClasses"/></resources> は削除 -->
    </deployment>
</jboss-deployment-structure>
```

```xml
<!-- pom.xml: 念のため testClasses を WAR に入れない -->
<plugin>
  <groupId>org.apache.maven.plugins</groupId>
  <artifactId>maven-war-plugin</artifactId>
  <configuration>
    <packagingExcludes>WEB-INF/classes/testClasses/**</packagingExcludes>
  </configuration>
</plugin>
```

### 確認方法

```bash
python scan-war.py iwinmichl.war    # ② が OK になること
grep -c WFLYSRV0058 server.log        # → 0
```

### 検証結果 (実測)

| 集計項目 (check-warnings.sh) | S0 修正前 | S1 修正後 (system/remove) | S1e 修正後 (elytron) | S1d 修正後 (dedicated) |
|---|---|---|---|---|
| WFLYSRV0058 resource root does not exist | 1 | 0 | 0 | 0 |

S0 = 修正前を再現した状態、S1 系 = 本書の実装を適用した状態。シナリオの詳細と全ログは「検証結果」シート (md では「検証結果」章)。

### 出典

- [ServerLogger (WFLYSRV0018/0058/0211/0220/0272/0273/0274)](https://github.com/wildfly/wildfly-core/blob/27.0.1.Final/server/src/main/java/org/jboss/as/server/logging/ServerLogger.java)
- [DeploymentStructureDescriptorParser (②)](https://github.com/wildfly/wildfly-core/blob/27.0.1.Final/server/src/main/java/org/jboss/as/server/deployment/module/descriptor/DeploymentStructureDescriptorParser.java)

## ③ WFLYSRV0018: デプロイが private モジュール org.apache.cxf.impl を使っている

**危険度 B**

**ユーザー環境のログ (原文)**

```text
WFLYSRV0018:デプロイメント"deployment.iwinmichl.warはプライベートモジュール"org.apache.cxf.impl"を使っていますが、このモジュールは今後のバージョンで予告なく削除される可能性があります。
```

### ひとことで (小学生向け)

> **【小学生にもわかる説明】**  
> ビルの図書館の本棚には「どなたでもどうぞ (public)」の棚と「職員専用 (private)」の棚があります。
> iwinmichl のお店は、貸出カードに職員専用の棚 (org.apache.cxf.impl) を自分で書き込みました。
> 司書さんは本を貸してくれますが、「職員用の本は予告なく入れ替えることがあるので、ある日突然使えなくなっても知りませんよ」と日記に書きました。

| たとえ | 本当の仕組み |
|---|---|
| 図書館の棚 | JBoss Modules のモジュール ($JBOSS_HOME/modules/... の module.xml) |
| 職員専用の札 | module.xml の <property name="jboss.api" value="private"/> |
| 貸出カードに自分で書く | jboss-deployment-structure.xml の <dependencies> や MANIFEST.MF の Dependencies: (ユーザー指定の依存) |
| 司書が気をきかせて付ける本 | サブシステムが自動で付ける暗黙の依存 (こちらは private でも警告しない) |

### メッセージの正体

| 項目 | 内容 |
|---|---|
| 英語原文 | WFLYSRV0018: Deployment "%s" is using a private module ("%s") which may be changed or removed in future versions without notice. |
| ID / レベル | WFLYSRV0018 / WARN |
| ロガー | org.jboss.as.dependency.private (unsupported は org.jboss.as.dependency.unsupported、deprecated は ...deprecated) |
| 出す場所 | ModuleLoadService#start (デプロイのモジュールを読み込むとき) |
| 兄弟 | WFLYSRV0019 (unsupported モジュール) / WFLYSRV0221 (deprecated モジュール) |

### 動作原理

- モジュールの module.xml には jboss.api プロパティで公開区分が書かれている: public (既定) / private / unsupported / deprecated。Red Hat は「JBoss EAP 8 Included Modules」で一覧を公開しており、org.apache.cxf は PUBLIC、org.apache.cxf.impl・org.jboss.vfs・org.jboss.logmanager.log4j2 は PRIVATE。
- デプロイのモジュールを読み込む ModuleLoadService は、依存のうち isUserSpecified() が true のもの(jboss-deployment-structure.xml の <dependencies>、WAR や WEB-INF/lib の jar の MANIFEST.MF の Dependencies:) だけについて、相手の jboss.api を調べ、private なら WFLYSRV0018 を出す。
- webservices サブシステムが JAX-WS のために自動で付ける CXF の依存は「暗黙の依存」なので、private でも警告しない。つまりこの警告は「アプリ自身が private モジュールを指名した」ことを示す。
- org.apache.cxf.impl には CXF の実装 (cxf-rt-frontend-jaxws、cxf-rt-transports-http = HTTPConduit / HTTPClientPolicy、WS-Security など) が入っている。CXF の HTTPConduit を直接触ってタイムアウトや TLS を設定するコードがあると、この依存が必要になる。
- 検証で見つかったもう 1 件: spring-core-6.2.19.jar の MANIFEST.MF に「Dependencies: jdk.unsupported,org.jboss.vfs」が書かれており(Spring が JBoss の VFS 上でクラスパスを走査するため)、Spring を使う WAR では org.jboss.vfs についても WFLYSRV0018 が必ず出る。

### 動作イメージ

```text
[デプロイのモジュールを読み込む]
 依存の一覧
  ├ 暗黙の依存 (logging, webservices, ee ...)            → チェックしない
  └ ユーザー指定の依存
       ├ jboss-deployment-structure.xml: org.apache.cxf.impl → jboss.api=private → WFLYSRV0018 ★今回
       └ spring-core.jar の MANIFEST.MF: jdk.unsupported, org.jboss.vfs → org.jboss.vfs は private → WFLYSRV0018
```

### 歴史・背景・必要になった経緯

- 2015-10 WFCORE-1090、2015-12 WFLY-5804: module.xml に jboss.api=private を付けて「内部用」を明示するようになった (WildFly 10 / EAP 7 系)。
- 目的は、サポートする API (public) と内部実装 (private) を分けること。内部ライブラリ (CXF など) はメジャー更新で中身が大きく変わるので、アプリが内部実装に依存すると EAP の更新で壊れる。それを事前に知らせるのがこの警告。
- EAP 8.1 のリリースノートにも「ActiveMQ Artemis の内部モジュールを private にし、公開用の org.apache.activemq.artemis.client を新設」という変更があり、private 化は現在も進んでいる。

### この環境での原因と切り分け

jboss-deployment-structure.xml に <module name="org.apache.cxf.impl"/> があります。アプリが CXF の実装クラスを直接使っているか、以前の対処の名残です。まず実際に使っているかを確かめます。

```bash
# WAR のクラスが CXF 実装クラスを参照しているか (JDK の jdeps)
jdeps -verbose:class -cp 'WEB-INF/lib/*' WEB-INF/classes | grep -E 'org\.apache\.cxf\.(transport|transports|jaxws|configuration\.jsse)'
# 明示依存の一覧 (記述子 + 各 jar の MANIFEST)
python scan-war.py iwinmichl.war   # ## ③ に org.apache.cxf.impl / org.jboss.vfs が出る
```

| よくある使い方 | 必要なクラス (所属モジュール) | private 依存なしの代替 |
|---|---|---|
| SOAP の接続/応答タイムアウト | HTTPConduit, HTTPClientPolicy (org.apache.cxf.impl) | BindingProvider のリクエストコンテキストに jakarta.xml.ws.client.connectionTimeout / receiveTimeout (CXF 4 が読む。検証で動作確認) |
| TLS の信頼設定 | TLSClientParameters (org.apache.cxf.impl) | JVM 既定のトラストストアに CA を入れる (TRUST_MODE=system) か -Djavax.net.ssl.trustStore。CXF は TLS パラメータ未指定時に javax.net.ssl.trustStore → cacerts を読む |
| CXF の Bus やインターセプタ | org.apache.cxf (cxf-core。public) | public な org.jboss.ws.cxf.jbossws-cxf-client (services="import") に依存する |

### 影響度と放置した場合のリスク

危険度 B。今は動きますが、EAP のアップデートやマイナーバージョンアップで CXF の実装が入れ替わると、コンパイル済みのアプリが実行時に壊れる可能性があり、Red Hat のサポート対象外の使い方でもあります。org.jboss.vfs の 1 件は Spring 自身の宣言によるもので、アプリ側では消せない (無害)。

### 対処方針の比較

| 方式 | 内容 | 評価 |
|---|---|---|
| 依存を削除し標準 API で書く ★推奨 | タイムアウトは jakarta.xml.ws.client.*Timeout、TLS は JVM 既定のトラストストア | ◎ private 依存ゼロ |
| public モジュールに置き換え | org.jboss.ws.cxf.jbossws-cxf-client (services="import")。CXF の公開 API の範囲で使う | ○ |
| CXF を WAR に同梱し webservices を除外 | アプリが CXF の版を自分で管理する | △ 更新・脆弱性対応を自分で負う |
| そのまま使い続ける | private と承知でテストを厚くする | △ 警告は残る |
| org.jboss.vfs (Spring 由来) | logging で WFLYSRV0018 のうち org.jboss.vfs の行だけをフィルタ (20-logging.cli) | ○ Spring の jar を改変するよりよい |

### 実装

**アプリ側 (org.apache.cxf.impl 不要)**

```java
// implementation/app/.../ws/SoapClientTimeouts.java (標準 API だけでタイムアウトを設定)
Map<String, Object> ctx = ((BindingProvider) port).getRequestContext();
ctx.put("jakarta.xml.ws.client.connectionTimeout", 5000);   // ms
ctx.put("jakarta.xml.ws.client.receiveTimeout", 30000);     // ms
```

```xml
<!-- jboss-deployment-structure.xml: <module name="org.apache.cxf.impl"/> を削除。
     CXF の公開 API が本当に必要なときだけ: -->
<dependencies>
    <module name="org.jboss.ws.cxf.jbossws-cxf-client" services="import"/>
</dependencies>
```

**サーバ側 (jboss-cli)**

```text
# 20-logging.cli (抜粋): spring-core 由来の org.jboss.vfs の 1 行だけを抑止
/subsystem=logging/logger=org.jboss.as.dependency.private:add(filter-spec="not(match(\"WFLYSRV0018: .*org.jboss.vfs\"))")
```

### 確認方法

```bash
grep WFLYSRV0018 server.log    # → org.apache.cxf.impl の行が無いこと
# SOAP のタイムアウトが効くこと (検証: 応答 3 秒のサービスに receiveTimeout=1000ms → 約 1.2 秒で SocketTimeoutException)
```

### 検証結果 (実測)

| 集計項目 (check-warnings.sh) | S0 修正前 | S1 修正後 (system/remove) | S1e 修正後 (elytron) | S1d 修正後 (dedicated) |
|---|---|---|---|---|
| WFLYSRV0018 private module used | 2 | 0 | 0 | 0 |
| of which org.apache.cxf.impl | 1 | 0 | 0 | 0 |
| of which org.jboss.vfs (spring-core) | 1 | 0 | 0 | 0 |

S0 = 修正前を再現した状態、S1 系 = 本書の実装を適用した状態。シナリオの詳細と全ログは「検証結果」シート (md では「検証結果」章)。

### 出典

- [JBoss EAP 8.1 Release notes](https://docs.redhat.com/en/documentation/red_hat_jboss_enterprise_application_platform/8.1/html-single/release_notes_for_red_hat_jboss_enterprise_application_platform_8.1/index)
- [JBoss EAP 8 Included Modules (public / private の分類)](https://access.redhat.com/node/7142689)
- [ServerLogger (WFLYSRV0018/0058/0211/0220/0272/0273/0274)](https://github.com/wildfly/wildfly-core/blob/27.0.1.Final/server/src/main/java/org/jboss/as/server/logging/ServerLogger.java)
- [ModuleLoadService (③ の判定: ユーザー指定の依存だけ)](https://github.com/wildfly/wildfly-core/blob/27.0.1.Final/server/src/main/java/org/jboss/as/server/moduleservice/ModuleLoadService.java)
- [Apache CXF Message (jakarta.xml.ws.client.connectionTimeout / receiveTimeout)](https://github.com/apache/cxf/blob/cxf-4.0.6/core/src/main/java/org/apache/cxf/message/Message.java)
- [Apache CXF jsse SSLUtils (javax.net.ssl.trustStore を自分で読む)](https://github.com/apache/cxf/blob/cxf-4.0.6/core/src/main/java/org/apache/cxf/configuration/jsse/SSLUtils.java)

## ④ WFLYEE0007: 例外のためオプションのコンポーネント ...ServletServerHttpResponse$ResponseAsyncListener をインストールしていない

**危険度 C**

**ユーザー環境のログ (原文)**

```text
WFLY0007: 例外が原因でオプションのコンポーネント org.springframework.http.server.reactive.ServletServerHttpResponse$ResponseAsyncListenerをインストールしていません（DEBUGレベルを有効にして、原因を確認してください）
```

### ひとことで (小学生向け)

> **【小学生にもわかる説明】**  
> ビルには「お店に入ってきた道具に、必要な物を配ってあげる親切な係 (EE サブシステム)」がいます。
> Spring の道具箱の中に「非同期の見張り番 (AsyncListener)」という道具が 6 つ入っていたので、係は配る準備をしようとしました。
> でもその道具は「親 (外側のクラス) と一緒でないと作れない」作りだったので、係は作れませんでした。これは「やってもやらなくてもよい仕事 (オプション)」だったので、係は「飛ばしました。理由は DEBUG で」とメモしました。
> Spring は見張り番を自分でちゃんと作って使うので、お店は何も困りません。

| たとえ | 本当の仕組み |
|---|---|
| 親切な係 | EE サブシステム (EEModuleConfigurationProcessor) |
| 配る準備をする道具 | Undertow が「注入対象の Web コンポーネント」として登録したクラス (AsyncListener 実装など) |
| 親と一緒でないと作れない | 引数なしコンストラクタが無い (非 static の内部クラス等) → WFLYEE0048 |
| やってもやらなくてもよい仕事 | オプションのコンポーネント (失敗しても WARN を出して続行) |
| Spring が自分で作る | Spring は new ResponseAsyncListener() を自分で生成し、AsyncContext#addListener(インスタンス) で登録する |

### メッセージの正体

| 項目 | 内容 |
|---|---|
| 英語原文 | WFLYEE0007: Not installing optional component %s due to an exception (enable DEBUG log level to see the cause) |
| ID / レベル | WFLYEE0007 / WARN  (ユーザーのログの「WFLY0007」は EE サブシステムの WFLYEE0007) |
| ロガー | org.jboss.as.ee |
| 出す場所 | EEModuleConfigurationProcessor (WFLY-924 で「WARN 1 行 + 原因は DEBUG」に要約) |
| DEBUG で出る原因 (実測) | WFLYEE0048: Could not find default constructor for class org.springframework...ResponseAsyncListener |
| 同じ理由で出る Spring のクラス (実測 6 件) | ServletServerHttpResponse$ResponseAsyncListener / ServletServerHttpRequest$RequestAsyncListener / ServletHttpHandlerAdapter$HttpHandlerAsyncListener / ServletServerHttpAsyncRequestControl / StandardServletAsyncWebRequest / ServerHttpObservationFilter$ObservationAsyncListener |

### 動作原理

- Servlet 仕様では、AsyncContext#createListener(Class) で作られる AsyncListener もリソース注入の対象になる。そのため WildFly の Undertow 連携 (WebComponentProcessor) は、デプロイのアノテーション索引から jakarta.servlet.AsyncListener を実装する具象クラスを全部探し、サーブレット・フィルタ・リスナ・TLD のタグ/バリデータと同じく「Web コンポーネント (オプション)」として登録する。
- EE サブシステムはコンポーネントごとにインスタンスの作り方を決める。Weld (CDI) が有効なデプロイなら Weld に作らせる (WeldComponentIntegrationProcessor が WeldManagedReferenceFactory を設定)。Weld が無効なら引数なしコンストラクタで作る (DefaultInterceptorConfigurator)。
- Spring の 6 クラスは非 static の内部クラスなど、引数なしコンストラクタを持たないため WFLYEE0048 になり、オプション扱いなので WFLYEE0007 を出して登録をやめる (デプロイは成功)。
- ④ と ⑤ の関係: 既定では spring-web に含まれる DelegatingPhaseListenerMulticaster (jakarta.faces.event.PhaseListener の実装) を見て JSF サブシステムが有効になり、Faces 4 は CDI 必須なのでデプロイが Weld デプロイになる → ④ は出ない。jboss-deployment-structure.xml で jsf を除外していると Weld デプロイにならず、④ (と ⑤) が出る。検証で両方を確認した。
- ⑦ の javax 版 JSTL の TLD バリデータ (PermittedTaglibsTLV / ScriptFreeTLV) も同じ仕組みでコンポーネント登録され、クラスが読めずに WFLYEE0007 になる (こちらは ⑦ で対処)。

### 動作イメージ

```text
[デプロイ: INSTALL フェーズ]
 Undertow: 索引から AsyncListener の実装クラスを列挙 → 6 クラスを「オプションの Web コンポーネント」として登録
 EE: 各コンポーネントの作り方を決める
   ├ Weld デプロイ (JSF 有効 / beans.xml あり 等) → Weld が作る → 問題なし
   └ Weld デプロイでない (jsf・weld を除外 等)    → 引数なしコンストラクタで作る
         └ コンストラクタが無い → WFLYEE0048 → オプションなので WFLYEE0007 (WARN) ★今回 → 登録だけやめる
[実行時]
 Spring: new ResponseAsyncListener() を自分で作り、asyncContext.addListener(インスタンス) → コンテナの注入は不要
         → 非同期処理は正常 (検証: /api/async が "async-ok on MvcAsync1")
```

### 歴史・背景・必要になった経緯

- 2009 Servlet 3.0 (Java EE 6): 非同期処理と AsyncListener、createListener による注入対象のリスナが導入された。
- JBoss AS 7 / WildFly: 注入をサポートするため、AsyncListener 実装をすべてコンポーネント化する実装になった。
- 2013 WFLY-924: オプションのコンポーネントの失敗は大量の例外を出さず、WARN 1 行 + DEBUG に要約する形 (現在の WFLYEE0007) に。
- 2017 Spring 5.0: リアクティブ対応 (spring-web にサーブレット上でリアクティブを動かすアダプタ類) が入り、Spring MVC だけを使うアプリの jar にも AsyncListener 実装クラスが含まれるようになった。

### この環境での原因と切り分け

原因は「Weld 無効の WAR で、Spring の AsyncListener 実装に引数なしコンストラクタが無い」こと。推測でなく DEBUG で確かめてから対処します (下の手順。検証では 6 クラスとも WFLYEE0048 を確認)。

**原因の確認 (ECS Exec などで)**

```bash
# 起動中のコンテナで一時的に DEBUG にして再デプロイ
/opt/jboss-eap/bin/jboss-cli.sh -c --commands='/subsystem=logging/logger=org.jboss.as.ee:add(level=DEBUG),/subsystem=logging/console-handler=CONSOLE:write-attribute(name=level,value=DEBUG),/deployment=iwinmichl.war:redeploy'
# → DEBUG [org.jboss.as.ee] Not installing optional component ...ResponseAsyncListener due to an exception:
#      ... WFLYEE0048: Could not find default constructor for class ...ResponseAsyncListener
# 確認後に戻す
/opt/jboss-eap/bin/jboss-cli.sh -c --commands='/subsystem=logging/console-handler=CONSOLE:write-attribute(name=level,value=INFO),/subsystem=logging/logger=org.jboss.as.ee:remove'
```

```bash
python scan-war.py iwinmichl.war   # ## ④ に「引数なしコンストラクタ無し」のクラスが一覧される
```

### 影響度と放置した場合のリスク

危険度 C (無害)。Spring の非同期処理 (DeferredResult / Callable / SSE) は影響を受けません (検証で確認)。ただしデプロイのたびに 6 行の WARN が出て、本当に見るべき WFLYEE0007 (自分のクラスの注入失敗など) が埋もれます。

### 対処方針の比較

| 方式 | 内容 | 評価 |
|---|---|---|
| 原因確認のうえ Spring の分だけ抑止 ★推奨 | org.jboss.as.ee ロガーに filter-spec を付け、"WFLYEE0007: Not installing optional component org.springframework." で始まる行だけ捨てる | ◎ 他の WFLYEE0007 は出る |
| Weld を有効にする | WEB-INF/beans.xml (bean-discovery-mode="annotated") で Weld デプロイにする | △ 警告は消えるが、使わない CDI を動かすことになる |
| jsf の除外をやめる | spring-web の PhaseListener で JSF + Weld が有効になる | × JSF を使わないのに有効化される |
| ロガーのレベルを ERROR にする | org.jboss.as.ee 全体を黙らせる | × 範囲が広すぎる |

### 実装 (jboss-cli)

```text
# 20-logging.cli (抜粋)
if (outcome != success) of /subsystem=logging/logger=org.jboss.as.ee:read-resource
    /subsystem=logging/logger=org.jboss.as.ee:add(filter-spec="not(match(\"WFLYEE0007: Not installing optional component org.springframework.\"))")
end-if
```

> **【注意・補足】**  
> jboss-logmanager の match() は「整形後のメッセージ」に対する部分一致 (RegexFilter#isLoggable が getFormattedMessage を使う)。メッセージ ID を含む文頭で絞ることで、Spring 以外のクラスの WFLYEE0007 は残ります。

### 確認方法

```bash
grep -c 'WFLYEE0007.*org.springframework' server.log   # → 0
curl http://localhost:8080/iwinmichl/api/async                 # Spring の非同期処理が動くこと
```

### 検証結果 (実測)

| 集計項目 (check-warnings.sh) | S0 修正前 | S1 修正後 (system/remove) | S1e 修正後 (elytron) | S1d 修正後 (dedicated) |
|---|---|---|---|---|
| WFLYEE0007 optional component not installed | 8 | 0 | 0 | 0 |
| of which org.springframework.* | 6 | 0 | 0 | 0 |
| of which javax.servlet.jsp.jstl.* (=⑦) | 2 | 0 | 0 | 0 |

S0 = 修正前を再現した状態、S1 系 = 本書の実装を適用した状態。シナリオの詳細と全ログは「検証結果」シート (md では「検証結果」章)。

### 出典

- [WebComponentProcessor (AsyncListener / TLD validator のコンポーネント化)](https://github.com/wildfly/wildfly/blob/35.0.1.Final/undertow/src/main/java/org/wildfly/extension/undertow/deployment/WebComponentProcessor.java)
- [EEModuleConfigurationProcessor (WFLYEE0007)](https://github.com/wildfly/wildfly/blob/35.0.1.Final/ee/src/main/java/org/jboss/as/ee/component/deployers/EEModuleConfigurationProcessor.java)
- [DefaultInterceptorConfigurator (WFLYEE0048)](https://github.com/wildfly/wildfly/blob/35.0.1.Final/ee/src/main/java/org/jboss/as/ee/component/DefaultInterceptorConfigurator.java)
- [CdiAnnotations / WeldDeploymentProcessor (WFLYWELD0013)](https://github.com/wildfly/wildfly/blob/35.0.1.Final/weld/subsystem/src/main/java/org/jboss/as/weld/CdiAnnotations.java)
- [JSFVersionProcessor (JSF 有効化で Weld デプロイにする)](https://github.com/wildfly/wildfly/blob/35.0.1.Final/jsf/subsystem/src/main/java/org/jboss/as/jsf/deployment/JSFVersionProcessor.java)
- [jboss-logmanager RegexFilter (match は整形後メッセージに部分一致)](https://github.com/jboss-logging/jboss-logmanager/blob/2.1.19.Final/src/main/java/org/jboss/logmanager/filters/RegexFilter.java)
- [Spring ServletServerHttpResponse (ResponseAsyncListener は非 static 内部クラス)](https://github.com/spring-projects/spring-framework/blob/v6.2.11/spring-web/src/main/java/org/springframework/http/server/reactive/ServletServerHttpResponse.java)

## ⑤ WFLYWELD0013: CDI アノテーションはあるが Bean アーカイブが見つからない

**危険度 B**

**ユーザー環境のログ (原文)**

```text
WFLYWELD0013: デプロイメント iwinmichl.warにはJakarta Contexts and Dependency Injectionアノテーションが含まれますが、Beanアーカイブは見つかりませんでした(beans.xmlおよびBeanを定義するアノテーションを持つクラスがありません）
```

### ひとことで (小学生向け)

> **【小学生にもわかる説明】**  
> ビルには「名簿係 (Weld)」がいて、「CDI のシール (アノテーション)」が貼ってある道具を見つけると、その道具を管理する名簿 (Bean アーカイブ) を作ろうとします。
> iwinmichl の荷物からは CDI のシールが見つかりました。でも、名簿を作るきっかけ (beans.xml という申込書や、道具そのものに貼られた「Bean です」シール) はありませんでした。
> 名簿係は「シールはあるのに名簿が無いけど、本当にいいの？」と日記に書きました。
> 見つかったシールは、お店の道具ではなく、荷物に紛れ込んでいたサーバ用の部品 (jakarta.transaction-api) に付いていたものでした。

| たとえ | 本当の仕組み |
|---|---|
| 名簿係 | Weld (CDI = Jakarta Contexts and Dependency Injection の実装) |
| CDI のシール | WildFly が「CDI アノテーション」と判定する 20 種 (@ApplicationScoped, @Dependent, @NormalScope, @Produces, @Observes, jakarta.inject.Singleton など) |
| 名簿 (Bean アーカイブ) | CDI が Bean を探す単位。beans.xml があるか、クラスに Bean 定義アノテーションが付いているとそうなる |
| 紛れ込んだサーバ用の部品 | WEB-INF/lib に同梱された EE の API jar (jakarta.transaction-api の TransactionScoped に @NormalScope が付いている) |

### メッセージの正体

| 項目 | 内容 |
|---|---|
| 英語原文 | WFLYWELD0013: Deployment %s contains Jakarta Contexts and Dependency Injection annotations but no bean archive was found (no beans.xml or class with bean defining annotations was present). |
| ID / レベル | WFLYWELD0013 / WARN |
| ロガー | org.jboss.weld.deployer |
| 出す場所 | WeldDeploymentProcessor (トップレベルのデプロイで、Weld デプロイでなく、CDI アノテーションの印が付いているとき) |
| 印を付ける場所 | CdiAnnotationProcessor (アノテーション索引に CdiAnnotations の 20 種のどれかがあれば印を付ける) |

### 動作原理

- CdiAnnotationProcessor は、デプロイ全体のアノテーション索引 (WEB-INF/classes と WEB-INF/lib の jar を含む) に、次の 20 種のどれかが使われていれば「CDI アノテーションあり」の印を付ける: Decorator, Delegate, ApplicationScoped, ConversationScoped, RequestScoped, SessionScoped, NormalScope, Dependent, jakarta.inject.Singleton, Observes, Alternative, Any, Default, Disposes, Model, New, Produces, Specializes, Stereotype, Typed。@Inject と @Named は含まれない (Spring で @Inject を使っていても、それだけではこの警告にならない)。
- Weld デプロイになる条件: beans.xml がある (BeansXmlProcessor)、クラスに Bean 定義アノテーションがある (WeldImplicitDeploymentProcessor)、EJB などの暗黙 Bean が必要、JSF が有効 (Faces 4 は CDI 必須のため JSFVersionProcessor が印を付ける)、JAX-WS エンドポイントがある、など。
- Weld デプロイでなく、CDI アノテーションの印があり、トップレベルのデプロイなら WFLYWELD0013 を出す (CDI は動かない)。
- jakarta.transaction-api.jar の jakarta.transaction.TransactionScoped は @NormalScope で注釈されている。これは「スコープの定義」であってアプリの Bean ではないので、Bean アーカイブにはならないが、索引には @NormalScope の使用として載る。
- jsf を除外していなければ、spring-web の PhaseListener 実装で JSF が有効になり Weld デプロイになるため、この警告は出ない (検証で確認)。

### 動作イメージ

```text
[デプロイ]
 アノテーション索引 (WEB-INF/classes + WEB-INF/lib/*.jar)
  └ jakarta.transaction-api-2.0.1.jar: TransactionScoped に @NormalScope  → 「CDI アノテーションあり」の印
 Weld デプロイか？
  ├ beans.xml なし / Bean 定義アノテーション付きのクラスなし
  ├ jsf を除外 (spring-web の PhaseListener による JSF 有効化が起きない)
  └ → Weld デプロイではない
 → 印あり かつ Weld デプロイでない → WFLYWELD0013 (WARN) ★今回
```

### 歴史・背景・必要になった経緯

- 2009 CDI 1.0 (Java EE 6): beans.xml を置いたアーカイブだけが Bean アーカイブ。
- 2013 CDI 1.1 (Java EE 7): beans.xml が無くても、Bean 定義アノテーション付きのクラスがあれば「暗黙的 Bean アーカイブ」になる (bean-discovery-mode = all / annotated / none)。
- 2022 CDI 4.0 (Jakarta EE 10): 中身の無い beans.xml の意味が all から annotated に変わった (WildFly は互換用に weld サブシステムの legacy-empty-beans-xml-treatment 属性を用意)。
- WildFly はこの警告で「CDI のつもりでアノテーションを書いたのに、Bean アーカイブにならず注入が黙って効いていない」事故を知らせる。

### この環境での原因と切り分け

WAR に同梱された EE の API jar (検証では jakarta.transaction-api) が CDI アノテーションの出どころで、jsf を除外しているため Weld デプロイにもならない、という組み合わせです。実際の WAR でどの jar かは scan-war.py で特定できます。

**検証用 WAR での実行結果**

```text
python scan-war.py iwinmichl.war
## ⑤ WildFly が「CDI アノテーション」と判定するもの (WFLYWELD0013 の材料)
  beans.xml: なし
  NG jakarta.transaction-api-2.0.1.jar: 1 件  例: ['jakarta.transaction.TransactionScoped @NormalScope']
  WEB-INF/lib の Jakarta/Java EE API jar (サーバが提供するので provided にする): ['jakarta.transaction-api-2.0.1.jar']
```

### 影響度と放置した場合のリスク

危険度 B。CDI を使っていない Spring アプリなら、警告そのものは無害です。ただし原因の「サーバが提供する API の jar を WAR に同梱」は、サーバ側の同じクラスとの食い違い (LinkageError / ClassCastException) の火種になります。また、本当に CDI を使うつもりのコードがある場合は、注入が効いていないことを示します。

### 対処方針の比較

| 方式 | 内容 | 評価 |
|---|---|---|
| EE API jar を同梱しない ★推奨 | pom.xml で jakarta.* の API を provided にする (サーバが提供する) | ◎ 根本対処 |
| CDI を使わないなら weld を除外 ★推奨 | jboss-deployment-structure.xml の exclude-subsystems に weld (jsf と一緒に) | ◎ 警告と Weld の起動コストが無くなる |
| CDI を使うなら beans.xml | WEB-INF/beans.xml (bean-discovery-mode="annotated") を置く | ○ CDI を使う場合のみ |
| weld サブシステムの属性で消す | require-bean-descriptor 等はこの警告を消すためのものではない | × 効かない |

> **【注意・補足】**  
> weld を除外すると、そのデプロイでは CDI に依存する機能 (CDI 連携の Bean Validation、JAX-RS の CDI 連携、Jakarta Security 等) が使えません。Spring MVC + JSP のアプリでは通常問題ありません。

### 実装 (WAR 側)

```xml
<!-- jboss-deployment-structure.xml -->
<exclude-subsystems>
    <subsystem name="jsf"/>
    <subsystem name="weld"/>
</exclude-subsystems>
```

```xml
<!-- pom.xml: サーバ提供の API は provided -->
<dependency>
  <groupId>jakarta.transaction</groupId>
  <artifactId>jakarta.transaction-api</artifactId>
  <scope>provided</scope>
</dependency>
```

### 確認方法

```bash
python scan-war.py iwinmichl.war    # ⑤ が「使用なし」になること
grep -c WFLYWELD0013 server.log       # → 0
```

### 検証結果 (実測)

| 集計項目 (check-warnings.sh) | S0 修正前 | S1 修正後 (system/remove) | S1e 修正後 (elytron) | S1d 修正後 (dedicated) |
|---|---|---|---|---|
| WFLYWELD0013 CDI annotations, no bean archive | 1 | 0 | 0 | 0 |

S0 = 修正前を再現した状態、S1 系 = 本書の実装を適用した状態。シナリオの詳細と全ログは「検証結果」シート (md では「検証結果」章)。

### 出典

- [CdiAnnotations / WeldDeploymentProcessor (WFLYWELD0013)](https://github.com/wildfly/wildfly/blob/35.0.1.Final/weld/subsystem/src/main/java/org/jboss/as/weld/CdiAnnotations.java)
- [JSFVersionProcessor (JSF 有効化で Weld デプロイにする)](https://github.com/wildfly/wildfly/blob/35.0.1.Final/jsf/subsystem/src/main/java/org/jboss/as/jsf/deployment/JSFVersionProcessor.java)
- [JBoss EAP 8 Included Modules (public / private の分類)](https://access.redhat.com/node/7142689)

## ⑥ WFLYSRV0274: jboss-deployment-structure.xml で除外した依存 org.jboss.logmanager.log4j2 が存在しない

**危険度 B**

**ユーザー環境のログ (原文)**

```text
WFLYSRV0274: jboss-deployment-structure.xmlを介して除外された依存関係.org.jboss.logmanager.log4j2は存在しません。
```

### ひとことで (小学生向け)

> **【小学生にもわかる説明】**  
> 引っ越しの荷物リストに「○○さんから届く荷物は受け取りません (除外)」と書きました。
> ところが、○○さんからは最初から何も届く予定がありませんでした。係は「受け取り拒否リストの○○さんは、届け物の予定に見当たりません」とメモしました。
> 本当に断りたかったのは、○○さんに荷物を頼んでいた△△さん (org.apache.logging.log4j.api) の方でした。だから、拒否したつもりの荷物は結局届いていて、お店のログは EAP の日記係に書かれています。

| たとえ | 本当の仕組み |
|---|---|
| 受け取り拒否リスト | jboss-deployment-structure.xml の <exclusions> |
| ○○さん | org.jboss.logmanager.log4j2 (Log4j 2 API を JBoss LogManager につなぐ部品。private) |
| △△さん | org.apache.logging.log4j.api (logging サブシステムがデプロイに自動で付ける依存。public) |
| 届け物の予定 | そのデプロイに実際に追加された依存の一覧 |

### メッセージの正体

| 項目 | 内容 |
|---|---|
| 英語原文 | WFLYSRV0274: Excluded dependency %s via jboss-deployment-structure.xml does not exist. |
| ID / レベル | WFLYSRV0274 / WARN (兄弟: WFLYSRV0273 = 存在しないサブシステムの除外) |
| ロガー | org.jboss.as.server.deployment |
| 出す場所 | DeploymentUnitPhaseService (CLEANUP フェーズ) が ModuleSpecification#getFictitiousExcludedDependencies を見て出す |
| 「does not exist」の本当の意味 | 「サーバにモジュールが無い」ではなく「このデプロイの依存に一度も追加されなかった (除外が空振りした)」 |

### 動作原理

- <exclusions> に書いたモジュールは ModuleSpecification の除外リストに入り、その後サブシステムが依存を追加するときに一致したものだけが取り除かれる (取り除いた記録も残る)。
- CLEANUP フェーズで「除外リストにあるのに、一度も取り除かれなかった (= 依存に入っていなかった)」ものを WFLYSRV0274 として報告する (WFCORE-4234)。
- logging サブシステムが暗黙に付ける依存は次の 7 つ (LoggingModuleDependency): org.apache.commons.logging、org.apache.logging.log4j.api (services import)、org.jboss.logging、org.jboss.logging.jul-to-slf4j-stub、org.jboss.logmanager、org.slf4j、org.slf4j.impl。org.jboss.logmanager.log4j2 はここに無い。
- org.jboss.logmanager.log4j2 は EAP 8.1 にも存在する (private) が、org.apache.logging.log4j.api の module.xml の中から使われる「内部の依存」なので、デプロイの依存には直接入らない。だから除外しても空振りになる。
- 結果: WAR に log4j-api / log4j-core を同梱していても、Log4j 2 API のクラスはサーバのモジュールから読まれ (暗黙の依存が WAR より先)、アプリのログは EAP の logging サブシステムに流れる。除外の意図は実現していない。

### 動作イメージ

```text
[依存の組み立て]
 logging サブシステム: org.apache.logging.log4j.api を追加 ──(この module.xml の中で)── org.jboss.logmanager.log4j2 を使う
 jboss-deployment-structure.xml: <exclusions> org.jboss.logmanager.log4j2
   → デプロイの依存に org.jboss.logmanager.log4j2 は来ない → 何も取り除かれない
[CLEANUP]
   → 「除外したのに一度も取り除いていない」→ WFLYSRV0274 (WARN) ★今回
[実行時 (検証 E9)]
   除外なし / org.jboss.logmanager.log4j2 を除外 : LoggerContext = org.jboss.logmanager.log4j.JBossLoggerContext (EAP のログ)
   org.apache.logging.log4j.api を除外         : LoggerContext = org.apache.logging.log4j.core.LoggerContext (アプリの log4j2.xml)
```

### 歴史・背景・必要になった経緯

- JBoss AS 7 (2011) から、デプロイごとに依存を除外できる <exclusions> がある (アプリ同梱のライブラリをサーバ版より優先させたいときに使う)。
- WildFly の logging サブシステムは Log4j 2 API の呼び出しを JBoss LogManager に流すブリッジ (log4j2-jboss-logmanager) を持ち、それを内部モジュール org.jboss.logmanager.log4j2 として同梱している。
- 2018-12 WFCORE-4233 / 4234: 名前の打ち間違いや取り違えで除外が空振りしても気づけないため、存在しないサブシステム・依存の除外を WARN で知らせるようになった (WFLYSRV0273 / 0274)。

### この環境での原因と切り分け

「アプリ同梱の Log4j 2 を使いたい」意図で除外を書いたものの、除外先を取り違えています。まず、どちらのログ設計にしたいかを決めます。

| 実験 (検証 E9) | 除外指定 | 結果 |
|---|---|---|
| none | なし | LoggerContext=JBossLoggerContext。log4j-api はサーバのモジュール (2.23.1) から読まれ、ログは EAP の形式で出力 |
| bad (現行) | org.jboss.logmanager.log4j2 | WFLYSRV0274 が出て、結果は none と同じ (空振り) |
| good | org.apache.logging.log4j.api | LoggerContext=org.apache.logging.log4j.core.LoggerContext。WAR の log4j-api 2.26.1 と log4j2.xml が使われる |

### 影響度と放置した場合のリスク

危険度 B。ログの出力先・書式・レベル設定が、開発者の意図 (アプリの log4j2.xml) と実際 (EAP の logging サブシステム) で食い違っています。障害調査のときに「出るはずのログが出ていない」「設定を変えても効かない」原因になります。

### 対処方針の比較

| 方式 | 内容 | 評価 |
|---|---|---|
| (A) EAP のログに乗せる ★ECS では推奨 | 除外を削除。log4j-core を同梱しない (log4j-api は provided)。レベルや形式は jboss-cli で管理。コンソール → awslogs → CloudWatch Logs に一元化 | ◎ 設定が 1 か所、コンテナ向き |
| (B) アプリの Log4j 2 を使う | 除外対象を org.apache.logging.log4j.api に直す (検証 E9 good)。log4j-api と log4j-core を同梱 | ○ ファイル出力 (EFS のローテーション等) をアプリで制御したい場合 |
| (B') サーバ全体で暗黙依存を止める | jboss-cli で /subsystem=logging:write-attribute(name=add-logging-api-dependencies, value=false) | △ サーバ全体に効く |

### 実装

```xml
<!-- (A) jboss-deployment-structure.xml: 誤った除外を削除するだけ -->
<!-- <exclusions><module name="org.jboss.logmanager.log4j2"/></exclusions>  ← 削除 -->

<!-- (B) アプリ同梱の Log4j 2 を使う場合 -->
<exclusions>
    <module name="org.apache.logging.log4j.api"/>
</exclusions>
```

```text
# (B') サーバ全体で logging API の暗黙依存を止める (20-logging.cli の調査用コメント参照)
/subsystem=logging:write-attribute(name=add-logging-api-dependencies, value=false)
```

### 確認方法

```bash
grep -c WFLYSRV0274 server.log   # → 0
# (B) の場合: アプリで LogManager.getContext(false).getClass() を出力し
#   org.apache.logging.log4j.core.LoggerContext になっていること
```

### 検証結果 (実測)

| 集計項目 (check-warnings.sh) | S0 修正前 | S1 修正後 (system/remove) | S1e 修正後 (elytron) | S1d 修正後 (dedicated) |
|---|---|---|---|---|
| WFLYSRV0274 excluded dependency does not exist | 1 | 0 | 0 | 0 |
| WFLYSRV0273 excluded subsystem does not exist | 0 | 0 | 0 | 0 |

S0 = 修正前を再現した状態、S1 系 = 本書の実装を適用した状態。シナリオの詳細と全ログは「検証結果」シート (md では「検証結果」章)。

### 出典

- [ServerLogger (WFLYSRV0018/0058/0211/0220/0272/0273/0274)](https://github.com/wildfly/wildfly-core/blob/27.0.1.Final/server/src/main/java/org/jboss/as/server/logging/ServerLogger.java)
- [ModuleSpecification#getFictitiousExcludedDependencies (⑥)](https://github.com/wildfly/wildfly-core/blob/27.0.1.Final/server/src/main/java/org/jboss/as/server/deployment/module/ModuleSpecification.java)
- [LoggingModuleDependency (logging の暗黙依存一覧)](https://github.com/wildfly/wildfly-core/blob/27.0.1.Final/logging/src/main/java/org/jboss/as/logging/LoggingModuleDependency.java)
- [JBoss EAP 8 Included Modules (public / private の分類)](https://access.redhat.com/node/7142689)

## ⑦ Failed to define class javax.servlet.jsp.jstl.tlv.PermittedTaglibsTLV (NoClassDefFoundError: Failed to link)

**危険度 B**

**ユーザー環境のログ (原文)**

```text
Failed to define class javax.servlet.jsp.jstl.tlv.Permitted.TaglibsTLV in Module "deployment.iwinmichl.war" from Service Module Loader: java.lang.NoClassDefFound Error: Failed to link javax/servlet/jsp/jstl/tlv/PermittedTaglibsTLVModule "deployment.iwinmichl.war" from Service Module Loader javax/servlet/jsp/tagext/TaglibraryValidator
```

### ひとことで (小学生向け)

> **【小学生にもわかる説明】**  
> 昔の教科書 (Java EE の javax) と、新しい教科書 (Jakarta EE の jakarta) があります。中身はほぼ同じですが、表紙の名前が違います。
> EAP 8.1 という学校には、新しい教科書しか置いてありません。
> お店の荷物に昔の教科書 (jstl-1.2.jar) が入っていて、その付録 (TLD) に「このページを読むには javax の本が必要」と書いてありました。
> 先生が javax の本を探しましたが見つからず、「この付録は使えません」と日記に書きました。
> 授業 (JSP の表示) は、学校が用意した新しい教科書で問題なく進みます。

| たとえ | 本当の仕組み |
|---|---|
| 昔の教科書 | Java EE 時代の javax.* API (javax.servlet.jsp.tagext.TagLibraryValidator など) |
| 新しい教科書 | Jakarta EE 9 以降の jakarta.* API (EAP 8 は jakarta.* のみ) |
| 荷物に入っていた昔の教科書 | WEB-INF/lib/jstl-1.2.jar (javax 版 JSTL) |
| 付録 | jar 内の TLD (permittedTaglibs.tld / scriptfree.tld) の <validator-class> |
| 学校が用意した教科書 | EAP が提供する Jakarta Standard Tag Library 3.0 |

### メッセージの正体

| 項目 | 内容 |
|---|---|
| 英語原文 (正しい形) | Failed to define class javax.servlet.jsp.jstl.tlv.PermittedTaglibsTLV in Module "deployment.iwinmichl.war" from Service Module Loader: java.lang.NoClassDefFoundError: Failed to link javax/servlet/jsp/jstl/tlv/PermittedTaglibsTLV (Module "deployment.iwinmichl.war" from Service Module Loader): javax/servlet/jsp/tagext/TagLibraryValidator |
| ID / レベル | ID なし (JBoss Modules のメッセージ) / WARN |
| ロガー | org.jboss.modules.define (JDKModuleLogger: カテゴリ org.jboss.modules + ".define") |
| 出す場所 | ModuleClassLoader#defineClass が Error を受けたとき (classDefineFailed) |
| 一緒に出るもの | WFLYEE0007: Not installing optional component javax.servlet.jsp.jstl.tlv.PermittedTaglibsTLV / ScriptFreeTLV (④ と同じ仕組み) |

### 動作原理

- Undertow (Jastow) はデプロイ時に WEB-INF/lib の jar 内の TLD を読み、WebComponentProcessor は TLD の <validator-class>・<tag-class>・<listener-class> を「注入対象の Web コンポーネント」として登録する。
- jstl-1.2.jar の permittedTaglibs.tld / scriptfree.tld は、バリデータとして javax.servlet.jsp.jstl.tlv.PermittedTaglibsTLV / ScriptFreeTLV を指定している。
- EE サブシステムがそのクラスを読み込むと、JBoss Modules がクラスを定義する際に親クラス javax.servlet.jsp.tagext.TagLibraryValidator を解決しようとする。EAP 8 には jakarta.servlet.jsp.tagext.TagLibraryValidator しか無いので NoClassDefFoundError (Failed to link) になり、org.jboss.modules.define が WARN を出す。続いて EE がオプションのコンポーネントとして WFLYEE0007 を出し、登録をやめる。
- JSP 自体は動く (検証: 旧 URI の c:out と fmt:formatNumber、新 URN の jakarta.tags.core がすべて HTTP 200)。EAP が提供する Jakarta JSTL 3.0 は旧 URI (http://java.sun.com/jsp/jstl/...) も受け付ける。

### 動作イメージ

```text
[デプロイ]
 TLD を走査: WEB-INF/lib/jstl-1.2.jar!/META-INF/permittedTaglibs.tld
   <validator><validator-class>javax.servlet.jsp.jstl.tlv.PermittedTaglibsTLV</validator-class></validator>
 → Web コンポーネントとして登録 → EE がクラスを読み込む
 → JBoss Modules: PermittedTaglibsTLV の親 javax.servlet.jsp.tagext.TagLibraryValidator が無い
      → NoClassDefFoundError: Failed to link → "Failed to define class ..." (WARN, org.jboss.modules.define) ★今回
 → EE: WFLYEE0007 (オプションなので登録をやめて続行)
[JSP の実行]
 taglib uri="http://java.sun.com/jsp/jstl/core" → EAP の Jakarta JSTL 3.0 が処理 → 正常
```

### 歴史・背景・必要になった経緯

- 2006 JSTL 1.2 (Java EE 5): javax.servlet.jsp.jstl パッケージ。permittedTaglibs / scriptfree は「使ってよいタグを制限する」ための検証用 TLD。
- 2017〜2019 Java EE が Eclipse Foundation に移管され、商標の都合で javax 名前空間を使い続けられなくなった。
- 2020-12 Jakarta EE 9: すべての API が javax.* から jakarta.* に一斉に改名された (中身はほぼ同じ)。
- 2022 Jakarta EE 10: Jakarta Standard Tag Library 3.0 で URI が jakarta.tags.core などの URN に変わった (旧 URI も引き続き使える)。
- 2024 EAP 8.0 / 2025 EAP 8.1: Jakarta EE 10 準拠。javax 版の API は含まれないので、javax のまま残った jar はこのように読めない。

### この環境での原因と切り分け

WAR に javax 版 JSTL (jstl-1.2.jar、または taglibs-standard-impl/spec 等) が残っています。Jakarta 移行のときに依存の整理が漏れたものです。

**検証用 WAR での実行結果**

```text
python scan-war.py iwinmichl.war
## ⑦ javax.* (Java EE 時代) の痕跡
  NG TLD jstl-1.2.jar:META-INF/permittedTaglibs.tld → javax.servlet.jsp.jstl.tlv.PermittedTaglibsTLV
  NG TLD jstl-1.2.jar:META-INF/scriptfree.tld → javax.servlet.jsp.jstl.tlv.ScriptFreeTLV
  NG jstl-1.2.jar: javax.servlet を参照・定義するクラス 160 個 (EAP 8 は jakarta.* のみ。Jakarta 版へ置換/除去)
```

### 影響度と放置した場合のリスク

危険度 B。今は JSP が動いていても、javax.* を直接使う Java コードや、旧 JSTL のクラスに頼るタグがあると、実行時に NoClassDefFoundError になります。Jakarta 移行が終わっていない印なので、他にも javax の jar が残っていないか確認します。

### 対処方針の比較

| 方式 | 内容 | 評価 |
|---|---|---|
| javax 版 JSTL を削除 ★推奨 | jstl-1.2.jar / taglibs-standard-* を依存から外し、EAP 提供の Jakarta JSTL を使う (API は provided) | ◎ |
| javax の混入をビルドで止める | maven-enforcer-plugin の bannedDependencies で javax.servlet:* 等を禁止 | ◎ 再発防止 |
| 移行ツールで一括点検 | Migration Toolkit for Applications (MTA) / Eclipse Transformer で javax の残りを洗い出す | ○ |
| taglib の URI を新 URN に | jakarta.tags.core 等へ。必須ではない (旧 URI も動く) | △ 任意 |

### 実装 (WAR 側)

```xml
<!-- pom.xml: javax 版を外し、Jakarta 版の API を provided で参照 -->
<dependency>
  <groupId>jakarta.servlet.jsp.jstl</groupId>
  <artifactId>jakarta.servlet.jsp.jstl-api</artifactId>
  <scope>provided</scope>
</dependency>
<!-- maven-enforcer-plugin: javax.servlet:*, javax.servlet.jsp.jstl:*, org.apache.taglibs:taglibs-standard-* を禁止
     (全文は implementation/app/pom-snippets.xml) -->
```

### 確認方法

```bash
grep -c 'Failed to define class javax' server.log     # → 0
curl http://localhost:8080/iwinmichl/<JSTL を使う画面>      # 表示が変わらないこと
```

### 検証結果 (実測)

| 集計項目 (check-warnings.sh) | S0 修正前 | S1 修正後 (system/remove) | S1e 修正後 (elytron) | S1d 修正後 (dedicated) |
|---|---|---|---|---|
| Failed to define class javax.* | 4 | 0 | 0 | 0 |
| of which javax.servlet.jsp.jstl.* (=⑦) | 2 | 0 | 0 | 0 |

S0 = 修正前を再現した状態、S1 系 = 本書の実装を適用した状態。シナリオの詳細と全ログは「検証結果」シート (md では「検証結果」章)。

### 出典

- [JDKModuleLogger (Failed to define class / org.jboss.modules.define)](https://github.com/jboss-modules/jboss-modules/blob/2.1.6.Final/src/main/java/org/jboss/modules/log/JDKModuleLogger.java)
- [WebComponentProcessor (AsyncListener / TLD validator のコンポーネント化)](https://github.com/wildfly/wildfly/blob/35.0.1.Final/undertow/src/main/java/org/wildfly/extension/undertow/deployment/WebComponentProcessor.java)
- [Jakarta Standard Tag Library 3.0](https://jakarta.ee/specifications/tags/3.0/)

## ⑧ IJ030040: 開いたままの Statement を閉じた (自分で後片付けしてください)

**危険度 B**

**ユーザー環境のログ (原文)**

```text
IJ030040: Closing a statement you left open please do your own housekeeping for: java/jdbc/MIF02JA_JDS - java.lang.Throwable: STACKTRACE
```

### ひとことで (小学生向け)

> **【小学生にもわかる説明】**  
> 図書館で本 (DB 接続) を借りて、その中のメモ用紙 (Statement) を使ったら、本を返す前にメモ用紙を片付けるルールです。
> あるお客さんが、メモ用紙を出しっぱなしで本を返しました。司書 (IronJacamar) が代わりに片付けて、「自分で片付けてね」と日記に書きました。誰が出しっぱなしにしたか (STACKTRACE) も一緒に書いてくれます。

| たとえ | 本当の仕組み |
|---|---|
| 本を借りる / 返す | DataSource#getConnection / Connection#close (プールに戻る) |
| メモ用紙 | Statement / PreparedStatement |
| 司書が代わりに片付ける | track-statements=true のとき、接続を返す時点で開いたままの Statement を閉じる |
| 誰が出しっぱなしにしたか | Statement を作った時点のスタックトレース (java.lang.Throwable: STACKTRACE) |

### メッセージの正体

| 項目 | 内容 |
|---|---|
| 英語原文 | IJ030040: Closing a statement you left open, please do your own housekeeping for: %s |
| ID / レベル | IJ030040 / WARN (%s はデータソースの JNDI 名 java:/jdbc/MIF02JA_JDS) |
| ロガー | org.jboss.jca.adapters.jdbc.WrappedConnection |
| 出す場所 | IronJacamar の WrappedConnection (接続ハンドルを閉じるときの closeStatements) |
| 付いてくるスタック | Statement を作った呼び出し元 (検証: com.example.iwinmichl.test.DbServlet.leak(DbServlet.java:70)) |

### 動作原理

- IronJacamar の JDBC アダプタは、アプリに渡す Connection / Statement / ResultSet を包んで (WrappedConnection など) 管理している。
- データソースの track-statements 属性: FALSE (追跡しない) / TRUE (追跡し、閉じ忘れを警告) / NOWARN (追跡し、黙って閉じる)。既定は NOWARN (IronJacamar の Defaults)。⑧⑫ が出ている = この環境では TRUE になっている。
- TRUE のとき、Statement を作るたびに作成箇所のスタック (Throwable) を記録する。アプリが Connection#close したとき、まだ開いている Statement があれば IJ030040 とスタックを出して閉じる。
- 接続はプールに戻るので「接続のリーク」ではないが、閉じるまでの間 DB 側のカーソルやサーバ側プリペアドステートメント、メモリを保持し続ける。

### 動作イメージ

```text
[リクエスト処理 (default task-N)]
 Connection c = ds.getConnection()          … プールから借りる
 PreparedStatement ps = c.prepareStatement() … 作成箇所を記録 (track-statements=TRUE)
 ResultSet rs = ps.executeQuery()            … 同上
 c.close()                                   … ps と rs を閉じていない
   → IronJacamar: 開いたままの ps を閉じる → IJ030040 + STACKTRACE (WARN) ★⑧
                  ps を閉じる際に rs も閉じる  → IJ030042 + STACKTRACE (WARN) ★⑫
   → 接続はプールへ戻る
```

### 歴史・背景・必要になった経緯

- JDBC 2.0 Optional Package (1999) で接続プールが標準化され、アプリは接続を「借りて返す」ようになった。
- JBoss AS 4/5 の JBossJCA の頃から、借りたまま閉じ忘れた Statement を追跡する track-statements があり、JBoss AS 7 (2011) 以降の IronJacamar に引き継がれた。
- プールでは接続が使い回されるため、閉じ忘れたリソースが次の利用者に持ち越されたり、DB 側に溜まったりする。それを防ぐ安全網と、開発者への通知を兼ねている。

### この環境での原因と切り分け

アプリのコードが Statement を閉じずに Connection だけ閉じています。スタックの中のアプリのフレームが直すべき場所です。analyze-ij-log.py で、作成箇所ごとの件数ランキングを出せます。

**検証ログでの実行結果**

```text
python analyze-ij-log.py server.log --pkg com.example
 (A) ⑧ IJ030040 / ⑫ IJ030042 閉じ忘れの「作った場所」ランキング
      1  IJ030040 Statement   com.example.iwinmichl.test.DbServlet.leak(DbServlet.java:70)
      1  IJ030042 ResultSet   com.example.iwinmichl.test.DbServlet.leak(DbServlet.java:71)
```

### 影響度と放置した場合のリスク

危険度 B。サーバが代わりに閉じているので即障害にはなりませんが、コードの不具合です。長いトランザクションや大量ループで同じ書き方をすると、DB 側のリソース (カーソル、プリペアドステートメント) を使い切ったり、メモリを圧迫したりします。NOWARN や FALSE に変えて警告だけ消すのは誤りです (FALSE だと後片付けもしなくなる)。

### 対処方針の比較

| 方式 | 内容 | 評価 |
|---|---|---|
| コードを直す ★推奨 | try-with-resources で Connection / Statement / ResultSet を必ず閉じる。Spring なら JdbcTemplate に任せる | ◎ 根本対処 |
| track-statements を環境で切り替え | 開発・検証は TRUE で検出、本番は修正後に NOWARN (安全網は残す) | ◎ 運用 |
| CCM の debug | 接続そのものの閉じ忘れ (リーク) を検出 (IJ000100) | ○ 補助 |
| FALSE にする | 追跡も後片付けもしない | × 警告が消えるだけでリスクが増える |

### 実装

**アプリ側**

```java
// 良い例 (implementation/app/.../dao/JdbcResourceSamples.java)
try (Connection c = ds.getConnection();
     PreparedStatement ps = c.prepareStatement("SELECT name FROM emp WHERE dept_id = ?")) {
    ps.setInt(1, deptId);
    try (ResultSet rs = ps.executeQuery()) {
        while (rs.next()) { names.add(rs.getString(1)); }
    }
}
```

**サーバ側 (jboss-cli)**

```text
# 30-datasource-mysql-xa.cli (抜粋): 環境変数で切り替え (既定 NOWARN)
track-statements="${env.DB_TRACK_STATEMENTS:NOWARN}"
# 31-jca-ccm.cli: 調査時だけ JCA_CCM_DEBUG=true
/subsystem=jca/cached-connection-manager=cached-connection-manager:write-attribute(name=debug, value="${env.JCA_CCM_DEBUG:false}")
```

### 確認方法

```bash
# 検証環境 (DB_TRACK_STATEMENTS=TRUE) でアプリを一通り動かし
grep -c IJ030040 server.log                 # → 0
python analyze-ij-log.py server.log --pkg com.example   # (A) が「該当なし」
```

### 検証結果 (実測)

| 集計項目 (check-warnings.sh) | S0 修正前 | S1 修正後 (system/remove) | S1e 修正後 (elytron) | S1d 修正後 (dedicated) |
|---|---|---|---|---|
| IJ030040 statement left open | 1 | 0 | 0 | 0 |

S0 = 修正前を再現した状態、S1 系 = 本書の実装を適用した状態。シナリオの詳細と全ログは「検証結果」シート (md では「検証結果」章)。

### 出典

- [IronJacamar AdaptersLogger (IJ030027/030040/030042)](https://github.com/ironjacamar/ironjacamar/blob/3.0.10.Final/adapters/src/main/java/org/jboss/jca/adapters/AdaptersLogger.java)
- [IronJacamar Defaults (track-statements=NOWARN 等)](https://github.com/ironjacamar/ironjacamar/blob/3.0.10.Final/common/api/src/main/java/org/jboss/jca/common/api/metadata/Defaults.java)
- [EAP 6/7/8 JDBC datasource not fault tolerant ... needs connection validation enabled](https://access.redhat.com/solutions/156103)

## ⑨ Resolved [HttpRequestMethodNotSupportedException: Request method 'POST' is not supported]

**危険度 B**

**ユーザー環境のログ (原文)**

```text
Resolved ( org.springframework.web.HttpRequestMethodNotSupportedException: RequestMethod 'POST' is not supported'
```

### ひとことで (小学生向け)

> **【小学生にもわかる説明】**  
> お店の窓口に「ここは “見るだけ (GET)” の窓口です」と書いてあるのに、誰かが「荷物を置かせて (POST)」と来ました。
> 店員 (Spring) は「この窓口ではできません (405)」と断り、日記に「断りました」とだけ書きました。
> でも、誰が・どの窓口に来たのかは書いていないので、このままでは理由が分かりません。

| たとえ | 本当の仕組み |
|---|---|
| 窓口 | Spring MVC のハンドラ (@GetMapping などで受け付ける URL とメソッドが決まる) |
| 見るだけ / 置かせて | HTTP メソッド GET / POST |
| 断る | 405 Method Not Allowed と Allow ヘッダ (受け付けるメソッド) を返す |
| 日記に断ったとだけ書く | DefaultHandlerExceptionResolver が "Resolved [...]" を WARN で出す (URL・送信元は出さない) |

### メッセージの正体

| 項目 | 内容 |
|---|---|
| 英語原文 (正しい形) | Resolved [org.springframework.web.HttpRequestMethodNotSupportedException: Request method 'POST' is not supported] |
| ID / レベル | ID なし (Spring Framework) / WARN |
| ロガー | org.springframework.web.servlet.mvc.support.DefaultHandlerExceptionResolver (warnLogCategory = 自分のクラス名) |
| 出す場所 | AbstractHandlerExceptionResolver#logException → buildLogMessage = "Resolved [" + 例外 + "]" |
| 応答 | HTTP 405 + Allow: GET (検証で確認) |
| ログの経路 | spring-jcl → (EAP が付ける) Log4j 2 API → JBoss LogManager → コンソール / server.log |

### 動作原理

- DispatcherServlet が URL に合うハンドラを探す。URL は合うがメソッドが合わないと HttpRequestMethodNotSupportedException を投げる。
- 例外リゾルバが順に処理する: ExceptionHandlerExceptionResolver (@ExceptionHandler / @ControllerAdvice) → ResponseStatusExceptionResolver → DefaultHandlerExceptionResolver (Spring MVC 標準の例外を 4xx に変換)。
- DefaultHandlerExceptionResolver はコンストラクタで setWarnLogCategory(自分のクラス名) をしており、処理した例外を "Resolved [例外]" という WARN 1 行で記録する。URL・送信元・ヘッダは記録しない。
- @ControllerAdvice で先に処理すると、DefaultHandlerExceptionResolver まで届かないので、この 1 行は出なくなる (代わりに自分で詳しい 1 行を出せる)。

### 動作イメージ

```text
[リクエスト] POST /iwinmichl/api/hello  (ハンドラは @GetMapping("/hello") だけ)
 DispatcherServlet → HandlerMapping: URL は一致、メソッド不一致 → HttpRequestMethodNotSupportedException
 例外リゾルバ
  ├ ExceptionHandlerExceptionResolver (@ControllerAdvice)  … 修正後はここで処理 → "HTTP 405 method=POST uri=... remote=..." を記録
  └ DefaultHandlerExceptionResolver                          … 修正前はここで処理 → "Resolved [...]" (WARN) ★今回
 → 405 Method Not Allowed / Allow: GET
```

### 歴史・背景・必要になった経緯

- 1999 HTTP/1.1 (RFC 2616) で 405 と Allow ヘッダが定義され、2022 RFC 9110 に引き継がれている。
- 2007 Spring 2.5 でアノテーションによるマッピング (@RequestMapping)、2009 Spring 3.0 で DefaultHandlerExceptionResolver。
- 2018-09 Spring 5.1 のログ整理で、文言が "Resolved exception caused by Handler execution: ..." から "Resolved [...]" に変わった (ソースで確認)。Spring 6 では 405 も warnLogCategory の WARN として出る。

### この環境での原因と切り分け

GET 専用の URL に POST が届いています。誰が・どの URL に送ったかがログに無いので、まずそれを記録できるようにします。

| よくある原因 | 見分け方 |
|---|---|
| フォームや JavaScript の送信先・メソッドの誤り | Referer が自サイトの画面。特定の URL に集中 |
| エラーページへの内部転送で POST のまま届く | dispatcher=ERROR、errorOrigin に元の URL (MethodNotAllowedAdvice が記録) |
| セッション切れ後の再送信・ブラウザの戻る | 同じ利用者の直前の要求を確認 |
| 脆弱性スキャナ・ボット | User-Agent、送信元 IP (X-Forwarded-For)、ランダムな URL |
| ALB のヘルスチェック | ヘルスチェックは GET / HEAD なので通常は原因にならない |

### 影響度と放置した場合のリスク

危険度 B。サーバの故障ではなく「要求の誤り (4xx)」です。ただし自サイトの画面からの送信なら機能が壊れており、スキャナなら攻撃の予兆の可能性もあるので、正体を確かめて対処を決めます。

### 対処方針の比較

| 方式 | 内容 | 評価 |
|---|---|---|
| 送信元と URL を記録 ★推奨 | 4xx/5xx だけの JSON アクセスログ (jboss-cli) + 405 の詳細 1 行 (@ControllerAdvice) | ◎ 原因が分かる |
| マッピングを直す | 正しい送信なら @PostMapping を追加 / 誤りなら送信側を直す | ◎ 原因が分かったら |
| スキャナなら入口で遮断 | AWS WAF のルール等 | ○ |
| ログレベルを下げる | DefaultHandlerExceptionResolver を ERROR に | △ 原因が分かってから |

### 実装

**サーバ側: 4xx/5xx の JSON アクセスログ (応答完了後に判定されるので応答コードで絞れる)**

```text
# 60-undertow.cli (抜粋)
/subsystem=undertow/server=default-server/http-listener=default:write-attribute(name=proxy-address-forwarding, value=true)
/subsystem=undertow/server=default-server/http-listener=default:write-attribute(name=record-request-start-time, value=true)
/subsystem=undertow/server=default-server/host=default-host/setting=console-access-log:add( \
    include-host-name=false, \
    predicate="regex(pattern=\"^[45]\", value=\"%s\", full-match=false)", \
    attributes={date-time={key=timestamp, date-format="yyyy-MM-dd'T'HH:mm:ss.SSSXXX"}, remote-ip={key=client}, \
                request-method={key=method}, request-url={key=path}, query-string={key=query}, response-code={key=status}, \
                response-time={key=ms, time-unit=MILLISECONDS}, \
                request-header={key-prefix="h_", names=["X-Forwarded-For","User-Agent","Referer"]}})
```

**アプリ側: 405 を詳しく 1 行で記録**

```java
@ExceptionHandler(HttpRequestMethodNotSupportedException.class)
public ResponseEntity<String> handleMethodNotAllowed(HttpRequestMethodNotSupportedException ex, HttpServletRequest req) {
    // method, uri, query, dispatcher, errorOrigin, remote, X-Forwarded-For, User-Agent, Referer を 1 行で WARN
    // (全文は implementation/app/.../web/MethodNotAllowedAdvice.java。改行の混入を除去してから記録)
    return new ResponseEntity<>("Method Not Allowed", headersWithAllow, HttpStatus.METHOD_NOT_ALLOWED);
}
```

### 確認方法

```text
curl -i -X POST http://localhost:8080/iwinmichl/api/hello   # 405 / Allow: GET
# ログ (検証結果):
# WARN [com.example.iwinmichl.web.MethodNotAllowedAdvice] HTTP 405 method=POST uri=/iwinmichl/api/hello ... allowed=[GET]
# {"eventSource":"web-access","timestamp":"...","client":"...","method":"POST","path":"/iwinmichl/api/hello","status":405,"ms":...}
```

### 検証結果 (実測)

| 集計項目 (check-warnings.sh) | S0 修正前 | S1 修正後 (system/remove) | S1e 修正後 (elytron) | S1d 修正後 (dedicated) |
|---|---|---|---|---|
| Resolved [...HttpRequestMethodNotSupported...] | 1 | 0 | 0 | 0 |
| HTTP 405 detail line (MethodNotAllowedAdvice) | 0 | 1 | 1 | 1 |

S0 = 修正前を再現した状態、S1 系 = 本書の実装を適用した状態。シナリオの詳細と全ログは「検証結果」シート (md では「検証結果」章)。

### 出典

- [Spring DefaultHandlerExceptionResolver (v6.2)](https://github.com/spring-projects/spring-framework/blob/v6.2.11/spring-webmvc/src/main/java/org/springframework/web/servlet/mvc/support/DefaultHandlerExceptionResolver.java)
- [RFC 9110 HTTP Semantics (405 / Allow)](https://www.rfc-editor.org/rfc/rfc9110)
- [EventLoggerHttpHandler (console-access-log の predicate は応答完了後に評価)](https://github.com/wildfly/wildfly/blob/35.0.1.Final/undertow/src/main/java/org/wildfly/extension/undertow/EventLoggerHttpHandler.java)

## ⑩ IJ030027: 有効でない接続を破棄する (Ping failed: java.lang.reflect.InvocationTargetException)

**危険度 B**

**ユーザー環境のログ (原文)**

```text
org.jboss.jca.adapters.jdbc.xa.XAManagedConnectionFactory default task-7 IJ030027: Destroying connection that is not valid, due to the following exception: com.mysql.cj.jdbc.ConnectionWrapper@752a69a6: java.sql.SQLException: Ping failed: java.lang.reflect.InvocationTargetException
```

### ひとことで (小学生向け)

> **【小学生にもわかる説明】**  
> タクシー会社 (接続プール) は、お客さん (リクエスト) に車 (DB 接続) を貸す前に、エンジンがかかるか確かめます (ping)。
> 長く駐車していた車は、知らないうちにバッテリーが上がっていました (DB 側に回線を切られていた)。
> 点検係は「この車は動かないので廃車にします。理由は…」と日記に書き (⑩)、配車係も「点検に通らなかった車を廃車にしました」と書いて (⑪)、別の車を出しました。お客さんは何も気づかずに目的地に着きます。

| たとえ | 本当の仕組み |
|---|---|
| 車 | DB への物理接続 (XA 接続。Connector/J の ConnectionWrapper) |
| エンジンの点検 | valid-connection-checker = MySQLValidConnectionChecker (接続の ping メソッドをリフレクションで呼ぶ) |
| バッテリー上がり | DB の wait_timeout や、経路 (NAT / NLB 等) のアイドル切断で TCP がもう切れている |
| 点検係の日記 | ⑩ IJ030027 (理由 = 例外の連鎖付き) |
| 配車係の日記 | ⑪ IJ000621 (貸出時検証で破棄した記録) |

### メッセージの正体

| 項目 | 内容 |
|---|---|
| 英語原文 | IJ030027: Destroying connection that is not valid, due to the following exception: %s |
| ID / レベル | IJ030027 / WARN (例外の連鎖 = Caused by が続けて出力される) |
| ロガー | org.jboss.jca.adapters.jdbc.xa.XAManagedConnectionFactory |
| 出す場所 | BaseWrapperManagedConnectionFactory#getInvalidConnections (貸出時検証・背景検証のどちらからも呼ばれる) |
| "Ping failed: ...InvocationTargetException" | MySQLValidConnectionChecker が ping をリフレクションで呼び、包まれた例外を SQLException("Ping failed: " + e, e) にしたもの |
| 本当の理由の見方 | 直後の Caused by を読む (検証: CommunicationsException: The client was disconnected by the server because of inactivity. See wait_timeout ...) |

### 動作原理

- データソースは validate-on-match=true (貸出時検証) と MySQLValidConnectionChecker で構成されている (⑪ がリクエスト処理スレッドで出ていること、Ping failed の文言から推定)。
- 貸出時、プールは待機中の接続を 1 本取り出し、getInvalidConnections → isValidConnection → MySQLValidConnectionChecker#isValidConnection を呼ぶ。
- チェッカは接続クラスの ping メソッドを探し (Connector/J の ConnectionWrapper にある)、Method#invoke で呼ぶ。TCP がもう切れていると ping の中で CommunicationsException が起き、InvocationTargetException に包まれて返る。チェッカはそれを SQLException("Ping failed: " + e.toString(), e) にして返す。
- ファクトリは IJ030027 を例外の連鎖付きで出し、その接続を「無効」と答える → プールが IJ000621 を出して破棄 → 次の接続を試す / 新しく作る。
- アプリには正常な接続が渡るので、この 2 行は「プールが自分で直した」記録。検証でも放置後の要求は HTTP 200 だった。

### 動作イメージ

```text
[待機] 接続はプールで待機 …… その間に
          ├ MySQL/Aurora: wait_timeout を超えた無操作の接続を切断 (8.0.24 以降はエラー 4031 を送ってから切る)
          └ 経路: NAT Gateway / NLB などが 350 秒の無通信で状態を捨てる (以後のパケットに RST)
[貸出 (default task-N)]
 プール: 待機中の接続を取り出す → validate-on-match → MySQLValidConnectionChecker
   → ConnectionWrapper.ping() (リフレクション) → 例外 → InvocationTargetException
   → SQLException("Ping failed: ...") → IJ030027 (WARN, Caused by 付き) ★⑩
 プール: その接続を破棄 → IJ000621 (WARN) ★⑪ → 別の接続 / 新規接続を渡す
 アプリ: 正常な接続で処理を続ける (エラーにならない)
```

### 歴史・背景・必要になった経緯

- JDBC 2.0 (1999) で接続プールが標準化され、使い回す接続が「いつの間にか死んでいる」問題が生まれた。
- JBoss の JCA 実装 (JBossJCA → 2011 年以降 IronJacamar) は、DB ごとの検証クラス (valid-connection-checker) と、致命的エラーを判定する exception-sorter を用意し、貸出時 (validate-on-match) または定期 (background-validation) の検証を選べるようにした。
- 2021 MySQL 8.0.24: wait_timeout で切断するとき、理由 (ER_CLIENT_INTERACTION_TIMEOUT = 4031) をクライアントに送るようになった (WL#12999)。以前は「Communications link failure」としか分からなかった。
- クラウドでは、NAT Gateway や NLB の 350 秒のアイドル切断が新たな原因として加わった (NLB は 2024-09 から変更可能)。

### この環境での原因と切り分け

「プールで待機している間に、接続が外から切られていた」ことは確実です。誰が切ったかは、IJ030027 の Caused by と、⑪ の「ログ時刻 - lastReturned (放置時間)」で判別します。

| Caused by の文言 | 切った者 | 放置時間の目安 |
|---|---|---|
| The client was disconnected by the server because of inactivity (4031) | DB の wait_timeout / interactive_timeout | ≧ wait_timeout (Aurora の既定は 28800 秒) |
| Connection reset / Communications link failure | 経路のアイドル切断 (NAT Gateway・NLB 350 秒等)、DB の再起動・フェイルオーバー | ≧ 350 秒なら経路を疑う |
| Read timed out | 半開き TCP (相手が消えた)。socketTimeout で打ち切った | - |

**検証ログ (MySQL wait_timeout=150 秒、170 秒放置) での実行結果**

```text
python analyze-ij-log.py server.log --tz +09:00
 (B) ⑪ IJ000621 死んでいた接続の放置時間 (ログ時刻 - lastReturned)
  log=2026-10-11 05:33:53+0000 lastReturned=2026-10-11T05:31:03Z idle=    170s
  -> 最も短い放置 170s で既に死んでいた。idle-timeout-minutes は 1 以下を推奨
 (C) ⑩ IJ030027 の根本原因 (直後の Caused by から分類)
      1  DB 側の wait_timeout / interactive_timeout による切断 (MySQL 8.0.24+ はエラー 4031 を返す)
```

> **【注意・補足】**  
> ユーザー環境の ⑪ は lastValidated が lastReturned の約 19 分前でした。lastValidated は「作成時刻か、最後の背景検証の時刻」で、貸出時検証では更新されません。背景検証 (background-validation) は動いていないと読めます (Red Hat の推奨どおり、貸出時検証のみの構成)。

### 影響度と放置した場合のリスク

危険度 B。アプリへのエラーにはなっていませんが、(1) 貸出のたびに死んだ接続を引くと検証と再接続のぶん遅くなる、(2) 半開き TCP では ping が socketTimeout まで固まる、(3) exception-sorter が無いと、使用中に死んだ接続がプールに戻されて別の要求が失敗する、といった形で悪化しえます。頻発するなら設定と経路の不一致です。

### 対処方針の比較

| 対処 | 内容 | 効く原因 |
|---|---|---|
| idle-timeout-minutes を短く ★ | 切られる前にプール側で捨てる。IdleRemover は idle-timeout の半分間隔なので最長 1.5 倍残る点を考慮 | wait_timeout / 経路のアイドル切断 |
| exception-sorter を追加 ★ | MySQLExceptionSorter。使用中に致命的エラーが出た接続をプールに戻さない | フェイルオーバー・再起動 |
| 貸出時検証は維持 ★ | validate-on-match=true + MySQLValidConnectionChecker。背景検証とは併用しない (Red Hat 推奨) | すべて (最後の砦) |
| TCP keepalive | Connector/J の tcpKeepAlive=true (既定) + ECS の systemControls で net.ipv4.tcp_keepalive_time=60 等 | 経路のアイドル切断 (wait_timeout には効かない) |
| socketTimeout | 半開き TCP で ping が固まらないよう上限を付ける (最長クエリより長く) | 半開き |
| DB / 経路側の設定 | wait_timeout、NLB の tcp.idle_timeout.seconds、経路から NAT を外す 等 | 原因に応じて |

### 実装 (jboss-cli + ECS)

```text
# 30-datasource-mysql-xa.cli (抜粋)
/subsystem=datasources/xa-data-source=MIF02JA_JDS:add( ... \
    idle-timeout-minutes="${env.DB_IDLE_TIMEOUT_MIN:5}", \
    validate-on-match=true, background-validation=false, \
    valid-connection-checker-class-name=org.jboss.jca.adapters.jdbc.extensions.mysql.MySQLValidConnectionChecker, \
    exception-sorter-class-name=org.jboss.jca.adapters.jdbc.extensions.mysql.MySQLExceptionSorter, ...)
/subsystem=datasources/xa-data-source=MIF02JA_JDS/xa-datasource-properties=TcpKeepAlive:add(value=true)
/subsystem=datasources/xa-data-source=MIF02JA_JDS/xa-datasource-properties=SocketTimeout:add(value="${env.DB_SOCKET_TIMEOUT_MS:120000}")
```

```json
// ECS タスク定義 (抜粋): awsvpc / Fargate ではタスク内の全コンテナに効くので 1 コンテナにだけ書く
"systemControls": [
  { "namespace": "net.ipv4.tcp_keepalive_time",   "value": "60" },
  { "namespace": "net.ipv4.tcp_keepalive_intvl",  "value": "10" },
  { "namespace": "net.ipv4.tcp_keepalive_probes", "value": "6" }
]
```

### 確認方法

```bash
# 待機中の接続が切られる時間より長く放置してから要求し、
grep -c -E 'IJ030027|IJ000621' server.log   # → 0
/opt/jboss-eap/bin/jboss-cli.sh -c '/subsystem=datasources/xa-data-source=MIF02JA_JDS/statistics=pool:read-resource(include-runtime=true)'
# DestroyedCount / InvalidCount などの増え方を見る (statistics-enabled=true)
```

### 検証結果 (実測)

| 集計項目 (check-warnings.sh) | S0 修正前 | S1 修正後 (system/remove) | S1e 修正後 (elytron) | S1d 修正後 (dedicated) |
|---|---|---|---|---|
| IJ030027 destroying connection not valid | 1 | 0 | 0 | 0 |
| IJ000621 destroying conn. not validated | 1 | 0 | 0 | 0 |

S0 = 修正前を再現した状態、S1 系 = 本書の実装を適用した状態。シナリオの詳細と全ログは「検証結果」シート (md では「検証結果」章)。

### 出典

- [IronJacamar AdaptersLogger (IJ030027/030040/030042)](https://github.com/ironjacamar/ironjacamar/blob/3.0.10.Final/adapters/src/main/java/org/jboss/jca/adapters/AdaptersLogger.java)
- [IronJacamar MySQLValidConnectionChecker](https://github.com/ironjacamar/ironjacamar/blob/3.0.10.Final/adapters/src/main/java/org/jboss/jca/adapters/jdbc/extensions/mysql/MySQLValidConnectionChecker.java)
- [EAP 6/7/8 JDBC datasource not fault tolerant ... needs connection validation enabled](https://access.redhat.com/solutions/156103)
- [WL#12999 wait_timeout 切断時のエラー通知 (4031)](https://dev.mysql.com/worklog/task/?id=12999)
- [NAT ゲートウェイの接続トラブルシューティング (350 秒のアイドルタイムアウト)](https://repost.aws/knowledge-center/vpc-troubleshoot-nat-gateway-connection)
- [NLB の TCP アイドルタイムアウトの変更](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/update-idle-timeout.html)
- [Fargate の追加 Linux 制御 (systemControls, 2023-08-09)](https://aws.amazon.com/blogs/containers/announcing-additional-linux-controls-for-amazon-ecs-tasks-on-aws-fargate/)
- [ECS TaskDefinition SystemControl (Fargate はプラットフォーム 1.4.0 以降)](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-properties-ecs-taskdefinition-systemcontrol.html)
- [Aurora MySQL version 8.4](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraMySQL.MySQL84.html)

## ⑪ IJ000621: 検証できなかった接続を破棄する (プール側の記録)

**危険度 B**

**ユーザー環境のログ (原文)**

```text
org.jboss.jca.core.connectionmanager.pool.strategy.OnePool default-task-7 IJ000621: Destroying connection that could not be validated: org.jboss.jca.core.connectionmanager.listener.TxConnectionListener@384d5be6[state=NORMAL managed connection=org.jboss.jca.adapters.jdbc.xa.XAManagedConnection@c24620c connection handles=0 lastReturned=1788828592947 lastValidated=1788827437514 lastCheckedOut=1788828592692 trackByTx=false pool=...OnePool@4a8f027f mcp=SemaphoreConcurrentLinkedDequeManagedConnectionPool@4a9fc932[pool=MIF02JA_JDS] xaResource=XAResourceWrapperImpl@5ece3ccd[... productName=MySQL productVersion=8.4.7 jndiName=java:/jdbc/MIF02JA_JDS] txSync=null]
```

### ひとことで (小学生向け)

> **【小学生にもわかる説明】**  
> ⑩ で「この車は動かない」と分かった車を、配車係 (プール) が実際に廃車にしたときの日記です。
> 日記には車の記録 (いつ最後に返ってきたか、いつ点検したか、いつ貸したか) も書いてあるので、「どれくらい駐車していたら動かなくなったか」を計算できます。

| たとえ | 本当の仕組み |
|---|---|
| 配車係 | OnePool (プール戦略) / SemaphoreConcurrentLinkedDequeManagedConnectionPool |
| 車の記録 | TxConnectionListener の lastReturned / lastValidated / lastCheckedOut など |
| 駐車していた時間 | ログの時刻 - lastReturned |

### メッセージの正体

| 項目 | 内容 |
|---|---|
| 英語原文 | IJ000621: Destroying connection that could not be validated: %s |
| ID / レベル | IJ000621 / WARN |
| ロガー | org.jboss.jca.core.connectionmanager.pool.strategy.OnePool |
| 出す場所 | SemaphoreConcurrentLinkedDequeManagedConnectionPool#getConnection の validate-on-match 分岐だけ |
| スレッドから分かること | default task-7 = HTTP 要求の処理スレッド → 貸出時検証で見つけた (背景検証は別スレッドで、IJ000621 は出さない) |

| フィールド (⑪のログ) | 意味 | この環境の値の読み方 |
|---|---|---|
| state=NORMAL | 接続リスナの状態 (NORMAL / DESTROY / DESTROYED) | 破棄の直前なので NORMAL |
| connection handles=0 | アプリに渡している接続ハンドルの数 | 0 = 誰も使っていない (プールで待機していた) |
| lastReturned=1788828592947 | 最後にプールへ戻された時刻 (エポックミリ秒, UTC) | 2026-09-08 09:49:52.947 JST |
| lastValidated=1788827437514 | 作成時刻、または最後の背景検証の時刻 (貸出時検証では更新されない) | 2026-09-08 09:30:37.514 JST (約 19 分前 = 背景検証は動いていない可能性が高い) |
| lastCheckedOut=1788828592692 | 最後に貸し出された時刻 | 09:49:52.692 JST → 255 ms 使って返却 |
| trackByTx=false | トランザクションに接続を固定するか | false (通常) |
| mcp=SemaphoreConcurrentLinkedDequeManagedConnectionPool | プールの実装クラス | EAP 8 の既定 |
| xaResource=XAResourceWrapperImpl[... pad=false overrideRmValue=false productName=MySQL productVersion=8.4.7] | XA リソースの情報 (pad-xid、same-rm-override、DB の製品名と版) | Aurora MySQL 8.4.7 (2026-05 GA の最初のマイナー版と一致) |

### 動作原理

- getConnection で待機中の接続を取り出し、matchManagedConnections のあと validate-on-match が true なら getInvalidConnections で検証する (⑩)。
- 無効と判定されたら IJ000621 を出し、プールから外して destroy する。続けて次の待機接続を試すか、新しい接続を作る。
- 背景検証 (background-validation) で無効を見つけた場合は IJ030027 だけで、IJ000621 は出ない (ソースで確認)。
- lastValidated は作成時と背景検証のときにだけ更新され、貸出時検証では更新されない。

### 動作イメージ

```text
[時刻の読み方 (ユーザー環境の値)]
 09:30:37.514  lastValidated  … 接続の作成 (または最後の背景検証)
 09:49:52.692  lastCheckedOut … 貸出
 09:49:52.947  lastReturned   … 返却 (255 ms 使用)
      ↓  ここから待機 (時間 = IJ000621 のログ時刻 - 09:49:52.947)
 ??:??:??      IJ000621       … 次の貸出時の検証で失敗 → 破棄
```

### 歴史・背景・必要になった経緯

⑩ と同じです。IronJacamar は「点検 (ファクトリ側の IJ030027)」と「廃車 (プール側の IJ000621)」を別々に記録するため、2 行がペアで出ます。

### この環境での原因と切り分け

⑩ と同じ原因です。⑪ のログ時刻と lastReturned の差 (放置時間) を、DB の wait_timeout や経路のアイドル切断 (350 秒等) と比べます。ユーザー環境のログには行の時刻が含まれていないため、CloudWatch Logs で同じ行の時刻を確認してください。

```bash
python analyze-ij-log.py server.log --tz +09:00   # (B) に放置時間と idle-timeout の推奨値が出る
```

### 影響度と放置した場合のリスク

危険度 B。⑩ と同じ。件数と時間帯 (夜間・休日明けの最初の要求に集中するか等) を CloudWatch Logs のメトリクスフィルタで監視すると、設定の妥当性を継続的に確かめられます。

### 対処方針の比較

⑩ と同じ (idle-timeout-minutes の短縮、exception-sorter、貸出時検証の維持、TCP keepalive)。放置時間の実測値から idle-timeout-minutes を決めます: idle-timeout × 1.5 < 最短の放置時間 (切られる時間)。

### 実装

```json
# ECS タスク定義の環境変数で調整 (30-datasource-mysql-xa.cli が参照)
{ "name": "DB_IDLE_TIMEOUT_MIN", "value": "5" }
```

### 確認方法

```text
grep -c IJ000621 server.log   # → 0
# CloudWatch Logs Insights
fields @timestamp, @message | filter @message like /IJ000621/ | stats count() by bin(1h)
```

### 検証結果 (実測)

| 集計項目 (check-warnings.sh) | S0 修正前 | S1 修正後 (system/remove) | S1e 修正後 (elytron) | S1d 修正後 (dedicated) |
|---|---|---|---|---|
| IJ000621 destroying conn. not validated | 1 | 0 | 0 | 0 |
| IJ030027 destroying connection not valid | 1 | 0 | 0 | 0 |

S0 = 修正前を再現した状態、S1 系 = 本書の実装を適用した状態。シナリオの詳細と全ログは「検証結果」シート (md では「検証結果」章)。

### 出典

- [IronJacamar SemaphoreConcurrentLinkedDequeManagedConnectionPool (IJ000615/000621)](https://github.com/ironjacamar/ironjacamar/blob/3.0.10.Final/core/impl/src/main/java/org/jboss/jca/core/connectionmanager/pool/mcp/SemaphoreConcurrentLinkedDequeManagedConnectionPool.java)
- [EAP 6/7/8 JDBC datasource not fault tolerant ... needs connection validation enabled](https://access.redhat.com/solutions/156103)
- [Aurora MySQL version 8.4](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraMySQL.MySQL84.html)

## ⑫ IJ030042: 開いたままの ResultSet を閉じた (自分で後片付けしてください)

**危険度 B**

**ユーザー環境のログ (原文)**

```text
org.jboss.jca.adapters.jdbc.WrappedConnection default-task-7 IJ030042: Closing a result set you left open please do your own housekeeping for: com.mysql.cj.jdbc.result.ResultSetImpl@46f61974:java.lang.Throwable: STACKTRACE
```

### ひとことで (小学生向け)

> **【小学生にもわかる説明】**  
> ⑧ の続きです。メモ用紙 (Statement) だけでなく、そこに書いた答えのプリント (ResultSet) も出しっぱなしでした。
> 司書がメモ用紙を片付けるときに、一緒にプリントも片付けて「これも自分で片付けてね」と書きました。

| たとえ | 本当の仕組み |
|---|---|
| 答えのプリント | ResultSet (SELECT の結果) |
| メモ用紙と一緒に片付ける | Statement を閉じるとき、その Statement の ResultSet も閉じる (WrappedStatement) |

### メッセージの正体

| 項目 | 内容 |
|---|---|
| 英語原文 | IJ030042: Closing a result set you left open, please do your own housekeeping for: %s |
| ID / レベル | IJ030042 / WARN (%s は ResultSet の toString。com.mysql.cj.jdbc.result.ResultSetImpl@...) |
| ロガー | org.jboss.jca.adapters.jdbc.WrappedConnection (WrappedStatement が接続のロガーで出す) |
| 出す場所 | WrappedStatement の closeResultSets (track-statements=TRUE のとき) |
| 付いてくるスタック | ResultSet を作った呼び出し元 (検証: DbServlet.leak(DbServlet.java:71)) |

### 動作原理

- track-statements=TRUE のとき、WrappedStatement は自分が作った ResultSet とその作成箇所を記録する。
- Statement が閉じられる (アプリが閉じる / ⑧ のように接続返却時に IronJacamar が閉じる) とき、開いたままの ResultSet があれば IJ030042 とスタックを出して閉じる。
- ⑧ と同じリクエストで、Statement も ResultSet も閉じていない場合は、⑧ → ⑫ の順にペアで出る (検証でも同じ)。

### 動作イメージ

```text
c.close()  (Statement も ResultSet も閉じていない)
  → IronJacamar: Statement を閉じる → IJ030040 (⑧)
       → その Statement の ResultSet を閉じる → IJ030042 (⑫) ★今回
```

### 歴史・背景・必要になった経緯

⑧ と同じ (JBossJCA から IronJacamar に引き継がれた track-statements の機能)。

### この環境での原因と切り分け

アプリのコードが ResultSet を閉じていません。⑧ と同じ箇所のことが多いので、analyze-ij-log.py のランキングで両方を一緒に直します。

### 影響度と放置した場合のリスク

危険度 B。MySQL Connector/J は既定で結果を全件クライアントに読み込むため、大きな結果を閉じずに持ち続けるとメモリを圧迫します。ストリーミング (fetchSize=Integer.MIN_VALUE) を使っている場合は、閉じるまで同じ接続で次の SQL を実行できません。

### 対処方針の比較

⑧ と同じ。ResultSet も try-with-resources で閉じる (Statement を閉じれば ResultSet も閉じるが、明示的に閉じる方が分かりやすい)。Spring JdbcTemplate の queryForStream など Stream を返す API は、呼び出し側で Stream を閉じないと同じ警告になる。

### 実装

```java
try (Connection c = ds.getConnection();
     PreparedStatement ps = c.prepareStatement(sql);
     ResultSet rs = ps.executeQuery()) {
    ...
}
// Spring: try (Stream<Emp> s = jdbcTemplate.queryForStream(sql, mapper)) { ... }
```

### 確認方法

```bash
grep -c IJ030042 server.log   # → 0 (DB_TRACK_STATEMENTS=TRUE の検証環境で)
```

### 検証結果 (実測)

| 集計項目 (check-warnings.sh) | S0 修正前 | S1 修正後 (system/remove) | S1e 修正後 (elytron) | S1d 修正後 (dedicated) |
|---|---|---|---|---|
| IJ030042 result set left open | 1 | 0 | 0 | 0 |
| IJ030040 statement left open | 1 | 0 | 0 | 0 |

S0 = 修正前を再現した状態、S1 系 = 本書の実装を適用した状態。シナリオの詳細と全ログは「検証結果」シート (md では「検証結果」章)。

### 出典

- [IronJacamar AdaptersLogger (IJ030027/030040/030042)](https://github.com/ironjacamar/ironjacamar/blob/3.0.10.Final/adapters/src/main/java/org/jboss/jca/adapters/AdaptersLogger.java)
- [IronJacamar Defaults (track-statements=NOWARN 等)](https://github.com/ironjacamar/ironjacamar/blob/3.0.10.Final/common/api/src/main/java/org/jboss/jca/common/api/metadata/Defaults.java)

## ⑬ IJ000615: 使用中の接続をプールで破棄した (停止時)

**危険度 A**

**ユーザー環境のログ (原文)**

```text
org.jboss.jca.core.connectionmanager.pool.strategy.OnePool ServerService Thread Pool -- 80) IJ000615: Destroying active connection in pool: MIF02JA_JDS (org.jboss.jca.adapters.jdbc.xa.XAManagedConnection@6c1a1d2)
```

### ひとことで (小学生向け)

> **【小学生にもわかる説明】**  
> お店を閉める時間 (タスク停止) になりました。本当は「新しいお客さんはお断りして、いま対応中のお客さんの用事が終わるまで待ってから閉店」したいのに、待ち時間の設定が 0 秒だったので、レジ (DB 接続) を使っている途中のお客さんがいるのに、レジを片付けてしまいました。
> 係は「使用中のレジを片付けました」と日記に書きました。そのお客さんの用事は失敗しています。

| たとえ | 本当の仕組み |
|---|---|
| 閉店の合図 | ECS からの SIGTERM (ローリングデプロイ・スケールイン・タスク停止) |
| 新しいお客さんを断って待つ | EAP のサスペンド (新規要求を 503 で断り、処理中の要求の完了を待つ) |
| 待ち時間の設定 | システムプロパティ org.wildfly.sigterm.suspend.timeout (秒)。既定 0 = 待たない |
| レジを片付ける | データソースのサービス停止 → プールの shutdown → 使用中の接続も破棄 (IJ000615) |

### メッセージの正体

| 項目 | 内容 |
|---|---|
| 英語原文 | IJ000615: Destroying active connection in pool: %s (%s) |
| ID / レベル | IJ000615 / WARN |
| ロガー | org.jboss.jca.core.connectionmanager.pool.strategy.OnePool |
| 出す場所 | SemaphoreConcurrentLinkedDequeManagedConnectionPool#shutdown (貸出中の接続があるときに出す) |
| スレッド ServerService Thread Pool | サーバのサービスを非同期で起動・停止する実行スレッド (データソースの停止はここで動く) |
| 一緒に出るもの (実測) | WFLYSRV0272: Suspending server → WFLYSRV0220: Server shutdown has been requested via an OS signal → IJ000615 → IJ030022: Lock owned during cleanup: default task-2 (使っていた要求のスレッド) |

### 動作原理

- プール (ManagedConnectionPool) の shutdown は、データソースのサービスが止まるとき (サーバ停止・リロード、データソースの無効化・削除、ドライバのアンデプロイ等) に呼ばれる。貸出中の接続があれば IJ000615 を出し、まとめて破棄する。
- SIGTERM を受けた JVM はシャットダウンフックを走らせ、サーバが RUNNING なら先にサスペンドする。待ち時間は org.wildfly.sigterm.suspend.timeout (秒)。未設定 (既定) は 0 で、ほぼ待たずにサービス停止へ進む (BootstrapImpl で確認)。EAP 8.1 の構成ガイドにも「OS シグナルで正常にシャットダウンするには org.wildfly.sigterm.suspend.timeout を設定する」とある。
- SIGTERM が JVM に届く前提として、standalone.sh は LAUNCH_JBOSS_IN_BACKGROUND が設定されているときだけ、受けた TERM を JVM に中継する。未設定で standalone.sh が PID 1 だと JVM に届かず、stopTimeout 後の SIGKILL で強制終了になる (この場合 IJ000615 も出ないが、停止処理自体が一切走らない)。
- ユーザー環境で IJ000615 が出ている = SIGTERM は JVM に届いているが、待ち時間が足りない (おそらく 0) と読める。

### 動作イメージ

```text
[修正前: suspend.timeout=0]
 ECS: SIGTERM → standalone.sh (LAUNCH_JBOSS_IN_BACKGROUND=true) → JVM
 JVM: WFLYSRV0272 Suspending server → すぐ (0 秒 + 0.5 秒) 停止へ → WFLYSRV0220
      データソース停止 → 処理中の要求 (SELECT SLEEP(15)) の接続を破棄 → IJ000615 ★ / IJ030022
      → 要求は失敗 (検証: HTTP 000 = 応答なしで切断)
[修正後: suspend.timeout=30]
 JVM: WFLYSRV0211 Suspending server with 30000 ms timeout → 新規要求は 503、処理中の要求を待つ
      → 要求が完了 (検証: HTTP 200 "slept 15") → 停止 → IJ000615 なし
[LAUNCH_JBOSS_IN_BACKGROUND 未設定]
 ECS: SIGTERM → PID 1 のシェルが受けても JVM に届かない → stopTimeout まで待って SIGKILL (検証: 91 秒、終了コード 137)
```

### 歴史・背景・必要になった経緯

- 2015 WildFly 9: サスペンド / レジューム とグレースフルシャットダウン (request-controller) が導入された。
- その後、OS シグナル (SIGTERM) による停止でもサスペンドの待ち時間を指定できる org.wildfly.sigterm.suspend.timeout が加わった (EAP 8.1 構成ガイドに記載)。
- Docker (2013)、ECS (2015)、Kubernetes の普及で「SIGTERM → 猶予 → SIGKILL」がアプリ停止の標準手順になり、PID 1 とシグナル中継、猶予時間の設計が重要になった。
- ECS の stopTimeout は既定 30 秒、Fargate の上限は 120 秒。ALB の deregistration delay (既定 300 秒) の間に新規要求は止まる。

### この環境での原因と切り分け

SIGTERM 時のサスペンド待ち時間が既定の 0 秒のままで、停止の瞬間に処理中だった要求の DB 接続がプールごと破棄されています。停止以外 (デプロイ・:reload・データソースの無効化) でも同じ警告になるので、直前のログで区別します。

| 直前に出ているもの | 判断 |
|---|---|
| WFLYSRV0272 / WFLYSRV0211 (Suspending server)、WFLYSRV0220 (OS signal) | SIGTERM による停止中 → 本対処 |
| WFLYSRV0028 (Stopped deployment) だけ / 管理操作のログ | アンデプロイ・再デプロイ・リロード |
| IJ000100 (CCM が閉じ忘れの接続を閉じた) | 接続リーク (要求が終わっても返されない接続) の疑い |

```bash
python analyze-ij-log.py server.log   # (D) に「停止処理中=N / それ以外=M」が出る
```

### 影響度と放置した場合のリスク

危険度 A。デプロイやスケールインのたびに、処理中の要求が途中で失敗します (利用者にはエラー画面、XA トランザクションは中断 → ロールバックや未確定状態の回復処理)。リリース頻度が上がるほど影響が増えます。

### 対処方針の比較

| 対処 | 内容 | 評価 |
|---|---|---|
| サスペンド待ち時間 ★ | jboss-cli で /system-property=org.wildfly.sigterm.suspend.timeout (値は環境変数で上書き可) | ◎ 本体 |
| シグナル中継 ★ | entrypoint で LAUNCH_JBOSS_IN_BACKGROUND=true を export し、exec standalone.sh | ◎ 前提条件 |
| ECS の時間設計 ★ | 最長の要求時間 ≦ suspend.timeout < stopTimeout (Fargate は最大 120 秒)。ALB の deregistration delay も最長の要求以上 | ◎ |
| initProcessEnabled | tini がゾンビを回収しシグナルを子に渡す。LAUNCH_JBOSS_IN_BACKGROUND の代わりにはならない | ○ 補助 |
| ドライバはモジュールで | ドライバを deployments に置くと、再デプロイで依存データソースが止まる | ○ |

### 実装

**jboss-cli**

```text
# 00-system-properties.cli
if (outcome != success) of /system-property=org.wildfly.sigterm.suspend.timeout:read-resource
    /system-property=org.wildfly.sigterm.suspend.timeout:add(value="${env.EAP_SIGTERM_SUSPEND_TIMEOUT:30}")
end-if
```

**entrypoint**

```bash
# entrypoint.sh (抜粋)
export LAUNCH_JBOSS_IN_BACKGROUND=true
exec "${JBOSS_HOME}/bin/standalone.sh" "${ARGS[@]}" "$@"
```

**ECS**

```json
// ECS タスク定義 (抜粋)
"stopTimeout": 60,
"environment": [ { "name": "EAP_SIGTERM_SUSPEND_TIMEOUT", "value": "45" } ],
"linuxParameters": { "initProcessEnabled": true }
// ALB ターゲットグループ: deregistration_delay.timeout_seconds は最長の要求時間以上 (例 60)
```

### 確認方法

```bash
# 長い要求の最中にタスクを止める (ECS: aws ecs stop-task / ローカル: docker stop -t 90)
grep -E 'WFLYSRV0211|IJ000615' server.log
# → "Suspending server with 30000 ms timeout." が出て、IJ000615 が出ないこと。要求は正常応答
```

### 検証結果 (実測)

| 集計項目 (check-warnings.sh) | S0 修正前 | S0n 修正前・中継なし | S1 修正後 (system/remove) | S1e 修正後 (elytron) | S1d 修正後 (dedicated) |
|---|---|---|---|---|---|
| IJ000615 destroying active connection | 1 | 0 | 0 | 0 | 0 |
| WFLYSRV0211/0272 suspending server | 1 | 0 | 1 | 1 | 1 |
| WFLYSRV0220 shutdown requested via OS signal | 1 | 0 | 1 | 1 | 1 |
| IJ030022 lock owned during cleanup | 1 | 0 | 0 | 0 | 0 |

S0 = 修正前を再現した状態、S1 系 = 本書の実装を適用した状態。シナリオの詳細と全ログは「検証結果」シート (md では「検証結果」章)。

### 出典

- [JBoss EAP 8.1 Configuration Guide (サスペンドと OS シグナルによる正常シャットダウン)](https://docs.redhat.com/en/documentation/red_hat_jboss_enterprise_application_platform/8.1/html-single/configuration_guide/index)
- [BootstrapImpl (org.wildfly.sigterm.suspend.timeout)](https://github.com/wildfly/wildfly-core/blob/27.0.1.Final/server/src/main/java/org/jboss/as/server/BootstrapImpl.java)
- [standalone.sh (LAUNCH_JBOSS_IN_BACKGROUND とシグナル中継)](https://github.com/wildfly/wildfly-core/blob/27.0.1.Final/core-feature-pack/common/src/main/resources/content/bin/standalone.sh)
- [IronJacamar SemaphoreConcurrentLinkedDequeManagedConnectionPool (IJ000615/000621)](https://github.com/ironjacamar/ironjacamar/blob/3.0.10.Final/core/impl/src/main/java/org/jboss/jca/core/connectionmanager/pool/mcp/SemaphoreConcurrentLinkedDequeManagedConnectionPool.java)
- [ContainerDefinition stopTimeout (既定 30 秒、Fargate 最大 120 秒)](https://docs.aws.amazon.com/sdk-for-kotlin/api/latest/ecs/aws.sdk.kotlin.services.ecs.model/-container-definition/stop-timeout.html)

## ①深掘り: 追加質問と ExtraSLB 実装レビュー

### 結論 (先に 3 行)

| 質問 | 答え | 根拠 |
|---|---|---|
| Q1. ルート CA を入れた p12 を既定以外のディレクトリに置くと、この警告は出るのか | 出ない。警告はインバウンド用の applicationKS (application.keystore) のもので、自前 p12 の置き場所とは無関係。ただし自前 p12 を Elytron の key-store に登録しているので、そのパスを誤ると同じ WFLYELY00023 が「そのパス」でも出て、空のトラストストアのまま正常起動してしまう (アウトバウンド TLS が全滅)。 | KeyStoreService のソース / 実測 E1・E3 |
| Q2. standalone.sh の実行時引数でパスを渡していても出るのか | 出る。-Djavax.net.ssl.trustStore / keyStore は JDK (JSSE) の設定で、Elytron の key-store リソースはそれを読まない。引数で Elytron 側のパスを変えたいなら、key-store の path を ${env.X:既定値} などの式にする。 | 実測 E2 (-Djavax.net.ssl.keyStore を渡しても同じ警告) |
| Q3. どう対処するのが適切か | ALB で TLS を終端し 8080 だけで受ける本構成では、使っていないインバウンド HTTPS 一式を jboss-cli で削除するのが最適。自前トラストストアは required=true にするか、さらに単純な「UBI のシステムトラストストアに CA を入れる方式」に移す。 | 実測 E4〜E7 / 検証 S1・S1e・S1d |

> **【小学生にもわかる説明】**  
> 警告は「お客さんに見せる自分の身分証の金庫」の話で、ルート CA の p12 は「信頼できる発行所の名簿」の話です。名簿をどの部屋に置いても、金庫の警告は消えません。使っていない受付 (8443) と金庫を設計図から消すのが一番すっきりします。

### Container_ExtraSLB_JVM_https_outbounds の実装 (確認した内容)

| ファイル | やっていること |
|---|---|
| base/Dockerfile | EAP 8.1 の公式イメージ (eap81-openjdk17-runtime-openshift-rhel9) を FROM。BuildKit Secrets で証明書を受け取り、トラストストア生成 → application.keystore の事前生成 → embed-server で Elytron 設定を適用 → standalone_xml_history 削除 |
| base/scripts/build-truststore.sh | JDK の cacerts を PKCS12 に変換してコピーし、受領した証明書 (PEM/DER/PKCS#7) を <提供元>-ca-<n> として追加。/opt/app/security/extraslb-truststore.p12 (パスワード changeit、0444) |
| base/jboss-cli/configure-outbound-tls.cli | key-store=extraslb-trust-store (path は ${env.EXTRASLB_TRUSTSTORE_PATH:...} の式、required 指定なし)、trust-manager、client-ssl-context (TLSv1.3/1.2)、default-ssl-context に登録 |
| base/scripts/entrypoint.sh | 起動前チェック、(必要なら) embed-server、履歴の正規化、application.keystore の補完、exec standalone.sh -Djavax.net.ssl.trustStore=... -Djavax.net.ssl.trustStorePassword=... -Djavax.net.ssl.trustStoreType=... |
| base/scripts/provision-application-keystore.sh | applicationKS と同じ形 (alias=server, CN=localhost, RSA2048, 3650 日, JKS, パスワード password) の鍵ストアを keytool で事前生成 |
| docs/wflyely00023-application-keystore.md | 警告は applicationKS 由来でアウトバウンドとは無関係、と分析。対処として事前生成を採用、削除案は却下 |

### 評価: 正しい点

- 警告の出どころの判定 (applicationKS 由来でアウトバウンドとは無関係) は正しい。ソース (KeyStoreService / elytron-app feature group) と実測 E1・E2 で確認。
- cacerts を土台に CA を追加する設計は正しい。パブリック CA 宛 (AWS SDK 等) の通信を壊さない (実測: Google 宛も 3 種類のクライアントで成功)。
- 「Elytron の default-ssl-context」と「-Djavax.net.ssl.trustStore」の二層構えは必要。Apache CXF は TLS パラメータ未指定時に javax.net.ssl.trustStore / trustStoreType / trustStorePassword を自分で読んで SSLContext を作り、Elytron の default-ssl-context は使わない (CXF の jsse SSLUtils で確認)。
- BuildKit Secrets で証明書をイメージ層に残さない、CLI をビルド時に適用して起動時の embed-server をなくす、standalone_xml_history を消す、起動前チェックで理由を出して止める、はいずれも良い実装。

### 評価: 改善した方がよい点

| 現状 | 問題 | 改善 (本書の実装) |
|---|---|---|
| 1. application.keystore を事前生成 (provision) | 既知のパスワード (password) の秘密鍵 (CN=localhost) を全タスクで共有し、使っていない 8443 が待ち受け続ける (実測 E5: 8443 で CN=localhost を返す) | 11-inbound-https-remove.cli で 8443 一式を削除 (実測 E6: 待ち受けなし、警告 0)。ALB→タスクも暗号化するなら 12-inbound-https-dedicated.cli |
| 2. extraslb-trust-store に required が無い (既定 false) | パスを誤ると WFLYELY00023 (WARN) だけで正常起動し、既定 SSLContext 経由の HTTPS がパブリック CA 宛も含めて全滅 (実測 E3) | required=true (実測 E4: WFLYELY00022 で起動時に必ず失敗が見える) + entrypoint の事前チェック |
| 3. ベースイメージが OpenJDK 17 の OpenShift 用 EAP イメージ | EAP 8.1 で OpenJDK 17 の OpenShift イメージは非推奨 (8.2 で削除予定)。実環境は OpenJDK 21 | UBI 9.8 + Red Hat build of OpenJDK 21 (ubi9/openjdk-21-runtime) を実行ベースに |
| 4. cacerts をコピーして Elytron に読ませる | ビルド時点のスナップショットで OS の CA 更新に追随しない。期限切れのルートがあると Elytron が WFLYELY00024 を出す | TRUST_MODE=system: CA を /etc/pki/ca-trust/source/anchors に置いて update-ca-trust。JDK の cacerts に入る (実測 E7)。-D も Elytron 設定も不要 |
| 5. -Djavax.net.ssl.trustStorePassword を引数で渡す | プロセス引数 (ps / /proc/<pid>/cmdline) に出る (中身は公開証明書なので実害は小さい) | system モードなら不要 |
| 6. entrypoint で LAUNCH_JBOSS_IN_BACKGROUND を設定していない | standalone.sh が PID 1 だと SIGTERM が JVM に届かず、停止処理が走らない (⑬ に関係) | entrypoint で export LAUNCH_JBOSS_IN_BACKGROUND=true |

### 信頼設定 (アウトバウンド) の 2 方式の比較

| 観点 | TRUST_MODE=system (推奨) | TRUST_MODE=elytron (ExtraSLB 方式を強化) |
|---|---|---|
| CA の置き場所 | /etc/pki/ca-trust/source/anchors/<提供元>-ca-<n>.pem → update-ca-trust → JDK の cacerts | /opt/app/security/extraslb-truststore.p12 (cacerts のコピー + CA) |
| SSLContext.getDefault() | JSSE 既定 (cacerts。CA 入り) | Elytron の DelegatingSSLContext (p12) |
| CXF 等の自前 SSLContext | cacerts (javax.net.ssl.trustStore 未指定) | -Djavax.net.ssl.trustStore の p12 |
| 必要な設定 | Dockerfile の 1 ステップだけ | Elytron の 4 リソース + standalone.sh の -D 引数 3 つ |
| OS の CA 更新への追随 | する (イメージ更新で ca-certificates と一緒に) | しない (ビルド時点のコピー) |
| WFLYELY00024 (期限切れの警告) | 出ない (Elytron は cacerts を読まない) | cacerts に期限切れのルートがあれば出る |
| OS のツール (curl 等) | 同じ CA を信頼する | 信頼しない |
| 向いている場合 | コンテナ全体で同じ CA を信頼してよい (通常これ) | 宛先ごとに信頼を分けたい / Elytron の authentication-client で使い分けたい |

| クライアント (検証で実測) | 参照する設定 | system | elytron | 現行 (修正前) |
|---|---|---|---|---|
| A HttpsURLConnection (既定) | SSLContext.getDefault() | OK | OK | OK |
| B java.net.http.HttpClient (既定) | SSLContext.getDefault() | OK | OK | OK |
| C new SSLContext(TLS).init(null,...) / CXF 等 | JSSE 既定の TrustManagerFactory (javax.net.ssl.trustStore → 無ければ cacerts) | OK | OK | OK |
| 参考: 自前 p12 のパスを誤った場合 (E3) | - | - | 起動時に失敗 (required=true) | A・B はパブリック CA 宛も NG、C は自己署名 CA 宛のみ NG |

> **【注意・補足】**  
> C の「パスを誤った場合」で自己署名 CA 宛だけ失敗しパブリック CA 宛は成功したのは、存在しない javax.net.ssl.trustStore を指定すると JDK が既定の cacerts に戻るため (実測)。一部の宛先だけが失敗するので、気づきにくい壊れ方になります。

### インバウンド HTTPS (8443) の扱い 4 方式の実測

| 方式 | WFLYELY00023 / 01084 | 8443 | 設定 | 評価 |
|---|---|---|---|---|
| keep (EAP 既定) | 出る / 出る | 初回接続時に CN=localhost の自己署名を生成して待ち受け | なし | △ |
| provision (ExtraSLB 現行) | 出ない / 出ない | CN=localhost (イメージに焼いた鍵) で待ち受け | keytool で事前生成 | ○ 不要な鍵と口が残る |
| remove ★ | 出ない / 出ない | 待ち受けなし | 11-inbound-https-remove.cli | ◎ 本構成に最適 |
| dedicated | 出ない / 出ない | 起動時に渡した証明書 (CN=iwinmichl.internal) で待ち受け | 12-inbound-https-dedicated.cli + Secrets | ○ ALB→タスクも暗号化する場合 |

### 推奨構成と移行手順

- 1) Dockerfile を implementation/container/Dockerfile に置き換える (ビルド段 UBI 9.8、実行段 ubi9/openjdk-21-runtime)。証明書の受け渡し (cacert-secret-args.sh と BuildKit Secrets) は ExtraSLB と同じ。
- 2) TRUST_MODE=system でビルドし、アウトバウンド HTTPS を確認する (自己署名 CA 宛とパブリック CA 宛)。問題があれば TRUST_MODE=elytron で ExtraSLB と同じ二層構え (required=true 付き) に戻せる。
- 3) INBOUND_HTTPS_MODE=remove でビルドし、ALB のターゲットグループが HTTP:8080 であることを確認する。
- 4) ExtraSLB の entrypoint.sh を使い続ける場合は、export LAUNCH_JBOSS_IN_BACKGROUND=true を追加し、EXTRASLB_APP_KEYSTORE_MODE=skip にする (事前生成が不要になるため)。
- 5) 起動ログで WFLYELY00023 / 01084 が 0 件、/subsystem=elytron:read-attribute(name=default-ssl-context) が undefined (system モード) であることを確認する。

### 実測の記録 (要約)

| 実験 | 条件 | 結果 |
|---|---|---|
| E1 | 現行 (修正前イメージ) | application.keystore について WFLYELY00023・01084。アウトバウンドは 3 クライアントとも OK。8443 は CN=localhost |
| E2 | -Djavax.net.ssl.keyStore も渡す | WFLYELY00023 は変わらず出る |
| E3 | 自前 p12 のパスを誤る (required=false) | そのパスでも WFLYELY00023。正常起動するが A・B は全宛先 NG、C は自己署名 CA 宛 NG |
| E4 | 同じ誤り + required=true | WFLYELY00022 → サービス起動失敗 → started (with errors)。entrypoint 経由なら起動前に FATAL |
| E5 | ExtraSLB の事前生成 | 警告 0、8443 で CN=localhost |
| E6 | remove / dedicated | remove: 警告 0、8443 なし。dedicated: 警告 0、8443 で正式な証明書。鍵ストア渡し忘れは entrypoint が FATAL |
| E7 | system モード | JDK の cacerts (/etc/pki/ca-trust/extracted/java/cacerts) に extraslbtestrootca が trustedCertEntry として入る |

## 実装

| ファイル (implementation/ 配下) | 役割 | 対応する警告 | 使う時点 |
|---|---|---|---|
| container/Dockerfile | 2 段ビルド (UBI 9.8 でEAP 展開・CLI 適用 → ubi9/openjdk-21-runtime で実行)。信頼設定・ドライバ・CLI をまとめる | ①③④⑥⑧⑨⑩⑪⑫⑬ | ビルド |
| container/cli/00-system-properties.cli | SIGTERM 時のサスペンド待ち時間 (org.wildfly.sigterm.suspend.timeout) | ⑬ | ビルド (embed-server) |
| container/cli/10-elytron-outbound-truststore.cli | elytron モードの信頼設定 (ExtraSLB と同じ構成 + required=true) | ① | ビルド (TRUST_MODE=elytron) |
| container/cli/11-inbound-https-remove.cli | 使っていないインバウンド HTTPS 一式 (8443) を削除 | ① | ビルド (INBOUND_HTTPS_MODE=remove) |
| container/cli/12-inbound-https-dedicated.cli | 8443 を起動時に渡す正式な鍵ストアで動かす | ① | ビルド (INBOUND_HTTPS_MODE=dedicated) |
| container/cli/20-logging.cli | ④ Spring 分の WFLYEE0007 と ③ spring-core 由来の org.jboss.vfs の WFLYSRV0018 だけを抑止。調査用コマンド | ③④⑥ | ビルド (embed-server) |
| container/cli/30-datasource-mysql-xa.cli | JDBC ドライバと XA データソース (検証・exception-sorter・idle-timeout・track-statements・TCP keepalive) | ⑧⑩⑪⑫ | ビルド (embed-server) |
| container/cli/31-jca-ccm.cli | 接続リーク検出 (CCM) を環境変数で切り替え | ⑧⑫⑬ | ビルド (embed-server) |
| container/cli/60-undertow.cli | X-Forwarded-* の採用と 4xx/5xx の JSON アクセスログ | ⑨ | ビルド (embed-server) |
| container/cli/70-transactions.cli | XA の node-identifier をタスクごとに一意に | (XA の前提) | ビルド (embed-server) |
| container/cli/90-verify.cli | 適用結果の表示 | 全般 | ビルド / 起動後 |
| container/scripts/apply-cli.sh | embed-server で cli/ を番号順に適用し、standalone_xml_history を残さない | 全般 | ビルド |
| container/scripts/install-ca-anchors.sh | 受領した CA を UBI のシステムトラストストアへ追加 (update-ca-trust) し、cacerts 入りを指紋で確認 | ① | ビルド (TRUST_MODE=system) |
| container/scripts/build-truststore.sh | Container_ExtraSLB_JVM_https_outbounds の同名スクリプト (変更なし)。cacerts のコピー + CA の p12 | ① | ビルド (TRUST_MODE=elytron) |
| container/scripts/entrypoint.sh | 起動前チェック、TX_NODE_ID、SIGTERM の中継 (LAUNCH_JBOSS_IN_BACKGROUND)、standalone.sh 起動 | ①⑬ | 起動 |
| container/modules/com/mysql/main/module.xml | MySQL Connector/J のモジュール定義 (デプロイではなくモジュールで) | ⑩⑪⑬ | ビルド |
| app/src/main/webapp/WEB-INF/jboss-deployment-structure.xml | 修正後の記述子 (testClasses・cxf.impl・誤った除外を削除、jsf と weld を除外) | ②③⑤⑥ | WAR |
| app/pom-snippets.xml | サーバ提供 API を provided に、javax.* と log4j-core の混入を enforcer で禁止 | ②⑤⑥⑦ | WAR |
| app/src/main/java/com/example/iwinmichl/web/MethodNotAllowedAdvice.java | 405 を送信元・URL 付きの 1 行で記録 | ⑨ | WAR |
| app/src/main/java/com/example/iwinmichl/dao/JdbcResourceSamples.java | JDBC リソースの正しい閉じ方 | ⑧⑫ | WAR |
| app/src/main/java/com/example/iwinmichl/ws/SoapClientTimeouts.java | 標準 API だけで SOAP のタイムアウトを設定 (cxf.impl 不要) | ③ | WAR |
| ecs/taskdef-container-fragment.json | ECS タスク定義 (secrets、stopTimeout、systemControls、healthCheck、awslogs) | ⑩⑪⑬ | デプロイ |
| tools/check-warnings.sh | ログから警告 ①〜⑬ と関連メッセージの件数を集計 | 全般 | 運用 |
| tools/analyze-ij-log.py | ⑧⑫ の作成箇所、⑪ の放置時間と idle-timeout の推奨値、⑩ の根本原因、⑬ の発生状況 | ⑧⑩⑪⑫⑬ | 運用 |
| tools/scan-war.py | WAR を静的に検査し ②③④⑤⑥⑦ の原因を特定 | ②③④⑤⑥⑦ | ビルド / CI |
| tools/cacert-secret-args.sh | Container_ExtraSLB_JVM_https_outbounds の同名スクリプト (変更なし)。証明書を 1 つのシークレットに | ① | ビルド |

### implementation/container/Dockerfile

```dockerfile
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
```

### implementation/container/cli/00-system-properties.cli

```text
# =====================================================================
# 00-system-properties.cli
#   ⑬ IJ000615 (Destroying active connection in pool) 対処 その 1
#
# ECS はタスク停止時に SIGTERM を送り、stopTimeout (既定 30 秒 / Fargate 最大 120 秒) 後に SIGKILL する。
# EAP は SIGTERM を受けるとシャットダウンフックで「サスペンド → 停止」を行うが、
# その待ち時間はシステムプロパティ org.wildfly.sigterm.suspend.timeout (秒) で決まり、
# 未設定 (既定) は 0 = 処理中リクエストを待たない。
#   → 処理中のリクエストが切られ、使用中の DB 接続がプール停止で破棄される (IJ000615)。
# (JBoss EAP 8.1 構成ガイド「OS シグナルを使用してサーバーを正常にシャットダウンする」)
#
# 値は ECS タスク定義の環境変数 EAP_SIGTERM_SUSPEND_TIMEOUT で上書きできる。
#   目安: 最長リクエスト処理時間 <= この値 < stopTimeout (余裕 5〜10 秒)
#   -1 は無期限に待つ (stopTimeout で SIGKILL されるので ECS では使わない)
#
# system-property リソースはブート時に JVM のシステムプロパティとして設定され、
# SIGTERM 受信時 (シャットダウンフック) に参照される。
# ※ SIGTERM が JVM に届くこと (LAUNCH_JBOSS_IN_BACKGROUND=true) が前提。entrypoint.sh 参照。
# =====================================================================
if (outcome != success) of /system-property=org.wildfly.sigterm.suspend.timeout:read-resource
    /system-property=org.wildfly.sigterm.suspend.timeout:add(value="${env.EAP_SIGTERM_SUSPEND_TIMEOUT:30}")
end-if
```

### implementation/container/cli/10-elytron-outbound-truststore.cli

```text
# =====================================================================
# 10-elytron-outbound-truststore.cli   (TRUST_MODE=elytron のときだけ適用)
#   ① 関連: 自己署名ルート CA (extraslb 等) を信頼するアウトバウンド TLS 設定
#
# Container_ExtraSLB_JVM_https_outbounds の configure-outbound-tls.cli と同じ構成に、
# 次の改善を加えたもの:
#   - key-store に required=true を付ける
#       トラストストアのパスを誤ったとき「WFLYELY00023 ... Used blank.」(警告のみ) で
#       空のトラストストアのまま起動し、default-ssl-context 経由のアウトバウンド TLS が
#       全滅する事故を防ぐ。required=true なら WFLYELY00022 で該当サービスが起動失敗し、
#       問題が起動時点で確実に見える (entrypoint.sh の事前チェックと二重の安全策)。
#   - 既存リソースがあっても required を必ず true にそろえる (冪等)
#
# ※ TRUST_MODE=system (推奨) では本ファイルは使わない。
#    CA を UBI のシステムトラストストア (update-ca-trust) に入れるため、
#    JDK 既定の cacerts だけで全クライアントが信頼でき、Elytron 側の設定も -D 引数も不要になる。
# =====================================================================

# --- 1. トラストストア (cacerts のコピー + 受領した CA 証明書群) ---
if (outcome != success) of /subsystem=elytron/key-store=extraslb-trust-store:read-resource
    /subsystem=elytron/key-store=extraslb-trust-store:add( \
        path="${env.EXTRASLB_TRUSTSTORE_PATH:/opt/app/security/extraslb-truststore.p12}", \
        type="${env.EXTRASLB_TRUSTSTORE_TYPE:PKCS12}", \
        required=true, \
        credential-reference={clear-text="${env.EXTRASLB_TRUSTSTORE_PASSWORD:changeit}"} \
    )
end-if
/subsystem=elytron/key-store=extraslb-trust-store:write-attribute(name=required, value=true)

# --- 2. トラストマネージャ ---
if (outcome != success) of /subsystem=elytron/trust-manager=extraslb-trust-manager:read-resource
    /subsystem=elytron/trust-manager=extraslb-trust-manager:add(key-store=extraslb-trust-store)
end-if

# --- 3. クライアント SSL コンテキスト ---
if (outcome != success) of /subsystem=elytron/client-ssl-context=extraslb-client-ssl-context:read-resource
    /subsystem=elytron/client-ssl-context=extraslb-client-ssl-context:add( \
        trust-manager=extraslb-trust-manager, \
        protocols=["TLSv1.3","TLSv1.2"] \
    )
end-if

# --- 4. JVM 既定の SSLContext (SSLContext.getDefault()) として登録 ---
#   HttpsURLConnection / java.net.http.HttpClient / RESTEasy Client 等が使う。
#   SSLContext を自分で組み立てるライブラリ (Apache CXF の HTTPConduit など) は
#   javax.net.ssl.trustStore を読むため、entrypoint.sh が -D 引数でも同じファイルを渡す。
/subsystem=elytron:write-attribute(name=default-ssl-context, value=extraslb-client-ssl-context)
```

### implementation/container/cli/11-inbound-https-remove.cli

```text
# =====================================================================
# 11-inbound-https-remove.cli   (INBOUND_HTTPS_MODE=remove のときだけ適用。既定)
#   ① WFLYELY00023 (KeyStore file '.../application.keystore' does not exist. Used blank.) 対処
#
# 原因: EAP 標準 standalone.xml のインバウンド HTTPS (8443) 用リソース
#         key-store=applicationKS      (application.keystore / JKS / パスワード password)
#         key-manager=applicationKM    (generate-self-signed-certificate-host=localhost)
#         server-ssl-context=applicationSSC
#         undertow https-listener=https (ssl-context=applicationSSC)
#       の applicationKS が、配布物に含まれない application.keystore を指している。
#       Elytron の key-store サービスは Mode.ACTIVE で、参照の有無に関係なくブート時に起動し、
#       ファイルが無ければ required=false (既定) のため WARN を出して空のストアで続行する。
#
# 本構成は ALB で TLS を終端し、コンテナは 8080 (HTTP) だけで受ける = 8443 は使っていない。
# 使っていないインバウンド HTTPS 一式を、参照する側から順に削除する:
#   https-listener → applicationSSC → applicationKM → applicationKS
# (逆順だと「参照されているリソースは削除できない」エラーになる)
#
# 効果: 警告が原因ごと消える / 未使用の 8443 が待ち受けなくなる (攻撃面の縮小) /
#       イメージに既知パスワードの秘密鍵を同梱しなくてよい
# 将来 ALB → タスク間も TLS にする場合は 12-inbound-https-dedicated.cli を使う。
# =====================================================================

# 1) https-listener (applicationSSC を参照している)
if (outcome == success) of /subsystem=undertow/server=default-server/https-listener=https:read-resource
    /subsystem=undertow/server=default-server/https-listener=https:remove
end-if

# 2) server-ssl-context
if (outcome == success) of /subsystem=elytron/server-ssl-context=applicationSSC:read-resource
    /subsystem=elytron/server-ssl-context=applicationSSC:remove
end-if

# 3) key-manager
if (outcome == success) of /subsystem=elytron/key-manager=applicationKM:read-resource
    /subsystem=elytron/key-manager=applicationKM:remove
end-if

# 4) key-store (これが WFLYELY00023 を出していた本体)
if (outcome == success) of /subsystem=elytron/key-store=applicationKS:read-resource
    /subsystem=elytron/key-store=applicationKS:remove
end-if

# ※ socket-binding=https (8443) は誰も使わなくなるが、残しても待ち受けは発生しない。
```

### implementation/container/cli/12-inbound-https-dedicated.cli

```text
# =====================================================================
# 12-inbound-https-dedicated.cli   (INBOUND_HTTPS_MODE=dedicated のときだけ適用)
#   ① の別解: ALB → タスク間も HTTPS (8443) で暗号化したい場合
#
# applicationKS を「起動時に用意される正式な鍵ストア」に差し替え、自己署名の自動生成をやめる。
#   - 鍵ストアは ECS の secrets (Secrets Manager) から entrypoint.sh がファイル化する等で用意し、
#     パスとパスワードを環境変数で渡す (イメージには焼き込まない)
#   - required=true: ファイルが無ければ WFLYELY00022 で起動時に失敗させる (黙って空で動かさない)
#   - ALB はターゲットの証明書を検証しない (自己署名・期限切れでも通る) ため、
#     ALB 用途だけなら ACM 等の公開証明書は不要。ただし鍵はタスク外で管理する。
# =====================================================================
/subsystem=elytron/key-store=applicationKS:write-attribute(name=path, value="${env.INBOUND_KEYSTORE_PATH:/opt/app/runtime-security/inbound-server.p12}")
/subsystem=elytron/key-store=applicationKS:undefine-attribute(name=relative-to)
/subsystem=elytron/key-store=applicationKS:write-attribute(name=type, value="${env.INBOUND_KEYSTORE_TYPE:PKCS12}")
/subsystem=elytron/key-store=applicationKS:write-attribute(name=required, value=true)
/subsystem=elytron/key-store=applicationKS:write-attribute(name=credential-reference, value={clear-text="${env.INBOUND_KEYSTORE_PASSWORD}"})
/subsystem=elytron/key-manager=applicationKM:undefine-attribute(name=generate-self-signed-certificate-host)
/subsystem=elytron/key-manager=applicationKM:write-attribute(name=credential-reference, value={clear-text="${env.INBOUND_KEYSTORE_PASSWORD}"})
```

### implementation/container/cli/20-logging.cli

```text
# =====================================================================
# 20-logging.cli
#
# ④ WFLYEE0007 (Not installing optional component ...) の「Spring の分だけ」を抑止する
#
#   仕組み: Undertow (WebComponentProcessor) は WAR 内の jakarta.servlet.AsyncListener 実装クラスを
#   すべて「注入対象の Web コンポーネント (オプション)」として登録する。Weld (CDI) が無効の WAR では
#   EE サブシステムが引数なしコンストラクタでインスタンス化しようとするが、Spring の
#   ServletServerHttpResponse$ResponseAsyncListener などは非 static の内部クラス
#   (コンストラクタが外側のインスタンスを引数に取る) のため WFLYEE0048 (Could not find default
#   constructor) となり、オプション扱いなので WFLYEE0007 の WARN だけを出して登録をやめる。
#   Spring はこれらのリスナーを自分で new して使うため、動作への影響は無い (検証で確認)。
#
#   方針: 必ず先に DEBUG で原因が WFLYEE0048 であることを確認してから入れる (下の「調査用」)。
#   フィルタは org.jboss.as.ee カテゴリの、メッセージが
#     "WFLYEE0007: Not installing optional component org.springframework."
#   で始まるものだけを捨てる。jboss-logmanager の match() は整形後のメッセージに部分一致する。
#   Spring 以外のクラスの WFLYEE0007 (本当に見たいもの) はそのまま出る。
# =====================================================================
if (outcome != success) of /subsystem=logging/logger=org.jboss.as.ee:read-resource
    /subsystem=logging/logger=org.jboss.as.ee:add(filter-spec="not(match(\"WFLYEE0007: Not installing optional component org.springframework.\"))")
end-if

# =====================================================================
# ③ WFLYSRV0018 (private モジュールの使用) のうち、spring-core 由来の org.jboss.vfs だけを抑止する
#
#   spring-core-6.x.jar の META-INF/MANIFEST.MF には JBoss Modules 用の
#     Dependencies: jdk.unsupported,org.jboss.vfs
#   が書かれている (Spring が JBoss の VFS 上でクラスパス走査をするため)。MANIFEST の Dependencies は
#   「ユーザー指定の依存」として扱われ、org.jboss.vfs は private なので Spring を使う WAR では必ず出る。
#   アプリ側で消すには spring-core の jar を改変するしかなく非推奨なので、この 1 モジュール分だけ絞って抑止する。
#   jboss-deployment-structure.xml の org.apache.cxf.impl のような「自分で書いた private 依存」は抑止しない
#   (そちらは依存を外して直す)。
# =====================================================================
if (outcome != success) of /subsystem=logging/logger=org.jboss.as.dependency.private:read-resource
    /subsystem=logging/logger=org.jboss.as.dependency.private:add(filter-spec="not(match(\"WFLYSRV0018: .*org.jboss.vfs\"))")
end-if

# ---------------------------------------------------------------------
# 調査用 (必要なときだけ jboss-cli で接続して実行し、終わったら戻す。ここでは実行しない)
#   ④ の原因 (DEBUG の 2 行目) を見る:
#     /subsystem=logging/logger=org.jboss.as.ee:write-attribute(name=level, value=DEBUG)
#     /subsystem=logging/console-handler=CONSOLE:write-attribute(name=level, value=DEBUG)
#     (再デプロイして "WFLYEE0048: Could not find default constructor" を確認)
#     /subsystem=logging/console-handler=CONSOLE:write-attribute(name=level, value=INFO)
#     /subsystem=logging/logger=org.jboss.as.ee:undefine-attribute(name=level)
#
#   ⑥ アプリに Log4j 2 実装 (log4j-core) を同梱して自前の log4j2.xml で出したい場合だけ:
#     (サーバ全体に効く点に注意。通常は jboss-deployment-structure.xml で
#      org.apache.logging.log4j.api を除外する方が影響範囲が狭い)
#     /subsystem=logging:write-attribute(name=add-logging-api-dependencies, value=false)
#
#   CloudWatch Logs Insights で扱いやすい JSON 形式にする場合 (任意):
#     /subsystem=logging/json-formatter=JSON:add(exception-output-type=formatted, pretty-print=false)
#     /subsystem=logging/console-handler=CONSOLE:write-attribute(name=named-formatter, value=JSON)
# ---------------------------------------------------------------------
```

### implementation/container/cli/30-datasource-mysql-xa.cli

```text
# =====================================================================
# 30-datasource-mysql-xa.cli
#   ⑧ IJ030040 / ⑫ IJ030042 (閉じ忘れ検出) と ⑩ IJ030027 / ⑪ IJ000621 (死んだ接続の破棄) の対処
#
# 対象: XA データソース MIF02JA_JDS (java:/jdbc/MIF02JA_JDS) / Aurora MySQL 8.4 (MySQL 8.4 互換)
# 接続先・資格情報は ECS タスク定義の environment / secrets から環境変数で渡す (イメージに焼かない)。
#
# 検証設定の方針 (Red Hat ナレッジ「EAP 6/7/8 JDBC datasource not fault tolerant ...」の推奨に従う):
#   - validate-on-match=true / background-validation=false  (両方 true にはしない)
#   - valid-connection-checker と exception-sorter は MySQL 用をペアで指定
#       checker 無しだと検証は何もしない / sorter 無しだと致命的エラーの接続がプールに残る
#   ⑪ IJ000621 + ⑩ IJ030027 は「貸し出し直前の検証で死んだ接続を見つけて捨てた」記録であり、
#   アプリにはエラーを返していない (自己修復)。根本対処は「接続がプールで死なないようにする」こと:
#   - idle-timeout-minutes を、接続が切られる時間 (MySQL wait_timeout / 経路のアイドル切断) より
#     十分短くする。IdleRemover は idle-timeout の半分間隔で動くので、最長で約 1.5 倍まで残る。
#       例: 経路に 350 秒で切る NAT/NLB がある → 3 分以下 (180 秒 × 1.5 = 270 秒 < 350 秒)
#           Aurora 直結で wait_timeout=28800 (既定) → 既定 30 分でも死なない
#   - TCP keepalive: Connector/J の tcpKeepAlive=true (既定) + ECS タスク定義の systemControls で
#     net.ipv4.tcp_keepalive_time 等を短くする (経路のアイドル切断対策。wait_timeout には効かない)
#   - socketTimeout: 半開き TCP で ping (検証) が長時間固まるのを防ぐ上限。最長クエリより長くする。
#
# track-statements: 既定は NOWARN (追跡して黙って閉じる)。
#   ⑧⑫ が出ている = 実環境では true になっている。開発・検証環境は TRUE で閉じ忘れを見つけて直し、
#   本番はアプリ修正後に NOWARN (安全網として閉じるが警告はしない) とするのが基本。
# =====================================================================

# --- JDBC ドライバ (モジュール com.mysql は Dockerfile が配置する) ---
#   driver-name 属性は非推奨 (WFLYCTL0028)。名前はアドレス (jdbc-driver=mysql) から決まるので指定しない。
if (outcome != success) of /subsystem=datasources/jdbc-driver=mysql:read-resource
    /subsystem=datasources/jdbc-driver=mysql:add( \
        driver-module-name=com.mysql, \
        driver-class-name=com.mysql.cj.jdbc.Driver, \
        driver-xa-datasource-class-name=com.mysql.cj.jdbc.MysqlXADataSource)
end-if

# --- XA データソース ---
if (outcome != success) of /subsystem=datasources/xa-data-source=MIF02JA_JDS:read-resource
    batch
    /subsystem=datasources/xa-data-source=MIF02JA_JDS:add( \
        jndi-name=java:/jdbc/MIF02JA_JDS, \
        driver-name=mysql, \
        user-name="${env.DB_USER}", \
        password="${env.DB_PASSWORD}", \
        min-pool-size="${env.DB_MIN_POOL_SIZE:0}", \
        max-pool-size="${env.DB_MAX_POOL_SIZE:20}", \
        idle-timeout-minutes="${env.DB_IDLE_TIMEOUT_MIN:5}", \
        blocking-timeout-wait-millis="${env.DB_BLOCKING_TIMEOUT_MS:5000}", \
        validate-on-match=true, \
        background-validation=false, \
        valid-connection-checker-class-name=org.jboss.jca.adapters.jdbc.extensions.mysql.MySQLValidConnectionChecker, \
        exception-sorter-class-name=org.jboss.jca.adapters.jdbc.extensions.mysql.MySQLExceptionSorter, \
        track-statements="${env.DB_TRACK_STATEMENTS:NOWARN}", \
        statistics-enabled=true)
    /subsystem=datasources/xa-data-source=MIF02JA_JDS/xa-datasource-properties=ServerName:add(value="${env.DB_HOST}")
    /subsystem=datasources/xa-data-source=MIF02JA_JDS/xa-datasource-properties=PortNumber:add(value="${env.DB_PORT:3306}")
    /subsystem=datasources/xa-data-source=MIF02JA_JDS/xa-datasource-properties=DatabaseName:add(value="${env.DB_NAME}")
    /subsystem=datasources/xa-data-source=MIF02JA_JDS/xa-datasource-properties=TcpKeepAlive:add(value=true)
    /subsystem=datasources/xa-data-source=MIF02JA_JDS/xa-datasource-properties=ConnectTimeout:add(value="${env.DB_CONNECT_TIMEOUT_MS:10000}")
    /subsystem=datasources/xa-data-source=MIF02JA_JDS/xa-datasource-properties=SocketTimeout:add(value="${env.DB_SOCKET_TIMEOUT_MS:120000}")
    run-batch
end-if

# ---------------------------------------------------------------------
# 参考 (この順に検討):
#   - ping の待ちを socketTimeout ではなく秒数で区切りたい場合 (最長クエリが長く socketTimeout を
#     大きくせざるを得ない場合) は JDBC4 の isValid(timeout) を使うチェッカーに替える:
#       valid-connection-checker-class-name=org.jboss.jca.adapters.jdbc.extensions.novendor.JDBC4ValidConnectionChecker
#       valid-connection-checker-properties={pingTimeOut=5}
#   - XA リカバリ (トランザクションマネージャの定期リカバリ) で XA RECOVER を実行するため、
#     MySQL 8.x では接続ユーザーに XA_RECOVER_ADMIN 権限が必要:  GRANT XA_RECOVER_ADMIN ON *.* TO '<user>'@'%';
# ---------------------------------------------------------------------
```

### implementation/container/cli/31-jca-ccm.cli

```text
# =====================================================================
# 31-jca-ccm.cli
#   ⑧⑫⑬ の補助: 接続の閉じ忘れ (コネクションリーク) を検出する
#
# cached-connection-manager (CCM) はリクエスト (EE コンポーネント呼び出し) の終わりに、
# 閉じられていない接続を見つける仕組み。
#   debug=true … 閉じ忘れた接続をサーバが閉じ、IJ000100 (Closing a connection for you ...) と
#                取得箇所のスタックトレースを出す
#   error=true … 閉じ忘れをエラー (例外) にする (開発環境向け)
# 本番は既定 (false) のまま、調査時だけ ECS の環境変数で true にしてタスクを入れ替える。
# =====================================================================
/subsystem=jca/cached-connection-manager=cached-connection-manager:write-attribute(name=debug, value="${env.JCA_CCM_DEBUG:false}")
/subsystem=jca/cached-connection-manager=cached-connection-manager:write-attribute(name=error, value="${env.JCA_CCM_ERROR:false}")
```

### implementation/container/cli/60-undertow.cli

```text
# =====================================================================
# 60-undertow.cli
#   ⑨ Resolved [HttpRequestMethodNotSupportedException ...] の調査を可能にする
#
# Spring の 405 ログには URL も送信元も出ない。サーバ側で
#   (1) ALB が付ける X-Forwarded-For / X-Forwarded-Proto を信頼して、送信元 IP を正しく記録する
#   (2) 4xx / 5xx の応答だけを JSON 形式のアクセスログとして標準出力 (= CloudWatch Logs) へ出す
# を行い、「どこから・どの URL に・どのメソッドで」来た 405 なのかを突き止められるようにする。
#
# console-access-log の predicate は応答完了後に評価される (EventLoggerHttpHandler) ため、
# 応答コード (%s) で絞り込める。全リクエストを記録したい場合は predicate を外す。
# =====================================================================

# (1) ALB の背後にいるので X-Forwarded-* を採用する (ALB 以外から直接届かないことが前提)
/subsystem=undertow/server=default-server/http-listener=default:write-attribute(name=proxy-address-forwarding, value=true)
#     応答時間 (response-time) を記録するにはリスナーで要求開始時刻の記録を有効にする (既定 false)
/subsystem=undertow/server=default-server/http-listener=default:write-attribute(name=record-request-start-time, value=true)

# (2) 4xx/5xx のみ JSON アクセスログ
#     request-url はコンテキストパス込みの URL (/iwinmichl/api/hello)。request-path はコンテキスト以下だけになる
if (outcome != success) of /subsystem=undertow/server=default-server/host=default-host/setting=console-access-log:read-resource
    /subsystem=undertow/server=default-server/host=default-host/setting=console-access-log:add( \
        include-host-name=false, \
        predicate="regex(pattern=\"^[45]\", value=\"%s\", full-match=false)", \
        attributes={ \
            date-time={key=timestamp, date-format="yyyy-MM-dd'T'HH:mm:ss.SSSXXX"}, \
            remote-ip={key=client}, \
            request-method={key=method}, \
            request-url={key=path}, \
            query-string={key=query}, \
            response-code={key=status}, \
            response-time={key=ms, time-unit=MILLISECONDS}, \
            request-header={key-prefix="h_", names=["X-Forwarded-For","User-Agent","Referer"]} \
        })
end-if
```

### implementation/container/cli/70-transactions.cli

```text
# =====================================================================
# 70-transactions.cli
#   XA データソース (MIF02JA_JDS) を複数タスクで使うための前提設定
#
# トランザクションマネージャの node-identifier は XA トランザクション ID (XID) に埋め込まれ、
# 障害後のリカバリで「自分のトランザクションか」を判定するのに使われる。
# ECS で同じイメージのタスクを複数動かすと、既定値 (1) のままでは全タスクが同じ ID になり、
# あるタスクのリカバリが別タスクの未完了トランザクションを巻き戻す危険がある
# (既定値のままだと WFLYTX0013 の警告も出る)。
# entrypoint.sh が ECS タスク ID から 23 バイト以内の値を作り、TX_NODE_ID で渡す。
# =====================================================================
/subsystem=transactions:write-attribute(name=node-identifier, value="${env.TX_NODE_ID:${jboss.tx.node.id:1}}")
```

### implementation/container/cli/90-verify.cli

```text
# =====================================================================
# 90-verify.cli
#   ビルド時 (embed-server) に適用結果を表示して確認する。起動後に jboss-cli.sh -c で実行してもよい。
#   (存在しない場合は "failed" になるだけで、適用済みの設定は変更しない)
# =====================================================================
echo ===== [verify] 0 system-property (⑬)
/system-property=org.wildfly.sigterm.suspend.timeout:read-resource

echo ===== [verify] 1 インバウンド HTTPS (①): remove モードなら https-listener と applicationKS は "failed" (= 無い) が正しい
/subsystem=undertow/server=default-server:read-children-names(child-type=https-listener)
/subsystem=elytron:read-children-names(child-type=key-store)

echo ===== [verify] 1 既定 SSLContext (①: TRUST_MODE=elytron なら extraslb-client-ssl-context / system なら undefined)
/subsystem=elytron:read-attribute(name=default-ssl-context)

echo ===== [verify] 2 logging (④)
/subsystem=logging/logger=org.jboss.as.ee:read-resource

echo ===== [verify] 3 datasource (⑧⑩⑪⑫)
/subsystem=datasources/xa-data-source=MIF02JA_JDS:read-resource(recursive=true)

echo ===== [verify] 4 undertow (⑨)
/subsystem=undertow/server=default-server/http-listener=default:read-attribute(name=proxy-address-forwarding)
/subsystem=undertow/server=default-server/host=default-host/setting=console-access-log:read-resource

echo ===== [verify] 5 transactions / jca
/subsystem=transactions:read-attribute(name=node-identifier)
/subsystem=jca/cached-connection-manager=cached-connection-manager:read-resource
```

### implementation/container/scripts/apply-cli.sh

```bash
#!/bin/bash
#
# apply-cli.sh [cli-dir]
#
# イメージのビルド時に jboss-cli の組み込みサーバ (embed-server, admin-only) を 1 回だけ起動し、
# cli/ 配下の .cli を番号順に適用して standalone.xml に焼き込む。
#   - ${env.*} 式はこの時点では解決されず、式のまま standalone.xml に保存される
#     (起動時に ECS タスク定義の環境変数から解決される)
#   - 起動時に embed-server を動かさないので、コンテナ 1 起動あたりの設定ブートは 1 回で済む
#     (Container_ExtraSLB_JVM_https_outbounds の docs/standalone-xml-history-ecs-vs-compose.md 参照)
#
# 選択適用:
#   10-elytron-outbound-truststore.cli … TRUST_MODE=elytron のときだけ
#   11-inbound-https-remove.cli        … INBOUND_HTTPS_MODE=remove (既定) のときだけ
#   12-inbound-https-dedicated.cli     … INBOUND_HTTPS_MODE=dedicated のときだけ
#   90-verify.cli                      … 最後に必ず実行 (結果の表示のみ)
set -euo pipefail

JBOSS_HOME="${JBOSS_HOME:?JBOSS_HOME is not set}"
CLI_DIR="${1:-/opt/app/cli}"
TRUST_MODE="${TRUST_MODE:-system}"
INBOUND_HTTPS_MODE="${INBOUND_HTTPS_MODE:-remove}"
SERVER_CONFIG="${SERVER_CONFIG:-standalone.xml}"

case "${TRUST_MODE}" in system|elytron) ;; *) echo "[apply-cli] FATAL: TRUST_MODE=${TRUST_MODE} (system|elytron)" >&2; exit 1 ;; esac
case "${INBOUND_HTTPS_MODE}" in remove|dedicated|keep) ;; *) echo "[apply-cli] FATAL: INBOUND_HTTPS_MODE=${INBOUND_HTTPS_MODE} (remove|dedicated|keep)" >&2; exit 1 ;; esac

BATCH="$(mktemp /tmp/apply-cli.XXXXXX.cli)"
trap 'rm -f "${BATCH}"' EXIT

{
    echo "embed-server --server-config=${SERVER_CONFIG} --std-out=echo"
    for f in "${CLI_DIR}"/[0-8]*.cli; do
        name="$(basename "${f}")"
        case "${name}" in
            10-elytron-outbound-truststore.cli) [[ "${TRUST_MODE}" == elytron ]] || continue ;;
            11-inbound-https-remove.cli)        [[ "${INBOUND_HTTPS_MODE}" == remove ]] || continue ;;
            12-inbound-https-dedicated.cli)     [[ "${INBOUND_HTTPS_MODE}" == dedicated ]] || continue ;;
        esac
        echo "echo ===== [apply] ${name}"
        cat "${f}"
        echo
    done
    cat "${CLI_DIR}/90-verify.cli"
    echo
    echo "stop-embedded-server"
} > "${BATCH}"

echo "[apply-cli] TRUST_MODE=${TRUST_MODE} INBOUND_HTTPS_MODE=${INBOUND_HTTPS_MODE} SERVER_CONFIG=${SERVER_CONFIG}"
"${JBOSS_HOME}/bin/jboss-cli.sh" --file="${BATCH}"

# embed-server が作った履歴をイメージに残さない
# (overlayfs の下位レイヤに standalone_xml_history/current が残ると、起動時の rename が失敗し得る)
rm -rf "${JBOSS_HOME}/standalone/configuration/standalone_xml_history"
echo "[apply-cli] done"
```

### implementation/container/scripts/install-ca-anchors.sh

```bash
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
```

### implementation/container/scripts/entrypoint.sh

```bash
#!/bin/bash
#
# entrypoint.sh — JBoss EAP 8.1 コンテナの起動スクリプト (ECS タスク用)
#
#   1. 起動前チェック (足りない設定があれば、EAP を起動する前に理由を出して止める)
#   2. XA 用のノード ID (TX_NODE_ID) をタスクごとに一意に決める
#   3. SIGTERM を JVM に中継させる (LAUNCH_JBOSS_IN_BACKGROUND=true) … ⑬ の前提
#   4. standalone.sh を exec で起動
#
# サブシステム設定はビルド時に jboss-cli で standalone.xml へ適用済み (apply-cli.sh)。
# 起動時に jboss-cli (embed-server) は実行しない。
set -euo pipefail

JBOSS_HOME="${JBOSS_HOME:-/opt/jboss-eap}"
TRUST_MODE="${TRUST_MODE:-system}"
INBOUND_HTTPS_MODE="${INBOUND_HTTPS_MODE:-remove}"

say() { echo "==> [entrypoint] $*"; }
die() { echo "==> [entrypoint] FATAL: $*" >&2; exit 1; }

# ---------------------------------------------------------------
# 1. 起動前チェック
# ---------------------------------------------------------------
# データソース (30-datasource-mysql-xa.cli) が使う環境変数。既定値の無い式は未設定だと起動時に解決できない。
for v in DB_HOST DB_NAME DB_USER DB_PASSWORD; do
    [[ -n "${!v:-}" ]] || die "環境変数 ${v} が未設定です (ECS タスク定義の environment / secrets を確認)"
done

if [[ "${TRUST_MODE}" == elytron ]]; then
    # 10-elytron-outbound-truststore.cli は required=true。ここでも先に確かめて分かりやすく止める。
    [[ -r "${EXTRASLB_TRUSTSTORE_PATH:-}" ]] || die "トラストストアが読めません: ${EXTRASLB_TRUSTSTORE_PATH:-(未設定)}"
fi

if [[ "${INBOUND_HTTPS_MODE}" == dedicated ]]; then
    [[ -r "${INBOUND_KEYSTORE_PATH:-/opt/app/runtime-security/inbound-server.p12}" ]] \
        || die "インバウンド用鍵ストアがありません: ${INBOUND_KEYSTORE_PATH:-/opt/app/runtime-security/inbound-server.p12}"
    [[ -n "${INBOUND_KEYSTORE_PASSWORD:-}" ]] || die "INBOUND_KEYSTORE_PASSWORD が未設定です"
fi

# ---------------------------------------------------------------
# 2. TX_NODE_ID (70-transactions.cli が参照。23 バイト以内・タスクごとに一意)
#    ECS のタスクメタデータ (v4) の TaskARN 末尾 = タスク ID (32 桁の 16 進) を使う。
# ---------------------------------------------------------------
if [[ -z "${TX_NODE_ID:-}" ]]; then
    TASK_ID=""
    if [[ -n "${ECS_CONTAINER_METADATA_URI_V4:-}" ]]; then
        TASK_ARN="$(curl -fsS --max-time 2 "${ECS_CONTAINER_METADATA_URI_V4}/task" 2>/dev/null \
                    | sed -n 's/.*"TaskARN"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' || true)"
        TASK_ID="${TASK_ARN##*/}"
    fi
    [[ -n "${TASK_ID}" ]] || TASK_ID="${HOSTNAME:-$(cat /proc/sys/kernel/hostname 2>/dev/null || echo node)}"
    TX_NODE_ID="$(printf '%s' "${TASK_ID}" | LC_ALL=C tr -cd 'A-Za-z0-9' | cut -c1-23)"
    export TX_NODE_ID
fi
say "TX_NODE_ID=${TX_NODE_ID}"

# ---------------------------------------------------------------
# 3. SIGTERM の中継 (⑬)
#    standalone.sh は LAUNCH_JBOSS_IN_BACKGROUND が設定されているときだけ、受けた TERM/INT を
#    JVM へ kill で中継し、JVM の終了を wait する。未設定だと PID 1 のシェルが SIGTERM を
#    受けても JVM に届かず、stopTimeout 後の SIGKILL で強制終了になる (停止処理が一切走らない)。
#    ECS の initProcessEnabled (tini) はゾンビ回収用で、これの代わりにはならない。
# ---------------------------------------------------------------
export LAUNCH_JBOSS_IN_BACKGROUND=true

# ---------------------------------------------------------------
# 4. 起動
# ---------------------------------------------------------------
ARGS=(-b "${JBOSS_BIND_ADDRESS:-0.0.0.0}" -c "${SERVER_CONFIG:-standalone.xml}")
if [[ "${TRUST_MODE}" == elytron ]]; then
    # Apache CXF の HTTPConduit 等、SSLContext を自前で組み立てるライブラリは
    # Elytron の default-ssl-context ではなく javax.net.ssl.trustStore* を読む (二層構え)。
    ARGS+=("-Djavax.net.ssl.trustStore=${EXTRASLB_TRUSTSTORE_PATH}"
           "-Djavax.net.ssl.trustStoreType=${EXTRASLB_TRUSTSTORE_TYPE:-PKCS12}"
           "-Djavax.net.ssl.trustStorePassword=${EXTRASLB_TRUSTSTORE_PASSWORD:-changeit}")
fi
say "TRUST_MODE=${TRUST_MODE} INBOUND_HTTPS_MODE=${INBOUND_HTTPS_MODE} EAP_SIGTERM_SUSPEND_TIMEOUT=${EAP_SIGTERM_SUSPEND_TIMEOUT:-30}"
exec "${JBOSS_HOME}/bin/standalone.sh" "${ARGS[@]}" "$@"
```

### implementation/container/modules/com/mysql/main/module.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!--
  MySQL Connector/J の JBoss モジュール定義 (⑩⑪⑬ のデータソースが使う JDBC ドライバ)。
  置き場所: ${JBOSS_HOME}/modules/com/mysql/main/  (system/layers/base ではなく、ユーザー用の modules 直下)
  jar は Dockerfile が mysql-connector-j.jar という名前でここへコピーする。

  ※ ドライバを standalone/deployments へ「デプロイ」する方式は使わない。
    ドライバを再デプロイ / アンデプロイすると、それに依存するデータソースが停止し、
    使用中の接続が破棄される (⑬ IJ000615 の原因になり得る)。
-->
<module xmlns="urn:jboss:module:1.9" name="com.mysql">
    <resources>
        <resource-root path="mysql-connector-j.jar"/>
    </resources>
    <dependencies>
        <!-- java.sql / java.naming / java.transaction.xa / java.management / java.security.jgss 等の JDK モジュール一式 -->
        <module name="java.se"/>
    </dependencies>
</module>
```

### implementation/app/src/main/webapp/WEB-INF/jboss-deployment-structure.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!--
  iwinmichl.war 用 jboss-deployment-structure.xml (修正後)

  ② WFLYSRV0058 … <resources><resource-root path="WEB-INF/classes/testClasses"/> を削除。
                  WEB-INF/classes は最初から WAR の resource-root なので、その配下を追加する必要はない。
                  テスト用クラスは本番 WAR に入れない (Maven の src/test は WAR に入らない)。
  ③ WFLYSRV0018 … <module name="org.apache.cxf.impl"/> を削除。
                  JAX-WS クライアントは webservices サブシステムが暗黙依存を付けるため記述不要。
                  タイムアウトは標準プロパティ (jakarta.xml.ws.client.*Timeout) で設定する。
                  CXF 固有 API が本当に必要な場合だけ、public な次のモジュールを使う:
                    <module name="org.jboss.ws.cxf.jbossws-cxf-client" services="import"/>
  ⑤ WFLYWELD0013 … このアプリは CDI を使わないため weld を除外 (jsf と一緒に)。
                  根本原因の EE API jar (jakarta.transaction-api など) の同梱は pom.xml 側で provided にする。
  ⑥ WFLYSRV0274 … <exclusions><module name="org.jboss.logmanager.log4j2"/> を削除。
                  このモジュールはデプロイの依存に直接入らないので、除外しても何も起きない (空振り)。
                  ・EAP のログ (logging サブシステム) に出す … 除外は不要 (推奨。log4j-core を同梱しない)
                  ・アプリ同梱の Log4j 2 実装で出す … 除外すべきは org.apache.logging.log4j.api
                    (下のコメントアウトを有効化。もしくは CLI で add-logging-api-dependencies=false)
-->
<jboss-deployment-structure xmlns="urn:jboss:deployment-structure:1.3">
    <deployment>
        <exclude-subsystems>
            <!-- spring-web の PhaseListener 実装で JSF が有効化されるのを防ぐ (JSF 不使用) -->
            <subsystem name="jsf"/>
            <!-- CDI 不使用。⑤ の警告と Weld の起動コストを無くす -->
            <subsystem name="weld"/>
        </exclude-subsystems>
        <!--
        <exclusions>
            <module name="org.apache.logging.log4j.api"/>
        </exclusions>
        -->
    </deployment>
</jboss-deployment-structure>
```

### implementation/app/pom-snippets.xml

```xml
<!--
  iwinmichl.war の pom.xml に入れる断片 (⑤⑥⑦ の WAR 側の是正)

  方針: EAP 8.1 (Jakarta EE 10) がサーバ側で提供する API は WAR に入れない (scope=provided)。
        Java EE 時代 (javax.*) の jar は入れない。ビルド時に enforcer で混入を止める。
-->
<project>

  <!-- (A) EAP 8.1 の BOM で、サーバが提供する API の版をそろえる (Red Hat Maven リポジトリ) -->
  <dependencyManagement>
    <dependencies>
      <dependency>
        <groupId>org.jboss.bom</groupId>
        <artifactId>jboss-eap-ee</artifactId>
        <!-- 版は Red Hat Maven リポジトリ (https://maven.repository.redhat.com/ga/) で、
             利用中の EAP 8.1 アップデートに対応する jboss-eap-ee の版を確認して指定する -->
        <version>${version.jboss.eap.bom}</version>
        <type>pom</type>
        <scope>import</scope>
      </dependency>
    </dependencies>
  </dependencyManagement>

  <dependencies>
    <!-- (B) サーバ提供 API は provided。WEB-INF/lib に入れない -->
    <dependency>
      <groupId>jakarta.platform</groupId>
      <artifactId>jakarta.jakartaee-api</artifactId>
      <version>10.0.0</version>
      <scope>provided</scope>
    </dependency>

    <!-- ⑤ jakarta.transaction-api などが推移的依存で WAR に入っている場合は provided に上書きする
         (TransactionScoped に @NormalScope が付いており、WildFly が「CDI アノテーションあり」と判定する) -->
    <dependency>
      <groupId>jakarta.transaction</groupId>
      <artifactId>jakarta.transaction-api</artifactId>
      <scope>provided</scope>
    </dependency>

    <!-- ⑦ JSTL は EAP 8.1 が Jakarta Standard Tag Library 3.0 を提供する。API だけ provided で参照する
         (javax.servlet:jstl:1.2 / taglibs-standard-* は削除する) -->
    <dependency>
      <groupId>jakarta.servlet.jsp.jstl</groupId>
      <artifactId>jakarta.servlet.jsp.jstl-api</artifactId>
      <scope>provided</scope>
    </dependency>

    <!-- ⑥ EAP の logging サブシステムに出す場合: log4j-api は provided、log4j-core は入れない -->
    <dependency>
      <groupId>org.apache.logging.log4j</groupId>
      <artifactId>log4j-api</artifactId>
      <scope>provided</scope>
    </dependency>
  </dependencies>

  <build>
    <plugins>
      <!-- (C) javax.* (Java EE) の jar と、サーバ提供 API の同梱をビルドで止める -->
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-enforcer-plugin</artifactId>
        <version>3.5.0</version>
        <executions>
          <execution>
            <id>ban-javaee-and-provided-apis</id>
            <goals><goal>enforce</goal></goals>
            <configuration>
              <rules>
                <bannedDependencies>
                  <excludes>
                    <exclude>javax.servlet:*</exclude>
                    <exclude>javax.servlet.jsp:*</exclude>
                    <exclude>javax.servlet.jsp.jstl:*</exclude>
                    <exclude>org.apache.taglibs:taglibs-standard-*</exclude>
                    <exclude>javax.transaction:*</exclude>
                    <exclude>javax.inject:*</exclude>
                    <exclude>org.apache.logging.log4j:log4j-core</exclude>
                  </excludes>
                </bannedDependencies>
              </rules>
            </configuration>
          </execution>
        </executions>
      </plugin>

      <!-- (D) ② テスト用クラスを WAR に入れない (src/test/** は元々 WAR に入らない)。
               どうしても WEB-INF/classes/testClasses を作っている場合は除外する -->
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-war-plugin</artifactId>
        <version>3.4.0</version>
        <configuration>
          <packagingExcludes>WEB-INF/classes/testClasses/**</packagingExcludes>
        </configuration>
      </plugin>
    </plugins>
  </build>
</project>
```

### implementation/app/src/main/java/com/example/iwinmichl/web/MethodNotAllowedAdvice.java

```java
package com.example.iwinmichl.web;

import java.util.Set;

import jakarta.servlet.RequestDispatcher;
import jakarta.servlet.http.HttpServletRequest;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;

/**
 * ⑨ 対処: 405 (HttpRequestMethodNotSupportedException) を「原因が追える 1 行」で記録する。
 *
 * Spring 既定の DefaultHandlerExceptionResolver は
 *   Resolved [org.springframework.web.HttpRequestMethodNotSupportedException: Request method 'POST' is not supported]
 * としか出さず、URL・送信元・エラーページ経由かどうかが分からない。
 * ここで先に処理すると (@ExceptionHandler が優先)、Spring 既定の WARN 行は出なくなり、代わりに
 *   HTTP 405 method=POST uri=/iwinmichl/api/hello remote=10.0.1.23 xff=203.0.113.5 ...
 * が 1 行だけ出る。応答は従来どおり 405 + Allow ヘッダ。
 *
 * ログ出力は commons-logging (spring-jcl) 経由 = EAP の logging サブシステムに乗る
 * (カテゴリ: com.example.iwinmichl.web.MethodNotAllowedAdvice)。
 */
@ControllerAdvice
@Order(Ordered.HIGHEST_PRECEDENCE)
public class MethodNotAllowedAdvice {

    private static final Log LOG = LogFactory.getLog(MethodNotAllowedAdvice.class);
    private static final int MAX_LEN = 200;

    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    public ResponseEntity<String> handleMethodNotAllowed(HttpRequestMethodNotSupportedException ex,
                                                         HttpServletRequest req) {
        Set<HttpMethod> supported = ex.getSupportedHttpMethods();
        HttpHeaders headers = new HttpHeaders();
        if (supported != null && !supported.isEmpty()) {
            headers.setAllow(supported);
        }
        if (LOG.isWarnEnabled()) {
            // エラーページへの内部転送 (ERROR ディスパッチ) で POST のまま届いたケースを見分ける
            Object errorOrigin = req.getAttribute(RequestDispatcher.ERROR_REQUEST_URI);
            LOG.warn(String.format(
                    "HTTP 405 method=%s uri=%s query=%s dispatcher=%s errorOrigin=%s remote=%s xff=%s ua=%s referer=%s allowed=%s",
                    req.getMethod(), clean(req.getRequestURI()), clean(req.getQueryString()),
                    req.getDispatcherType(), clean(errorOrigin == null ? null : errorOrigin.toString()),
                    req.getRemoteAddr(), clean(req.getHeader("X-Forwarded-For")),
                    clean(req.getHeader("User-Agent")), clean(req.getHeader("Referer")), supported));
        }
        return new ResponseEntity<>("Method Not Allowed", headers, HttpStatus.METHOD_NOT_ALLOWED);
    }

    /** ログ注入 (改行の混入) を防ぎ、長すぎる値は切り詰める。 */
    private static String clean(String s) {
        if (s == null) {
            return "-";
        }
        String t = s.replaceAll("[\\r\\n\\t]", "_");
        return t.length() > MAX_LEN ? t.substring(0, MAX_LEN) + "..." : t;
    }
}
```

### implementation/app/src/main/java/com/example/iwinmichl/dao/JdbcResourceSamples.java

```java
package com.example.iwinmichl.dao;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;

import javax.sql.DataSource;

/**
 * ⑧ IJ030040 / ⑫ IJ030042 対処: JDBC リソースの正しい閉じ方。
 *
 * 警告の STACKTRACE (java.lang.Throwable: STACKTRACE) に出ている
 * 「prepareStatement / executeQuery を呼んだ行」が直すべき場所。
 *
 * ルール:
 *   1. Connection / Statement / ResultSet は「取得した順と逆順」に必ず閉じる
 *   2. そのために try-with-resources を使う (例外時も確実に閉じる)
 *   3. Spring を使っているなら JdbcTemplate に任せる (内部で同じことをしている)
 */
public final class JdbcResourceSamples {

    private JdbcResourceSamples() {
    }

    /** 悪い例: Statement と ResultSet を閉じていない (接続返却時に IronJacamar が代わりに閉じて警告する)。 */
    static List<String> findNamesLeaky(DataSource ds, int deptId) throws SQLException {
        try (Connection c = ds.getConnection()) {
            PreparedStatement ps = c.prepareStatement("SELECT name FROM emp WHERE dept_id = ?"); // ← IJ030040
            ps.setInt(1, deptId);
            ResultSet rs = ps.executeQuery();                                                   // ← IJ030042
            List<String> names = new ArrayList<>();
            while (rs.next()) {
                names.add(rs.getString(1));
            }
            return names;
        }
    }

    /** 良い例: 3 つとも try-with-resources で閉じる。 */
    public static List<String> findNames(DataSource ds, int deptId) throws SQLException {
        try (Connection c = ds.getConnection();
             PreparedStatement ps = c.prepareStatement("SELECT name FROM emp WHERE dept_id = ?")) {
            ps.setInt(1, deptId);
            try (ResultSet rs = ps.executeQuery()) {
                List<String> names = new ArrayList<>();
                while (rs.next()) {
                    names.add(rs.getString(1));
                }
                return names;
            }
        }
    }

    /*
     * Spring JdbcTemplate を使う場合 (推奨。Statement / ResultSet の後始末を JdbcTemplate が行う):
     *
     *   List<String> names = jdbcTemplate.queryForList(
     *           "SELECT name FROM emp WHERE dept_id = ?", String.class, deptId);
     *
     * 注意: JdbcTemplate#queryForStream / Stream を返す API は、呼び出し側が Stream を
     *       try-with-resources で閉じないと同じ警告が出る。
     */
}
```

### implementation/app/src/main/java/com/example/iwinmichl/ws/SoapClientTimeouts.java

```java
package com.example.iwinmichl.ws;

import java.util.Map;

import jakarta.xml.ws.BindingProvider;

/**
 * ③ WFLYSRV0018 対処: SOAP クライアントのタイムアウトを「標準 API」だけで設定する。
 *
 * よくある private モジュール (org.apache.cxf.impl) 依存の理由は、次のような CXF 実装クラスの直接利用:
 *   HTTPConduit conduit = (HTTPConduit) ClientProxy.getClient(port).getConduit();
 *   HTTPClientPolicy policy = new HTTPClientPolicy();
 *   policy.setConnectionTimeout(5000); policy.setReceiveTimeout(30000);
 *   conduit.setClient(policy);
 * HTTPConduit / HTTPClientPolicy は cxf-rt-transports-http に入っており、EAP では private な
 * org.apache.cxf.impl モジュールに属する。
 *
 * Apache CXF 4.x (EAP 8.x 同梱) は BindingProvider のリクエストコンテキストに置いた
 *   jakarta.xml.ws.client.connectionTimeout / jakarta.xml.ws.client.receiveTimeout (ミリ秒)
 * を HTTPConduit が読む (org.apache.cxf.message.Message#CONNECTION_TIMEOUT / RECEIVE_TIMEOUT)。
 * これなら jakarta.xml.ws.* (標準 API) だけで書け、jboss-deployment-structure.xml の
 * org.apache.cxf.impl 依存を削除できる。
 */
public final class SoapClientTimeouts {

    public static final String CONNECTION_TIMEOUT = "jakarta.xml.ws.client.connectionTimeout";
    public static final String RECEIVE_TIMEOUT = "jakarta.xml.ws.client.receiveTimeout";

    private SoapClientTimeouts() {
    }

    /**
     * ポート (サービスエンドポイントインタフェースのプロキシ) または Dispatch にタイムアウトを設定する。
     *
     * @param portOrDispatch Service#getPort / Service#createDispatch で得たオブジェクト
     * @param connectMillis  接続確立までの上限 (ミリ秒)
     * @param receiveMillis  応答待ちの上限 (ミリ秒)
     */
    public static void apply(Object portOrDispatch, int connectMillis, int receiveMillis) {
        Map<String, Object> ctx = ((BindingProvider) portOrDispatch).getRequestContext();
        ctx.put(CONNECTION_TIMEOUT, connectMillis);
        ctx.put(RECEIVE_TIMEOUT, receiveMillis);
    }
}
```

### implementation/ecs/taskdef-container-fragment.json

```json
{
  "family": "iwinmichl-back",
  "requiresCompatibilities": ["FARGATE"],
  "networkMode": "awsvpc",
  "cpu": "1024",
  "memory": "2048",
  "runtimePlatform": { "operatingSystemFamily": "LINUX", "cpuArchitecture": "X86_64" },
  "containerDefinitions": [
    {
      "name": "iwinmichl",
      "image": "123456789012.dkr.ecr.ap-northeast-1.amazonaws.com/iwinmichl-back:1.0.0",
      "essential": true,
      "portMappings": [ { "containerPort": 8080, "protocol": "tcp" } ],
      "environment": [
        { "name": "DB_HOST", "value": "mif02ja.cluster-xxxxxxxx.ap-northeast-1.rds.amazonaws.com" },
        { "name": "DB_PORT", "value": "3306" },
        { "name": "DB_NAME", "value": "mif02ja" },
        { "name": "DB_MIN_POOL_SIZE", "value": "0" },
        { "name": "DB_MAX_POOL_SIZE", "value": "20" },
        { "name": "DB_IDLE_TIMEOUT_MIN", "value": "5" },
        { "name": "DB_SOCKET_TIMEOUT_MS", "value": "120000" },
        { "name": "DB_TRACK_STATEMENTS", "value": "NOWARN" },
        { "name": "EAP_SIGTERM_SUSPEND_TIMEOUT", "value": "45" },
        { "name": "JCA_CCM_DEBUG", "value": "false" },
        { "name": "TZ", "value": "Asia/Tokyo" }
      ],
      "secrets": [
        { "name": "DB_USER", "valueFrom": "arn:aws:secretsmanager:ap-northeast-1:123456789012:secret:mif02ja-db-AbCdEf:username::" },
        { "name": "DB_PASSWORD", "valueFrom": "arn:aws:secretsmanager:ap-northeast-1:123456789012:secret:mif02ja-db-AbCdEf:password::" }
      ],
      "stopTimeout": 60,
      "linuxParameters": { "initProcessEnabled": true },
      "systemControls": [
        { "namespace": "net.ipv4.tcp_keepalive_time", "value": "60" },
        { "namespace": "net.ipv4.tcp_keepalive_intvl", "value": "10" },
        { "namespace": "net.ipv4.tcp_keepalive_probes", "value": "6" }
      ],
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -fsS -o /dev/null http://localhost:9990/health/ready || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 120
      },
      "readonlyRootFilesystem": false,
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/iwinmichl-back",
          "awslogs-region": "ap-northeast-1",
          "awslogs-stream-prefix": "eap",
          "mode": "non-blocking",
          "max-buffer-size": "8m"
        }
      }
    }
  ]
}
```

### implementation/tools/check-warnings.sh

```bash
#!/bin/bash
#
# check-warnings.sh <server.log | docker logs の保存ファイル | CloudWatch Logs から落としたファイル>
#
# 警告 ①〜⑬ と関連メッセージの件数を数える (対処の前後比較・定期チェック用)。
# メッセージ ID で数えるので、日本語ロケールのログでも英語ロケールのログでも使える。
set -uo pipefail
LOG="${1:?usage: check-warnings.sh <logfile>}"
[[ -r "${LOG}" ]] || { echo "cannot read ${LOG}" >&2; exit 1; }

count() { grep -a -c -E -- "$1" "${LOG}" 2>/dev/null || true; }
row()   { printf '%-6s %-44s %5s\n' "$1" "$2" "$(count "$3")"; }

printf '%-6s %-44s %5s\n' "No" "Message" "Count"
printf '%-6s %-44s %5s\n' "------" "--------------------------------------------" "-----"
row "①"   "WFLYELY00023 keystore file does not exist"        'WFLYELY00023'
row "  ①+" "WFLYELY01084 self-signed will be generated"       'WFLYELY01084'
row "  ①+" "WFLYELY00022 does not exist and required"         'WFLYELY00022'
row "  ①+" "WFLYELY00024 certificate in keystore not valid"   'WFLYELY00024'
row "②"   "WFLYSRV0058 resource root does not exist"         'WFLYSRV0058'
row "③"   "WFLYSRV0018 private module used"                  'WFLYSRV0018'
row "  ③+" "  of which org.apache.cxf.impl"                  'WFLYSRV0018.*org\.apache\.cxf\.impl'
row "  ③+" "  of which org.jboss.vfs (spring-core)"          'WFLYSRV0018.*org\.jboss\.vfs'
row "④"   "WFLYEE0007 optional component not installed"     'WFLYEE0007'
row "  ④+" "  of which org.springframework.*"                 'WFLYEE0007.*org\.springframework\.'
row "  ④+" "  of which javax.servlet.jsp.jstl.* (=⑦)"         'WFLYEE0007.*javax\.servlet\.jsp\.jstl'
row "⑤"   "WFLYWELD0013 CDI annotations, no bean archive"   'WFLYWELD0013'
row "⑥"   "WFLYSRV0274 excluded dependency does not exist"  'WFLYSRV0274'
row "  ⑥+" "WFLYSRV0273 excluded subsystem does not exist"   'WFLYSRV0273'
row "⑦"   "Failed to define class javax.*"                  'Failed to define class javax\.'
row "⑧"   "IJ030040 statement left open"                    'IJ030040'
row "⑨"   "Resolved [...HttpRequestMethodNotSupported...]"  'Resolved \[.*HttpRequestMethodNotSupportedException'
row "  ⑨+" "HTTP 405 detail line (MethodNotAllowedAdvice)"   'HTTP 405 method='
row "⑩"   "IJ030027 destroying connection not valid"        'IJ030027'
row "⑪"   "IJ000621 destroying conn. not validated"         'IJ000621'
row "⑫"   "IJ030042 result set left open"                   'IJ030042'
row "⑬"   "IJ000615 destroying active connection"           'IJ000615'
row "  ⑬+" "IJ000100 CCM closed a leaked connection"         'IJ000100'
row "  ⑬+" "WFLYSRV0211/0272 suspending server"            'WFLYSRV02(11|72)'
row "  ⑬+" "WFLYSRV0220 shutdown requested via OS signal"   'WFLYSRV0220'
row "  ⑬+" "IJ030022 lock owned during cleanup"             'IJ030022'
row "  他" "WFLYTX0013 node-identifier is default"           'WFLYTX0013'
echo
echo "total (①〜⑬ 本体) = $(( $(count 'WFLYELY00023') + $(count 'WFLYSRV0058') + $(count 'WFLYSRV0018') + $(count 'WFLYEE0007') + $(count 'WFLYWELD0013') + $(count 'WFLYSRV0274') + $(count 'Failed to define class javax\.') + $(count 'IJ030040') + $(count 'Resolved \[.*HttpRequestMethodNotSupportedException') + $(count 'IJ030027') + $(count 'IJ000621') + $(count 'IJ030042') + $(count 'IJ000615') ))"
```

### implementation/tools/analyze-ij-log.py

```python
#!/usr/bin/env python3
"""
analyze-ij-log.py — IronJacamar (データソース) 系の警告 ⑧⑩⑪⑫⑬ をログから解析する

  (A) ⑧ IJ030040 / ⑫ IJ030042 … 閉じ忘れた Statement / ResultSet を「作った場所」のランキング
  (B) ⑪ IJ000621             … 死んでいた接続の放置時間 (= ログ時刻 - lastReturned) と idle-timeout の推奨値
  (C) ⑩ IJ030027             … 直後の Caused by から根本原因を分類 (wait_timeout / RST / 読み取りタイムアウト 等)
  (D) ⑬ IJ000615             … 停止処理中に出たのか (SIGTERM 等)、それ以外 (アンデプロイ・リロード等) か

使い方:
  python analyze-ij-log.py server.log [--pkg com.example] [--tz +09:00] [--date 2026-09-08]
    --pkg  : アプリのパッケージ接頭辞 (A の「作った場所」を探すのに使う。省略時はフレームワーク以外の最初の行)
    --tz   : ログ時刻のタイムゾーン (lastReturned 等のエポックミリ秒は UTC。既定 +00:00)
    --date : ログ行に日付が無い (HH:mm:ss,SSS だけの) 場合の日付。省略時は lastReturned から推定
"""
import argparse
import datetime as dt
import re
import statistics
import sys
from collections import Counter

TS_PATTERNS = [
    (re.compile(r'^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})[,.](\d{3})'), 'datetime'),
    (re.compile(r'^(\d{2}:\d{2}:\d{2}),(\d{3})'), 'time'),
]
FRAMEWORK_PREFIXES = ('java.', 'javax.', 'jakarta.', 'jdk.', 'sun.', 'com.sun.', 'org.jboss.', 'org.wildfly.',
                      'io.undertow.', 'com.mysql.', 'org.springframework.', 'org.apache.', 'org.hibernate.',
                      'org.mybatis.', 'org.eclipse.')
SHUTDOWN_MARKERS = ('WFLYSRV0220', 'WFLYSRV0272', 'WFLYSRV0211', 'WFLYSRV0236', 'WFLYSRV0050')


def parse_ts(line, tz, default_date):
    for pat, kind in TS_PATTERNS:
        m = pat.match(line)
        if not m:
            continue
        if kind == 'datetime':
            t = dt.datetime.strptime(f"{m.group(1)} {m.group(2)}.{m.group(3)}", "%Y-%m-%d %H:%M:%S.%f")
        else:
            if default_date is None:
                return ('time', m.group(1), m.group(2))
            t = dt.datetime.strptime(f"{default_date} {m.group(1)}.{m.group(2)}", "%Y-%m-%d %H:%M:%S.%f")
        return t.replace(tzinfo=tz)
    return None


def resolve_time_only(raw, ref_utc, tz):
    """日付の無い時刻を、基準 (lastReturned) の日付で補う。基準より前なら翌日とみなす。"""
    _, hms, ms = raw
    ref_local = ref_utc.astimezone(tz)
    t = dt.datetime.strptime(f"{ref_local:%Y-%m-%d} {hms}.{ms}", "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=tz)
    if t < ref_local - dt.timedelta(minutes=1):
        t += dt.timedelta(days=1)
    return t


def epoch_ms(value):
    return dt.datetime.fromtimestamp(int(value) / 1000, tz=dt.timezone.utc)


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')  # Windows のコンソールでも UTF-8 で出す
    ap = argparse.ArgumentParser()
    ap.add_argument('log')
    ap.add_argument('--pkg', default=None)
    ap.add_argument('--tz', default='+00:00')
    ap.add_argument('--date', default=None)
    a = ap.parse_args()
    sign = 1 if a.tz[0] != '-' else -1
    hh, mm = a.tz.lstrip('+-').split(':')
    tz = dt.timezone(sign * dt.timedelta(hours=int(hh), minutes=int(mm)))

    with open(a.log, encoding='utf-8', errors='replace') as f:
        lines = [l.rstrip('\n') for l in f]

    def stack_after(i):
        out = []
        for l in lines[i + 1:i + 200]:
            s = l.strip()
            if s.startswith('at ') or s.startswith('Caused by:') or s.startswith('...') or s.startswith('Suppressed:'):
                out.append(s)
            elif out:
                break
        return out

    # ---------- (A) ----------
    leak = Counter()
    for i, l in enumerate(lines):
        kind = 'IJ030040 Statement' if 'IJ030040' in l else ('IJ030042 ResultSet' if 'IJ030042' in l else None)
        if not kind:
            continue
        site = '(アプリのフレームが見つからない)'
        for s in stack_after(i):
            if not s.startswith('at '):
                continue
            frame = s[3:]
            if '//' in frame:  # JBoss Modules 形式: 'deployment.iwinmichl.war//com.example.Foo.bar(...)'
                frame = frame.split('//', 1)[1]
            if (a.pkg and frame.startswith(a.pkg)) or (not a.pkg and not frame.startswith(FRAMEWORK_PREFIXES)):
                site = frame
                break
        leak[(kind, site)] += 1
    print('=' * 70)
    print(' (A) ⑧ IJ030040 / ⑫ IJ030042 閉じ忘れの「作った場所」ランキング')
    print('=' * 70)
    if not leak:
        print('  (該当なし)')
    for (kind, site), n in leak.most_common(30):
        print(f'  {n:5d}  {kind:20s} {site}')

    # ---------- (B) ----------
    print('\n' + '=' * 70)
    print(' (B) ⑪ IJ000621 死んでいた接続の放置時間 (ログ時刻 - lastReturned)')
    print('=' * 70)
    idles = []
    pat = re.compile(r'lastReturned=(\d+) lastValidated=(\d+) lastCheckedOut=(\d+)')
    for l in lines:
        if 'IJ000621' not in l:
            continue
        m = pat.search(l)
        if not m:
            continue
        ret, val, out = (epoch_ms(x) for x in m.groups())
        ts = parse_ts(l, tz, a.date)
        if isinstance(ts, tuple):
            ts = resolve_time_only(ts, ret, tz)
        if ts is None:
            print(f'  (ログ時刻が読めない行) lastReturned={ret:%Y-%m-%dT%H:%M:%SZ}')
            continue
        idle = (ts - ret).total_seconds()
        idles.append(idle)
        print(f'  log={ts:%Y-%m-%d %H:%M:%S%z} lastReturned={ret:%Y-%m-%dT%H:%M:%SZ} '
              f'idle={idle:7.0f}s lastValidated={val:%H:%M:%SZ} (作成 or 最後の背景検証)')
    if idles:
        lo = min(idles)
        print(f'  件数={len(idles)}  最小={lo:.0f}s  中央値={statistics.median(idles):.0f}s  最大={max(idles):.0f}s')
        rec = max(1, int(lo / 1.5 // 60))
        print(f'  -> 最も短い放置 {lo:.0f}s で既に死んでいた。idle-timeout-minutes は {rec} 以下を推奨')
        print('     (IdleRemover は idle-timeout の半分間隔で動くため、接続は最長で約 1.5 倍まで残る)')
        print('     あわせて MySQL の wait_timeout、経路のアイドル切断 (NAT Gateway/NLB 350 秒 等) を確認すること')
    else:
        print('  (該当なし)')

    # ---------- (C) ----------
    print('\n' + '=' * 70)
    print(' (C) ⑩ IJ030027 の根本原因 (直後の Caused by から分類)')
    print('=' * 70)
    causes = Counter()
    for i, l in enumerate(lines):
        if 'IJ030027' not in l:
            continue
        text = ' '.join(stack_after(i)) + ' ' + l
        if '4031' in text or 'because of inactivity' in text:
            c = 'DB 側の wait_timeout / interactive_timeout による切断 (MySQL 8.0.24+ はエラー 4031 を返す)'
        elif 'Connection reset' in text:
            c = 'TCP RST (経路のアイドル切断 / DB 再起動・フェイルオーバー 等)'
        elif 'Read timed out' in text or 'SocketTimeoutException' in text:
            c = '読み取りタイムアウト (半開き TCP。socketTimeout で打ち切られた)'
        elif 'No operations allowed after connection closed' in text:
            c = 'ドライバ側で既に閉じられていた接続'
        elif 'Communications link failure' in text:
            c = '通信断 (Communications link failure。詳細は Caused by の下位を確認)'
        else:
            c = 'その他 (スタックトレースを個別に確認)'
        causes[c] += 1
    print(f'  IJ030027 件数={sum(causes.values())}')
    for c, n in causes.most_common():
        print(f'  {n:5d}  {c}')

    # ---------- (D) ----------
    print('\n' + '=' * 70)
    print(' (D) ⑬ IJ000615 (使用中の接続をプール停止で破棄) の発生状況')
    print('=' * 70)
    during, other = 0, 0
    for i, l in enumerate(lines):
        if 'IJ000615' not in l:
            continue
        window = lines[max(0, i - 400):i]
        if any(mk in w for w in window for mk in SHUTDOWN_MARKERS):
            during += 1
        else:
            other += 1
    print(f'  停止処理中={during}  それ以外 (アンデプロイ / リロード / データソース停止 等)={other}')
    if during:
        print('  停止処理中 -> org.wildfly.sigterm.suspend.timeout / ECS stopTimeout / ALB 登録解除遅延 / '
              'LAUNCH_JBOSS_IN_BACKGROUND を確認')
    if other:
        print('  それ以外   -> 直前の管理操作 (deploy/undeploy/:reload/データソース無効化) を確認。'
              '接続リーク疑いなら CCM debug (IJ000100)')


if __name__ == '__main__':
    sys.exit(main())
```

### implementation/tools/scan-war.py

```python
#!/usr/bin/env python3
"""
scan-war.py — WAR を静的に検査して、警告 ②③④⑤⑥⑦ の「原因になっている中身」を特定する

  ② jboss-deployment-structure.xml の <resource-root> が WAR 内に実在するか
  ③ jboss-deployment-structure.xml / MANIFEST.MF の Dependencies にある private モジュール
     (WAR 本体だけでなく WEB-INF/lib の各 jar の MANIFEST も見る。例: spring-core → org.jboss.vfs)
  ④ jakarta.servlet.AsyncListener 実装クラスのうち「引数なしコンストラクタが無い」もの
     (Weld 無効の WAR では WFLYEE0048 → WFLYEE0007 になる)
  ⑤ WildFly が「CDI アノテーション」と判定する 20 種のアノテーションの使用箇所 (どの jar か)
     と beans.xml の有無、WEB-INF/lib に同梱された Jakarta EE API jar
  ⑥ <exclusions> に書かれたモジュールのうち、デプロイの依存に直接入らないもの (空振りになる)
  ⑦ javax.* (Java EE 時代の名前空間) のクラスや TLD を含む jar

使い方:
  python scan-war.py iwinmichl.war [--jboss-home /opt/jboss-eap]
    --jboss-home を渡すと、実サーバの module.xml の jboss.api を読んで ③ を正確に判定する
外部ライブラリ不要 (Python 3.8+ 標準ライブラリのみ)。
"""
import argparse
import io
import os
import re
import struct
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict

# WildFly (weld/subsystem CdiAnnotations) が「CDI アノテーションあり」と判定する 20 種
CDI_ANNOTATIONS = [
    'jakarta/decorator/Decorator', 'jakarta/decorator/Delegate',
    'jakarta/enterprise/context/ApplicationScoped', 'jakarta/enterprise/context/ConversationScoped',
    'jakarta/enterprise/context/RequestScoped', 'jakarta/enterprise/context/SessionScoped',
    'jakarta/enterprise/context/NormalScope', 'jakarta/enterprise/context/Dependent',
    'jakarta/inject/Singleton', 'jakarta/enterprise/event/Observes',
    'jakarta/enterprise/inject/Alternative', 'jakarta/enterprise/inject/Any', 'jakarta/enterprise/inject/Default',
    'jakarta/enterprise/inject/Disposes', 'jakarta/enterprise/inject/Model', 'jakarta/enterprise/inject/New',
    'jakarta/enterprise/inject/Produces', 'jakarta/enterprise/inject/Specializes',
    'jakarta/enterprise/inject/Stereotype', 'jakarta/enterprise/inject/Typed',
]
CDI_DESC = {'L' + a + ';' for a in CDI_ANNOTATIONS}
ASYNC_LISTENER = 'jakarta/servlet/AsyncListener'

# --jboss-home 無しで使う既知の private モジュール (Red Hat「JBoss EAP 8 Included Modules」より抜粋)
KNOWN_PRIVATE = {'org.apache.cxf.impl', 'org.jboss.vfs', 'org.jboss.logmanager.log4j2', 'org.jboss.ws.spi',
                 'org.jboss.as.server', 'org.jboss.as.controller', 'org.jboss.as.ee', 'org.jboss.as.web-common',
                 'org.jboss.jandex', 'org.jboss.modules', 'org.wildfly.security.elytron-private'}
# logging サブシステムが暗黙に追加するモジュール (add-logging-api-dependencies=true のとき)
LOGGING_IMPLICIT = {'org.apache.commons.logging', 'org.apache.logging.log4j.api', 'org.jboss.logging',
                    'org.jboss.logging.jul-to-slf4j-stub', 'org.jboss.logmanager', 'org.slf4j', 'org.slf4j.impl'}
EE_API_JAR = re.compile(r'(jakarta|javax)\.[a-z.]+-api|(^|/)jakarta\.(inject|annotation|transaction|persistence|'
                        r'validation|enterprise|interceptor|servlet|ws\.rs|xml\.bind|xml\.ws|faces|ejb|jms|mail|json)',
                        re.I)


# ---------------------------------------------------------------- class file parser (最小限)
class ClassInfo:
    __slots__ = ('name', 'super', 'interfaces', 'flags', 'ctors', 'annotations', 'refs_javax_servlet')


def parse_class(data):
    if data[:4] != b'\xca\xfe\xba\xbe':
        return None
    pos = 8
    (count,) = struct.unpack_from('>H', data, pos); pos += 2
    utf8, classes = {}, {}
    i = 1
    while i < count:
        tag = data[pos]; pos += 1
        if tag == 1:
            (ln,) = struct.unpack_from('>H', data, pos); pos += 2
            utf8[i] = data[pos:pos + ln].decode('utf-8', 'replace'); pos += ln
        elif tag == 7:
            (idx,) = struct.unpack_from('>H', data, pos); pos += 2; classes[i] = idx
        elif tag in (8, 16, 19, 20):
            pos += 2
        elif tag == 15:
            pos += 3
        elif tag in (3, 4, 9, 10, 11, 12, 17, 18):
            pos += 4
        elif tag in (5, 6):
            pos += 8; i += 1
        else:
            return None
        i += 1
    cname = lambda ci: utf8.get(classes.get(ci, 0), '')
    flags, this_c, super_c, icount = struct.unpack_from('>HHHH', data, pos); pos += 8
    ifaces = [cname(struct.unpack_from('>H', data, pos + 2 * k)[0]) for k in range(icount)]
    pos += 2 * icount
    annots = set()

    def read_ev(p):
        tag = chr(data[p]); p += 1
        if tag in 'BCDFIJSZsc':
            return p + 2
        if tag == 'e':
            return p + 4
        if tag == '@':
            return read_annotation(p)
        if tag == '[':
            (n,) = struct.unpack_from('>H', data, p); p += 2
            for _ in range(n):
                p = read_ev(p)
            return p
        raise ValueError(tag)

    def read_annotation(p):
        tidx, npairs = struct.unpack_from('>HH', data, p); p += 4
        annots.add(utf8.get(tidx, ''))
        for _ in range(npairs):
            p = read_ev(p + 2)
        return p

    def read_attrs(p, ctor_holder=None):
        (n,) = struct.unpack_from('>H', data, p); p += 2
        for _ in range(n):
            nidx, ln = struct.unpack_from('>HI', data, p); p += 6
            an = utf8.get(nidx, '')
            if an in ('RuntimeVisibleAnnotations', 'RuntimeInvisibleAnnotations'):
                (k,) = struct.unpack_from('>H', data, p); q = p + 2
                for _ in range(k):
                    q = read_annotation(q)
            elif an in ('RuntimeVisibleParameterAnnotations', 'RuntimeInvisibleParameterAnnotations'):
                q = p + 1
                for _ in range(data[p]):
                    (k,) = struct.unpack_from('>H', data, q); q += 2
                    for _ in range(k):
                        q = read_annotation(q)
            p += ln
        return p

    ctors = []
    for member in ('fields', 'methods'):
        (n,) = struct.unpack_from('>H', data, pos); pos += 2
        for _ in range(n):
            _, nidx, didx = struct.unpack_from('>HHH', data, pos); pos += 6
            if member == 'methods' and utf8.get(nidx) == '<init>':
                ctors.append(utf8.get(didx, ''))
            pos = read_attrs(pos)
    read_attrs(pos)
    ci = ClassInfo()
    ci.name, ci.super, ci.interfaces, ci.flags = cname(this_c), cname(super_c), ifaces, flags
    ci.ctors, ci.annotations = ctors, annots
    ci.refs_javax_servlet = any(v.startswith(('javax/servlet/', 'Ljavax/servlet/')) or 'Ljavax/servlet/' in v
                                for v in utf8.values())
    return ci


# ---------------------------------------------------------------- WAR walking
def walk_archive(zf, origin, out_classes, out_meta):
    for info in zf.infolist():
        n = info.filename
        if n.endswith('.class'):
            try:
                ci = parse_class(zf.read(n))
            except Exception:
                ci = None
            if ci:
                out_classes.append((origin, ci))
        elif n.upper() == 'META-INF/MANIFEST.MF':
            out_meta[origin]['manifest'] = zf.read(n).decode('utf-8', 'replace')
        elif n.lower().endswith('.tld'):
            out_meta[origin].setdefault('tlds', []).append((n, zf.read(n).decode('utf-8', 'replace')))
        elif n.endswith('beans.xml'):
            out_meta[origin].setdefault('beans', []).append(n)


def manifest_deps(text):
    if not text:
        return []
    joined = re.sub(r'\r?\n ', '', text)
    for line in joined.splitlines():
        if line.lower().startswith('dependencies:'):
            return [d.strip().split()[0] for d in line.split(':', 1)[1].split(',') if d.strip()]
    return []


def module_api(jboss_home, name):
    if not jboss_home:
        return 'private' if name in KNOWN_PRIVATE else '?'
    rel = name.replace('.', os.sep)
    for base in (os.path.join(jboss_home, 'modules', 'system', 'layers', 'base'), os.path.join(jboss_home, 'modules')):
        p = os.path.join(base, rel, 'main', 'module.xml')
        if os.path.exists(p):
            m = re.search(r'name="jboss\.api"\s+value="([^"]+)"', open(p, encoding='utf-8').read())
            return m.group(1) if m else 'public'
    return 'not-found'


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')  # Windows のコンソールでも UTF-8 で出す
    ap = argparse.ArgumentParser()
    ap.add_argument('war')
    ap.add_argument('--jboss-home')
    a = ap.parse_args()
    war = zipfile.ZipFile(a.war)
    names = set(war.namelist())
    classes, meta = [], defaultdict(dict)
    walk_archive(war, '(WAR)', classes, meta)
    libs = sorted(n for n in names if n.startswith('WEB-INF/lib/') and n.endswith('.jar'))
    for lib in libs:
        try:
            walk_archive(zipfile.ZipFile(io.BytesIO(war.read(lib))), lib.split('/')[-1], classes, meta)
        except zipfile.BadZipFile:
            pass

    jds = None
    for cand in ('WEB-INF/jboss-deployment-structure.xml', 'META-INF/jboss-deployment-structure.xml'):
        if cand in names:
            jds = ET.fromstring(war.read(cand))
    strip = lambda t: t.split('}')[-1]
    findall = lambda el, tag: [e for e in el.iter() if strip(e.tag) == tag] if el is not None else []

    print(f'# scan-war: {a.war}  (classes={len(classes)}, WEB-INF/lib jars={len(libs)})')

    # ② -------------------------------------------------------------
    print('\n## ② resource-root (jboss-deployment-structure.xml)')
    roots = [e.get('path') for e in findall(jds, 'resource-root')]
    if not roots:
        print('  OK: 追加リソースルートの指定なし')
    for r in roots:
        exists = any(n == r or n.startswith(r.rstrip('/') + '/') for n in names)
        print(f'  {"OK " if exists else "NG "} {r}  {"(存在する)" if exists else "← WAR に無い: WFLYSRV0058 の原因。記述を削除する"}')

    # ③ -------------------------------------------------------------
    print('\n## ③ 明示依存 (jboss-deployment-structure.xml / MANIFEST.MF Dependencies)')
    deps = [(e.get('name'), 'jboss-deployment-structure.xml') for e in findall(jds, 'dependencies')
            for e in findall(e, 'module')]
    for origin, m in meta.items():
        for d in manifest_deps(m.get('manifest')):
            deps.append((d, f'{origin} の MANIFEST.MF'))
    if not deps:
        print('  明示依存なし')
    for name, src in deps:
        api = module_api(a.jboss_home, name)
        mark = 'NG ' if api in ('private', 'unsupported', 'deprecated') else 'OK '
        print(f'  {mark}{name:40s} jboss.api={api:11s} 出どころ: {src}')

    # ⑥ -------------------------------------------------------------
    print('\n## ⑥ exclusions (除外指定)')
    excl = [e.get('name') for e in findall(jds, 'exclusions') for e in findall(e, 'module')]
    if not excl:
        print('  除外指定なし')
    for x in excl:
        if x == 'org.jboss.logmanager.log4j2':
            print(f'  NG {x}: デプロイの依存に直接入らない (org.apache.logging.log4j.api の内部依存) → 空振り = WFLYSRV0274。'
                  ' 自前の Log4j 2 を使うなら除外対象は org.apache.logging.log4j.api')
        elif x in LOGGING_IMPLICIT:
            print(f'  OK {x}: logging サブシステムの暗黙依存 (除外は有効)')
        else:
            print(f'  ?  {x}: 暗黙依存に入っていなければ WFLYSRV0274 (空振り)。サーバログで確認')
    subs = [e.get('name') for e in findall(jds, 'exclude-subsystems') for e in findall(e, 'subsystem')]
    print(f'  exclude-subsystems: {subs or "なし"}')

    # ④ -------------------------------------------------------------
    print('\n## ④ jakarta.servlet.AsyncListener 実装 (Weld 無効の WAR では引数なしコンストラクタが必要)')
    by_name = {ci.name: (o, ci) for o, ci in classes}

    def implements(cn, target, seen=None):
        seen = seen or set()
        if cn in seen or cn not in by_name:
            return False
        seen.add(cn)
        _, c = by_name[cn]
        if target in c.interfaces:
            return True
        return any(implements(x, target, seen) for x in c.interfaces + [c.super])

    hits = 0
    for o, ci in classes:
        if ci.flags & 0x0600:  # interface / abstract
            continue
        if implements(ci.name, ASYNC_LISTENER):
            hits += 1
            ok = '()V' in ci.ctors
            print(f'  {"OK " if ok else "NG "}{ci.name.replace("/", ".")}  [{o}]'
                  f'{"" if ok else "  ← 引数なしコンストラクタ無し (WFLYEE0048 → WFLYEE0007)"}')
    if not hits:
        print('  該当なし')

    # ⑤ -------------------------------------------------------------
    print('\n## ⑤ WildFly が「CDI アノテーション」と判定するもの (WFLYWELD0013 の材料)')
    beans = [(o, b) for o, m in meta.items() for b in m.get('beans', [])]
    print(f'  beans.xml: {beans or "なし"}')
    cdi_by_origin = defaultdict(set)
    for o, ci in classes:
        for d in ci.annotations & CDI_DESC:
            cdi_by_origin[o].add(f'{ci.name.replace("/", ".")} @{d[1:-1].split("/")[-1]}')
    if not cdi_by_origin:
        print('  使用なし')
    for o, uses in sorted(cdi_by_origin.items()):
        print(f'  NG {o}: {len(uses)} 件  例: {sorted(uses)[:3]}')
    ee_api = [l.split('/')[-1] for l in libs if EE_API_JAR.search(l.split('/')[-1])]
    print(f'  WEB-INF/lib の Jakarta/Java EE API jar (サーバが提供するので provided にする): {ee_api or "なし"}')

    # ⑦ -------------------------------------------------------------
    print('\n## ⑦ javax.* (Java EE 時代) の痕跡')
    javax_jars = defaultdict(int)
    for o, ci in classes:
        if ci.name.startswith('javax/servlet/') or ci.refs_javax_servlet:
            javax_jars[o] += 1
    for o, m in meta.items():
        for tld, text in m.get('tlds', []):
            for cls in re.findall(r'<(?:validator-class|tag-class|listener-class)>\s*(javax\.[\w.$]+)', text):
                print(f'  NG TLD {o}:{tld} → {cls}')
    for o, n in sorted(javax_jars.items()):
        print(f'  NG {o}: javax.servlet を参照・定義するクラス {n} 個 (EAP 8 は jakarta.* のみ。Jakarta 版へ置換/除去)')
    if not javax_jars:
        print('  javax.servlet の参照なし')
    return 0


if __name__ == '__main__':
    sys.exit(main())
```

## 検証結果

### シナリオ

| 記号 | 内容 |
|---|---|
| S0 修正前 | EAP 既定 + ExtraSLB 方式の信頼設定 + 修正前 WAR + 修正前データソース。SIGTERM は JVM へ中継 (LAUNCH_JBOSS_IN_BACKGROUND=true)、サスペンド待ち 0 秒 |
| S0n 修正前・中継なし | S0 と同じで LAUNCH_JBOSS_IN_BACKGROUND 未設定 (SIGTERM が JVM に届かない場合) |
| S1 修正後 (system/remove) | 本書の実装: TRUST_MODE=system、INBOUND_HTTPS_MODE=remove + 修正後 WAR。EAP_SIGTERM_SUSPEND_TIMEOUT=30、DB_IDLE_TIMEOUT_MIN=1、DB_TRACK_STATEMENTS=TRUE |
| S1e 修正後 (elytron) | S1 の TRUST_MODE を elytron (ExtraSLB 方式 + required=true) にしたもの |
| S1d 修正後 (dedicated) | S1 の INBOUND_HTTPS_MODE を dedicated (起動時に渡す正式な鍵ストア) にしたもの |

共通: MySQL 8.4.11 (wait_timeout=150 秒)、自己署名ルート CA の HTTPS テストサーバ (extraslb-test)、SOAP バックエンド (ws-backend.war)。各シナリオは ブート → 機能確認 → 170 秒放置して DB 接続を切らせて再利用 → 15 秒かかる DB 処理の最中に docker stop (SIGTERM) の順。

### 警告の件数 (check-warnings.sh)

| 項目 | S0 修正前 | S0n 修正前・中継なし | S1 修正後 (system/remove) |
|---|---|---|---|
| ①    WFLYELY00023 keystore file does not exist | 1 | 1 | 0 |
| ①+ WFLYELY01084 self-signed will be generated | 1 | 1 | 0 |
| ①+ WFLYELY00022 does not exist and required | 0 | 0 | 0 |
| ①+ WFLYELY00024 certificate in keystore not valid | 0 | 0 | 0 |
| ②    WFLYSRV0058 resource root does not exist | 1 | 1 | 0 |
| ③    WFLYSRV0018 private module used | 2 | 2 | 0 |
| ③+   of which org.apache.cxf.impl | 1 | 1 | 0 |
| ③+   of which org.jboss.vfs (spring-core) | 1 | 1 | 0 |
| ④    WFLYEE0007 optional component not installed | 8 | 8 | 0 |
| ④+   of which org.springframework.* | 6 | 6 | 0 |
| ④+   of which javax.servlet.jsp.jstl.* (=⑦) | 2 | 2 | 0 |
| ⑤    WFLYWELD0013 CDI annotations, no bean archive | 1 | 1 | 0 |
| ⑥    WFLYSRV0274 excluded dependency does not exist | 1 | 1 | 0 |
| ⑥+ WFLYSRV0273 excluded subsystem does not exist | 0 | 0 | 0 |
| ⑦    Failed to define class javax.* | 4 | 4 | 0 |
| ⑧    IJ030040 statement left open | 1 | 1 | 0 |
| ⑨    Resolved [...HttpRequestMethodNotSupported...] | 1 | 1 | 0 |
| ⑨+ HTTP 405 detail line (MethodNotAllowedAdvice) | 0 | 0 | 1 |
| ⑩    IJ030027 destroying connection not valid | 1 | 0 | 0 |
| ⑪    IJ000621 destroying conn. not validated | 1 | 0 | 0 |
| ⑫    IJ030042 result set left open | 1 | 1 | 0 |
| ⑬    IJ000615 destroying active connection | 1 | 0 | 0 |
| ⑬+ IJ000100 CCM closed a leaked connection | 0 | 0 | 0 |
| ⑬+ WFLYSRV0211/0272 suspending server | 1 | 0 | 1 |
| ⑬+ WFLYSRV0220 shutdown requested via OS signal | 1 | 0 | 1 |
| ⑬+ IJ030022 lock owned during cleanup | 1 | 0 | 0 |
| 他  WFLYTX0013 node-identifier is default | 1 | 1 | 0 |
| 合計 (①〜⑬ 本体) | 24 | 21 | 0 |

S1e (TRUST_MODE=elytron) と S1d (INBOUND_HTTPS_MODE=dedicated) の件数は、全項目で S1 と同じ値でした (①〜⑬ の本体合計 0)。

### 機能確認の記録 (S0 修正前)

```text
### label=s0-before image=wl-before:1 war=iwinmichl-bad.war args=-e LAUNCH_JBOSS_IN_BACKGROUND=true
### boot line
05:30:51,136 INFO  [org.jboss.as] (Controller Boot Thread) WFLYSRV0025: WildFly 35.0.1.Final (WildFly Core 27.0.1.Final) started in 14239ms - Started 906 of 1113 services (334 services are lazy, passive or on-demand) - Server configuration file in use: standalone.xml - Minimum feature stability level: community
### GET /iwinmichl/jstl.jsp (⑦)
JSTL-OK (old URI http://java.sun.com/jsp/jstl/core)
  (HTTP 200)
### GET /iwinmichl/jstl-fmt.jsp (⑦)
1,234.5
  (HTTP 200)
### GET /iwinmichl/jstl-new.jsp (⑦)
<html><head><title>Error</title></head><body>/iwinmichl/jstl-new.jsp</body></html>  (HTTP 404)
### POST /iwinmichl/api/hello (⑨)
HTTP/1.1 405 Method Not Allowed
Allow: GET
### GET /iwinmichl/api/async (④: Spring の非同期処理)
async-ok on MvcAsync1  (HTTP 200)
### GET /iwinmichl/tls?url=https://extraslb-test/ (①: 自己署名ルート CA)
SSLContext.getDefault() = org.wildfly.security.ssl.DelegatingSSLContext (provider=SunJSSE)
javax.net.ssl.trustStore = /opt/app/security/extraslb-truststore.p12
A HttpsURLConnection(default)         -> OK  HTTP 200 issuer=CN=ExtraSLB Test Root CA,O=ExtraSLB Test
B java.net.http.HttpClient(default)   -> OK  HTTP 200
C new SSLContext(TLS).init(null,...)  -> OK  HTTP 200 issuer=CN=ExtraSLB Test Root CA,O=ExtraSLB Test
### GET /iwinmichl/tls?url=https://www.google.com/ (①: パブリック CA)
SSLContext.getDefault() = org.wildfly.security.ssl.DelegatingSSLContext (provider=SunJSSE)
javax.net.ssl.trustStore = /opt/app/security/extraslb-truststore.p12
A HttpsURLConnection(default)         -> OK  HTTP 200 issuer=CN=WR2,O=Google Trust Services,C=US
B java.net.http.HttpClient(default)   -> OK  HTTP 200
C new SSLContext(TLS).init(null,...)  -> OK  HTTP 200 issuer=CN=WR2,O=Google Trust Services,C=US
### GET /iwinmichl/soap?sleepMs=3000&timeoutMs=1000 (③: 標準プロパティでタイムアウト)
TIMEOUT/ERROR after 1482 ms: java.net.SocketTimeoutException: Read timed out
### GET /iwinmichl/soap?sleepMs=200&timeoutMs=3000 (③: 正常応答)
OK in 266 ms: slept 200 (client=org.apache.cxf.jaxws.DispatchImpl)
### GET /iwinmichl/db/ok
ok 1
  (HTTP 200)
### GET /iwinmichl/db/leak (⑧⑫)
leaked 1
  (HTTP 200)
### 170 秒放置 (MySQL wait_timeout=150 を超える) → 再利用 (⑩⑪)
### GET /iwinmichl/db/ok (放置後)
ok 1
  (HTTP 200)
### ⑬: /db/slow?sec=15 の実行中 (3 秒後) に docker stop -t 90 (SIGTERM)
docker stop 所要: 13 秒 / コンテナ終了コード: 0
slow の応答:   (HTTP 000)
```

### 機能確認の記録 (S1 修正後)

```text
### label=s1-after-system image=wl-after-system-remove:1 war=iwinmichl-fixed.war args=-e EAP_SIGTERM_SUSPEND_TIMEOUT=30 -e DB_IDLE_TIMEOUT_MIN=1 -e DB_TRACK_STATEMENTS=TRUE
### boot line
05:48:16,545 INFO  [org.jboss.as] (Controller Boot Thread) WFLYSRV0025: WildFly 35.0.1.Final (WildFly Core 27.0.1.Final) started in 5147ms - Started 597 of 804 services (334 services are lazy, passive or on-demand) - Server configuration file in use: standalone.xml - Minimum feature stability level: community
### GET /iwinmichl/jstl.jsp (⑦)
JSTL-OK (old URI http://java.sun.com/jsp/jstl/core)
  (HTTP 200)
### GET /iwinmichl/jstl-fmt.jsp (⑦)
1,234.5
  (HTTP 200)
### GET /iwinmichl/jstl-new.jsp (⑦)
JSTL-OK (new URN jakarta.tags.core)
  (HTTP 200)
### POST /iwinmichl/api/hello (⑨)
HTTP/1.1 405 Method Not Allowed
Allow: GET
### GET /iwinmichl/api/async (④: Spring の非同期処理)
async-ok on MvcAsync1  (HTTP 200)
### GET /iwinmichl/tls?url=https://extraslb-test/ (①: 自己署名ルート CA)
SSLContext.getDefault() = javax.net.ssl.SSLContext (provider=SunJSSE)
javax.net.ssl.trustStore = null
A HttpsURLConnection(default)         -> OK  HTTP 200 issuer=CN=ExtraSLB Test Root CA,O=ExtraSLB Test
B java.net.http.HttpClient(default)   -> OK  HTTP 200
C new SSLContext(TLS).init(null,...)  -> OK  HTTP 200 issuer=CN=ExtraSLB Test Root CA,O=ExtraSLB Test
### GET /iwinmichl/tls?url=https://www.google.com/ (①: パブリック CA)
SSLContext.getDefault() = javax.net.ssl.SSLContext (provider=SunJSSE)
javax.net.ssl.trustStore = null
A HttpsURLConnection(default)         -> OK  HTTP 200 issuer=CN=WR2,O=Google Trust Services,C=US
B java.net.http.HttpClient(default)   -> OK  HTTP 200
C new SSLContext(TLS).init(null,...)  -> OK  HTTP 200 issuer=CN=WR2,O=Google Trust Services,C=US
### GET /iwinmichl/soap?sleepMs=3000&timeoutMs=1000 (③: 標準プロパティでタイムアウト)
TIMEOUT/ERROR after 1183 ms: java.net.SocketTimeoutException: Read timed out
### GET /iwinmichl/soap?sleepMs=200&timeoutMs=3000 (③: 正常応答)
OK in 232 ms: slept 200 (client=org.apache.cxf.jaxws.DispatchImpl)
### GET /iwinmichl/db/ok
ok 1
  (HTTP 200)
### GET /iwinmichl/db/fixed (⑧⑫)
fixed 1
  (HTTP 200)
### 170 秒放置 (MySQL wait_timeout=150 を超える) → 再利用 (⑩⑪)
### GET /iwinmichl/db/ok (放置後)
ok 1
  (HTTP 200)
### ⑬: /db/slow?sec=15 の実行中 (3 秒後) に docker stop -t 90 (SIGTERM)
docker stop 所要: 13 秒 / コンテナ終了コード: 0
slow の応答: slept 15
  (HTTP 200)
```

### SIGTERM が JVM に届かない場合 (S0n)

```text
: /db/slow?sec=15 の実行中 (3 秒後) に docker stop -t 90 (SIGTERM)
docker stop 所要: 91 秒 / コンテナ終了コード: 137
slow の応答: slept 15
  (HTTP 200)
```

standalone.sh が PID 1 で LAUNCH_JBOSS_IN_BACKGROUND が未設定だと、SIGTERM が JVM に届かず、docker stop の猶予 (90 秒) を使い切って SIGKILL (終了コード 137) された。停止ログも出ない (処理中の要求は猶予の間に終わったので成功している)。

### ① の追加実験 (Q1・Q2・方式比較)

```text
########## E1 現行 (修正前イメージ): p12 は /opt/app/security、-Djavax.net.ssl.trustStore* を standalone.sh 引数で渡す
--- e1-current: boot result / keystore 関連 / サービス失敗
05:40:50,679 WARN  [org.wildfly.extension.elytron] (MSC service thread 1-6) WFLYELY00023: KeyStore file '/opt/jboss-eap/standalone/configuration/application.keystore' does not exist. Used blank.
05:40:50,686 WARN  [org.wildfly.extension.elytron] (MSC service thread 1-1) WFLYELY01084: KeyStore /opt/jboss-eap/standalone/configuration/application.keystore not found, it will be auto-generated on first use with a self-signed certificate for host localhost
05:40:53,271 INFO  [org.jboss.as] (Controller Boot Thread) WFLYSRV0025: WildFly 35.0.1.Final (WildFly Core 27.0.1.Final) started in 4970ms - Started 533 of 740 services (329 services are lazy, passive or on-demand) - Server configuration file in use: standalon
--- outbound TLS probe (https://extraslb-test/)
SSLContext.getDefault() = org.wildfly.security.ssl.DelegatingSSLContext (provider=SunJSSE)
javax.net.ssl.trustStore = /opt/app/security/extraslb-truststore.p12
A HttpsURLConnection(default)         -> OK  HTTP 200 issuer=CN=ExtraSLB Test Root CA,O=ExtraSLB Test
B java.net.http.HttpClient(default)   -> OK  HTTP 200
C new SSLContext(TLS).init(null,...)  -> OK  HTTP 200 issuer=CN=ExtraSLB Test Root CA,O=ExtraSLB Test
--- 8443: subject=CN=localhost

########## E2 Q2: 引数で -Djavax.net.ssl.keyStore=<p12> も渡す
--- e2-keystore-arg: boot result / keystore 関連 / サービス失敗
05:41:03,046 WARN  [org.wildfly.extension.elytron] (MSC service thread 1-1) WFLYELY00023: KeyStore file '/opt/jboss-eap/standalone/configuration/application.keystore' does not exist. Used blank.
05:41:03,075 WARN  [org.wildfly.extension.elytron] (MSC service thread 1-1) WFLYELY01084: KeyStore /opt/jboss-eap/standalone/configuration/application.keystore not found, it will be auto-generated on first use with a self-signed certificate for host localhost
05:41:05,744 INFO  [org.jboss.as] (Controller Boot Thread) WFLYSRV0025: WildFly 35.0.1.Final (WildFly Core 27.0.1.Final) started in 5033ms - Started 533 of 740 services (329 services are lazy, passive or on-demand) - Server configuration file in use: standalon

########## E3 現行設定 (required=false) で自前トラストストアのパスを誤る
--- e3-wrongpath-current: boot result / keystore 関連 / サービス失敗
05:41:13,973 WARN  [org.wildfly.extension.elytron] (MSC service thread 1-2) WFLYELY00023: KeyStore file '/opt/jboss-eap/standalone/configuration/application.keystore' does not exist. Used blank.
05:41:13,984 WARN  [org.wildfly.extension.elytron] (MSC service thread 1-3) WFLYELY00023: KeyStore file '/opt/app/security/NOT-EXIST.p12' does not exist. Used blank.
05:41:13,988 WARN  [org.wildfly.extension.elytron] (MSC service thread 1-5) WFLYELY01084: KeyStore /opt/jboss-eap/standalone/configuration/application.keystore not found, it will be auto-generated on first use with a self-signed certificate for host localhost
05:41:16,434 INFO  [org.jboss.as] (Controller Boot Thread) WFLYSRV0025: WildFly 35.0.1.Final (WildFly Core 27.0.1.Final) started in 4895ms - Started 533 of 740 services (329 services are lazy, passive or on-demand) - Server configuration file in use: standalon
--- outbound TLS probe (https://extraslb-test/)
SSLContext.getDefault() = org.wildfly.security.ssl.DelegatingSSLContext (provider=SunJSSE)
javax.net.ssl.trustStore = /opt/app/security/NOT-EXIST.p12
A HttpsURLConnection(default)         -> NG  InvalidAlgorithmParameterException: the trustAnchors parameter must be non-empty
B java.net.http.HttpClient(default)   -> NG  InvalidAlgorithmParameterException: the trustAnchors parameter must be non-empty
C new SSLContext(TLS).init(null,...)  -> NG  SunCertPathBuilderException: unable to find valid certification path to requested target
--- outbound TLS probe (https://www.google.com/)
SSLContext.getDefault() = org.wildfly.security.ssl.DelegatingSSLContext (provider=SunJSSE)
javax.net.ssl.trustStore = /opt/app/security/NOT-EXIST.p12
A HttpsURLConnection(default)         -> NG  InvalidAlgorithmParameterException: the trustAnchors parameter must be non-empty
B java.net.http.HttpClient(default)   -> NG  InvalidAlgorithmParameterException: the trustAnchors parameter must be non-empty
C new SSLContext(TLS).init(null,...)  -> OK  HTTP 200 issuer=CN=WR2,O=Google Trust Services,C=US

########## E4 修正後 elytron (required=true) で自前トラストストアのパスを誤る (entrypoint の事前チェックを迂回)
--- e4-wrongpath-required: boot result / keystore 関連 / サービス失敗
Caused by: org.jboss.msc.service.StartException in anonymous service: WFLYELY00022: KeyStore file '/opt/app/security/NOT-EXIST.p12' does not exist and required.
    Caused by: org.jboss.msc.service.StartException in anonymous service: WFLYELY00022: KeyStore file '/opt/app/security/NOT-EXIST.p12' does not exist and required."}}
WFLYCTL0186:   Services which failed to start:      service org.wildfly.security.key-store.extraslb-trust-store: WFLYELY00004: Unable to start the service.
WFLYCTL0448: 3 additional services are down due to their dependencies being missing or failed
05:41:26,959 ERROR [org.jboss.as] (Controller Boot Thread) WFLYSRV0026: WildFly 35.0.1.Final (WildFly Core 27.0.1.Final) started (with errors) in 3909ms - Started 348 of 568 services (5 services failed or missing dependencies, 326 services are lazy, passive or
--- outbound TLS probe (https://extraslb-test/)
<html><head><title>Error</title></head><body>404 - Not Found</body></html>--- 参考: entrypoint 経由なら起動前に止まる
==> [entrypoint] FATAL: トラストストアが読めません: /opt/app/security/NOT-EXIST.p12

########## E5 ExtraSLB の事前生成方式 (provision-application-keystore.sh を起動前に実行)
--- e5-provision: boot result / keystore 関連 / サービス失敗
==> [app-keystore]   -> EAP が初回 HTTPS 接続時に自動生成するものと同じ内容です (WFLYELY00023/01084 が出なくなります)
05:41:37,890 INFO  [org.jboss.as] (Controller Boot Thread) WFLYSRV0025: WildFly 35.0.1.Final (WildFly Core 27.0.1.Final) started in 4919ms - Started 533 of 740 services (329 services are lazy, passive or on-demand) - Server configuration file in use: standalon
--- 8443: subject=CN=localhost

########## E6 remove / dedicated の 8443
--- e6-remove: boot result / keystore 関連 / サービス失敗
05:41:49,059 INFO  [org.jboss.as] (Controller Boot Thread) WFLYSRV0025: WildFly 35.0.1.Final (WildFly Core 27.0.1.Final) started in 5053ms - Started 528 of 735 services (329 services are lazy, passive or on-demand) - Server configuration file in use: standalon
--- 8443: 接続できない (待ち受けなし)
--- e6-dedicated: boot result / keystore 関連 / サービス失敗
05:42:00,942 INFO  [org.jboss.as] (Controller Boot Thread) WFLYSRV0025: WildFly 35.0.1.Final (WildFly Core 27.0.1.Final) started in 5215ms - Started 533 of 740 services (329 services are lazy, passive or on-demand) - Server configuration file in use: standalon
--- 8443: subject=O=Verification, CN=iwinmichl.internal
--- 参考: dedicated で鍵ストアを渡し忘れた場合 (entrypoint)
==> [entrypoint] FATAL: インバウンド用鍵ストアがありません: /opt/app/runtime-security/inbound-server.p12

########## E7 TRUST_MODE=system: JDK cacerts に CA が入っていること / -D なし
/etc/pki/ca-trust/extracted/java/cacerts
extraslbtestrootca, Oct 11, 2026, trustedCertEntry, 
Certificate fingerprint (SHA-256): CA:93:57:A2:E6:55:25:CE:80:77:28:08:9B:2D:71:6A:C8:86:A2:F4:17:6F:34:A7:8F:32:72:1C:7E:5F:D6:BA
extraslb-ca-1.pem
```

### ④ の原因 (DEBUG) と ⑥ の除外指定の実験

```text
########## E8 ④ の原因を DEBUG で確認 (org.jboss.as.ee を DEBUG、CONSOLE ハンドラも DEBUG にして再デプロイ)
Not installing optional component javax.servlet.jsp.jstl.tlv.PermittedTaglibsTLV due to an exception: java.lang.NoClassDefFoundError: Failed to link javax/servlet/jsp/jstl/tlv/PermittedTaglibsTLV (Module "deployment.iwinmichl.war" from Service Module Loader): javax/servlet/jsp/tagext/TagLibraryValidator
Not installing optional component javax.servlet.jsp.jstl.tlv.ScriptFreeTLV due to an exception: java.lang.NoClassDefFoundError: Failed to link javax/servlet/jsp/jstl/tlv/ScriptFreeTLV (Module "deployment.iwinmichl.war" from Service Module Loader): javax/servlet/jsp/tagext/TagLibraryValidator
Not installing optional component org.springframework.http.server.ServletServerHttpAsyncRequestControl due to an exception: org.jboss.as.server.deployment.DeploymentUnitProcessingException: WFLYEE0048: Could not find default constructor for class org.springframework.http.server.ServletServerHttpAsyncRequestControl
Not installing optional component org.springframework.http.server.reactive.ServletHttpHandlerAdapter$HttpHandlerAsyncListener due to an exception: org.jboss.as.server.deployment.DeploymentUnitProcessingException: WFLYEE0048: Could not find default constructor for class org.springframework.http.server.reactive.ServletHttpHandlerA
Not installing optional component org.springframework.http.server.reactive.ServletServerHttpRequest$RequestAsyncListener due to an exception: org.jboss.as.server.deployment.DeploymentUnitProcessingException: WFLYEE0048: Could not find default constructor for class org.springframework.http.server.reactive.ServletServerHttpRequest
Not installing optional component org.springframework.http.server.reactive.ServletServerHttpResponse$ResponseAsyncListener due to an exception: org.jboss.as.server.deployment.DeploymentUnitProcessingException: WFLYEE0048: Could not find default constructor for class org.springframework.http.server.reactive.ServletServerHttpRespo
Not installing optional component org.springframework.web.context.request.async.StandardServletAsyncWebRequest due to an exception: org.jboss.as.server.deployment.DeploymentUnitProcessingException: WFLYEE0048: Could not find default constructor for class org.springframework.web.context.request.async.StandardServletAsyncWebReques
Not installing optional component org.springframework.web.filter.ServerHttpObservationFilter$ObservationAsyncListener due to an exception: org.jboss.as.server.deployment.DeploymentUnitProcessingException: WFLYEE0048: Could not find default constructor for class org.springframework.web.filter.ServerHttpObservationFilter$Observati

########## E9 ⑥ Log4j 2 を同梱した WAR + 除外指定 = none
(jboss-deployment-structure.xml なし)
LoggerContext=org.jboss.logmanager.log4j.JBossLoggerContext
log4j-api loaded from=(jar:file:/opt/jboss-eap/modules/system/layers/base/org/apache/logging/log4j/api/main/log4j-api-2.23.1.jar!/ <no signer certificates>)
05:47:36,626 INFO  [com.example.l4j.L4jServlet] (default task-1) hello-from-app-log4j2

########## E9 ⑥ Log4j 2 を同梱した WAR + 除外指定 = bad
(<exclusions><module name="org.jboss.logmanager.log4j2"/>)
LoggerContext=org.jboss.logmanager.log4j.JBossLoggerContext
log4j-api loaded from=(jar:file:/opt/jboss-eap/modules/system/layers/base/org/apache/logging/log4j/api/main/log4j-api-2.23.1.jar!/ <no signer certificates>)
05:47:42,661 WARN  [org.jboss.as.server.deployment] (MSC service thread 1-2) WFLYSRV0274: Excluded dependency org.jboss.logmanager.log4j2 via jboss-deployment-structure.xml does not exist.
05:47:45,887 INFO  [com.example.l4j.L4jServlet] (default task-1) hello-from-app-log4j2

########## E9 ⑥ Log4j 2 を同梱した WAR + 除外指定 = good
(<exclusions><module name="org.apache.logging.log4j.api"/>)
LoggerContext=org.apache.logging.log4j.core.LoggerContext
log4j-api loaded from=(vfs:/content/l4j.war/WEB-INF/lib/log4j-api-2.26.1.jar <no signer certificates>)
05:47:55,327 INFO  [stdout] (default task-1) APPLOG4J|INFO|com.example.l4j.L4jServlet|hello-from-app-log4j2
```

### 修正前ログの抜粋 (S0)

```text
05:30:41,309 WARN  [org.wildfly.extension.elytron] (MSC service thread 1-1) WFLYELY00023: KeyStore file '/opt/jboss-eap/standalone/configuration/application.keystore' does not exist. Used blank.
05:30:41,353 WARN  [org.wildfly.extension.elytron] (MSC service thread 1-1) WFLYELY01084: KeyStore /opt/jboss-eap/standalone/configuration/application.keystore not found, it will be auto-generated on first use with a self-signed certificate for host localhost
05:30:45,529 WARN  [org.jboss.as.server.deployment] (MSC service thread 1-5) WFLYSRV0058: Additional resource root /content/iwinmichl.war/WEB-INF/classes/testClasses added via jboss-deployment-structure.xml does not exist
05:30:46,115 WARN  [org.jboss.as.dependency.private] (MSC service thread 1-1) WFLYSRV0018: Deployment "deployment.iwinmichl.war" is using a private module ("org.apache.cxf.impl") which may be changed or removed in future versions without notice.
05:30:46,402 WARN  [org.jboss.modules.define] (MSC service thread 1-4) Failed to define class javax.servlet.jsp.jstl.tlv.PermittedTaglibsTLV in Module "deployment.iwinmichl.war" from Service Module Loader: java.lang.NoClassDefFoundError: Failed to link javax/servlet/jsp/jstl/tlv/PermittedTaglibsTLV (Module "deployment.iwinmichl.war" from Service Module Loader): javax/servlet/jsp/tagext/TagLibraryValidator
05:30:46,647 WARN  [org.jboss.as.ee] (MSC service thread 1-2) WFLYEE0007: Not installing optional component org.springframework.http.server.reactive.ServletServerHttpRequest$RequestAsyncListener due to an exception (enable DEBUG log level to see the cause)
05:30:47,028 WARN  [org.jboss.weld.deployer] (MSC service thread 1-2) WFLYWELD0013: Deployment iwinmichl.war contains Jakarta Contexts and Dependency Injection annotations but no bean archive was found (no beans.xml or class with bean defining annotations was present).
05:30:47,184 WARN  [org.jboss.as.server.deployment] (MSC service thread 1-7) WFLYSRV0274: Excluded dependency org.jboss.logmanager.log4j2 via jboss-deployment-structure.xml does not exist.
05:31:03,460 WARN  [org.jboss.jca.adapters.jdbc.WrappedConnection] (default task-1) IJ030040: Closing a statement you left open, please do your own housekeeping for: java:/jdbc/MIF02JA_JDS: java.lang.Throwable: STACKTRACE
05:31:03,462 WARN  [org.jboss.jca.adapters.jdbc.WrappedConnection] (default task-1) IJ030042: Closing a result set you left open, please do your own housekeeping for: com.mysql.cj.jdbc.result.ResultSetImpl@31930dd2: java.lang.Throwable: STACKTRACE
05:30:58,443 WARN  [org.springframework.web.servlet.mvc.support.DefaultHandlerExceptionResolver] (default task-1) Resolved [org.springframework.web.HttpRequestMethodNotSupportedException: Request method 'POST' is not supported]
05:33:53,659 WARN  [org.jboss.jca.adapters.jdbc.xa.XAManagedConnectionFactory] (default task-2) IJ030027: Destroying connection that is not valid, due to the following exception: com.mysql.cj.jdbc.ConnectionWrapper@108e4853: java.sql.SQLException: Ping failed: java.lang.reflect.InvocationTargetException
Caused by: com.mysql.cj.jdbc.exceptions.CommunicationsException: The client was disconnected by the server because of inactivity. See wait_timeout and interactive_timeout for configuring this behavior.
05:33:53,660 WARN  [org.jboss.jca.core.connectionmanager.pool.strategy.OnePool] (default task-2) IJ000621: Destroying connection that could not be validated: org.jboss.jca.core.connectionmanager.listener.TxConnectionListener@6de24e05[state=NORMAL managed connection=org.jboss.jca.adapters.jdbc.xa.XAManagedConnection@4f826b56 connection handles=0 lastReturned=1791696663462 lastValidated=1791696663317 lastCheckedOut=179
05:33:57,011 INFO  [org.jboss.as.server] (Thread-1) WFLYSRV0272: Suspending server
05:33:57,517 INFO  [org.jboss.as.server] (Thread-1) WFLYSRV0220: Server shutdown has been requested via an OS signal
05:33:57,567 WARN  [org.jboss.jca.core.connectionmanager.pool.strategy.OnePool] (ServerService Thread Pool -- 119) IJ000615: Destroying active connection in pool: MIF02JA_JDS (org.jboss.jca.adapters.jdbc.xa.XAManagedConnection@6ff3fec7)
05:33:57,580 WARN  [org.jboss.jca.adapters.jdbc.xa.XAManagedConnectionFactory] (ServerService Thread Pool -- 119) IJ030022: Lock owned during cleanup: default task-2: java.lang.Throwable: Lock owned during cleanup: default task-2
```

### IronJacamar ログの解析 (S0)

```text
======================================================================
 (A) ⑧ IJ030040 / ⑫ IJ030042 閉じ忘れの「作った場所」ランキング
======================================================================
      1  IJ030040 Statement   com.example.iwinmichl.test.DbServlet.leak(DbServlet.java:70)
      1  IJ030042 ResultSet   com.example.iwinmichl.test.DbServlet.leak(DbServlet.java:71)

======================================================================
 (B) ⑪ IJ000621 死んでいた接続の放置時間 (ログ時刻 - lastReturned)
======================================================================
  log=2026-10-11 05:33:53+0000 lastReturned=2026-10-11T05:31:03Z idle=    170s lastValidated=05:31:03Z (作成 or 最後の背景検証)
  件数=1  最小=170s  中央値=170s  最大=170s
  -> 最も短い放置 170s で既に死んでいた。idle-timeout-minutes は 1 以下を推奨
     (IdleRemover は idle-timeout の半分間隔で動くため、接続は最長で約 1.5 倍まで残る)
     あわせて MySQL の wait_timeout、経路のアイドル切断 (NAT Gateway/NLB 350 秒 等) を確認すること

======================================================================
 (C) ⑩ IJ030027 の根本原因 (直後の Caused by から分類)
======================================================================
  IJ030027 件数=1
      1  DB 側の wait_timeout / interactive_timeout による切断 (MySQL 8.0.24+ はエラー 4031 を返す)

======================================================================
 (D) ⑬ IJ000615 (使用中の接続をプール停止で破棄) の発生状況
======================================================================
  停止処理中=1  それ以外 (アンデプロイ / リロード / データソース停止 等)=0
  停止処理中 -> org.wildfly.sigterm.suspend.timeout / ECS stopTimeout / ALB 登録解除遅延 / LAUNCH_JBOSS_IN_BACKGROUND を確認
```

### 再現手順

```bash
# 1. 部品の取得 (WildFly 35.0.1 / Spring 6.2.19 / jstl-1.2 / jakarta.transaction-api / Connector/J 26.7.0 等を Maven Central から)
# 2. テスト用 PKI と WAR
bash verification/infra/make-test-pki.sh <pki>
bash verification/build-test-wars.sh <jars> <wars>
# 3. イメージ
DOCKER_BUILDKIT=1 docker build --build-context dist=<dl> --build-context impl=implementation/container \
  --secret id=cacerts,src=<pki>/cacerts-bundle.tar -t wl-before:1 verification/before
DOCKER_BUILDKIT=1 docker build --build-context dist=<dl> --secret id=cacerts,src=<pki>/cacerts-bundle.tar \
  --build-arg EAP_DIST=wildfly-dist-35.0.1.Final.tar.gz --build-arg TRUST_MODE=system --build-arg INBOUND_HTTPS_MODE=remove \
  -t wl-after-system-remove:1 implementation/container
# 4. MySQL 8.4 (wait_timeout=150) と HTTPS テストサーバを wl-net 上に起動
# 5. シナリオ
WARS=<wars> PKI=<pki> bash verification/run-all.sh
WARS=<wars> L4J_JARS=<log4j jars> JARS=<jars> bash verification/run-extra-experiments.sh
```

## 年表

| 年月 | 出来事 | 関係する警告 |
|---|---|---|
| 1999 | HTTP/1.1 (RFC 2616) に 405 Method Not Allowed と Allow ヘッダ | ⑨ |
| 2006 | JSTL 1.2 (Java EE 5)。javax.servlet.jsp.jstl パッケージ、検証用 TagLibraryValidator (PermittedTaglibsTLV 等) | ⑦ |
| 2007 | Spring 2.5: アノテーションによる @RequestMapping | ⑨ |
| 2009-12 | Java EE 6: Servlet 3.0 (非同期処理と AsyncListener)、CDI 1.0 | ④⑤ |
| 2009-12 | Spring 3.0: DefaultHandlerExceptionResolver | ⑨ |
| 2011-07 | JBoss AS 7.0: JBoss Modules、jboss-deployment-structure.xml、IronJacamar | ②③⑥⑦⑧⑩⑪⑫⑬ |
| 2013 | Java EE 7: CDI 1.1 で暗黙的 Bean アーカイブ (bean-discovery-mode) を導入 | ⑤ |
| 2013-07 | WFLY-924: オプションコンポーネントの失敗を WARN 1 行 + DEBUG に要約 (WFLYEE0007 の形) | ④ |
| 2015-07 | WildFly 9: メッセージ ID が JBAS → WFLY 系に。サスペンド / グレースフルシャットダウン導入 | 全般 / ⑬ |
| 2015-10 | WFCORE-1090: module.xml に jboss.api=private を付与 (private モジュールの明示) | ③ |
| 2016-06 | WFCORE-1576: 初回利用時に自己署名証明書を自動生成 (レガシーセキュリティ)。「SSL out of the box」 | ① |
| 2017 | WildFly 11 / EAP 7.1: Elytron 導入。Spring 5.0: リアクティブ対応 (spring-web にサーブレット用アダプタ) | ① / ④ |
| 2018-09 | Spring 5.1: 例外解決ログが "Resolved [...]" 形式に | ⑨ |
| 2018-12 | WFCORE-4233 / 4234: 存在しないサブシステム・依存の除外を WARN (WFLYSRV0273 / 0274) | ⑥ |
| 2020-11 | WFCORE-5095: Elytron でも自己署名証明書の自動生成。既定構成に applicationKS/KM/SSC | ① |
| 2020-12 | Jakarta EE 9: javax.* → jakarta.* の名前空間変更 | ⑦ |
| 2021 | MySQL 8.0.24: wait_timeout 切断時にエラー 4031 を通知。WildFly 25: レガシーセキュリティ削除 | ⑩ / ① |
| 2022 | Jakarta EE 10 (CDI 4.0、Jakarta Tags 3.0 で jakarta.tags.* URN)、Spring 6.0、RFC 9110 | ⑤⑦⑨ |
| 2023-08 | ECS on Fargate で systemControls (sysctl。TCP keepalive 等) が利用可能に | ⑩⑪ |
| 2024-02 | JBoss EAP 8.0 GA (Jakarta EE 10、Elytron に一本化) | 全般 |
| 2024-04 | MySQL 8.4 LTS | ⑩⑪ |
| 2024-09 | NLB の TCP アイドルタイムアウトが 60〜6000 秒で変更可能に (既定 350 秒のまま) | ⑩ |
| 2025-04 / 09 | JBoss EAP 8.1 ベータ (04-28) / GA (09-02) | 全般 |
| 2026-05 | Aurora MySQL 8.4 GA (最初のマイナー 8.4.7。ログの productVersion=8.4.7 と一致) | ⑩⑪ |
| 2026-09 | JBoss EAP 8.1.8 (Update 8) | 全般 |

## 用語集

| 用語 | 小学生向けのひとこと | 技術的な意味 |
|---|---|---|
| JBoss EAP | お店 (アプリ) が入る大きなビル | Red Hat の Jakarta EE アプリケーションサーバ。上流は WildFly |
| サブシステム | ビルの中の係 (部署) | elytron, undertow, datasources 等の機能単位。standalone.xml に設定 |
| jboss-cli | 設計図を正しい手順で書き換える道具 | 管理 CLI。.cli ファイルで手順を記録・再実行できる |
| embed-server | お客さんを入れずに設計図だけ直すモード | jboss-cli 内でサーバを管理専用に起動するモード (ビルド時の設定適用に使う) |
| JBoss Modules | 図書館の棚と貸出カード | モジュール単位でクラスの見える範囲を区切るクラスローダ |
| private モジュール | 職員専用の棚 | jboss.api=private。アプリが直接使うと将来壊れても保証されない |
| jboss-deployment-structure.xml | 引っ越しの荷物リスト | WAR の依存・除外・追加リソースルートを宣言する記述子 |
| Elytron | 警備室 | WildFly / EAP のセキュリティ基盤 (認証・TLS・鍵管理) |
| キーストア | 自分の身分証とハンコの金庫 | 自分の証明書と秘密鍵を入れるファイル (サーバ側 TLS で使う) |
| トラストストア | 信頼できる発行所の名簿 | 信頼する CA 証明書の一覧 (相手の証明書の検証に使う) |
| ルート CA (自己署名) | 名簿のいちばん上の発行所 | 自分で自分に署名した CA 証明書。名簿に入れないと信頼されない |
| cacerts | JDK に最初から付いている名簿 | JDK 既定のトラストストア。UBI の RPM 版 OpenJDK ではシステムトラストストアへのリンク |
| update-ca-trust | 名簿を作り直す係 | RHEL / UBI で CA を追加・反映するコマンド (/etc/pki/ca-trust/source/anchors に置いて実行) |
| Undertow | 受付係 | EAP の Web サーバ (HTTP/HTTPS リスナ、サーブレットコンテナ) |
| Weld / CDI | 名簿係 | CDI (Jakarta Contexts and Dependency Injection) の実装。Bean を管理する |
| Bean アーカイブ | 名簿に載る道具箱 | CDI が Bean を探す単位 (beans.xml や Bean 定義アノテーションで決まる) |
| AsyncListener | 非同期の見張り番 | サーブレットの非同期処理の完了・タイムアウト等を受け取るインタフェース |
| Jakarta EE / javax | 新しい教科書 / 昔の教科書 | Jakarta EE 9 で API のパッケージ名が javax.* から jakarta.* に変わった |
| JSTL / TLD | JSP 用の便利な道具とその説明書 | JSP 標準タグライブラリと、その定義ファイル (タグライブラリ記述子) |
| IronJacamar | タクシー会社 | EAP の JCA 実装。JDBC データソースの接続プールを提供 |
| XA データソース | 2 つ以上の店で同時に会計する仕組みに参加できるレジ | 分散トランザクション (2 相コミット) に参加できるデータソース |
| wait_timeout | 長く黙っているお客さんの電話を切る時間 | MySQL が無操作の接続を切るまでの秒数 (既定 28800) |
| TCP keepalive | 黙っていても時々「もしもし」と言う | 無通信の TCP 接続に定期的に確認パケットを送る仕組み |
| SIGTERM / SIGKILL | 「閉店してください」/ 強制停電 | 終了要求シグナル (後片付けできる) / 強制終了 (後片付けできない) |
| サスペンド | 新しいお客さんを断り、今のお客さんを待つ | EAP のグレースフルシャットダウンの前段 (要求の受付停止と完了待ち) |
| ALB / NLB | 案内係 | AWS のロードバランサ (L7 / L4) |
| Fargate | お店の建物を AWS が用意してくれる方式 | サーバ管理不要で ECS タスクを動かす実行環境 |

## 前提・版

### 前提にした環境と、検証に使った版

| 項目 | 本書の前提 (実環境) | 検証に使った版 |
|---|---|---|
| アプリケーションサーバ | JBoss EAP 8.1 (最新 8.1.8 / Update 8, 2026-09-22) | WildFly 35.0.1.Final (EAP 8.1 の上流。WildFly Core 27.0.1。EAP 8.1 は 27.1.x) |
| Elytron | EAP 8.1 同梱版 | wildfly-elytron 2.6.0.Final |
| Undertow | EAP 8.1 同梱版 | Undertow 2.3.18.Final |
| IronJacamar | EAP 8.1 同梱版 (3.0.x 系) | IronJacamar 3.0.10.Final |
| Weld | EAP 8.1 同梱版 (5.1.x 系) | Weld 5.1.4.Final |
| JBossWS-CXF / Apache CXF | EAP 8.1 同梱版 | JBossWS-CXF 7.3.1.Final / Apache CXF 4.0.6 |
| JBoss Modules / jboss-logmanager | EAP 8.1 同梱版 | JBoss Modules 2.1.6.Final / jboss-logmanager 2.1.19.Final |
| OS / JDK | UBI 9.8 + Red Hat build of OpenJDK 21 | RHEL 9.8 UBI、java-21-openjdk-headless 21.0.12.1 (2026-08-18)、ubi9/openjdk-21-runtime 1.24 |
| DB | Aurora MySQL 8.4 互換 (8.4.7) | MySQL 8.4.11 (検証のため wait_timeout=150 秒) |
| JDBC ドライバ | MySQL Connector/J (com.mysql.cj) | Connector/J 26.7.0 (2026-07。9.7.0 の次の版) |
| Spring Framework | 6.x (Spring MVC) | Spring Framework 6.2.19 / Micrometer 1.16.7 |
| 実行基盤 | Amazon ECS (Fargate) | Docker Desktop 29.8.1 (Windows 11) 上のコンテナで再現 |

### 推定した点 (実物で確認できなかったこと)

・jboss-deployment-structure.xml は jsf サブシステムを除外していると推定した (④ と ⑤ が同時に出るのはこの条件。除外しないと spring-web の PhaseListener 実装で JSF が有効化され、Weld デプロイになって ④⑤ が出ない。検証で確認)。

・⑤ の「CDI アノテーション」の出どころは jakarta.transaction-api の同梱を想定した。実際の WAR では scan-war.py で特定できる。

・データソースは validate-on-match=true + MySQLValidConnectionChecker、track-statements=true と推定した (⑪ がリクエスト処理スレッドで出ている、⑧⑫ が出ている、Ping failed の文言から)。

・⑬ はタスク停止時 (SIGTERM) に出たと推定した (スレッド ServerService Thread Pool はサービス停止の実行スレッド)。デプロイ・リロード時でも同じ警告になる。

### 確認してほしい点

・実際の jboss-deployment-structure.xml の全文 (exclude-subsystems の内容)

・Spring Framework・Apache CXF の利用箇所 (org.apache.cxf.impl を必要としていた理由)

・データソースの現在の設定値 (/subsystem=datasources/xa-data-source=MIF02JA_JDS:read-resource)

・Aurora のパラメータグループの wait_timeout / interactive_timeout、DB への経路 (NAT / NLB / Transit Gateway の有無)

・⑪ のログ行そのものの時刻 (「ログ時刻 - lastReturned」で放置時間を出すため)

・ECS タスク定義の stopTimeout、ALB ターゲットグループの deregistration delay、最長リクエストの処理時間

・LAUNCH_JBOSS_IN_BACKGROUND がイメージのどこかで設定されているか (⑬ の IJ000615 が出ている = SIGTERM は JVM に届いている可能性が高い)

## 出典

| 区分 | 資料 | URL |
|---|---|---|
| Red Hat | JBoss EAP 8.1 Release notes | <https://docs.redhat.com/en/documentation/red_hat_jboss_enterprise_application_platform/8.1/html-single/release_notes_for_red_hat_jboss_enterprise_application_platform_8.1/index> |
| Red Hat | JBoss EAP 8.1 Configuration Guide (サスペンドと OS シグナルによる正常シャットダウン) | <https://docs.redhat.com/en/documentation/red_hat_jboss_enterprise_application_platform/8.1/html-single/configuration_guide/index> |
| Red Hat | Configuring SSL/TLS in JBoss EAP 8.1 | <https://docs.redhat.com/en/documentation/red_hat_jboss_enterprise_application_platform/8.1/html-single/configuring_ssltls_in_jboss_eap/index> |
| Red Hat | Updating Red Hat JBoss EAP 8.1 | <https://docs.redhat.com/en/documentation/red_hat_jboss_enterprise_application_platform/8.1/html-single/updating_red_hat_jboss_enterprise_application_platform/index> |
| Red Hat | JBoss EAP 8 Included Modules (public / private の分類) | <https://access.redhat.com/node/7142689> |
| Red Hat | EAP 6/7/8 JDBC datasource not fault tolerant ... needs connection validation enabled | <https://access.redhat.com/solutions/156103> |
| Red Hat | JBoss EAP 8.1 GA (Red Hat Developers, 2025-09-02) | <https://developers.redhat.com/blog/2025/09/02/jboss-eap-81-modernizing-enterprise-java-applications> |
| Red Hat | RHSA-2026:70230 (JBoss EAP 8.1.8) | <https://access.redhat.com/errata/RHSA-2026:70230> |
| WildFly | WFCORE-5095 Elytron の自己署名証明書の自動生成 (設計提案) | <https://docs.wildfly.org/wildfly-proposals/elytron/WFCORE-5095-automatic-self-signed-certificate-generation.html> |
| ソース | KeyStoreService (WFLYELY00022/00023/00024) | <https://github.com/wildfly/wildfly-core/blob/27.0.1.Final/elytron/src/main/java/org/wildfly/extension/elytron/KeyStoreService.java> |
| ソース | elytron-app feature group (applicationKS/KM/SSC の既定構成) | <https://github.com/wildfly/wildfly-core/blob/27.0.1.Final/core-feature-pack/galleon-common/src/main/resources/feature_groups/elytron-app.xml> |
| ソース | ServerLogger (WFLYSRV0018/0058/0211/0220/0272/0273/0274) | <https://github.com/wildfly/wildfly-core/blob/27.0.1.Final/server/src/main/java/org/jboss/as/server/logging/ServerLogger.java> |
| ソース | DeploymentStructureDescriptorParser (②) | <https://github.com/wildfly/wildfly-core/blob/27.0.1.Final/server/src/main/java/org/jboss/as/server/deployment/module/descriptor/DeploymentStructureDescriptorParser.java> |
| ソース | ModuleLoadService (③ の判定: ユーザー指定の依存だけ) | <https://github.com/wildfly/wildfly-core/blob/27.0.1.Final/server/src/main/java/org/jboss/as/server/moduleservice/ModuleLoadService.java> |
| ソース | ModuleSpecification#getFictitiousExcludedDependencies (⑥) | <https://github.com/wildfly/wildfly-core/blob/27.0.1.Final/server/src/main/java/org/jboss/as/server/deployment/module/ModuleSpecification.java> |
| ソース | LoggingModuleDependency (logging の暗黙依存一覧) | <https://github.com/wildfly/wildfly-core/blob/27.0.1.Final/logging/src/main/java/org/jboss/as/logging/LoggingModuleDependency.java> |
| ソース | BootstrapImpl (org.wildfly.sigterm.suspend.timeout) | <https://github.com/wildfly/wildfly-core/blob/27.0.1.Final/server/src/main/java/org/jboss/as/server/BootstrapImpl.java> |
| ソース | standalone.sh (LAUNCH_JBOSS_IN_BACKGROUND とシグナル中継) | <https://github.com/wildfly/wildfly-core/blob/27.0.1.Final/core-feature-pack/common/src/main/resources/content/bin/standalone.sh> |
| ソース | WebComponentProcessor (AsyncListener / TLD validator のコンポーネント化) | <https://github.com/wildfly/wildfly/blob/35.0.1.Final/undertow/src/main/java/org/wildfly/extension/undertow/deployment/WebComponentProcessor.java> |
| ソース | EEModuleConfigurationProcessor (WFLYEE0007) | <https://github.com/wildfly/wildfly/blob/35.0.1.Final/ee/src/main/java/org/jboss/as/ee/component/deployers/EEModuleConfigurationProcessor.java> |
| ソース | DefaultInterceptorConfigurator (WFLYEE0048) | <https://github.com/wildfly/wildfly/blob/35.0.1.Final/ee/src/main/java/org/jboss/as/ee/component/DefaultInterceptorConfigurator.java> |
| ソース | CdiAnnotations / WeldDeploymentProcessor (WFLYWELD0013) | <https://github.com/wildfly/wildfly/blob/35.0.1.Final/weld/subsystem/src/main/java/org/jboss/as/weld/CdiAnnotations.java> |
| ソース | JSFVersionProcessor (JSF 有効化で Weld デプロイにする) | <https://github.com/wildfly/wildfly/blob/35.0.1.Final/jsf/subsystem/src/main/java/org/jboss/as/jsf/deployment/JSFVersionProcessor.java> |
| ソース | EventLoggerHttpHandler (console-access-log の predicate は応答完了後に評価) | <https://github.com/wildfly/wildfly/blob/35.0.1.Final/undertow/src/main/java/org/wildfly/extension/undertow/EventLoggerHttpHandler.java> |
| ソース | JDKModuleLogger (Failed to define class / org.jboss.modules.define) | <https://github.com/jboss-modules/jboss-modules/blob/2.1.6.Final/src/main/java/org/jboss/modules/log/JDKModuleLogger.java> |
| ソース | jboss-logmanager RegexFilter (match は整形後メッセージに部分一致) | <https://github.com/jboss-logging/jboss-logmanager/blob/2.1.19.Final/src/main/java/org/jboss/logmanager/filters/RegexFilter.java> |
| ソース | IronJacamar AdaptersLogger (IJ030027/030040/030042) | <https://github.com/ironjacamar/ironjacamar/blob/3.0.10.Final/adapters/src/main/java/org/jboss/jca/adapters/AdaptersLogger.java> |
| ソース | IronJacamar MySQLValidConnectionChecker | <https://github.com/ironjacamar/ironjacamar/blob/3.0.10.Final/adapters/src/main/java/org/jboss/jca/adapters/jdbc/extensions/mysql/MySQLValidConnectionChecker.java> |
| ソース | IronJacamar SemaphoreConcurrentLinkedDequeManagedConnectionPool (IJ000615/000621) | <https://github.com/ironjacamar/ironjacamar/blob/3.0.10.Final/core/impl/src/main/java/org/jboss/jca/core/connectionmanager/pool/mcp/SemaphoreConcurrentLinkedDequeManagedConnectionPool.java> |
| ソース | IronJacamar Defaults (track-statements=NOWARN 等) | <https://github.com/ironjacamar/ironjacamar/blob/3.0.10.Final/common/api/src/main/java/org/jboss/jca/common/api/metadata/Defaults.java> |
| ソース | Spring DefaultHandlerExceptionResolver (v6.2) | <https://github.com/spring-projects/spring-framework/blob/v6.2.11/spring-webmvc/src/main/java/org/springframework/web/servlet/mvc/support/DefaultHandlerExceptionResolver.java> |
| ソース | Spring ServletServerHttpResponse (ResponseAsyncListener は非 static 内部クラス) | <https://github.com/spring-projects/spring-framework/blob/v6.2.11/spring-web/src/main/java/org/springframework/http/server/reactive/ServletServerHttpResponse.java> |
| ソース | Apache CXF Message (jakarta.xml.ws.client.connectionTimeout / receiveTimeout) | <https://github.com/apache/cxf/blob/cxf-4.0.6/core/src/main/java/org/apache/cxf/message/Message.java> |
| ソース | Apache CXF jsse SSLUtils (javax.net.ssl.trustStore を自分で読む) | <https://github.com/apache/cxf/blob/cxf-4.0.6/core/src/main/java/org/apache/cxf/configuration/jsse/SSLUtils.java> |
| 仕様 | Jakarta Standard Tag Library 3.0 | <https://jakarta.ee/specifications/tags/3.0/> |
| 仕様 | RFC 9110 HTTP Semantics (405 / Allow) | <https://www.rfc-editor.org/rfc/rfc9110> |
| MySQL | WL#12999 wait_timeout 切断時のエラー通知 (4031) | <https://dev.mysql.com/worklog/task/?id=12999> |
| AWS | Aurora MySQL version 8.4 | <https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraMySQL.MySQL84.html> |
| AWS | NAT ゲートウェイの接続トラブルシューティング (350 秒のアイドルタイムアウト) | <https://repost.aws/knowledge-center/vpc-troubleshoot-nat-gateway-connection> |
| AWS | NLB の TCP アイドルタイムアウトの変更 | <https://docs.aws.amazon.com/elasticloadbalancing/latest/network/update-idle-timeout.html> |
| AWS | Fargate の追加 Linux 制御 (systemControls, 2023-08-09) | <https://aws.amazon.com/blogs/containers/announcing-additional-linux-controls-for-amazon-ecs-tasks-on-aws-fargate/> |
| AWS | ECS TaskDefinition SystemControl (Fargate はプラットフォーム 1.4.0 以降) | <https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-properties-ecs-taskdefinition-systemcontrol.html> |
| AWS | ContainerDefinition stopTimeout (既定 30 秒、Fargate 最大 120 秒) | <https://docs.aws.amazon.com/sdk-for-kotlin/api/latest/ecs/aws.sdk.kotlin.services.ecs.model/-container-definition/stop-timeout.html> |
| AWS | ALB はターゲットの証明書を検証しない (re:Post) | <https://www.repost.aws/questions/QU97HoG_YMQxO1LXTj76ui-w/traffic-between-alb-and-backend-ec2-instance-needs-to-be-encrypted> |
