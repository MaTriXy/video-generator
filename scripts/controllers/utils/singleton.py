from threading import RLock
from typing import Dict, Any, Type


class SingletonMeta(type):
    """Thread-safe Singleton metaclass with reentrant lock."""
    _instances: Dict[Type, Any] = {}
    _lock: RLock = RLock()  # Use RLock to allow reentrant locking

    def __call__(cls, *args, **kwargs):
        # Fast path: if instance already exists, return it
        if cls in cls._instances:
            return cls._instances[cls]

        # Slow path: need to create instance
        with cls._lock:
            # Double-check after acquiring lock
            if cls not in cls._instances:
                # Create the instance
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance

        return cls._instances[cls]