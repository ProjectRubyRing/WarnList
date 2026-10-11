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
