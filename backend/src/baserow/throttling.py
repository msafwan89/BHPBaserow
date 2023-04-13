from uuid import uuid4

from django.conf import settings

from django_redis import get_redis_connection
from loguru import logger
from opentelemetry import trace
from rest_framework.throttling import SimpleRateThrottle

from baserow.core.telemetry.utils import baserow_trace_methods

BASEROW_CONCURRENCY_THROTTLE_REQUEST_ID = "baserow_concurrency_throttle_request_id"

tracer = trace.get_tracer(__name__)

# Slightly modified version of
# https://gist.github.com/ptarjan/e38f45f2dfe601419ca3af937fff574d
incr_concurrent_requests_count_if_allowed_lua_script = """
local key = KEYS[1]

local max_concurrent_requests = tonumber(ARGV[1])
local timestamp = tonumber(ARGV[2])
local request_id = ARGV[3]
local timeout = tonumber(ARGV[4])
local old_request_cutoff = timestamp - timeout
local wait = 0

local count = redis.call("zcard", key)
local allowed = count < max_concurrent_requests

if not allowed then
  -- If we failed then try to expire any old requests that might still be running and try again
  -- We don't always call "zremrangebyscore" to speed up the normal path that doesn't get throttled.
  local num_removed = redis.call("zremrangebyscore", key, 0, old_request_cutoff)
  count = count - num_removed
  allowed = count < max_concurrent_requests
end

if allowed then
  redis.call("zadd", key, timestamp, request_id)
else
    local first = redis.call("zrange", key, 0, 0, "WITHSCORES")
    wait = tonumber(first[2]) - old_request_cutoff
end

return { allowed, count, wait }
"""


def _get_redis_cli():
    return get_redis_connection("default")


class ConcurrentUserRequestsThrottle(
    SimpleRateThrottle, metaclass=baserow_trace_methods(tracer)
):
    """
    Limits the number of concurrent requests made by a given user.
    """

    scope = "concurrent_user_requests"
    redis_cli = None

    def __new__(cls, *args, **kwargs):
        if cls.redis_cli is None:
            cls._init_redis_cli()
        return super().__new__(cls, *args, **kwargs)

    @classmethod
    def _init_redis_cli(cls):
        cls.redis_cli = _get_redis_cli()
        cls.incr_concurrent_requests_count_if_allowed = cls.redis_cli.register_script(
            incr_concurrent_requests_count_if_allowed_lua_script
        )

    @classmethod
    def _log(cls, request, log_msg, request_id=None, *args, **kwargs):
        logger.debug(
            "{{path={path},user_id={user_id},req_id={request_id}}} %s" % log_msg,
            *args,
            path=request.path,
            user_id=request.user.id if request.user.is_authenticated else None,
            request_id=str(request_id),
            **kwargs,
        )

    def parse_rate(self, rate):
        duration = settings.BASEROW_CONCURRENT_USER_REQUESTS_THROTTLE_TIMEOUT
        return int(rate), duration

    @classmethod
    def get_cache_key(cls, request, view=None):
        user = request.user
        if user.is_authenticated and not user.is_staff:
            return cls.cache_format % {
                "scope": cls.scope,
                "ident": request.user.id,
            }

        if not user.is_authenticated:
            cls._log(request, "ALLOWING: not throttling anonymous users")
        elif user.is_staff:
            cls._log(request, "ALLOWING: not throttling staff users")

        return None

    def allow_request(self, request, view):
        if self.num_requests <= 0:
            self._log(
                request,
                "ALLOWING: throttling disabled as 'BASEROW_MAX_CONCURRENT_USER_REQUESTS' <= 0",
            )
            return True

        if (key := self.get_cache_key(request)) is None:
            return True

        self.key = key
        limit = self.num_requests
        self.timestamp = timestamp = self.timer()
        request_id = str(uuid4())

        args = [limit, timestamp, request_id, self.duration]
        allowed, count, wait = self.incr_concurrent_requests_count_if_allowed(
            [key], args
        )

        if allowed:
            django_request = getattr(request, "_request")
            setattr(django_request, BASEROW_CONCURRENCY_THROTTLE_REQUEST_ID, request_id)
            log_msg = "ALLOWING: as count={count} < limit={limit}"
        else:
            self._wait = wait
            log_msg = "DENYING: as count={count} >= limit={limit}. Wait {wait} secs"

        self._log(
            request, log_msg, request_id=request_id, count=count, limit=limit, wait=wait
        )

        return bool(allowed)

    @classmethod
    def on_request_processed(cls, request):
        request_id = getattr(request, BASEROW_CONCURRENCY_THROTTLE_REQUEST_ID, None)

        if request_id is not None and (key := cls.get_cache_key(request)):
            cls._log(request, "UNTRACKING: request has finished", request_id=request_id)
            cls.redis_cli.zrem(key, request_id)

    def wait(self):
        return self._wait
