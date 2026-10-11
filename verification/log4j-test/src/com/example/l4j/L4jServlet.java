package com.example.l4j;

import java.io.IOException;

import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

/**
 * ⑥ の検証用: アプリが Log4j 2 API で出したログが「どこへ」行くかを確かめる。
 *   - EAP の logging サブシステム (JBoss LogManager) に流れる … 既定 / 除外が空振りの場合
 *   - アプリ同梱の log4j-core + WEB-INF/classes/log4j2.xml で出る … org.apache.logging.log4j.api を除外した場合
 */
@WebServlet("/log")
public class L4jServlet extends HttpServlet {
    private static final long serialVersionUID = 1L;

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        Logger log = LogManager.getLogger(L4jServlet.class);
        log.info("hello-from-app-log4j2");
        resp.setContentType("text/plain;charset=UTF-8");
        resp.getWriter().println("LoggerContext=" + LogManager.getContext(false).getClass().getName());
        resp.getWriter().println("log4j-api loaded from=" + LogManager.class.getProtectionDomain().getCodeSource());
    }
}
