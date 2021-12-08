import errno
import os
import sys


def main():
    "Main"
    args = len(sys.argv)
    if args == 2:
        path = os.path.abspath(sys.argv[1])
        for root, _, files in os.walk(path):
            for file in files:
                if file.startswith("."):
                    try:
                        filename = os.path.join(root, file)
                        print(f"Deleting {os.path.abspath(filename)}")
                        os.remove(os.path.abspath(filename))
                    except OSError as e:
                        if e.errno != errno.ENOENT:
                            raise
    else:
        print("Not enough parameters: python3 remove_trash_files.py PATH")


if __name__ == "__main__":
    main()
