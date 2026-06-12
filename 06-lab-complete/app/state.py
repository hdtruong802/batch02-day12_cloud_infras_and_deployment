"""Shared runtime state for FastAPI app."""
import os
import time
import uuid

start_time = time.time()
is_ready = False
request_count = 0
error_count = 0
instance_id = os.getenv("INSTANCE_ID", f"instance-{uuid.uuid4().hex[:6]}")
