#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
在线采集队列系统 - 纯内存顺序执行
"""

import os
import sys

sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

import re
import uuid
import time
import threading
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime


class QueueType(Enum):
    HTML_FILE = "html_file"
    ONLINE_URL = "online_url"
    ONLINE_ID = "online_id"


class ItemStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class ItemType(Enum):
    URL = "url"
    PRODUCT_ID = "product_id"


@dataclass
class OnlineQueueItem:
    id: str = ""
    item_type: ItemType = ItemType.PRODUCT_ID
    source: str = ""
    status: ItemStatus = ItemStatus.PENDING
    queue_type: QueueType = QueueType.ONLINE_ID
    product_id: Optional[str] = None
    product_url: Optional[str] = None
    product_title: Optional[str] = None
    main_images: List[str] = field(default_factory=list)
    color_images: List[str] = field(default_factory=list)
    detail_images: List[str] = field(default_factory=list)
    videos: List[str] = field(default_factory=list)
    extended_data: Dict[str, Any] = field(default_factory=dict)
    dsid: Optional[str] = None
    target_price: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    is_temporary: bool = True
    session_id: Optional[str] = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:8]


def validate_input(text: str) -> Optional[str]:
    """验证输入是否为有效的URL或商品ID"""
    text = text.strip()
    if not text:
        return None

    if ',' in text:
        text = text.split(',')[0].strip()

    url_pattern = r'^https?://detail\.1688\.com/offer/(\d+)\.html.*$'
    match = re.match(url_pattern, text)
    if match:
        return match.group(1)

    url_pattern_jd = r'^https?://item\.jd\.com/(\d+).*'
    match = re.match(url_pattern_jd, text)
    if match:
        return match.group(1)

    id_pattern = r'^(\d{10,15})$'
    match = re.match(id_pattern, text)
    if match:
        return match.group(1)

    return None


def parse_batch_input(text: str, platform: str = "1688") -> List[str]:
    """解析批量输入，返回有效的商品ID列表"""
    results = []
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        product_id = validate_input(line)
        if product_id:
            results.append(product_id)
    return results


class CoreQueue:
    """核心处理队列 - 纯内存顺序执行"""

    MAX_RETRY = 3

    def __init__(self):
        self.queue: List[OnlineQueueItem] = []
        self.processing: Optional[OnlineQueueItem] = None
        self.completed: List[OnlineQueueItem] = []
        self.failed: List[OnlineQueueItem] = []
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._worker_thread = None
        self._lock = threading.Lock()
        self._callbacks: List[Callable] = []
        self._collect_fn = None
        self._save_fn = None

    def set_collect_fn(self, fn: Callable):
        self._collect_fn = fn

    def set_save_fn(self, fn: Callable):
        self._save_fn = fn

    def register_callback(self, callback: Callable):
        self._callbacks.append(callback)

    def _notify(self, item: OnlineQueueItem = None, event: str = "update"):
        for cb in self._callbacks:
            try:
                cb(item=item, event=event)
            except Exception:
                pass

    def add_item(self, item: OnlineQueueItem) -> str:
        with self._lock:
            item.status = ItemStatus.PENDING
            self.queue.append(item)
        self._notify(item, "added")
        return item.id

    def add_items_batch(self, items: List[OnlineQueueItem]) -> List[str]:
        ids = []
        with self._lock:
            for item in items:
                item.status = ItemStatus.PENDING
                self.queue.append(item)
                ids.append(item.id)
        self._notify(event="batch_added")
        return ids

    def remove_item(self, item_id: str) -> bool:
        with self._lock:
            for i, item in enumerate(self.queue):
                if item.id == item_id:
                    self.queue.pop(i)
                    self._notify(event="removed")
                    return True
        return False

    def start_processing(self):
        if self._worker_thread and self._worker_thread.is_alive():
            if self._pause_event.is_set():
                self._pause_event.clear()
                self._notify(event="resumed")
            return

        self._stop_event.clear()
        self._pause_event.clear()
        self._worker_thread = threading.Thread(target=self._process_loop, daemon=True)
        self._worker_thread.start()
        self._notify(event="started")

    def pause_processing(self):
        self._pause_event.set()
        self._notify(event="paused")

    def stop_processing(self):
        self._stop_event.set()
        self._pause_event.clear()
        self._notify(event="stopped")

    def _process_loop(self):
        while not self._stop_event.is_set():
            while self._pause_event.is_set():
                time.sleep(0.2)
                if self._stop_event.is_set():
                    return

            item = self._get_next_item()
            if item:
                self._process_item(item)
            else:
                time.sleep(0.5)

        self._notify(event="finished")

    def _get_next_item(self) -> Optional[OnlineQueueItem]:
        with self._lock:
            for item in self.queue:
                if item.status == ItemStatus.PENDING:
                    return item
        return None

    def _process_item(self, item: OnlineQueueItem):
        try:
            item.status = ItemStatus.PROCESSING
            item.started_at = datetime.now()
            with self._lock:
                self.processing = item
            self._notify(item, "processing")

            if self._collect_fn:
                result = self._collect_fn(item.source, item.item_type)
            else:
                result = None

            if result:
                item.product_id = result.get('product_id')
                item.product_title = result.get('product_title', '')
                item.main_images = result.get('main_images', [])
                item.color_images = result.get('color_images', [])
                item.detail_images = result.get('detail_images', [])
                item.videos = result.get('videos', [])
                item.extended_data = result.get('extended_data', {})

                if self._save_fn:
                    self._save_fn(result)

                item.status = ItemStatus.COMPLETED
                item.completed_at = datetime.now()
                with self._lock:
                    self.completed.append(item)
                    if item in self.queue:
                        self.queue.remove(item)
                self._notify(item, "completed")
            else:
                raise Exception("采集无数据")

        except Exception as e:
            item.status = ItemStatus.FAILED
            item.error_message = str(e)
            item.retry_count += 1

            if item.retry_count < self.MAX_RETRY:
                item.status = ItemStatus.PENDING
                self._notify(item, "retrying")
            else:
                with self._lock:
                    self.failed.append(item)
                    if item in self.queue:
                        self.queue.remove(item)
                self._notify(item, "failed")

        finally:
            with self._lock:
                self.processing = None

    def clear_completed(self):
        with self._lock:
            self.completed.clear()
        self._notify(event="cleared_completed")

    def clear_failed(self):
        with self._lock:
            for item in self.failed:
                item.status = ItemStatus.PENDING
                item.retry_count = 0
                self.queue.append(item)
            self.failed.clear()
        self._notify(event="retried_failed")

    def clear_all(self):
        with self._lock:
            self.queue.clear()
            self.completed.clear()
            self.failed.clear()
            self.processing = None
        self._stop_event.set()
        self._notify(event="cleared_all")

    def get_queue_status(self) -> Dict:
        with self._lock:
            pending = sum(1 for item in self.queue if item.status == ItemStatus.PENDING)
            processing = 1 if self.processing else 0
            completed = len(self.completed)
            failed = len(self.failed)
            total = len(self.queue) + completed + failed + processing
        return {
            'pending': pending,
            'processing': processing,
            'completed': completed,
            'failed': failed,
            'total': total,
        }

    def get_all_items(self) -> List[OnlineQueueItem]:
        with self._lock:
            items = []
            if self.processing:
                items.append(self.processing)
            items.extend(self.queue)
            items.extend(self.completed)
            items.extend(self.failed)
        return items

    @property
    def is_running(self):
        return self._worker_thread is not None and self._worker_thread.is_alive() and not self._pause_event.is_set()

    @property
    def is_paused(self):
        return self._pause_event.is_set()
