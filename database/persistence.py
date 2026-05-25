"""
RetailIQ — Persistence Layer
Dual-backend: Supabase (production) / SQLite (local fallback).
"""

import sqlite3, gzip, pickle, uuid, os
from datetime import datetime
import pandas as pd
import streamlit as st

_SQLITE_PATH = "retailiq_local.db"


def _use_supabase() -> bool:
    try:
        return bool(st.secrets.get("SUPABASE_URL") and st.secrets.get("SUPABASE_KEY"))
    except Exception:
        return False


def _sb():
    from supabase import create_client
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


def _sqlite_connect():
    conn = sqlite3.connect(_SQLITE_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS data_batches (
            id TEXT PRIMARY KEY, label TEXT, filename TEXT,
            date_min TEXT, date_max TEXT, row_count INTEGER,
            created_at TEXT, blob BLOB
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_customers (
            user_id INTEGER, customer_num TEXT,
            PRIMARY KEY (user_id, customer_num)
        )""")
    conn.commit()
    return conn


# ── Batches ──────────────────────────────────────────────────────────────────

def save_batch(label: str, filename: str, df: pd.DataFrame) -> str:
    bid = str(uuid.uuid4())
    date_min = str(df["_date"].min().date()) if "_date" in df.columns else ""
    date_max = str(df["_date"].max().date()) if "_date" in df.columns else ""
    blob = gzip.compress(pickle.dumps(df))

    if _use_supabase():
        path = f"batches/{bid}.pkl.gz"
        _sb().storage.from_("salesiq").upload(path, blob)
        _sb().table("data_batches").insert({
            "id": bid, "label": label, "filename": filename,
            "date_min": date_min, "date_max": date_max,
            "row_count": len(df), "storage_path": path,
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
    else:
        conn = _sqlite_connect()
        conn.execute(
            "INSERT INTO data_batches VALUES (?,?,?,?,?,?,?,?)",
            (bid, label, filename, date_min, date_max, len(df),
             datetime.utcnow().isoformat(), blob)
        )
        conn.commit(); conn.close()
    return bid


def load_all_batches() -> list[dict]:
    if _use_supabase():
        return _sb().table("data_batches").select(
            "id,label,filename,date_min,date_max,row_count,created_at"
        ).execute().data or []
    conn = _sqlite_connect()
    rows = conn.execute(
        "SELECT id,label,filename,date_min,date_max,row_count,created_at FROM data_batches ORDER BY created_at"
    ).fetchall()
    conn.close()
    keys = ["id","label","filename","date_min","date_max","row_count","created_at"]
    return [dict(zip(keys, r)) for r in rows]


def load_batch_df(batch_id: str) -> pd.DataFrame:
    if _use_supabase():
        meta = _sb().table("data_batches").select("storage_path").eq("id", batch_id).execute().data
        if not meta:
            return pd.DataFrame()
        blob = _sb().storage.from_("salesiq").download(meta[0]["storage_path"])
        return pickle.loads(gzip.decompress(blob))
    conn = _sqlite_connect()
    row = conn.execute("SELECT blob FROM data_batches WHERE id=?", (batch_id,)).fetchone()
    conn.close()
    return pickle.loads(gzip.decompress(row[0])) if row else pd.DataFrame()


def load_combined_df() -> pd.DataFrame:
    batches = load_all_batches()
    if not batches:
        return pd.DataFrame()
    frames = [load_batch_df(b["id"]) for b in batches]
    frames = [f for f in frames if not f.empty]
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    if "_date" in combined.columns:
        combined = combined.sort_values("_date").reset_index(drop=True)
    return combined


def delete_batch(batch_id: str):
    if _use_supabase():
        meta = _sb().table("data_batches").select("storage_path").eq("id", batch_id).execute().data
        if meta:
            _sb().storage.from_("salesiq").remove([meta[0]["storage_path"]])
        _sb().table("data_batches").delete().eq("id", batch_id).execute()
    else:
        conn = _sqlite_connect()
        conn.execute("DELETE FROM data_batches WHERE id=?", (batch_id,))
        conn.commit(); conn.close()


def rename_batch(batch_id: str, new_label: str):
    if _use_supabase():
        _sb().table("data_batches").update({"label": new_label}).eq("id", batch_id).execute()
    else:
        conn = _sqlite_connect()
        conn.execute("UPDATE data_batches SET label=? WHERE id=?", (new_label, batch_id))
        conn.commit(); conn.close()


def check_date_overlap(date_min: str, date_max: str) -> list[dict]:
    batches = load_all_batches()
    overlaps = []
    for b in batches:
        if not b.get("date_min") or not b.get("date_max"):
            continue
        if b["date_min"] <= date_max and b["date_max"] >= date_min:
            overlaps.append(b)
    return overlaps


# ── Users ─────────────────────────────────────────────────────────────────────

def get_users() -> list[dict]:
    if _use_supabase():
        return _sb().table("users").select("*").execute().data or []
    conn = _sqlite_connect()
    rows = conn.execute("SELECT id, name FROM users ORDER BY name").fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1]} for r in rows]


def add_user(name: str):
    if _use_supabase():
        _sb().table("users").insert({"name": name}).execute()
    else:
        conn = _sqlite_connect()
        conn.execute("INSERT OR IGNORE INTO users (name) VALUES (?)", (name,))
        conn.commit(); conn.close()


def delete_user(user_id: int):
    if _use_supabase():
        _sb().table("users").delete().eq("id", user_id).execute()
        _sb().table("user_customers").delete().eq("user_id", user_id).execute()
    else:
        conn = _sqlite_connect()
        conn.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.execute("DELETE FROM user_customers WHERE user_id=?", (user_id,))
        conn.commit(); conn.close()


# ── Portfolio ─────────────────────────────────────────────────────────────────

def get_portfolio(user_id: int) -> list[str]:
    if _use_supabase():
        rows = _sb().table("user_customers").select("customer_num").eq("user_id", user_id).execute().data or []
        return [r["customer_num"] for r in rows]
    conn = _sqlite_connect()
    rows = conn.execute("SELECT customer_num FROM user_customers WHERE user_id=?", (user_id,)).fetchall()
    conn.close()
    return [str(r[0]) for r in rows]


def add_to_portfolio(user_id: int, customer_num: str):
    if _use_supabase():
        _sb().table("user_customers").upsert({"user_id": user_id, "customer_num": str(customer_num)}).execute()
    else:
        conn = _sqlite_connect()
        conn.execute("INSERT OR IGNORE INTO user_customers VALUES (?,?)", (user_id, str(customer_num)))
        conn.commit(); conn.close()


def remove_from_portfolio(user_id: int, customer_num: str):
    if _use_supabase():
        _sb().table("user_customers").delete().eq("user_id", user_id).eq("customer_num", str(customer_num)).execute()
    else:
        conn = _sqlite_connect()
        conn.execute("DELETE FROM user_customers WHERE user_id=? AND customer_num=?", (user_id, str(customer_num)))
        conn.commit(); conn.close()
