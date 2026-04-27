# Backward-compatibility shim.
# The application entry point is now `agent_fix.py`.
# Run:  python agent_fix.py fix --target-dir ./broken_app
from agent_fix import main

if __name__ == "__main__":
    main()