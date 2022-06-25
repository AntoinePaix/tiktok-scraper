import argparse

from downloader import run

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("user", help="Tiktok User Name", type=str)
    args = parser.parse_args()
    user = args.user.lower()
    run(user)
