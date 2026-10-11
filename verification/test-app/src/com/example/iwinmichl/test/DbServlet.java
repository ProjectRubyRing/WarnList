package com.example.iwinmichl.test;

import java.io.IOException;
import java.io.PrintWriter;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

import javax.sql.DataSource;

import jakarta.annotation.Resource;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

/**
 * データソース (java:/jdbc/MIF02JA_JDS) の挙動を確かめるサーブレット。
 *
 *   /db/ok    … try-with-resources で正しく閉じる (⑩⑪ の再現・確認に使う)
 *   /db/leak  … Statement と ResultSet を閉じずに Connection だけ閉じる (⑧⑫ の再現)
 *   /db/fixed … /db/leak と同じ処理を正しく書いたもの (⑧⑫ の対処確認)
 *   /db/slow?sec=N … SELECT SLEEP(N) で接続を N 秒使い続ける (⑬ の再現: 停止中の処理)
 */
@WebServlet(urlPatterns = "/db/*")
public class DbServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;

    @Resource(lookup = "java:/jdbc/MIF02JA_JDS")
    private DataSource ds;

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        String op = req.getPathInfo() == null ? "/ok" : req.getPathInfo();
        resp.setContentType("text/plain;charset=UTF-8");
        PrintWriter out = resp.getWriter();
        try {
            switch (op) {
                case "/ok" -> out.println("ok " + selectOne());
                case "/leak" -> out.println("leaked " + leak());
                case "/fixed" -> out.println("fixed " + selectOne());
                case "/slow" -> {
                    String s = req.getParameter("sec");
                    int sec = s == null ? 10 : Integer.parseInt(s);
                    out.println("slept " + sleep(sec));
                }
                default -> resp.sendError(HttpServletResponse.SC_NOT_FOUND);
            }
        } catch (SQLException e) {
            resp.setStatus(HttpServletResponse.SC_INTERNAL_SERVER_ERROR);
            out.println("SQLException: " + e);
        }
    }

    /** 正しい書き方: 取得したものは全部 try-with-resources で閉じる。 */
    private int selectOne() throws SQLException {
        try (Connection c = ds.getConnection();
             PreparedStatement ps = c.prepareStatement("SELECT 1");
             ResultSet rs = ps.executeQuery()) {
            rs.next();
            return rs.getInt(1);
        }
    }

    /** ⑧⑫ の再現: PreparedStatement と ResultSet を閉じ忘れる (Connection だけ閉じる)。 */
    private int leak() throws SQLException {
        try (Connection c = ds.getConnection()) {
            PreparedStatement ps = c.prepareStatement("SELECT 1"); // 閉じ忘れ (IJ030040)
            ResultSet rs = ps.executeQuery();                      // 閉じ忘れ (IJ030042)
            rs.next();
            return rs.getInt(1);
        }
    }

    /** ⑬ の再現用: 接続を sec 秒使い続ける。 */
    private int sleep(int sec) throws SQLException {
        try (Connection c = ds.getConnection();
             PreparedStatement ps = c.prepareStatement("SELECT SLEEP(?)")) {
            ps.setInt(1, sec);
            try (ResultSet rs = ps.executeQuery()) {
                rs.next();
                return sec;
            }
        }
    }
}
