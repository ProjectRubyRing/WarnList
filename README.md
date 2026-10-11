# WarnList — JBoss EAP 8.1 警告 13 件の徹底解説と jboss-cli による対処実装

ECS タスク上の UBI 9.8 + Red Hat build of OpenJDK 21 + JBoss EAP 8.1 コンテナで出ている警告 ①〜⑬ について、
小学生にもわかる説明・動作原理・動作イメージ・歴史と背景を解説し、jboss-cli で各サブシステムを設定する前提の対処を実装・検証しました。

## 成果物

| ファイル / フォルダ | 内容 |
|---|---|
| `JBossEAP81_WARN13_解説.xlsx` | 解説ブック (Meiryo UI / モノトーン / 24 シート)。表紙・一覧・基礎知識・警告 13 シート・①深掘り・実装マップ・実装コード・検証結果・年表・用語集・前提・出典 |
| `JBossEAP81_WARN13_解説.md` | 同じ原稿から生成した Markdown 版 |
| `implementation/` | 対処の実装 (Dockerfile、jboss-cli の .cli、entrypoint、ECS タスク定義、WAR 側の修正、運用ツール) |
| `verification/` | 修正前に 13 件すべてを再現し、修正後に 0 件になることを確かめた検証一式とログ |
| `tools/` | 解説の原稿 (`content_*.py`) と、xlsx / md を生成する `build_docs.py` |
| `Gemini_DeepResearch_Prompt_JBossEAP81_WARN13.md` | 同じテーマを Gemini Deep Research で調べるためのプロンプト |

再生成: `python tools/build_docs.py` (openpyxl が必要)

## 13 件の要点

| No | 警告 | 本当の原因 (実測で確認) | 主な対処 | 修正前→後 |
|---|---|---|---|---|
| ① | WFLYELY00023 | EAP 標準の 8443 用 applicationKS。自前 p12 の置き場所や -D 引数とは無関係 | 未使用の 8443 一式を jboss-cli で削除 | 1 → 0 |
| ② | WFLYSRV0058 | 記述子に WAR に無い testClasses が残っている | 記述を削除 | 1 → 0 |
| ③ | WFLYSRV0018 | org.apache.cxf.impl への明示依存 (+ spring-core の MANIFEST の org.jboss.vfs) | 依存を削除し標準プロパティでタイムアウト | 2 → 0 |
| ④ | WFLYEE0007 | Weld 無効の WAR で Spring の AsyncListener に引数なしコンストラクタが無い (WFLYEE0048) | 原因確認のうえ Spring の分だけ抑止 | 8 → 0 |
| ⑤ | WFLYWELD0013 | 同梱の jakarta.transaction-api の @NormalScope (+ jsf 除外で Weld 無効) | EE API を provided、weld を除外 | 1 → 0 |
| ⑥ | WFLYSRV0274 | org.jboss.logmanager.log4j2 は依存に直接入らない (除外が空振り) | 除外を削除 (自前 Log4j 2 なら log4j.api を除外) | 1 → 0 |
| ⑦ | Failed to define class javax.* | javax 版 jstl-1.2.jar の TLD バリデータ | javax 版 JSTL を削除 | 4 → 0 |
| ⑧ | IJ030040 | Statement の閉じ忘れ | try-with-resources | 1 → 0 |
| ⑨ | Resolved [405] | GET 専用 URL への POST (送信元がログに無い) | JSON アクセスログ + 405 詳細ログで特定 | 1 → 0 |
| ⑩ | IJ030027 | 待機中の接続が wait_timeout 等で切られていた | idle-timeout 短縮、exception-sorter、keepalive | 1 → 0 |
| ⑪ | IJ000621 | ⑩ のプール側の記録 (貸出時検証) | ⑩ と同じ | 1 → 0 |
| ⑫ | IJ030042 | ResultSet の閉じ忘れ | try-with-resources | 1 → 0 |
| ⑬ | IJ000615 | SIGTERM 時のサスペンド待ち時間が 0 秒 | org.wildfly.sigterm.suspend.timeout + LAUNCH_JBOSS_IN_BACKGROUND + stopTimeout | 1 → 0 |
