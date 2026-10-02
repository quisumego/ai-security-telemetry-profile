# The demo GIF at the top of README.md: two report commands that reproduce the
# attack corpus result and the headline verdict from the committed captures.
# Ruled at M8 (spec/rulings.py, rulings 22 to 24).
#
# Render from the repository root with `vhs docs/demo.tape`, and never publish
# it. The prompt and the working directory are set inside the tape, by a hidden
# first command that names no path, so no username, host name or home path can
# appear in a frame. Every command is a report command: neither form of
# detect.evaluate appears, and no line that names a holdout figure.

Output docs/demo.gif

Require git

Set Shell "bash"
Set FontSize 16
Set Width 1280
Set Height 720
Set Padding 24
Set Framerate 25
Set TypingSpeed 40ms

Hide
Type `cd "$(git rev-parse --show-toplevel)" && PS1='$ ' && clear`
Enter
Sleep 1s
Show

Sleep 500ms
Type ".venv/bin/python -m attacks.report"
Sleep 300ms
Enter
Sleep 6s

Type "clear"
Enter
Sleep 300ms
Type `.venv/bin/python -m ablation.matrix | sed -n '/^[*][*]Headline/p; /^| Required field/,/^$/p'`
Sleep 300ms
Enter
Sleep 7s
