import logging
from copy import deepcopy
from typing import Optional
from urllib.parse import urlparse

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from instagrapi.instinx.account import AccountMixin
from instagrapi.instinx.album import DownloadAlbumMixin, UploadAlbumMixin
from instagrapi.instinx.attestation import DeviceAttestationMixin
from instagrapi.instinx.auth import LoginMixin
from instagrapi.instinx.bloks import BloksMixin
from instagrapi.instinx.challenge import ChallengeResolveMixin
from instagrapi.instinx.clip import ClipMixin, DownloadClipMixin, UploadClipMixin
from instagrapi.instinx.collection import CollectionMixin
from instagrapi.instinx.comment import CommentMixin
from instagrapi.instinx.crossposting import CrossPostingMixin
from instagrapi.instinx.direct import DirectMixin
from instagrapi.instinx.explore import ExploreMixin
from instagrapi.instinx.fbsearch import FbSearchMixin
from instagrapi.instinx.fundraiser import FundraiserMixin
from instagrapi.instinx.graphql import PrivateGraphQLRequestMixin
from instagrapi.instinx.hashtag import HashtagMixin
from instagrapi.instinx.highlight import HighlightMixin
from instagrapi.instinx.igtv import DownloadIGTVMixin, UploadIGTVMixin
from instagrapi.instinx.insights import InsightsMixin
from instagrapi.instinx.location import LocationMixin
from instagrapi.instinx.media import MediaMixin
from instagrapi.instinx.multiple_accounts import MultipleAccountsMixin
from instagrapi.instinx.note import NoteMixin
from instagrapi.instinx.notification import NotificationMixin
from instagrapi.instinx.password import PasswordMixin
from instagrapi.instinx.photo import DownloadPhotoMixin, UploadPhotoMixin
from instagrapi.instinx.private import PrivateRequestMixin
from instagrapi.instinx.public import (
    ProfilePublicMixin,
    PublicRequestMixin,
    TopSearchesPublicMixin,
)
from instagrapi.instinx.quicksnap import QuickSnapMixin
from instagrapi.instinx.realtime import RealtimeMixin
from instagrapi.instinx.share import ShareMixin
from instagrapi.instinx.signup import SignUpMixin
from instagrapi.instinx.story import StoryMixin
from instagrapi.instinx.timeline import ReelsMixin
from instagrapi.instinx.totp import TOTPMixin
from instagrapi.instinx.track import TrackMixin
from instagrapi.instinx.user import UserMixin
from instagrapi.instinx.video import DownloadVideoMixin, UploadVideoMixin

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Used as fallback logger if another is not provided.
DEFAULT_LOGGER = logging.getLogger("instagrapi")


class Client(
    PublicRequestMixin,
    ChallengeResolveMixin,
    PrivateRequestMixin,
    PrivateGraphQLRequestMixin,
    CrossPostingMixin,
    TopSearchesPublicMixin,
    ProfilePublicMixin,
    LoginMixin,
    ShareMixin,
    TrackMixin,
    FbSearchMixin,
    HighlightMixin,
    DownloadPhotoMixin,
    UploadPhotoMixin,
    DownloadVideoMixin,
    UploadVideoMixin,
    DownloadAlbumMixin,
    NotificationMixin,
    UploadAlbumMixin,
    DownloadIGTVMixin,
    UploadIGTVMixin,
    MediaMixin,
    UserMixin,
    InsightsMixin,
    CollectionMixin,
    AccountMixin,
    DirectMixin,
    LocationMixin,
    HashtagMixin,
    CommentMixin,
    StoryMixin,
    PasswordMixin,
    SignUpMixin,
    ClipMixin,
    DownloadClipMixin,
    UploadClipMixin,
    ReelsMixin,
    ExploreMixin,
    DeviceAttestationMixin,
    BloksMixin,
    TOTPMixin,
    MultipleAccountsMixin,
    NoteMixin,
    QuickSnapMixin,
    FundraiserMixin,
    RealtimeMixin,
):
    proxy = None

    def __init__(
        self,
        settings: Optional[dict] = None,
        proxy: Optional[str] = None,
        delay_range: Optional[list] = None,
        logger=DEFAULT_LOGGER,
        override_app_version: bool = False,
        **kwargs,
    ):
        self.tls_verify = kwargs.pop("tls_verify", True)
        self.request_timeout = kwargs.pop("request_timeout", 1)
        self.public_request_retries_count = kwargs.pop("public_request_retries_count", 3)
        self.public_request_retries_timeout = kwargs.pop("public_request_retries_timeout", 2)
        self.session_retry_total = kwargs.pop("session_retry_total", 3)
        self.session_retry_backoff_factor = kwargs.pop("session_retry_backoff_factor", 2)
        self.session_retry_statuses = list(kwargs.pop("session_retry_statuses", [429, 500, 502, 503, 504]))
        self.timezone_offset = kwargs.pop("timezone_offset", -14400)
        self.timezone_name = kwargs.pop("timezone_name", "")
        self.push_disabled = kwargs.pop("push_disabled", True)

        super().__init__(**kwargs)

        self.settings = deepcopy(settings or {})
        self.override_app_version = override_app_version
        self.logger = logger
        self.delay_range = delay_range

        self.set_proxy(proxy)

        self.init()

    def set_proxy(self, dsn: Optional[str]):
        if dsn:
            assert isinstance(dsn, str), f'Proxy must been string (URL), but now "{dsn}" ({type(dsn)})'
            self.proxy = dsn
            proxy_href = "{scheme}{href}".format(
                scheme="http://" if not urlparse(self.proxy).scheme else "",
                href=self.proxy,
            )
            proxies = {
                "http": proxy_href,
                "https": proxy_href,
            }
            self.public.proxies = self.private.proxies = proxies
            if hasattr(self, "graphql"):
                self.graphql.proxies = proxies
            return True
        self.public.proxies = self.private.proxies = {}
        if hasattr(self, "graphql"):
            self.graphql.proxies = {}
        return False
