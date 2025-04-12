import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.app import Application

if __name__ == "__main__":
    app = Application()
    app.run()