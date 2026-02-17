#!/data/data/com.termux/files/usr/bin/bash
set -e

clear
echo -e "\033[1;36m"
echo "╔════════════════════════════════════════════╗"
echo "║     Cloudflare IP Scanner Installer        ║"
echo "║          Termux Optimized - 2025           ║"
echo "╚════════════════════════════════════════════╝"
echo -e "\033[0m"

if [[ ! -d "/data/data/com.termux" ]]; then
    echo -e "\033[1;31mاین اسکریپت فقط در Termux اجرا می‌شود!\033[0m"
    exit 1
fi

INSTALL_DIR="$HOME/.cfscan"
BIN_DIR="$HOME/.shortcuts"
SCRIPT_NAME="cfscan"

echo -e "\n\033[1;33mنصب پیش‌نیازها ...\033[0m"
pkg update -y && pkg upgrade -y >/dev/null 2>&1
pkg install python git -y >/dev/null 2>&1

pip install --upgrade pip -q
pip install requests icmplib -q

mkdir -p "$INSTALL_DIR" "$BIN_DIR"

echo -e "\033[1;33mدانلود اسکریپت اصلی ...\033[0m"
curl -fsSL https://raw.githubusercontent.com/IMANAM71/cf-ip-scanner-termux/main/scanner.py -o "$INSTALL_DIR/scanner.py"

chmod +x "$INSTALL_DIR/scanner.py"

cat > "$BIN_DIR/$SCRIPT_NAME" << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
python \( HOME/.cfscan/scanner.py " \)@"
EOF

chmod +x "$BIN_DIR/$SCRIPT_NAME"

echo -e "\n\033[1;32mنصب تمام شد ✓\033[0m"
echo -e "دستور اجرا:   \033[1;42m cfscan \033[0m"
echo -e "\nفایل ip.txt رو توی پوشه فعلی بساز"
echo -e "آپدیت دوباره: bash <(curl -fsSL https://raw.githubusercontent.com/IMANAM71/cfscanner-termux-/main/install.sh)"
