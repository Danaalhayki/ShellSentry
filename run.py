#!/usr/bin/env python3
"""
Simple script to run the ShellSentry application
"""
from app import app

if __name__ == '__main__':
    print("=" * 60)
    print("ShellSentry - LLM-to-Bash Secure Command Execution")
    print("=" * 60)
    print("\nStarting application...")
    print("Default admin credentials:")
    print("  Username: admin")
    print("  Password: admin123")
    print("\n⚠️  IMPORTANT: Change the default password after first login!")
    print("\nApplication will be available at: http://localhost:5000")
    print("=" * 60)
    print()
    
    app.run(debug=True, host='0.0.0.0', port=5000)

