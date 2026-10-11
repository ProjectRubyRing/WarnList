# -*- coding: utf-8 -*-
"""警告 ⑤〜⑨ の原稿"""
from doclib import B, C, DIA, KID, NOTE, P, S, T

# =====================================================================
# ⑤ WFLYWELD0013
# =====================================================================
W05 = {
    "key": "W05", "no": "⑤", "sheet": "⑤WFLYWELD0013", "id": "WFLYWELD0013", "severity": "B",
    "title": "⑤ WFLYWELD0013: CDI アノテーションはあるが Bean アーカイブが見つからない",
    "user_log": "WFLYWELD0013: デプロイメント iwinmichl.warにはJakarta Contexts and Dependency Injectionアノテーションが含まれますが、Beanアーカイブは見つかりませんでした(beans.xmlおよびBeanを定義するアノテーションを持つクラスがありません）",
    "verify_labels": ["WFLYWELD0013 CDI annotations, no bean archive"],
    "sections": [
        S("ひとことで (小学生向け)",
          KID("ビルには「名簿係 (Weld)」がいて、「CDI のシール (アノテーション)」が貼ってある道具を見つけると、"
              "その道具を管理する名簿 (Bean アーカイブ) を作ろうとします。\n"
              "iwinmichl の荷物からは CDI のシールが見つかりました。でも、名簿を作るきっかけ "
              "(beans.xml という申込書や、道具そのものに貼られた「Bean です」シール) はありませんでした。\n"
              "名簿係は「シールはあるのに名簿が無いけど、本当にいいの？」と日記に書きました。\n"
              "見つかったシールは、お店の道具ではなく、荷物に紛れ込んでいたサーバ用の部品 (jakarta.transaction-api) に付いていたものでした。"),
          T(["たとえ", "本当の仕組み"], [
              ["名簿係", "Weld (CDI = Jakarta Contexts and Dependency Injection の実装)"],
              ["CDI のシール", "WildFly が「CDI アノテーション」と判定する 20 種 (@ApplicationScoped, @Dependent, @NormalScope, @Produces, @Observes, jakarta.inject.Singleton など)"],
              ["名簿 (Bean アーカイブ)", "CDI が Bean を探す単位。beans.xml があるか、クラスに Bean 定義アノテーションが付いているとそうなる"],
              ["紛れ込んだサーバ用の部品", "WEB-INF/lib に同梱された EE の API jar (jakarta.transaction-api の TransactionScoped に @NormalScope が付いている)"],
          ], widths=[1, 3])),
        S("メッセージの正体",
          T(["項目", "内容"], [
              ["英語原文", "WFLYWELD0013: Deployment %s contains Jakarta Contexts and Dependency Injection annotations but no bean archive was found "
                          "(no beans.xml or class with bean defining annotations was present)."],
              ["ID / レベル", "WFLYWELD0013 / WARN"],
              ["ロガー", "org.jboss.weld.deployer"],
              ["出す場所", "WeldDeploymentProcessor (トップレベルのデプロイで、Weld デプロイでなく、CDI アノテーションの印が付いているとき)"],
              ["印を付ける場所", "CdiAnnotationProcessor (アノテーション索引に CdiAnnotations の 20 種のどれかがあれば印を付ける)"],
          ], widths=[1, 4])),
        S("動作原理",
          B("CdiAnnotationProcessor は、デプロイ全体のアノテーション索引 (WEB-INF/classes と WEB-INF/lib の jar を含む) に、"
            "次の 20 種のどれかが使われていれば「CDI アノテーションあり」の印を付ける: Decorator, Delegate, ApplicationScoped, "
            "ConversationScoped, RequestScoped, SessionScoped, NormalScope, Dependent, jakarta.inject.Singleton, Observes, Alternative, Any, "
            "Default, Disposes, Model, New, Produces, Specializes, Stereotype, Typed。"
            "@Inject と @Named は含まれない (Spring で @Inject を使っていても、それだけではこの警告にならない)。",
            "Weld デプロイになる条件: beans.xml がある (BeansXmlProcessor)、クラスに Bean 定義アノテーションがある (WeldImplicitDeploymentProcessor)、"
            "EJB などの暗黙 Bean が必要、JSF が有効 (Faces 4 は CDI 必須のため JSFVersionProcessor が印を付ける)、JAX-WS エンドポイントがある、など。",
            "Weld デプロイでなく、CDI アノテーションの印があり、トップレベルのデプロイなら WFLYWELD0013 を出す (CDI は動かない)。",
            "jakarta.transaction-api.jar の jakarta.transaction.TransactionScoped は @NormalScope で注釈されている。"
            "これは「スコープの定義」であってアプリの Bean ではないので、Bean アーカイブにはならないが、索引には @NormalScope の使用として載る。",
            "jsf を除外していなければ、spring-web の PhaseListener 実装で JSF が有効になり Weld デプロイになるため、この警告は出ない (検証で確認)。")),
        S("動作イメージ",
          DIA("""[デプロイ]
 アノテーション索引 (WEB-INF/classes + WEB-INF/lib/*.jar)
  └ jakarta.transaction-api-2.0.1.jar: TransactionScoped に @NormalScope  → 「CDI アノテーションあり」の印
 Weld デプロイか？
  ├ beans.xml なし / Bean 定義アノテーション付きのクラスなし
  ├ jsf を除外 (spring-web の PhaseListener による JSF 有効化が起きない)
  └ → Weld デプロイではない
 → 印あり かつ Weld デプロイでない → WFLYWELD0013 (WARN) ★今回""")),
        S("歴史・背景・必要になった経緯",
          B("2009 CDI 1.0 (Java EE 6): beans.xml を置いたアーカイブだけが Bean アーカイブ。",
            "2013 CDI 1.1 (Java EE 7): beans.xml が無くても、Bean 定義アノテーション付きのクラスがあれば「暗黙的 Bean アーカイブ」になる "
            "(bean-discovery-mode = all / annotated / none)。",
            "2022 CDI 4.0 (Jakarta EE 10): 中身の無い beans.xml の意味が all から annotated に変わった "
            "(WildFly は互換用に weld サブシステムの legacy-empty-beans-xml-treatment 属性を用意)。",
            "WildFly はこの警告で「CDI のつもりでアノテーションを書いたのに、Bean アーカイブにならず注入が黙って効いていない」事故を知らせる。")),
        S("この環境での原因と切り分け",
          P("WAR に同梱された EE の API jar (検証では jakarta.transaction-api) が CDI アノテーションの出どころで、"
            "jsf を除外しているため Weld デプロイにもならない、という組み合わせです。実際の WAR でどの jar かは scan-war.py で特定できます。"),
          C("""python scan-war.py iwinmichl.war
## ⑤ WildFly が「CDI アノテーション」と判定するもの (WFLYWELD0013 の材料)
  beans.xml: なし
  NG jakarta.transaction-api-2.0.1.jar: 1 件  例: ['jakarta.transaction.TransactionScoped @NormalScope']
  WEB-INF/lib の Jakarta/Java EE API jar (サーバが提供するので provided にする): ['jakarta.transaction-api-2.0.1.jar']""",
            "text", "検証用 WAR での実行結果")),
        S("影響度と放置した場合のリスク",
          P("危険度 B。CDI を使っていない Spring アプリなら、警告そのものは無害です。ただし原因の「サーバが提供する API の jar を WAR に同梱」は、"
            "サーバ側の同じクラスとの食い違い (LinkageError / ClassCastException) の火種になります。"
            "また、本当に CDI を使うつもりのコードがある場合は、注入が効いていないことを示します。")),
        S("対処方針の比較",
          T(["方式", "内容", "評価"], [
              ["EE API jar を同梱しない ★推奨", "pom.xml で jakarta.* の API を provided にする (サーバが提供する)", "◎ 根本対処"],
              ["CDI を使わないなら weld を除外 ★推奨", "jboss-deployment-structure.xml の exclude-subsystems に weld (jsf と一緒に)", "◎ 警告と Weld の起動コストが無くなる"],
              ["CDI を使うなら beans.xml", "WEB-INF/beans.xml (bean-discovery-mode=\"annotated\") を置く", "○ CDI を使う場合のみ"],
              ["weld サブシステムの属性で消す", "require-bean-descriptor 等はこの警告を消すためのものではない", "× 効かない"],
          ], widths=[2, 5, 2]),
          NOTE("weld を除外すると、そのデプロイでは CDI に依存する機能 (CDI 連携の Bean Validation、JAX-RS の CDI 連携、Jakarta Security 等) が使えません。"
               "Spring MVC + JSP のアプリでは通常問題ありません。")),
        S("実装 (WAR 側)",
          C("""<!-- jboss-deployment-structure.xml -->
<exclude-subsystems>
    <subsystem name="jsf"/>
    <subsystem name="weld"/>
</exclude-subsystems>""", "xml"),
          C("""<!-- pom.xml: サーバ提供の API は provided -->
<dependency>
  <groupId>jakarta.transaction</groupId>
  <artifactId>jakarta.transaction-api</artifactId>
  <scope>provided</scope>
</dependency>""", "xml")),
        S("確認方法",
          C("""python scan-war.py iwinmichl.war    # ⑤ が「使用なし」になること
grep -c WFLYWELD0013 server.log       # → 0""", "bash")),
    ],
    "refs": ["src-cdi", "src-jsf", "eap-mods"],
}

# =====================================================================
# ⑥ WFLYSRV0274
# =====================================================================
W06 = {
    "key": "W06", "no": "⑥", "sheet": "⑥WFLYSRV0274", "id": "WFLYSRV0274", "severity": "B",
    "title": "⑥ WFLYSRV0274: jboss-deployment-structure.xml で除外した依存 org.jboss.logmanager.log4j2 が存在しない",
    "user_log": "WFLYSRV0274: jboss-deployment-structure.xmlを介して除外された依存関係.org.jboss.logmanager.log4j2は存在しません。",
    "verify_labels": ["WFLYSRV0274 excluded dependency does not exist", "WFLYSRV0273 excluded subsystem does not exist"],
    "sections": [
        S("ひとことで (小学生向け)",
          KID("引っ越しの荷物リストに「○○さんから届く荷物は受け取りません (除外)」と書きました。\n"
              "ところが、○○さんからは最初から何も届く予定がありませんでした。係は「受け取り拒否リストの○○さんは、届け物の予定に見当たりません」"
              "とメモしました。\n"
              "本当に断りたかったのは、○○さんに荷物を頼んでいた△△さん (org.apache.logging.log4j.api) の方でした。だから、拒否したつもりの荷物は"
              "結局届いていて、お店のログは EAP の日記係に書かれています。"),
          T(["たとえ", "本当の仕組み"], [
              ["受け取り拒否リスト", "jboss-deployment-structure.xml の <exclusions>"],
              ["○○さん", "org.jboss.logmanager.log4j2 (Log4j 2 API を JBoss LogManager につなぐ部品。private)"],
              ["△△さん", "org.apache.logging.log4j.api (logging サブシステムがデプロイに自動で付ける依存。public)"],
              ["届け物の予定", "そのデプロイに実際に追加された依存の一覧"],
          ], widths=[1, 3])),
        S("メッセージの正体",
          T(["項目", "内容"], [
              ["英語原文", "WFLYSRV0274: Excluded dependency %s via jboss-deployment-structure.xml does not exist."],
              ["ID / レベル", "WFLYSRV0274 / WARN (兄弟: WFLYSRV0273 = 存在しないサブシステムの除外)"],
              ["ロガー", "org.jboss.as.server.deployment"],
              ["出す場所", "DeploymentUnitPhaseService (CLEANUP フェーズ) が ModuleSpecification#getFictitiousExcludedDependencies を見て出す"],
              ["「does not exist」の本当の意味", "「サーバにモジュールが無い」ではなく「このデプロイの依存に一度も追加されなかった (除外が空振りした)」"],
          ], widths=[1, 4])),
        S("動作原理",
          B("<exclusions> に書いたモジュールは ModuleSpecification の除外リストに入り、その後サブシステムが依存を追加するときに"
            "一致したものだけが取り除かれる (取り除いた記録も残る)。",
            "CLEANUP フェーズで「除外リストにあるのに、一度も取り除かれなかった (= 依存に入っていなかった)」ものを WFLYSRV0274 として報告する "
            "(WFCORE-4234)。",
            "logging サブシステムが暗黙に付ける依存は次の 7 つ (LoggingModuleDependency): org.apache.commons.logging、"
            "org.apache.logging.log4j.api (services import)、org.jboss.logging、org.jboss.logging.jul-to-slf4j-stub、org.jboss.logmanager、"
            "org.slf4j、org.slf4j.impl。org.jboss.logmanager.log4j2 はここに無い。",
            "org.jboss.logmanager.log4j2 は EAP 8.1 にも存在する (private) が、org.apache.logging.log4j.api の module.xml の中から使われる"
            "「内部の依存」なので、デプロイの依存には直接入らない。だから除外しても空振りになる。",
            "結果: WAR に log4j-api / log4j-core を同梱していても、Log4j 2 API のクラスはサーバのモジュールから読まれ "
            "(暗黙の依存が WAR より先)、アプリのログは EAP の logging サブシステムに流れる。除外の意図は実現していない。")),
        S("動作イメージ",
          DIA("""[依存の組み立て]
 logging サブシステム: org.apache.logging.log4j.api を追加 ──(この module.xml の中で)── org.jboss.logmanager.log4j2 を使う
 jboss-deployment-structure.xml: <exclusions> org.jboss.logmanager.log4j2
   → デプロイの依存に org.jboss.logmanager.log4j2 は来ない → 何も取り除かれない
[CLEANUP]
   → 「除外したのに一度も取り除いていない」→ WFLYSRV0274 (WARN) ★今回
[実行時 (検証 E9)]
   除外なし / org.jboss.logmanager.log4j2 を除外 : LoggerContext = org.jboss.logmanager.log4j.JBossLoggerContext (EAP のログ)
   org.apache.logging.log4j.api を除外         : LoggerContext = org.apache.logging.log4j.core.LoggerContext (アプリの log4j2.xml)""")),
        S("歴史・背景・必要になった経緯",
          B("JBoss AS 7 (2011) から、デプロイごとに依存を除外できる <exclusions> がある (アプリ同梱のライブラリをサーバ版より優先させたいときに使う)。",
            "WildFly の logging サブシステムは Log4j 2 API の呼び出しを JBoss LogManager に流すブリッジ (log4j2-jboss-logmanager) を持ち、"
            "それを内部モジュール org.jboss.logmanager.log4j2 として同梱している。",
            "2018-12 WFCORE-4233 / 4234: 名前の打ち間違いや取り違えで除外が空振りしても気づけないため、存在しないサブシステム・依存の除外を "
            "WARN で知らせるようになった (WFLYSRV0273 / 0274)。")),
        S("この環境での原因と切り分け",
          P("「アプリ同梱の Log4j 2 を使いたい」意図で除外を書いたものの、除外先を取り違えています。まず、どちらのログ設計にしたいかを決めます。"),
          T(["実験 (検証 E9)", "除外指定", "結果"], [
              ["none", "なし", "LoggerContext=JBossLoggerContext。log4j-api はサーバのモジュール (2.23.1) から読まれ、ログは EAP の形式で出力"],
              ["bad (現行)", "org.jboss.logmanager.log4j2", "WFLYSRV0274 が出て、結果は none と同じ (空振り)"],
              ["good", "org.apache.logging.log4j.api", "LoggerContext=org.apache.logging.log4j.core.LoggerContext。WAR の log4j-api 2.26.1 と log4j2.xml が使われる"],
          ], widths=[1, 2, 6])),
        S("影響度と放置した場合のリスク",
          P("危険度 B。ログの出力先・書式・レベル設定が、開発者の意図 (アプリの log4j2.xml) と実際 (EAP の logging サブシステム) で食い違っています。"
            "障害調査のときに「出るはずのログが出ていない」「設定を変えても効かない」原因になります。")),
        S("対処方針の比較",
          T(["方式", "内容", "評価"], [
              ["(A) EAP のログに乗せる ★ECS では推奨", "除外を削除。log4j-core を同梱しない (log4j-api は provided)。レベルや形式は jboss-cli で管理。"
                                              "コンソール → awslogs → CloudWatch Logs に一元化", "◎ 設定が 1 か所、コンテナ向き"],
              ["(B) アプリの Log4j 2 を使う", "除外対象を org.apache.logging.log4j.api に直す (検証 E9 good)。log4j-api と log4j-core を同梱", "○ ファイル出力 (EFS のローテーション等) をアプリで制御したい場合"],
              ["(B') サーバ全体で暗黙依存を止める", "jboss-cli で /subsystem=logging:write-attribute(name=add-logging-api-dependencies, value=false)", "△ サーバ全体に効く"],
          ], widths=[2, 5, 2])),
        S("実装",
          C("""<!-- (A) jboss-deployment-structure.xml: 誤った除外を削除するだけ -->
<!-- <exclusions><module name="org.jboss.logmanager.log4j2"/></exclusions>  ← 削除 -->

<!-- (B) アプリ同梱の Log4j 2 を使う場合 -->
<exclusions>
    <module name="org.apache.logging.log4j.api"/>
</exclusions>""", "xml"),
          C("""# (B') サーバ全体で logging API の暗黙依存を止める (20-logging.cli の調査用コメント参照)
/subsystem=logging:write-attribute(name=add-logging-api-dependencies, value=false)""", "text")),
        S("確認方法",
          C("""grep -c WFLYSRV0274 server.log   # → 0
# (B) の場合: アプリで LogManager.getContext(false).getClass() を出力し
#   org.apache.logging.log4j.core.LoggerContext になっていること""", "bash")),
    ],
    "refs": ["src-serverlogger", "src-modspec", "src-logdeps", "eap-mods"],
}

# =====================================================================
# ⑦ Failed to define class javax.servlet.jsp.jstl.tlv.PermittedTaglibsTLV
# =====================================================================
W07 = {
    "key": "W07", "no": "⑦", "sheet": "⑦javax定義失敗", "id": "Failed to define class", "severity": "B",
    "title": "⑦ Failed to define class javax.servlet.jsp.jstl.tlv.PermittedTaglibsTLV (NoClassDefFoundError: Failed to link)",
    "user_log": "Failed to define class javax.servlet.jsp.jstl.tlv.Permitted.TaglibsTLV in Module \"deployment.iwinmichl.war\" from Service Module Loader: java.lang.NoClassDefFound Error: Failed to link javax/servlet/jsp/jstl/tlv/PermittedTaglibsTLVModule \"deployment.iwinmichl.war\" from Service Module Loader javax/servlet/jsp/tagext/TaglibraryValidator",
    "verify_labels": ["Failed to define class javax.*", "  of which javax.servlet.jsp.jstl.* (=⑦)"],
    "sections": [
        S("ひとことで (小学生向け)",
          KID("昔の教科書 (Java EE の javax) と、新しい教科書 (Jakarta EE の jakarta) があります。中身はほぼ同じですが、表紙の名前が違います。\n"
              "EAP 8.1 という学校には、新しい教科書しか置いてありません。\n"
              "お店の荷物に昔の教科書 (jstl-1.2.jar) が入っていて、その付録 (TLD) に「このページを読むには javax の本が必要」と書いてありました。\n"
              "先生が javax の本を探しましたが見つからず、「この付録は使えません」と日記に書きました。\n"
              "授業 (JSP の表示) は、学校が用意した新しい教科書で問題なく進みます。"),
          T(["たとえ", "本当の仕組み"], [
              ["昔の教科書", "Java EE 時代の javax.* API (javax.servlet.jsp.tagext.TagLibraryValidator など)"],
              ["新しい教科書", "Jakarta EE 9 以降の jakarta.* API (EAP 8 は jakarta.* のみ)"],
              ["荷物に入っていた昔の教科書", "WEB-INF/lib/jstl-1.2.jar (javax 版 JSTL)"],
              ["付録", "jar 内の TLD (permittedTaglibs.tld / scriptfree.tld) の <validator-class>"],
              ["学校が用意した教科書", "EAP が提供する Jakarta Standard Tag Library 3.0"],
          ], widths=[1, 3])),
        S("メッセージの正体",
          T(["項目", "内容"], [
              ["英語原文 (正しい形)", "Failed to define class javax.servlet.jsp.jstl.tlv.PermittedTaglibsTLV in Module \"deployment.iwinmichl.war\" from Service Module Loader: "
                                  "java.lang.NoClassDefFoundError: Failed to link javax/servlet/jsp/jstl/tlv/PermittedTaglibsTLV "
                                  "(Module \"deployment.iwinmichl.war\" from Service Module Loader): javax/servlet/jsp/tagext/TagLibraryValidator"],
              ["ID / レベル", "ID なし (JBoss Modules のメッセージ) / WARN"],
              ["ロガー", "org.jboss.modules.define (JDKModuleLogger: カテゴリ org.jboss.modules + \".define\")"],
              ["出す場所", "ModuleClassLoader#defineClass が Error を受けたとき (classDefineFailed)"],
              ["一緒に出るもの", "WFLYEE0007: Not installing optional component javax.servlet.jsp.jstl.tlv.PermittedTaglibsTLV / ScriptFreeTLV (④ と同じ仕組み)"],
          ], widths=[1, 4])),
        S("動作原理",
          B("Undertow (Jastow) はデプロイ時に WEB-INF/lib の jar 内の TLD を読み、WebComponentProcessor は TLD の <validator-class>・<tag-class>・"
            "<listener-class> を「注入対象の Web コンポーネント」として登録する。",
            "jstl-1.2.jar の permittedTaglibs.tld / scriptfree.tld は、バリデータとして javax.servlet.jsp.jstl.tlv.PermittedTaglibsTLV / ScriptFreeTLV を指定している。",
            "EE サブシステムがそのクラスを読み込むと、JBoss Modules がクラスを定義する際に親クラス javax.servlet.jsp.tagext.TagLibraryValidator を"
            "解決しようとする。EAP 8 には jakarta.servlet.jsp.tagext.TagLibraryValidator しか無いので NoClassDefFoundError (Failed to link) になり、"
            "org.jboss.modules.define が WARN を出す。続いて EE がオプションのコンポーネントとして WFLYEE0007 を出し、登録をやめる。",
            "JSP 自体は動く (検証: 旧 URI の c:out と fmt:formatNumber、新 URN の jakarta.tags.core がすべて HTTP 200)。"
            "EAP が提供する Jakarta JSTL 3.0 は旧 URI (http://java.sun.com/jsp/jstl/...) も受け付ける。")),
        S("動作イメージ",
          DIA("""[デプロイ]
 TLD を走査: WEB-INF/lib/jstl-1.2.jar!/META-INF/permittedTaglibs.tld
   <validator><validator-class>javax.servlet.jsp.jstl.tlv.PermittedTaglibsTLV</validator-class></validator>
 → Web コンポーネントとして登録 → EE がクラスを読み込む
 → JBoss Modules: PermittedTaglibsTLV の親 javax.servlet.jsp.tagext.TagLibraryValidator が無い
      → NoClassDefFoundError: Failed to link → "Failed to define class ..." (WARN, org.jboss.modules.define) ★今回
 → EE: WFLYEE0007 (オプションなので登録をやめて続行)
[JSP の実行]
 taglib uri="http://java.sun.com/jsp/jstl/core" → EAP の Jakarta JSTL 3.0 が処理 → 正常""")),
        S("歴史・背景・必要になった経緯",
          B("2006 JSTL 1.2 (Java EE 5): javax.servlet.jsp.jstl パッケージ。permittedTaglibs / scriptfree は「使ってよいタグを制限する」ための検証用 TLD。",
            "2017〜2019 Java EE が Eclipse Foundation に移管され、商標の都合で javax 名前空間を使い続けられなくなった。",
            "2020-12 Jakarta EE 9: すべての API が javax.* から jakarta.* に一斉に改名された (中身はほぼ同じ)。",
            "2022 Jakarta EE 10: Jakarta Standard Tag Library 3.0 で URI が jakarta.tags.core などの URN に変わった (旧 URI も引き続き使える)。",
            "2024 EAP 8.0 / 2025 EAP 8.1: Jakarta EE 10 準拠。javax 版の API は含まれないので、javax のまま残った jar はこのように読めない。")),
        S("この環境での原因と切り分け",
          P("WAR に javax 版 JSTL (jstl-1.2.jar、または taglibs-standard-impl/spec 等) が残っています。Jakarta 移行のときに依存の整理が漏れたものです。"),
          C("""python scan-war.py iwinmichl.war
## ⑦ javax.* (Java EE 時代) の痕跡
  NG TLD jstl-1.2.jar:META-INF/permittedTaglibs.tld → javax.servlet.jsp.jstl.tlv.PermittedTaglibsTLV
  NG TLD jstl-1.2.jar:META-INF/scriptfree.tld → javax.servlet.jsp.jstl.tlv.ScriptFreeTLV
  NG jstl-1.2.jar: javax.servlet を参照・定義するクラス 160 個 (EAP 8 は jakarta.* のみ。Jakarta 版へ置換/除去)""",
            "text", "検証用 WAR での実行結果")),
        S("影響度と放置した場合のリスク",
          P("危険度 B。今は JSP が動いていても、javax.* を直接使う Java コードや、旧 JSTL のクラスに頼るタグがあると、実行時に NoClassDefFoundError になります。"
            "Jakarta 移行が終わっていない印なので、他にも javax の jar が残っていないか確認します。")),
        S("対処方針の比較",
          T(["方式", "内容", "評価"], [
              ["javax 版 JSTL を削除 ★推奨", "jstl-1.2.jar / taglibs-standard-* を依存から外し、EAP 提供の Jakarta JSTL を使う (API は provided)", "◎"],
              ["javax の混入をビルドで止める", "maven-enforcer-plugin の bannedDependencies で javax.servlet:* 等を禁止", "◎ 再発防止"],
              ["移行ツールで一括点検", "Migration Toolkit for Applications (MTA) / Eclipse Transformer で javax の残りを洗い出す", "○"],
              ["taglib の URI を新 URN に", "jakarta.tags.core 等へ。必須ではない (旧 URI も動く)", "△ 任意"],
          ], widths=[2, 5, 2])),
        S("実装 (WAR 側)",
          C("""<!-- pom.xml: javax 版を外し、Jakarta 版の API を provided で参照 -->
<dependency>
  <groupId>jakarta.servlet.jsp.jstl</groupId>
  <artifactId>jakarta.servlet.jsp.jstl-api</artifactId>
  <scope>provided</scope>
</dependency>
<!-- maven-enforcer-plugin: javax.servlet:*, javax.servlet.jsp.jstl:*, org.apache.taglibs:taglibs-standard-* を禁止
     (全文は implementation/app/pom-snippets.xml) -->""", "xml")),
        S("確認方法",
          C("""grep -c 'Failed to define class javax' server.log     # → 0
curl http://localhost:8080/iwinmichl/<JSTL を使う画面>      # 表示が変わらないこと""", "bash")),
    ],
    "refs": ["src-jbm", "src-webcomp", "spec-tags"],
}

# =====================================================================
# ⑧ IJ030040
# =====================================================================
W08 = {
    "key": "W08", "no": "⑧", "sheet": "⑧IJ030040", "id": "IJ030040", "severity": "B",
    "title": "⑧ IJ030040: 開いたままの Statement を閉じた (自分で後片付けしてください)",
    "user_log": "IJ030040: Closing a statement you left open please do your own housekeeping for: java/jdbc/MIF02JA_JDS - java.lang.Throwable: STACKTRACE",
    "verify_labels": ["IJ030040 statement left open"],
    "sections": [
        S("ひとことで (小学生向け)",
          KID("図書館で本 (DB 接続) を借りて、その中のメモ用紙 (Statement) を使ったら、本を返す前にメモ用紙を片付けるルールです。\n"
              "あるお客さんが、メモ用紙を出しっぱなしで本を返しました。司書 (IronJacamar) が代わりに片付けて、"
              "「自分で片付けてね」と日記に書きました。誰が出しっぱなしにしたか (STACKTRACE) も一緒に書いてくれます。"),
          T(["たとえ", "本当の仕組み"], [
              ["本を借りる / 返す", "DataSource#getConnection / Connection#close (プールに戻る)"],
              ["メモ用紙", "Statement / PreparedStatement"],
              ["司書が代わりに片付ける", "track-statements=true のとき、接続を返す時点で開いたままの Statement を閉じる"],
              ["誰が出しっぱなしにしたか", "Statement を作った時点のスタックトレース (java.lang.Throwable: STACKTRACE)"],
          ], widths=[1, 3])),
        S("メッセージの正体",
          T(["項目", "内容"], [
              ["英語原文", "IJ030040: Closing a statement you left open, please do your own housekeeping for: %s"],
              ["ID / レベル", "IJ030040 / WARN (%s はデータソースの JNDI 名 java:/jdbc/MIF02JA_JDS)"],
              ["ロガー", "org.jboss.jca.adapters.jdbc.WrappedConnection"],
              ["出す場所", "IronJacamar の WrappedConnection (接続ハンドルを閉じるときの closeStatements)"],
              ["付いてくるスタック", "Statement を作った呼び出し元 (検証: com.example.iwinmichl.test.DbServlet.leak(DbServlet.java:70))"],
          ], widths=[1, 4])),
        S("動作原理",
          B("IronJacamar の JDBC アダプタは、アプリに渡す Connection / Statement / ResultSet を包んで (WrappedConnection など) 管理している。",
            "データソースの track-statements 属性: FALSE (追跡しない) / TRUE (追跡し、閉じ忘れを警告) / NOWARN (追跡し、黙って閉じる)。"
            "既定は NOWARN (IronJacamar の Defaults)。⑧⑫ が出ている = この環境では TRUE になっている。",
            "TRUE のとき、Statement を作るたびに作成箇所のスタック (Throwable) を記録する。アプリが Connection#close したとき、"
            "まだ開いている Statement があれば IJ030040 とスタックを出して閉じる。",
            "接続はプールに戻るので「接続のリーク」ではないが、閉じるまでの間 DB 側のカーソルやサーバ側プリペアドステートメント、メモリを保持し続ける。")),
        S("動作イメージ",
          DIA("""[リクエスト処理 (default task-N)]
 Connection c = ds.getConnection()          … プールから借りる
 PreparedStatement ps = c.prepareStatement() … 作成箇所を記録 (track-statements=TRUE)
 ResultSet rs = ps.executeQuery()            … 同上
 c.close()                                   … ps と rs を閉じていない
   → IronJacamar: 開いたままの ps を閉じる → IJ030040 + STACKTRACE (WARN) ★⑧
                  ps を閉じる際に rs も閉じる  → IJ030042 + STACKTRACE (WARN) ★⑫
   → 接続はプールへ戻る""")),
        S("歴史・背景・必要になった経緯",
          B("JDBC 2.0 Optional Package (1999) で接続プールが標準化され、アプリは接続を「借りて返す」ようになった。",
            "JBoss AS 4/5 の JBossJCA の頃から、借りたまま閉じ忘れた Statement を追跡する track-statements があり、"
            "JBoss AS 7 (2011) 以降の IronJacamar に引き継がれた。",
            "プールでは接続が使い回されるため、閉じ忘れたリソースが次の利用者に持ち越されたり、DB 側に溜まったりする。それを防ぐ安全網と、開発者への通知を兼ねている。")),
        S("この環境での原因と切り分け",
          P("アプリのコードが Statement を閉じずに Connection だけ閉じています。スタックの中のアプリのフレームが直すべき場所です。"
            "analyze-ij-log.py で、作成箇所ごとの件数ランキングを出せます。"),
          C("""python analyze-ij-log.py server.log --pkg com.example
 (A) ⑧ IJ030040 / ⑫ IJ030042 閉じ忘れの「作った場所」ランキング
      1  IJ030040 Statement   com.example.iwinmichl.test.DbServlet.leak(DbServlet.java:70)
      1  IJ030042 ResultSet   com.example.iwinmichl.test.DbServlet.leak(DbServlet.java:71)""",
            "text", "検証ログでの実行結果")),
        S("影響度と放置した場合のリスク",
          P("危険度 B。サーバが代わりに閉じているので即障害にはなりませんが、コードの不具合です。"
            "長いトランザクションや大量ループで同じ書き方をすると、DB 側のリソース (カーソル、プリペアドステートメント) を使い切ったり、"
            "メモリを圧迫したりします。NOWARN や FALSE に変えて警告だけ消すのは誤りです (FALSE だと後片付けもしなくなる)。")),
        S("対処方針の比較",
          T(["方式", "内容", "評価"], [
              ["コードを直す ★推奨", "try-with-resources で Connection / Statement / ResultSet を必ず閉じる。Spring なら JdbcTemplate に任せる", "◎ 根本対処"],
              ["track-statements を環境で切り替え", "開発・検証は TRUE で検出、本番は修正後に NOWARN (安全網は残す)", "◎ 運用"],
              ["CCM の debug", "接続そのものの閉じ忘れ (リーク) を検出 (IJ000100)", "○ 補助"],
              ["FALSE にする", "追跡も後片付けもしない", "× 警告が消えるだけでリスクが増える"],
          ], widths=[2, 5, 2])),
        S("実装",
          C("""// 良い例 (implementation/app/.../dao/JdbcResourceSamples.java)
try (Connection c = ds.getConnection();
     PreparedStatement ps = c.prepareStatement("SELECT name FROM emp WHERE dept_id = ?")) {
    ps.setInt(1, deptId);
    try (ResultSet rs = ps.executeQuery()) {
        while (rs.next()) { names.add(rs.getString(1)); }
    }
}""", "java", "アプリ側"),
          C("""# 30-datasource-mysql-xa.cli (抜粋): 環境変数で切り替え (既定 NOWARN)
track-statements="${env.DB_TRACK_STATEMENTS:NOWARN}"
# 31-jca-ccm.cli: 調査時だけ JCA_CCM_DEBUG=true
/subsystem=jca/cached-connection-manager=cached-connection-manager:write-attribute(name=debug, value="${env.JCA_CCM_DEBUG:false}")""",
            "text", "サーバ側 (jboss-cli)")),
        S("確認方法",
          C("""# 検証環境 (DB_TRACK_STATEMENTS=TRUE) でアプリを一通り動かし
grep -c IJ030040 server.log                 # → 0
python analyze-ij-log.py server.log --pkg com.example   # (A) が「該当なし」""", "bash")),
    ],
    "refs": ["src-ij-adapters", "src-ij-defaults", "kb-ds"],
}

# =====================================================================
# ⑨ Resolved [HttpRequestMethodNotSupportedException]
# =====================================================================
W09 = {
    "key": "W09", "no": "⑨", "sheet": "⑨405 Resolved", "id": "HttpRequestMethodNotSupportedException", "severity": "B",
    "title": "⑨ Resolved [HttpRequestMethodNotSupportedException: Request method 'POST' is not supported]",
    "user_log": "Resolved ( org.springframework.web.HttpRequestMethodNotSupportedException: RequestMethod 'POST' is not supported'",
    "verify_labels": ["Resolved [...HttpRequestMethodNotSupported...]", "HTTP 405 detail line (MethodNotAllowedAdvice)"],
    "sections": [
        S("ひとことで (小学生向け)",
          KID("お店の窓口に「ここは “見るだけ (GET)” の窓口です」と書いてあるのに、誰かが「荷物を置かせて (POST)」と来ました。\n"
              "店員 (Spring) は「この窓口ではできません (405)」と断り、日記に「断りました」とだけ書きました。\n"
              "でも、誰が・どの窓口に来たのかは書いていないので、このままでは理由が分かりません。"),
          T(["たとえ", "本当の仕組み"], [
              ["窓口", "Spring MVC のハンドラ (@GetMapping などで受け付ける URL とメソッドが決まる)"],
              ["見るだけ / 置かせて", "HTTP メソッド GET / POST"],
              ["断る", "405 Method Not Allowed と Allow ヘッダ (受け付けるメソッド) を返す"],
              ["日記に断ったとだけ書く", "DefaultHandlerExceptionResolver が \"Resolved [...]\" を WARN で出す (URL・送信元は出さない)"],
          ], widths=[1, 3])),
        S("メッセージの正体",
          T(["項目", "内容"], [
              ["英語原文 (正しい形)", "Resolved [org.springframework.web.HttpRequestMethodNotSupportedException: Request method 'POST' is not supported]"],
              ["ID / レベル", "ID なし (Spring Framework) / WARN"],
              ["ロガー", "org.springframework.web.servlet.mvc.support.DefaultHandlerExceptionResolver (warnLogCategory = 自分のクラス名)"],
              ["出す場所", "AbstractHandlerExceptionResolver#logException → buildLogMessage = \"Resolved [\" + 例外 + \"]\""],
              ["応答", "HTTP 405 + Allow: GET (検証で確認)"],
              ["ログの経路", "spring-jcl → (EAP が付ける) Log4j 2 API → JBoss LogManager → コンソール / server.log"],
          ], widths=[1, 4])),
        S("動作原理",
          B("DispatcherServlet が URL に合うハンドラを探す。URL は合うがメソッドが合わないと HttpRequestMethodNotSupportedException を投げる。",
            "例外リゾルバが順に処理する: ExceptionHandlerExceptionResolver (@ExceptionHandler / @ControllerAdvice) → ResponseStatusExceptionResolver → "
            "DefaultHandlerExceptionResolver (Spring MVC 標準の例外を 4xx に変換)。",
            "DefaultHandlerExceptionResolver はコンストラクタで setWarnLogCategory(自分のクラス名) をしており、処理した例外を "
            "\"Resolved [例外]\" という WARN 1 行で記録する。URL・送信元・ヘッダは記録しない。",
            "@ControllerAdvice で先に処理すると、DefaultHandlerExceptionResolver まで届かないので、この 1 行は出なくなる "
            "(代わりに自分で詳しい 1 行を出せる)。")),
        S("動作イメージ",
          DIA("""[リクエスト] POST /iwinmichl/api/hello  (ハンドラは @GetMapping("/hello") だけ)
 DispatcherServlet → HandlerMapping: URL は一致、メソッド不一致 → HttpRequestMethodNotSupportedException
 例外リゾルバ
  ├ ExceptionHandlerExceptionResolver (@ControllerAdvice)  … 修正後はここで処理 → "HTTP 405 method=POST uri=... remote=..." を記録
  └ DefaultHandlerExceptionResolver                          … 修正前はここで処理 → "Resolved [...]" (WARN) ★今回
 → 405 Method Not Allowed / Allow: GET""")),
        S("歴史・背景・必要になった経緯",
          B("1999 HTTP/1.1 (RFC 2616) で 405 と Allow ヘッダが定義され、2022 RFC 9110 に引き継がれている。",
            "2007 Spring 2.5 でアノテーションによるマッピング (@RequestMapping)、2009 Spring 3.0 で DefaultHandlerExceptionResolver。",
            "2018-09 Spring 5.1 のログ整理で、文言が \"Resolved exception caused by Handler execution: ...\" から \"Resolved [...]\" に変わった "
            "(ソースで確認)。Spring 6 では 405 も warnLogCategory の WARN として出る。")),
        S("この環境での原因と切り分け",
          P("GET 専用の URL に POST が届いています。誰が・どの URL に送ったかがログに無いので、まずそれを記録できるようにします。"),
          T(["よくある原因", "見分け方"], [
              ["フォームや JavaScript の送信先・メソッドの誤り", "Referer が自サイトの画面。特定の URL に集中"],
              ["エラーページへの内部転送で POST のまま届く", "dispatcher=ERROR、errorOrigin に元の URL (MethodNotAllowedAdvice が記録)"],
              ["セッション切れ後の再送信・ブラウザの戻る", "同じ利用者の直前の要求を確認"],
              ["脆弱性スキャナ・ボット", "User-Agent、送信元 IP (X-Forwarded-For)、ランダムな URL"],
              ["ALB のヘルスチェック", "ヘルスチェックは GET / HEAD なので通常は原因にならない"],
          ], widths=[2, 3])),
        S("影響度と放置した場合のリスク",
          P("危険度 B。サーバの故障ではなく「要求の誤り (4xx)」です。ただし自サイトの画面からの送信なら機能が壊れており、"
            "スキャナなら攻撃の予兆の可能性もあるので、正体を確かめて対処を決めます。")),
        S("対処方針の比較",
          T(["方式", "内容", "評価"], [
              ["送信元と URL を記録 ★推奨", "4xx/5xx だけの JSON アクセスログ (jboss-cli) + 405 の詳細 1 行 (@ControllerAdvice)", "◎ 原因が分かる"],
              ["マッピングを直す", "正しい送信なら @PostMapping を追加 / 誤りなら送信側を直す", "◎ 原因が分かったら"],
              ["スキャナなら入口で遮断", "AWS WAF のルール等", "○"],
              ["ログレベルを下げる", "DefaultHandlerExceptionResolver を ERROR に", "△ 原因が分かってから"],
          ], widths=[2, 5, 2])),
        S("実装",
          C("""# 60-undertow.cli (抜粋)
/subsystem=undertow/server=default-server/http-listener=default:write-attribute(name=proxy-address-forwarding, value=true)
/subsystem=undertow/server=default-server/http-listener=default:write-attribute(name=record-request-start-time, value=true)
/subsystem=undertow/server=default-server/host=default-host/setting=console-access-log:add( \\
    include-host-name=false, \\
    predicate="regex(pattern=\\"^[45]\\", value=\\"%s\\", full-match=false)", \\
    attributes={date-time={key=timestamp, date-format="yyyy-MM-dd'T'HH:mm:ss.SSSXXX"}, remote-ip={key=client}, \\
                request-method={key=method}, request-url={key=path}, query-string={key=query}, response-code={key=status}, \\
                response-time={key=ms, time-unit=MILLISECONDS}, \\
                request-header={key-prefix="h_", names=["X-Forwarded-For","User-Agent","Referer"]}})""",
            "text", "サーバ側: 4xx/5xx の JSON アクセスログ (応答完了後に判定されるので応答コードで絞れる)"),
          C("""@ExceptionHandler(HttpRequestMethodNotSupportedException.class)
public ResponseEntity<String> handleMethodNotAllowed(HttpRequestMethodNotSupportedException ex, HttpServletRequest req) {
    // method, uri, query, dispatcher, errorOrigin, remote, X-Forwarded-For, User-Agent, Referer を 1 行で WARN
    // (全文は implementation/app/.../web/MethodNotAllowedAdvice.java。改行の混入を除去してから記録)
    return new ResponseEntity<>("Method Not Allowed", headersWithAllow, HttpStatus.METHOD_NOT_ALLOWED);
}""", "java", "アプリ側: 405 を詳しく 1 行で記録")),
        S("確認方法",
          C("""curl -i -X POST http://localhost:8080/iwinmichl/api/hello   # 405 / Allow: GET
# ログ (検証結果):
# WARN [com.example.iwinmichl.web.MethodNotAllowedAdvice] HTTP 405 method=POST uri=/iwinmichl/api/hello ... allowed=[GET]
# {"eventSource":"web-access","timestamp":"...","client":"...","method":"POST","path":"/iwinmichl/api/hello","status":405,"ms":...}""", "text")),
    ],
    "refs": ["src-spring-dher", "rfc9110", "src-eventlogger"],
}
