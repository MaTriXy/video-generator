from scripts.controllers.manifest_controller import ManifestController


def list_deployed_videos():
    controller = ManifestController()
    videos = controller.get_deployed_videos()
    if videos:
        print('Deployed videos:')
        for i, url in enumerate(videos, 1):
            print(f'  {i}. {url}')
    else:
        print('No deployed videos found. Use /create-video command to generate videos')


if __name__ == "__main__":
    list_deployed_videos()
