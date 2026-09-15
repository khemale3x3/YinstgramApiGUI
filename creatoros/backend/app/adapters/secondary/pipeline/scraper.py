"""Selenium scraper adapter — a clean port of the user's iteration01scraper.py.

Implements ScraperPort. This is a self-contained conversation of the working
multi-session scraper: headless Chrome with a `sessionid` cookie per worker,
GraphQL profile/timeline capture over the performance network log, location
extraction, HD profile-picture download, per-username JSON output, and the
backup-session pool that recovers a worker when its active session is refused.
"""
from __future__ import annotations

import json
import os
import queue
import random
import re
import threading
import time
from pathlib import Path

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from app.core.domain.pipeline import ScrapeReport, ScrapeStats
from app.core.ports.scraper import ScraperPort

TIMELINE_KEY = "xdt_api__v1__feed__user_timeline_graphql_connection"

_stats_lock = threading.Lock()
_done_lock = threading.Lock()
_session_lock = threading.Lock()


def get_username(url: str) -> str:
    return url.strip().rstrip("/").split("/")[-1].split("?")[0]


def is_private_profile(profile_data) -> bool:
    if not profile_data:
        return False
    try:
        user_node = profile_data["data"]["user"]
        if isinstance(user_node, dict) and isinstance(user_node.get("data"), dict):
            user_node = user_node["data"]
        return bool(user_node.get("is_private", False))
    except (KeyError, TypeError, AttributeError):
        return False


def extract_location_data(node) -> dict | None:
    loc_data = node.get("location")
    if not loc_data:
        return None
    location = {
        "id": loc_data.get("pk") or loc_data.get("id"),
        "name": loc_data.get("name"),
        "lat": loc_data.get("lat") or loc_data.get("latitude"),
        "lng": loc_data.get("lng") or loc_data.get("longitude"),
        "address": loc_data.get("address"),
        "city": loc_data.get("city"),
        "short_name": loc_data.get("short_name"),
        "facebook_places_id": loc_data.get("facebook_places_id"),
    }
    return {k: v for k, v in location.items() if v is not None} or None


def process_graphql_response(response_body, config) -> dict:
    data = {"profile_info": None, "reel_info": None}
    if not isinstance(response_body, dict):
        return data
    response_data = response_body.get("data", {})
    if not isinstance(response_data, dict):
        return data

    PROFILE_KEYS = {
        "biography", "pk", "full_name", "follower_count",
        "following_count", "profile_pic_url", "username",
    }

    user_node = response_data.get("user")
    if isinstance(user_node, dict):
        candidate = user_node.get("data") if isinstance(user_node.get("data"), dict) else user_node
        if PROFILE_KEYS & set(candidate.keys()):
            data["profile_info"] = response_body

    WEB_PROFILE_KEY = "xdt_api__v1__users__web_profile_info"
    if not data["profile_info"] and WEB_PROFILE_KEY in response_data:
        inner = response_data[WEB_PROFILE_KEY]
        if isinstance(inner, dict):
            candidate = inner.get("data") if isinstance(inner.get("data"), dict) else inner
            if PROFILE_KEYS & set(candidate.keys()):
                data["profile_info"] = response_body

    if config.get("target_timeline", TIMELINE_KEY) in response_data:
        data["reel_info"] = response_body
    return data


def get_network_responses(driver):
    logs = driver.get_log("performance")
    responses = []
    for entry in logs:
        try:
            log_data = json.loads(entry["message"])["message"]
            if "Network.response" in log_data["method"] or "Network.responseReceived" in log_data["method"]:
                responses.append(log_data)
        except Exception:
            pass
    return responses


def merge_timeline_data(existing_data, new_data):
    if not existing_data:
        return new_data
    if not new_data:
        return existing_data
    try:
        timeline_key = TIMELINE_KEY
        existing_edges = existing_data["data"][timeline_key]["edges"]
        new_edges = new_data["data"][timeline_key]["edges"]
        existing_ids = {edge["node"]["id"] for edge in existing_edges}
        for edge in new_edges:
            if edge["node"]["id"] not in existing_ids:
                existing_edges.append(edge)
                existing_ids.add(edge["node"]["id"])
        existing_data["data"][timeline_key]["edges"] = existing_edges
        return existing_data
    except Exception:
        return existing_data


def scrape_profile(driver, url, max_posts: int, delay_range) -> dict:
    """Scrape one profile URL with enhanced scrolling."""
    username = get_username(url)
    combined = {"profile_info": None, "reel_info": None}
    posts_count = 0
    no_new = 0
    max_scroll_attempts = max(12, max_posts)

    try:
        driver.execute_cdp_cmd("Network.clearBrowserCache", {})
        driver.get("about:blank")
        driver.execute_cdp_cmd("Network.enable", {})
        driver.get(url)
        time.sleep(random.uniform(2.5, 3.5))

        for _ in range(max_scroll_attempts):
            try:
                for response in get_network_responses(driver):
                    try:
                        params = response.get("params", {})
                        response_entry = params.get("response", {})
                        response_url = response_entry.get("url", "")
                        if "graphql/query" not in response_url and "api/graphql" not in response_url:
                            continue
                        request_id = params.get("requestId")
                        if not request_id:
                            continue
                        try:
                            body = driver.execute_cdp_cmd(
                                "Network.getResponseBody", {"requestId": request_id}
                            )
                        except Exception:
                            continue
                        if body.get("base64Encoded"):
                            continue
                        response_body = json.loads(body.get("body", "{}"))
                        new_data = process_graphql_response(
                            response_body, {"target_timeline": TIMELINE_KEY}
                        )
                        if new_data["profile_info"]:
                            combined["profile_info"] = new_data["profile_info"]
                        if new_data["reel_info"]:
                            combined["reel_info"] = merge_timeline_data(
                                combined["reel_info"], new_data["reel_info"]
                            )
                    except Exception:
                        continue

                current = 0
                if combined["reel_info"]:
                    try:
                        current = len(
                            combined["reel_info"]["data"][TIMELINE_KEY]["edges"]
                        )
                    except Exception:
                        current = 0

                if current == posts_count:
                    no_new += 1
                    if no_new >= 3:
                        break
                else:
                    no_new = 0
                    posts_count = current
                if posts_count >= max_posts:
                    break

                driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
                time.sleep(random.uniform(*delay_range))
                if _ % 5 == 0:
                    driver.execute_script("window.scrollBy(0, -200);")
                    time.sleep(0.5)
                    driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            except Exception:
                break

        if combined["reel_info"]:
            try:
                for edge in combined["reel_info"]["data"][TIMELINE_KEY]["edges"]:
                    node = edge.get("node", {})
                    location = extract_location_data(node)
                    if location:
                        node["processed_location"] = location
            except Exception:
                pass
    except Exception:
        pass
    return combined


def download_profile_picture(username, profile_info, save_dir) -> bool:
    try:
        pic_url = None
        quality_suffix = ""
        try:
            user_data = profile_info["data"]["user"]
            if user_data.get("profile_pic_url_hd"):
                pic_url = user_data["profile_pic_url_hd"]
            elif user_data.get("hd_profile_pic_url_info", {}).get("url"):
                pic_url = user_data["hd_profile_pic_url_info"]["url"]
            elif user_data.get("profile_pic_url"):
                pic_url = user_data["profile_pic_url"]
            if pic_url:
                pic_url = re.sub(r"/s\d+x\d+/", "/s1080x1080/", pic_url)
        except (KeyError, TypeError):
            pic_url = None

        if not pic_url:
            return False

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36"
            ),
            "Referer": "https://www.instagram.com/",
        }
        response = requests.get(pic_url, stream=True, timeout=20, headers=headers)
        if response.status_code != 200:
            return False
        content_type = response.headers.get("content-type", "").lower()
        if "png" in content_type:
            ext = "png"
        elif "webp" in content_type:
            ext = "webp"
        else:
            ext = "jpg"
        file_path = os.path.join(save_dir, f"{username}{quality_suffix}.{ext}")
        with open(file_path, "wb") as fh:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    fh.write(chunk)
        if os.path.getsize(file_path) > 0:
            return True
        os.remove(file_path)
    except Exception:
        pass
    return False


def configure_driver(session_id, headless: bool, timeout: int):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-infobars")
    options.add_argument("--mute-audio")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.videos": 2,
    }
    options.add_experimental_option("prefs", prefs)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(timeout)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    driver.execute_cdp_cmd("Network.enable", {})
    driver.execute_cdp_cmd("Page.enable", {})
    if session_id:
        driver.get("https://www.instagram.com/")
        time.sleep(1.5)
        driver.add_cookie(
            {
                "name": "sessionid",
                "value": session_id,
                "domain": ".instagram.com",
                "path": "/",
                "secure": True,
                "httpOnly": True,
            }
        )
    return driver


class SeleniumScraperAdapter(ScraperPort):
    """Driven adapter implementing ScraperPort with the ported scraper."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or configure_driver

    def scrape(self, urls, output_dir, sessions, config, on_event=None, metadata_store=None):
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        start = time.time()
        stats = ScrapeStats(total=len(urls))
        failed_urls: list[str] = []
        done_urls: list[str] = []

        if config.test_mode:
            urls = urls[: config.max_test_profiles]
            stats.total = len(urls)

        if not urls:
            return ScrapeReport(stats=stats)

        sessions = sessions or []
        session_ids = list(sessions)
        active_limit = max(1, config.active_sessions) if session_ids else 0
        active = session_ids[:active_limit]
        backups = session_ids[active_limit:]
        _state = {"index": 0}

        def next_session():
            with _session_lock:
                chosen = active[_state["index"] % len(active)] if active else ""
                _state["index"] += 1
                return chosen

        def consume_backup():
            """Pop a backup session (if any) for a worker recovering from a ban."""
            with _session_lock:
                return backups.pop(0) if backups else None

        def emit(event_type, message="", **data):
            if on_event:
                try:
                    on_event(event_type, message, **data)
                except Exception:
                    pass

        def count_locations(data) -> int:
            if not data.get("reel_info"):
                return 0
            try:
                return sum(
                    1
                    for edge in data["reel_info"]["data"][TIMELINE_KEY]["edges"]
                    if edge.get("node", {}).get("processed_location")
                )
            except Exception:
                return 0

        def count_posts(data) -> int:
            if not data.get("reel_info"):
                return 0
            try:
                return len(data["reel_info"]["data"][TIMELINE_KEY]["edges"])
            except Exception:
                return 0

        def save_data(username, data, url, session_id) -> bool:
            with _done_lock:
                if url in done_urls:
                    return False
            if not data.get("profile_info") and not data.get("reel_info"):
                return False
            if is_private_profile(data.get("profile_info")):
                return False

            user_dir = output_dir / username
            user_dir.mkdir(parents=True, exist_ok=True)
            saved = False
            if data.get("profile_info"):
                (user_dir / "userInfo.json").write_text(
                    json.dumps(data["profile_info"], indent=4), encoding="utf-8"
                )
                saved = True
                if download_profile_picture(username, data["profile_info"], str(user_dir)):
                    with _stats_lock:
                        stats.pictures_downloaded += 1
            if data.get("reel_info"):
                (user_dir / "postInfo.json").write_text(
                    json.dumps(data["reel_info"], indent=4), encoding="utf-8"
                )
                with _stats_lock:
                    stats.posts_saved += count_posts(data)
                    stats.locations_found += count_locations(data)

            if metadata_store is not None:
                try:
                    metadata_store.save_profile(
                        username,
                        url,
                        data.get("profile_info") or {},
                        data.get("reel_info") or {},
                        stats.__dict__,
                    )
                except Exception:
                    pass

            if saved:
                with done_urls_lock_guard():
                    done_urls.append(url)
                emit(
                    "profile_saved",
                    f"saved @{username}",
                    username=username,
                    url=url,
                    session=session_id,
                )
            return saved

        def done_urls_lock_guard():
            return _done_lock

        def worker_thread(session_id, q):
            driver = None
            try:
                driver = self._session_factory(session_id, config.headless, config.timeout)
            except Exception as exc:
                backup = consume_backup()
                if backup:
                    emit("log", f"worker session failed, trying backup session: {exc}")
                    try:
                        driver = self._session_factory(backup, config.headless, config.timeout)
                    except Exception as exc2:
                        emit("log", f"backup session also failed: {exc2}")
                else:
                    emit("log", f"worker session failed, no backup available: {exc}")
                if driver is None:
                    return

            try:
                while True:
                    try:
                        url = q.get_nowait()
                    except queue.Empty:
                        break
                    try:
                        username = get_username(url)
                        emit("log", f"processing @{username} with session ...{session_id[-6:]}")
                        data = scrape_profile(driver, url, config.max_posts, config.delay_range)
                        ok = save_data(username, data, url, session_id)
                        if ok:
                            with _stats_lock:
                                stats.saved += 1
                        else:
                            with _stats_lock:
                                stats.failed += 1
                            with _done_lock:
                                failed_urls.append(url)
                            emit("profile_failed", f"failed/private @{username}", url=url)
                    except Exception as exc:
                        with _stats_lock:
                            stats.failed += 1
                        with _done_lock:
                            failed_urls.append(url)
                        emit("profile_failed", f"error processing {url}: {exc}", url=url)
                    finally:
                        q.task_done()
                        with _stats_lock:
                            processed = stats.saved + stats.failed
                        emit("progress", "progress", progress=processed / max(stats.total, 1) * 100)
            finally:
                try:
                    driver.quit()
                except Exception:
                    pass

        q = queue.Queue()
        for url in urls:
            q.put(url)

        max_workers = max(1, min(config.max_workers, len(active) or config.max_workers, len(urls)))
        threads = []
        for i in range(max_workers):
            sid = next_session()
            thread = threading.Thread(
                target=worker_thread, args=(sid, q), name=f"scraper-{i + 1}", daemon=True
            )
            thread.start()
            threads.append(thread)
            time.sleep(0.5)
        for thread in threads:
            thread.join(timeout=None)

        stats.elapsed_sec = time.time() - start
        emit("log", f"scraper finished: {stats.saved} saved, {stats.failed} failed "
                    f"in {stats.elapsed_sec:.1f}s")
        return ScrapeReport(stats=stats, failed_urls=failed_urls)