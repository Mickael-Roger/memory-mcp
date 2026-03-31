from .config import load_config
from .tools import mcp


def main():
    load_config()
    mcp.run()


if __name__ == "__main__":
    main()
