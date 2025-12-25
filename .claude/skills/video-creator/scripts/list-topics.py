import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../..'))
from scripts.controllers.utils.system_io_controller import system_io

def list_topics_with_video_status():
    outputs_dir = "Outputs"

    if not system_io.exists(outputs_dir):
        return []

    directories = system_io.list_directories(outputs_dir)
    topics_with_status = []

    for directory in directories:
        status_file_path = os.path.join(outputs_dir, directory, "video-status.json")
        if system_io.exists(status_file_path):
            topics_with_status.append(directory)

    return topics_with_status

if __name__ == "__main__":
    topics = list_topics_with_video_status()
    for topic in topics:
        print(topic)
