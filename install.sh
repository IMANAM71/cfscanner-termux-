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

# pip upgrade removed - Termux manages it via pkg
# No need for pip install --upgrade pip

echo "Installing Python libraries..."
pip install requests icmplib -q

mkdir -p "$INSTALL_DIR" "$BIN_DIR"

echo "Downloading main script..."
curl -fsSL https://raw.githubusercontent.com/IMANAM71/cfscanner-termux-/main/scanner.py -o "$INSTALL_DIR/scanner.py"

chmod +x "$INSTALL_DIR/scanner.py"

cat > "$BIN_DIR/$SCRIPT_NAME" << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
python \( HOME/.cfscan/scanner.py " \)@"
EOF

chmod +x "$BIN_DIR/$SCRIPT_NAME"

# Create sample ip.txt if not exists
if [ ! -f "ip.txt" ]; then
    echo "ip.txt not found → copying default sample..."
    curl -fsSL https://raw.githubusercontent.com/IMANAM71/cfscanner-termux-/main/ip.txt.example -o "ip.txt"
    echo "ip.txt created with suggested ranges."
    echo "You can edit it with: nano ip.txt"
else
    echo "ip.txt already exists → using your version."
fi

echo ""
echo "Installation completed successfully."
echo "Run with:   cfscan"
echo ""
echo "Make sure ip.txt is in current directory (or use the sample created)"
echo "Update script: bash <(curl -fsSL https://raw.githubusercontent.com/IMANAM71/cfscanner-termux-/main/install.sh)"
echo ""
