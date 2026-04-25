import json
from src.utils.redis_client import get_redis
from src.utils.logger import get_logger

logger = get_logger(__name__)

ASSIGNMENT_TTL = 3600  # 1 hour
EXPERIMENT_TTL = 300   # 5 minutes


def assignment_key(user_id: str, experiment_name: str) -> str:
    return f"assignment:{user_id}:{experiment_name}"


def experiment_key(experiment_name: str) -> str:
    return f"experiment:{experiment_name}"


def get_cached_assignment(user_id: str, experiment_name: str) -> dict | None:
    redis = get_redis()
    key = assignment_key(user_id, experiment_name)
    try:
        data = redis.get(key)
        if data:
            logger.info("Cache HIT for assignment", extra={
                "user_id": user_id,
                "experiment": experiment_name
            })
            return json.loads(data)
        logger.info("Cache MISS for assignment", extra={
            "user_id": user_id,
            "experiment": experiment_name
        })
        return None
    except Exception as e:
        logger.error(f"Redis get failed: {e}")
        return None


def set_cached_assignment(user_id: str, experiment_name: str, result: dict) -> None:
    redis = get_redis()
    key = assignment_key(user_id, experiment_name)
    try:
        redis.setex(key, ASSIGNMENT_TTL, json.dumps(result))
        logger.info("Assignment cached", extra={
            "user_id": user_id,
            "experiment": experiment_name
        })
    except Exception as e:
        logger.error(f"Redis set failed: {e}")


def invalidate_assignment(user_id: str, experiment_name: str) -> None:
    redis = get_redis()
    key = assignment_key(user_id, experiment_name)
    try:
        redis.delete(key)
        logger.info("Assignment cache invalidated", extra={
            "user_id": user_id,
            "experiment": experiment_name
        })
    except Exception as e:
        logger.error(f"Redis delete failed: {e}")


def invalidate_experiment(experiment_name: str) -> None:
    """Invalidate all assignments for an experiment when it's updated."""
    redis = get_redis()
    pattern = f"assignment:*:{experiment_name}"
    try:
        keys = redis.keys(pattern)
        if keys:
            redis.delete(*keys)
            logger.info("Experiment cache invalidated", extra={
                "experiment": experiment_name,
                "keys_deleted": len(keys)
            })
    except Exception as e:
        logger.error(f"Redis invalidate failed: {e}")
