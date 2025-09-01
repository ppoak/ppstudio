import subprocess


def main():
    subprocess.call(["litellm", "--config", "litellm.yaml"])


if __name__ == "__main__":
    main()
