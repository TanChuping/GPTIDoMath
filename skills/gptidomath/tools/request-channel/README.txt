request-channel v2

Tested on Windows 11 + Google Drive for desktop + Python 3.12; other setups untested

Place channel.py, VERSION and this README in Drive's shared tools folder.
The coordinator copies them into the task's temporary ChatGPT sandbox.
Use Python 3 and a fresh REQUEST_CHANNEL_HOME for each task (default ~/.request-channel).

Run inside that sandbox:
  python3 channel.py --selftest
  python3 channel.py install --sandbox-home "$HOME"
  python3 channel.py record --version N --mtime '<Drive ISO-8601 modification time>'
  python3 channel.py due
  python3 channel.py status

Install writes the selected home's .request-channel/, Bash profiles and IPython startup.
Use install ONLY in a disposable remote sandbox, never in your regular local home.
Keep REQUEST_CHANNEL_HOME set for later commands if you choose a custom state directory.
For an existing Bash shell, activate the installed hook:
  export BASH_ENV="$HOME/.request-channel/bash_env.sh"
  . "$BASH_ENV"
For an existing IPython kernel:
  import runpy; from pathlib import Path
  runpy.run_path(str(Path.home()/'.request-channel/channel.py'))['register_ipython_hook'](get_ipython())
Adjust these paths when using a custom state directory.

Hooks remind at command/cell boundaries after 15 minutes; due also checks the local timer.
Follow PROMPT-BLOCK.md for request checks. If hooks fail, keep checking at task checkpoints.

This is a local reminder, not a Drive reader or a timer that interrupts a model.
Only the coordinator checks Drive; workers receive updates from the coordinator.
Use a fresh REQUEST_CHANNEL_HOME per task. The state records confirmed versions and
exact Drive modification times; same-version edits and version rollback are rejected.
Read UTF-8 with or without a BOM. Marker writes retry briefly when a sync client locks them.

Exit codes: 0 successful operation (due prints DUE/NOT_DUE), 1 failed selftest,
2 invalid CLI/state/record. install returns 0 even if optional hooks cannot be installed;
read its INSTALL result and use coordination checkpoints as the fallback.
An interruption has the interpreter's normal interrupt behavior.
