#!/data/data/com.termux/files/usr/bin/bash
set -e

clear
echo "============================================"
echo "     Cloudflare IP Scanner Installer       "
echo "          Termux Optimized - 2025          "
echo "============================================"

if [[ ! -d "/data/data/com.termux" ]]; then
    echo "This script runs only in Termux!"
    exit 1
fi

INSTALL_DIR="$HOME/.cfscan"
BIN_DIR="$HOME/.shortcuts"
SCRIPT_NAME="cfscan"

echo "Updating packages and installing prerequisites..."
pkg update -y && pkg upgrade -y >/dev/null 2>&1
pkg install python git -y >/dev/null 2>&1

echo "Installing required Python libraries..."
pip install requests icmplib -q

mkdir -p "$INSTALL_DIR" "$BIN_DIR"

echo "Downloading main scanner script..."
curl -fsSL https://raw.githubusercontent.com/IMANAM71/cfscanner-termux-/main/scanner.py -o "$INSTALL_DIR/scanner.py"

chmod +x "$INSTALL_DIR/scanner.py"

echo "Creating shortcut command..."
cat > "$BIN_DIR/$SCRIPT_NAME" << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
python \( HOME/.cfscan/scanner.py " \)@"
EOF

chmod +x "$BIN_DIR/$SCRIPT_NAME"

# Handle ip.txt sample
if [ ! -f "ip.txt" ]; then
    echo "ip.txt not found → copying your sample from repo..."
    curl -fsSL https://raw.githubusercontent.com/IMANAM71/cfscanner-termux-/main/ip.txt -o "ip.txt"
    echo "ip.txt created with your suggested ranges."
    echo "You can edit it anytime: nano ip.txt"
else
    echo "ip.txt already exists in current directory → using your version."
fi

echo ""
echo "Installation completed successfully ✓"
echo "Run the tool with:   cfscan"
echo ""
echo "Important: Make sure ip.txt is in your current working directory"
echo "To update later: bash <(curl -fsSL https://raw.githubusercontent.com/IMANAM71/cfscanner-termux-/main/install.sh)"
echo ""
