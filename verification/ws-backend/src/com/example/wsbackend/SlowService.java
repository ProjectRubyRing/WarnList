package com.example.wsbackend;

import jakarta.jws.WebService;

/**
 * ③ の検証用バックエンド (別 WAR: ws-backend.war)。
 * 指定ミリ秒だけ待ってから応答する SOAP サービス。
 * iwinmichl.war とは別デプロイにして、iwinmichl.war 側の Weld 判定に影響させない。
 */
@WebService(serviceName = "SlowService", targetNamespace = "http://wsbackend.example.com/")
public class SlowService {

    public String sleep(int ms) throws InterruptedException {
        Thread.sleep(ms);
        return "slept " + ms;
    }
}
