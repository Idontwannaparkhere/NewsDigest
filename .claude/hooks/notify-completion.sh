# ~/.claude/hooks/notify-completion.sh
#!/bin/bash

# 根据操作系统选择通知方式
OS=$(uname -s)

case "$OS" in
    Darwin)  # macOS
        osascript -e 'display notification "任务完成" with title "Claude Code"'
        ;;
    Linux)
        notify-send "Claude Code" "✅ 任务完成"
        afplay /System/Library/Sounds/Glass.aiff

        ;;
    *)
        echo "Unsupported OS: $OS"
        ;;
esac

exit 0
