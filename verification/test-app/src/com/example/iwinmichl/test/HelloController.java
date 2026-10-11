package com.example.iwinmichl.test;

import java.util.concurrent.Callable;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * ⑨ の再現: /api/hello は GET 専用。POST すると Spring が 405 を返し
 *   "Resolved [org.springframework.web.HttpRequestMethodNotSupportedException: Request method 'POST' is not supported]"
 *   を WARN で出す (DefaultHandlerExceptionResolver)。
 * ④ の検証: /api/async は Spring MVC の非同期処理 (内部で AsyncListener を使う)。
 */
@RestController
public class HelloController {

    @GetMapping("/hello")
    public String hello() {
        return "hello";
    }

    @GetMapping("/async")
    public Callable<String> async() {
        return () -> "async-ok on " + Thread.currentThread().getName();
    }
}
