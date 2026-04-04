# ~/.claude/hooks/notify-interaction.sh
#!/bin/bash

# 根据操作系统选择通知方式
OS=$(uname -s)
PROJECT_NAME=$(basename "$PWD")

case "$OS" in
    Darwin)  # macOS
        osascript -e "display notification \"项目: $PROJECT_NAME\" with title \"🤔 Claude Code - 需要交互\""
        afplay /System/Library/Sounds/Glass.aiff

        ;;
    Linux)
        notify-send "🤔 Claude Code - 需要交互" "项目: $PROJECT_NAME"
        ;;
    *)
        echo "Unsupported OS: $OS"
        ;;
esac

exit 0
