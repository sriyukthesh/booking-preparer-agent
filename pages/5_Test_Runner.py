import streamlit as st
import subprocess
import os
import json
import sys
from pathlib import Path

st.set_page_config(page_title="Test Runner", layout="wide")
st.title("Official Test Cases Runner")

st.markdown("""
This page runs the automated CLI test suite (`tests/run_testcases.py`) which tests the Agent Graph against the mock site under 4 specific conditions.
""")

if st.button("Run All 4 Official Test Cases", type="primary"):
    with st.spinner("Running test cases in background... This takes about 10-15 seconds."):
        project_root = Path(__file__).resolve().parent.parent
        result = subprocess.run(
            [sys.executable, str(project_root / "tests" / "run_testcases.py")],
            capture_output=True,
            text=True,
            cwd=project_root,
            check=False,
        )
        
        st.text("CLI Output:")
        st.code(result.stdout)
        if result.returncode != 0:
            st.error(f"Test runner exited with status {result.returncode}.")
            st.code(result.stderr)
            st.stop()
        
        if os.path.exists("test_results.json"):
            with open("test_results.json", "r") as f:
                data = json.load(f)
                st.success("Test Results JSON Generated!")
                st.json(data)