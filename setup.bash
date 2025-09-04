pip install --break-system-packages --root-user-action=ignore -r requirements.txt beautifulsoup4

if [[ "$PREFIX" == *"com.termux"* ]] || [[ -d "$PREFIX" && "$PREFIX" == "/data/data/com.termux/files/usr" ]]; then
    INSTALL_DIR="$PREFIX/bin"
    SCRIPT_NAME="PhMScRaper"
else
    INSTALL_DIR="/usr/local/bin"
    SCRIPT_NAME="PhMScRaper"
fi

if [ ! -f "PhMScRaper.py" ]; then
    echo -e "\e[31mError: PhMScRaper.py not found in current directory\e[0m"
    exit 1
fi

if [[ "$PREFIX" != *"com.termux"* ]]; then
    if [ "$EUID" -ne 0 ]; then
        echo -e "\e[31mError: Please run PhMScRaper as root (use sudo)\e[0m"
        exit 1
    fi
fi
cp PhMScRaper.py "$INSTALL_DIR/PhMScRaper.py"
chmod +x "$INSTALL_DIR/PhMScRaper.py"
cat > "$INSTALL_DIR/$SCRIPT_NAME" << EOF
#!/bin/bash
SCRIPT_DIR="\$(dirname "\$(readlink -f "\$0")")"
python3 "\$SCRIPT_DIR/PhMScRaper.py" "\$@"
EOF
if [[ "$PREFIX" == *"com.termux"* ]]; then
    sed -i 's|\$SCRIPT_DIR/PhMScRaper.py|'"$PREFIX"'/bin/PhMScRaper.py|g' "$INSTALL_DIR/$SCRIPT_NAME"
fi
chmod +x "$INSTALL_DIR/$SCRIPT_NAME"
echo -e "\e[32mInstallation completed successfully!\e[0m"
echo -e "\e[32mYou can now use: $SCRIPT_NAME -f websites.txt -o database\e[0m"
