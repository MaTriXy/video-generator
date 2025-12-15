import argparse
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.controllers.git_controller import git_controller
from scripts.logging_config import get_utility_logger, set_console_logging

set_console_logging()
logger = get_utility_logger('GitCheckout')

REPO_URL = "https://github.com/outscal/video-output.git"
OUTPUTS_DIR = os.path.join(project_root, "Outputs")


def main():
    parser = argparse.ArgumentParser(description='Checkout Outputs repository to specified branch')
    parser.add_argument('--branch', required=True, help='Branch name to checkout')
    args = parser.parse_args()

    branch_name = args.branch

    logger.info("=" * 60)
    logger.info("Outputs Repository Checkout")
    logger.info("=" * 60)
    logger.info(f"Branch name: {branch_name}")

    success = git_controller.checkout_and_sync_branch(
        repo_path=OUTPUTS_DIR,
        branch_name=branch_name,
        repo_url=REPO_URL,
        clone_if_missing=True
    )

    if success:
        logger.info("=" * 60)
        logger.info("Outputs Repository Checkout Complete!")
        logger.info("=" * 60)
        logger.info(f"You are now on branch '{branch_name}' in the Outputs folder")
        sys.exit(0)
    else:
        logger.error("=" * 60)
        logger.error("Checkout Failed!")
        logger.error("=" * 60)
        logger.error(f"Failed to checkout to branch '{branch_name}'")
        sys.exit(1)


if __name__ == "__main__":
    main()
