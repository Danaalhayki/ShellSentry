#!/bin/bash
# Script to copy SSH public key to server (for Git Bash)

echo "=========================================="
echo "Copying SSH Public Key to Server"
echo "=========================================="
echo ""

# Try to find the public key
if [ -f ~/.ssh/id_rsa.pub ]; then
    PUBKEY_PATH=~/.ssh/id_rsa.pub
elif [ -f /c/Users/danah/.ssh/id_rsa.pub ]; then
    PUBKEY_PATH=/c/Users/danah/.ssh/id_rsa.pub
else
    echo "Error: Could not find id_rsa.pub"
    echo "Please check your SSH key location"
    exit 1
fi

echo "Found public key at: $PUBKEY_PATH"
echo ""
echo "Your public key:"
cat "$PUBKEY_PATH"
echo ""
echo "=========================================="
echo "Copying to server..."
echo "Password: hero"
echo "=========================================="
echo ""

cat "$PUBKEY_PATH" | ssh hero@192.168.56.101 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && chmod 700 ~/.ssh"

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "SUCCESS! SSH key copied to server."
    echo "=========================================="
    echo ""
    echo "Testing connection (should not ask for password)..."
    ssh hero@192.168.56.101 "echo 'SSH key authentication works!'"
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "=========================================="
        echo "SSH Key Authentication Setup Complete!"
        echo "=========================================="
    fi
else
    echo ""
    echo "Error: Failed to copy key. Please try manually."
fi

