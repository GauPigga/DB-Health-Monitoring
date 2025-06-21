from flask import Flask, jsonify,request
from flask_cors import CORS
from utils.db import fetch_all_dict, fetch_one_dict
from datetime import datetime
import threading
import time

app = Flask(__name__)
CORS(app)

ORACLE_CONFIG = {}

def update_db_config(new_config):
    global ORACLE_CONFIG
    ORACLE_CONFIG = new_config

@app.route("/api/set-db-config", methods=["POST"])
def set_db_config():
    data = request.json
    required_keys = {"user", "password", "host", "port", "service_name"}
    if not all(k in data for k in required_keys):
        return jsonify({"error": "Missing parameters"}), 400
    update_db_config(data)
    return jsonify({"message": "DB config updated"})

def get_current_db_config():
    if not ORACLE_CONFIG:
        raise Exception("DB config not set. Use /api/set-db-config")
    return ORACLE_CONFIG

sql_trend_data = []

def collect_sql_trend():
    while True:
        try:
            query = """
                SELECT 
                    ROUND(AVG(elapsed_time / (executions * 1000)), 2) AS avg_exec_time_ms,
                    COUNT(*) AS total_queries,
                    COUNT(CASE WHEN (elapsed_time / executions) > 1000000 THEN 1 END) AS slow_queries
                FROM v$sql
                WHERE executions > 0
            """
            result = fetch_one_dict(query)
            if result:
                sample = {
                    "time": datetime.now().strftime("%H:%M"),
                    "avg_exec_time_ms": float(result.get("avg_exec_time_ms") or 0),
                    "slow_queries": int(result.get("slow_queries") or 0)
                }
                sql_trend_data.append(sample)
                if len(sql_trend_data) > 50:
                    sql_trend_data.pop(0)
        except Exception as e:
            print("Trend sample error:", e)
        time.sleep(60) 

threading.Thread(target=collect_sql_trend, daemon=True).start()

@app.route("/api/db-status")
def db_status():
    try:
        query = """
            SELECT status, host_name, TO_CHAR(startup_time, 'YYYY-MM-DD HH24:MI:SS') AS uptime
            FROM v$instance
        """
        data = fetch_one_dict(query)
        if not data:
            return jsonify({
                "status": "DOWN",
                "host": "N/A",
                "uptime": "N/A"
            })
        return jsonify({
            "status": data.get("status", "UNKNOWN"),
            "host": data.get("host_name", "UNKNOWN"),
            "uptime": data.get("uptime")
        })
    except Exception as e:
        return jsonify({
            "status": "DOWN",
            "host": "N/A",
            "uptime": "N/A",
            "error": str(e)
        })


@app.route("/api/sessions")
def sessions():
    try:
        active_q = "SELECT COUNT(*) as count FROM v$session WHERE status = 'ACTIVE'"
        idle_q = "SELECT COUNT(*) as count FROM v$session WHERE status = 'INACTIVE'"
        blocking_q = "SELECT COUNT(DISTINCT blocking_session) as count FROM v$session WHERE blocking_session IS NOT NULL"

        active = fetch_one_dict(active_q)
        idle = fetch_one_dict(idle_q)
        blocking = fetch_one_dict(blocking_q)

        if not (active and idle and blocking):
            return jsonify({
                "active_sessions": None,
                "idle_sessions": None,
                "blocking_sessions": None,
                "db_status": "DOWN"
            })

        return jsonify({
            "active_sessions": active.get("count", 0),
            "idle_sessions": idle.get("count", 0),
            "blocking_sessions": blocking.get("count", 0)
        })
    except Exception as e:
        return jsonify({
            "error": "Failed to fetch session stats",
            "details": str(e),
            "active_sessions": None,
            "idle_sessions": None,
            "blocking_sessions": None,
            "db_status": "DOWN"
        }), 500


@app.route("/api/cpu-memory")
def cpu_memory():
    try:
        cpu_q = """
            SELECT value FROM v$sysmetric WHERE metric_name = 'CPU Usage Per Sec' AND rownum = 1
        """
        cpu_usage = fetch_one_dict(cpu_q)
        mem_q = """
            SELECT SUM(bytes) AS mem_bytes FROM v$sgastat WHERE pool = 'shared pool'
        """
        mem_used = fetch_one_dict(mem_q)

        mem_used_gb = round(mem_used["mem_bytes"] / 1024 / 1024 / 1024, 2) if mem_used and mem_used["mem_bytes"] else None

        return jsonify({
            "cpu_usage_percent": round(cpu_usage["value"], 2) if cpu_usage else None,
            "memory_used_gb": mem_used_gb,
            "memory_total_gb": None 
        })
    except Exception as e:
        return jsonify({"error": "Failed to fetch CPU/Memory usage", "details": str(e)}), 500

@app.route("/api/alerts")
def alerts():
    try:
        query = """
            SELECT TO_CHAR(originating_timestamp, 'YYYY-MM-DD HH24:MI') as alert_time, message_text as message
            FROM X$DBGALERTEXT
            WHERE ROWNUM <= 10
            ORDER BY originating_timestamp DESC
        """
        alerts = fetch_all_dict(query)
        result = [{"time": a["alert_time"], "message": a["message"]} for a in alerts]
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": "Failed to fetch alerts", "details": str(e)}), 500

@app.route("/api/sql-performance")
def sql_performance():
    try:
        query = """
            SELECT sql_text, 
                   executions, 
                   ROUND(
                       CASE 
                           WHEN executions > 0 THEN elapsed_time / (executions * 1000) 
                           ELSE NULL 
                       END, 2
                   ) AS avg_exec_time_ms, 
                   cpu_time AS total_cpu_time,
                   TO_CHAR(last_load_time, 'YYYY-MM-DD HH24:MI:SS') AS last_execution
            FROM v$sqlarea
            WHERE executions > 0
              AND LENGTH(sql_text) > 20
              AND NOT (
                  sql_text LIKE 'BEGIN %'
                  OR sql_text LIKE 'INSERT INTO WRI$_%'
                  OR sql_text LIKE 'DELETE FROM SYS.%'
                  OR sql_text LIKE 'SELECT /*+%'
              )
              AND ROWNUM <= 50
            ORDER BY executions DESC
        """
        data = fetch_all_dict(query)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": "Failed to fetch SQL performance", "details": str(e)}), 500





@app.route("/api/tablespaces")
def tablespaces():
    try:
        query = """
            SELECT df.tablespace_name,
                   ROUND(SUM(df.bytes) / 1024 / 1024 / 1024, 4) AS total_space_gb,
                   ROUND((SUM(df.bytes) - NVL(SUM(fs.bytes), 0)) / 1024 / 1024 / 1024, 4) AS used_space_gb
            FROM dba_data_files df
            LEFT JOIN dba_free_space fs ON df.tablespace_name = fs.tablespace_name
            GROUP BY df.tablespace_name
        """
        raw = fetch_all_dict(query)

        result = []
        for item in raw:
            total = item.get("total_space_gb", 0) or 0
            used = item.get("used_space_gb", 0) or 0

            if total == 0:
                usage = 0.0
                status = "UNALLOCATED"
            else:
                usage = round((used / total) * 100, 2)
                status = "OK"

            result.append({
                "tablespace_name": item["tablespace_name"],
                "total_space_gb": total,
                "used_space_gb": used,
                "usage_percent": usage,
                "status": status
            })

        return jsonify(result)
    except Exception as e:
        return jsonify({
            "error": "Failed to fetch tablespaces",
            "details": str(e)
        }), 500



@app.route("/api/largest-tables")
def largest_tables():
    try:
        query = """
            SELECT
                segment_name AS table_name,
                ROUND(SUM(bytes) / 1024 / 1024, 2) AS size_mb
            FROM
                user_segments
            WHERE
                segment_type = 'TABLE'
            GROUP BY
                segment_name
            ORDER BY
                size_mb DESC
            FETCH FIRST 5 ROWS ONLY
        """
        data = fetch_all_dict(query)
        return jsonify(data), 200
    except Exception as e:
        return jsonify({
            "error": "Failed to fetch largest tables",
            "details": str(e)
        }), 500




@app.route("/api/user-activity")
def user_activity():
    try:
        query = """
            SELECT s.username,
                   COUNT(*) AS total_sessions,
                   COUNT(CASE WHEN s.status = 'ACTIVE' THEN 1 END) AS active_sessions,
                   COUNT(q.sql_id) AS total_queries,
                   ROUND(COALESCE(SUM(q.cpu_time), 0) / 1000, 2) AS total_cpu_ms
            FROM v$session s
            LEFT JOIN v$sql q ON s.sql_id = q.sql_id
            WHERE s.username IS NOT NULL
            GROUP BY s.username
        """
        data = fetch_all_dict(query)
        return jsonify(data)
    except Exception as e:
        return jsonify({
            "error": "Failed to fetch user activity",
            "details": str(e)
        }), 500


@app.route("/api/sql-performance-trends")
def sql_performance_trends():
    try:
        return jsonify(sql_trend_data)
    except Exception as e:
        return jsonify({"error": "Failed to fetch performance trends", "details": str(e)}), 500

if __name__ == "__main__":
    threading.Thread(target=collect_sql_trend, daemon=True).start()
    app.run(debug=True)
