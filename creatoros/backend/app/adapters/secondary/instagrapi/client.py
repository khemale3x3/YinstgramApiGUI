from __future__ import annotations
from instagrapi import Client
from instagrapi.types import Media, User, UserShort

from app.core.domain.creator import Creator
from app.core.domain.post import CreatorPost
from app.core.ports.instagram import InstagramPort

MEDIA_TYPE_NAMES = {1: "photo", 2: "video", 8: "album"}


class InstagrapiAdapter(InstagramPort):
    """Driven adapter that implements `InstagramPort` using the instagrapi library.

    This is the only module in the codebase that talks to instagrapi directly.
    Instagram behavior can change independently of the library — anything on the
    other side of this adapter is not CreatorOS's concern.
    """

    def __init__(self) -> None:
        self._client = Client()
        self._client.set_locale("en_US")

    @property
    def username(self) -> str | None:
        return self._client.username

    # ------------------------------------------------------------------ auth
    def login(self, username: str, password: str) -> bool:
        return bool(self._client.login(username, password))

    def load_session(self, settings: dict | None) -> None:
        if settings:
            self._client.set_settings(dict(settings))

    def dump_session(self) -> dict:
        return self._client.get_settings()

    def verify_session(self) -> bool:
        try:
            self._client.account_info()
            return True
        except Exception:
            return False

    # ------------------------------------------------------------ lookups
    def get_profile(self, username: str) -> Creator:
        user: User = self._client.user_info_by_username(username)
        return Creator(
            pk=str(user.pk),
            username=user.username,
            full_name=user.full_name,
            biography=user.biography or "",
            external_url=str(user.external_url) if user.external_url else None,
            followers=user.follower_count,
            following=user.following_count,
            media_count=user.media_count,
            is_private=user.is_private,
            is_verified=user.is_verified,
            category=user.category or "",
        )

    def get_posts(self, username: str, amount: int = 10) -> list[CreatorPost]:
        user_id = self._client.user_id_from_username(username)
        medias: list[Media] = self._client.user_medias(user_id, amount=amount)
        return [self._to_post(media) for media in medias]

    def search_users(self, query: str, count: int = 20) -> list[dict]:
        results: list[UserShort] = self._client.search_users_v1(query, count=int(count))
        out: list[dict] = []
        for user in results[:count]:
            followers = getattr(user, "follower_count", None) or 0
            out.append(
                {
                    "pk": str(getattr(user, "pk", "") or ""),
                    "username": getattr(user, "username", "") or "",
                    "full_name": getattr(user, "full_name", "") or "",
                    "biography": "",
                    "external_url": str(getattr(user, "external_url", "") or "") or None,
                    "followers": int(followers),
                    "following": 0,
                    "media_count": int(getattr(user, "media_count", None) or 0),
                    "is_private": bool(getattr(user, "is_private", False)),
                    "is_verified": bool(getattr(user, "is_verified", False)),
                    "category": "",
                    "profile_pic_url": str(getattr(user, "profile_pic_url", "") or ""),
                }
            )
        return out

    def get_network(self, username: str, direction: str, amount: int = 100) -> list[dict]:
        user_id = self._client.user_id_from_username(username)
        fetch = self._client.user_followers if direction == "followers" else self._client.user_following
        users = fetch(user_id, amount=int(amount))
        return [{"pk": str(user.pk), "username": user.username, "full_name": user.full_name} for user in users]

    def execute_action(self, action: str, payload: dict) -> dict:
        if action == "insights":
            if payload.get("media_id"):
                result = self._client.insights_media(int(payload["media_id"]))
            else:
                result = self._client.insights_account()
            return {"action": action, "insights": result}
        if action == "publish_photo":
            media = self._client.photo_upload(payload["path"], payload.get("caption", ""))
            return {"action": action, "media_id": str(media.pk), "code": media.code}
        if action == "publish_video":
            media = self._client.video_upload(payload["path"], payload.get("caption", ""))
            return {"action": action, "media_id": str(media.pk), "code": media.code}
        if action == "publish_album":
            media = self._client.album_upload(payload["paths"], payload.get("caption", ""))
            return {"action": action, "media_id": str(media.pk), "code": media.code}
        if action == "comment":
            comment = self._client.media_comment(payload["media_id"], payload["text"])
            return {"action": action, "comment_id": str(comment.pk), "text": comment.text}
        if action == "comments":
            comments = self._client.media_comments(payload["media_id"], amount=int(payload.get("limit", 50)))
            return {"action": action, "comments": [{"id": str(item.pk), "text": item.text, "user": item.user.username} for item in comments]}
        if action == "direct_send":
            thread = self._client.direct_send(payload["text"], user_ids=[int(payload["user_id"])])
            return {"action": action, "thread_id": str(thread.thread_id)}
        if action == "hashtag_info":
            return {"action": action, "hashtag": self._client.hashtag_info(payload["hashtag"]).dict()}
        if action in ("hashtag_recent", "hashtag_top"):
            method = self._client.hashtag_medias_recent if action == "hashtag_recent" else self._client.hashtag_medias_top
            medias = method(payload["hashtag"], amount=int(payload.get("limit", 25)))
            return {"action": action, "media": [{"id": str(item.pk), "code": item.code, "caption": item.caption_text or ""} for item in medias]}
        raise ValueError(f"unsupported Instagram action: {action}")

    @staticmethod
    def _to_post(media: Media) -> CreatorPost:
        location = getattr(media, "location", None)
        return CreatorPost(
            pk=str(media.pk),
            shortcode=media.code,
            media_type=MEDIA_TYPE_NAMES.get(media.media_type, "unknown"),
            taken_at=media.taken_at.isoformat() if media.taken_at else None,
            caption=media.caption_text or "",
            likes=media.like_count,
            comments=media.comment_count or 0,
            plays=media.play_count or 0,
            views=media.view_count or 0,
            thumbnail_url=str(media.thumbnail_url) if media.thumbnail_url else None,
            video_url=str(media.video_url) if media.video_url else None,
            location=location.name if location else None,
        )