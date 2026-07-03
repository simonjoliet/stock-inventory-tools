#!/bin/bash
cd "$(dirname "$0")" || exit 1

find_python_with_module() {
  module="$1"
  for python in \
    /opt/homebrew/bin/python3.11 \
    /usr/local/bin/python3.11 \
    python3.11 \
    /opt/homebrew/bin/python3 \
    /usr/local/bin/python3 \
    python3 \
    /usr/bin/python3
  do
    if command -v "$python" >/dev/null 2>&1 && "$python" -c "import $module" >/dev/null 2>&1; then
      printf '%s\n' "$python"
      return 0
    fi
  done
  return 1
}

GUI_PYTHON="$(find_python_with_module tkinter)"
SCRIPT_PYTHON="$(find_python_with_module selenium)"

if [ -z "$GUI_PYTHON" ]; then
  echo "Could not find a Python install with Tkinter for the GUI."
  echo "Try installing Python from https://www.python.org/downloads/macos/"
  read -r -p "Press Return to close..."
  exit 1
fi

if [ -z "$SCRIPT_PYTHON" ]; then
  echo "Could not find a Python install with Selenium for the inventory scripts."
  echo "Install it with: python3 -m pip install selenium"
  read -r -p "Press Return to close..."
  exit 1
fi

export INVENTORY_SCRIPT_PYTHON="$SCRIPT_PYTHON"
export TK_SILENCE_DEPRECATION=1
"$GUI_PYTHON" inventory-gui.py
