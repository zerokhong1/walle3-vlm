"""walle_terminal — Entry point for the WallE TUI.

Invoked as: ros2 run walle_demo walle_terminal
Or directly: python -m walle_demo.walle_terminal
"""

from walle_demo.terminal.app import main

if __name__ == "__main__":
    main()
