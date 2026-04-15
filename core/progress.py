"""
Progress tracking module for background operations
"""

global_progress = {
    "status": "idle", # "idle", "indexing", "embedding"
    "message": "System ready.",
    "progress": 0.0
}

def set_progress(status: str, message: str, progress: float):
    global_progress["status"] = status
    global_progress["message"] = message
    global_progress["progress"] = progress
