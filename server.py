import sys
import runpy
import os

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    runpy.run_path("시스템_관리_서버.py", run_name="__main__")
