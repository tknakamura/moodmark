# -*- coding: utf-8 -*-
"""
記事在庫の永続化: JSON ファイル or PostgreSQL（DATABASE_URL）。
"""

from __future__ import annotations

import json
import os
import uuid
from abc import ABC, abstractmethod
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import DateTime, Integer, String, and_, create_engine, delete, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Session, mapped_column

from tools.moodmark_stock import state as state_mod

STATE_VERSION = state_mod.STATE_VERSION


def _optional_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_iso_datetime(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://") and "+psycopg2" not in url.split("://", 1)[0]:
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


class Base(DeclarativeBase):
    pass


class MoodmarkStockArticleRow(Base):
    __tablename__ = "moodmark_stock_articles"

    id = mapped_column(String(36), primary_key=True)
    url = mapped_column(String(2048), unique=True, nullable=False)
    label = mapped_column(String(512), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at = mapped_column(DateTime(timezone=True), nullable=False)
    ga4_pageviews_7d = mapped_column(Integer, nullable=True)
    ga4_pv_fetched_at = mapped_column(DateTime(timezone=True), nullable=True)
    ga4_pv_error = mapped_column(String(512), nullable=True)


class MoodmarkStockRunRow(Base):
    __tablename__ = "moodmark_stock_runs"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_at = mapped_column(DateTime(timezone=True), nullable=False)
    snapshot_json = mapped_column(JSONB, nullable=False)


class ArticleStockStore(ABC):
    @abstractmethod
    def load_state(self) -> Dict[str, Any]:
        """version, articles, last_snapshot, updated_at"""

    @abstractmethod
    def add_article(self, url: str, label: str) -> Optional[str]:
        """エラーメッセージ or None"""

    @abstractmethod
    def remove_article(self, article_id: str) -> None:
        pass

    @abstractmethod
    def update_article(
        self,
        article_id: str,
        url: Optional[str] = None,
        label: Optional[str] = None,
    ) -> Optional[str]:
        pass

    @abstractmethod
    def set_article_ga4_pageviews(
        self,
        article_id: str,
        fetched_at: datetime,
        *,
        pageviews: Optional[int] = None,
        error: Optional[str] = None,
    ) -> None:
        """成功時は pageviews を渡し error は None。失敗時は error のみ（既存 PV は維持）。"""

    @abstractmethod
    def record_snapshot(self, snapshot: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def import_full_state(self, data: Dict[str, Any]) -> Optional[str]:
        """JSONインポートで全置換。エラー時メッセージ。"""

    def export_state_json(self) -> str:
        return json.dumps(self.load_state(), ensure_ascii=False, indent=2)

    @property
    def backend_label(self) -> str:
        return "unknown"


class JsonArticleStockStore(ArticleStockStore):
    def __init__(self, path: Optional[str] = None):
        self._path = path or state_mod.get_state_path()

    @property
    def backend_label(self) -> str:
        return f"json:{self._path}"

    def load_state(self) -> Dict[str, Any]:
        return state_mod.load_state(self._path)

    def add_article(self, url: str, label: str) -> Optional[str]:
        s = self.load_state()
        s, err = state_mod.add_article(s, url, label)
        if err:
            return err
        state_mod.save_state(s, self._path)
        return None

    def remove_article(self, article_id: str) -> None:
        s = self.load_state()
        state_mod.remove_article(s, article_id)
        state_mod.save_state(s, self._path)

    def update_article(
        self,
        article_id: str,
        url: Optional[str] = None,
        label: Optional[str] = None,
    ) -> Optional[str]:
        s = self.load_state()
        s, err = state_mod.update_article(s, article_id, url=url, label=label)
        if err:
            return err
        state_mod.save_state(s, self._path)
        return None

    def set_article_ga4_pageviews(
        self,
        article_id: str,
        fetched_at: datetime,
        *,
        pageviews: Optional[int] = None,
        error: Optional[str] = None,
    ) -> None:
        s = self.load_state()
        for a in s.get("articles", []):
            if a.get("id") != article_id:
                continue
            a["ga4_pv_fetched_at"] = fetched_at.isoformat()
            if pageviews is not None:
                a["ga4_pageviews_7d"] = int(pageviews)
                a.pop("ga4_pv_error", None)
            elif error:
                err = (error or "")[:512]
                if err:
                    a["ga4_pv_error"] = err
            state_mod.save_state(s, self._path)
            return

    def record_snapshot(self, snapshot: Dict[str, Any]) -> None:
        s = self.load_state()
        state_mod.attach_snapshot(s, snapshot)
        state_mod.save_state(s, self._path)

    def import_full_state(self, data: Dict[str, Any]) -> Optional[str]:
        data = deepcopy(data)
        data["version"] = STATE_VERSION
        data.setdefault("articles", [])
        data.setdefault("last_snapshot", None)
        state_mod.save_state(data, self._path)
        return None


class PostgresArticleStockStore(ArticleStockStore):
    def __init__(self, database_url: str):
        self._url = _normalize_database_url(database_url)
        self._engine = create_engine(
            self._url,
            pool_pre_ping=True,
            pool_size=3,
            max_overflow=5,
        )
        Base.metadata.create_all(self._engine)

    @property
    def backend_label(self) -> str:
        return "postgresql"

    def _session(self) -> Session:
        return Session(self._engine)

    def load_state(self) -> Dict[str, Any]:
        with self._session() as sess:
            rows = sess.scalars(
                select(MoodmarkStockArticleRow).order_by(
                    MoodmarkStockArticleRow.created_at
                )
            ).all()
            articles: List[Dict[str, Any]] = []
            for r in rows:
                ad: Dict[str, Any] = {
                    "id": r.id,
                    "url": r.url,
                    "label": r.label,
                }
                if r.ga4_pageviews_7d is not None:
                    ad["ga4_pageviews_7d"] = int(r.ga4_pageviews_7d)
                if r.ga4_pv_fetched_at is not None:
                    ad["ga4_pv_fetched_at"] = r.ga4_pv_fetched_at.isoformat()
                if r.ga4_pv_error:
                    ad["ga4_pv_error"] = r.ga4_pv_error
                articles.append(ad)
            last_run = sess.scalars(
                select(MoodmarkStockRunRow).order_by(MoodmarkStockRunRow.run_at.desc())
            ).first()
            last_snapshot = None
            updated_at = None
            if last_run:
                last_snapshot = last_run.snapshot_json
                if isinstance(last_snapshot, dict):
                    pass
                updated_at = last_run.run_at.isoformat() if last_run.run_at else None
            return {
                "version": STATE_VERSION,
                "articles": articles,
                "last_snapshot": last_snapshot,
                "updated_at": updated_at,
            }

    def add_article(self, url: str, label: str) -> Optional[str]:
        u = state_mod._normalize_article_url(url)
        if not u:
            return "有効な記事URLを入力してください（isetan.mistore.jp の moodmark 配下推奨）"
        now = datetime.now(timezone.utc)
        aid = str(uuid.uuid4())[:8]
        with self._session() as sess:
            existing = sess.scalars(select(MoodmarkStockArticleRow).where(MoodmarkStockArticleRow.url == u)).first()
            if existing:
                return "同じURLが既に登録されています"
            sess.add(
                MoodmarkStockArticleRow(
                    id=aid,
                    url=u,
                    label=(label or "").strip() or u,
                    created_at=now,
                    updated_at=now,
                )
            )
            sess.commit()
        return None

    def set_article_ga4_pageviews(
        self,
        article_id: str,
        fetched_at: datetime,
        *,
        pageviews: Optional[int] = None,
        error: Optional[str] = None,
    ) -> None:
        with self._session() as sess:
            row = sess.get(MoodmarkStockArticleRow, article_id)
            if not row:
                return
            row.ga4_pv_fetched_at = fetched_at
            if pageviews is not None:
                row.ga4_pageviews_7d = int(pageviews)
                row.ga4_pv_error = None
            elif error:
                row.ga4_pv_error = (error or "")[:512] or None
            sess.commit()

    def remove_article(self, article_id: str) -> None:
        with self._session() as sess:
            row = sess.get(MoodmarkStockArticleRow, article_id)
            if row:
                sess.delete(row)
                sess.commit()

    def update_article(
        self,
        article_id: str,
        url: Optional[str] = None,
        label: Optional[str] = None,
    ) -> Optional[str]:
        with self._session() as sess:
            row = sess.get(MoodmarkStockArticleRow, article_id)
            if not row:
                return "記事が見つかりません"
            if url is not None and url.strip():
                nu = state_mod._normalize_article_url(url)
                if not nu:
                    return "URLが無効です"
                other = sess.scalars(
                    select(MoodmarkStockArticleRow).where(
                        and_(
                            MoodmarkStockArticleRow.url == nu,
                            MoodmarkStockArticleRow.id != article_id,
                        )
                    )
                ).first()
                if other:
                    return "同じURLが既に登録されています"
                row.url = nu
            if label is not None:
                row.label = label.strip() or row.url
            row.updated_at = datetime.now(timezone.utc)
            sess.commit()
        return None

    def record_snapshot(self, snapshot: Dict[str, Any]) -> None:
        raw = snapshot.get("run_at")
        if raw:
            try:
                run_at = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                run_at = datetime.now(timezone.utc)
        else:
            run_at = datetime.now(timezone.utc)
        payload = deepcopy(snapshot)
        with self._session() as sess:
            sess.add(
                MoodmarkStockRunRow(
                    run_at=run_at,
                    snapshot_json=payload,
                )
            )
            sess.commit()

    def import_full_state(self, data: Dict[str, Any]) -> Optional[str]:
        arts = data.get("articles") or []
        snap = data.get("last_snapshot")
        now = datetime.now(timezone.utc)
        seen_urls: set = set()
        try:
            with self._session() as sess:
                sess.execute(delete(MoodmarkStockRunRow))
                sess.execute(delete(MoodmarkStockArticleRow))
                sess.commit()
                for a in arts:
                    aid = a.get("id") or str(uuid.uuid4())[:8]
                    u = state_mod._normalize_article_url(a.get("url", ""))
                    if not u or u in seen_urls:
                        continue
                    seen_urls.add(u)
                    gpv = _optional_int(a.get("ga4_pageviews_7d"))
                    gfp = _parse_iso_datetime(a.get("ga4_pv_fetched_at"))
                    gerr = (a.get("ga4_pv_error") or "").strip() or None
                    if gerr:
                        gerr = gerr[:512]
                    sess.add(
                        MoodmarkStockArticleRow(
                            id=str(aid)[:36],
                            url=u,
                            label=(a.get("label") or "").strip() or u,
                            created_at=now,
                            updated_at=now,
                            ga4_pageviews_7d=gpv,
                            ga4_pv_fetched_at=gfp,
                            ga4_pv_error=gerr,
                        )
                    )
                sess.commit()
                if snap and isinstance(snap, dict):
                    run_at_raw = snap.get("run_at")
                    if run_at_raw:
                        try:
                            run_at = datetime.fromisoformat(
                                str(run_at_raw).replace("Z", "+00:00")
                            )
                        except (ValueError, TypeError):
                            run_at = now
                    else:
                        run_at = now
                    sess.add(
                        MoodmarkStockRunRow(
                            run_at=run_at, snapshot_json=deepcopy(snap)
                        )
                    )
                    sess.commit()
        except Exception as e:
            return f"DBエラー: {e}"
        return None


_pg_store: Optional[PostgresArticleStockStore] = None


def get_store() -> ArticleStockStore:
    """DATABASE_URL ありなら PostgreSQL、なければ JSON ファイル。"""
    global _pg_store
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        if _pg_store is None:
            _pg_store = PostgresArticleStockStore(url)
        return _pg_store
    p = os.environ.get("MOODMARK_STOCK_STATE_PATH", "").strip()
    return JsonArticleStockStore(p if p else None)


def reset_postgres_store_cache() -> None:
    """テスト用: DATABASE_URL を差し替える前に呼ぶ。"""
    global _pg_store
    _pg_store = None
