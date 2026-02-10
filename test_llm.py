#!/usr/bin/env python3
"""
Test script to diagnose LLM API connection issues
"""
from src.config import Config
from src.llm_client import LLMClient
import sys

def test_llm_connection():
    """Test LLM API connection and configuration"""
    print("=" * 60)
    print("ShellSentry LLM API Diagnostic Test")
    print("=" * 60)
    print()
    
    # Check configuration
    print("[*] Configuration Check:")
    print(f"  LLM_API_KEY: {'[OK] SET' if Config.LLM_API_KEY else '[ERROR] NOT SET'}")
    print(f"  LLM_API_BASE_URL: {Config.LLM_API_BASE_URL}")
    print(f"  LLM_MODEL: {Config.LLM_MODEL}")
    print(f"  LLM_API_TYPE: {Config.LLM_API_TYPE}")
    print()
    
    if not Config.LLM_API_KEY:
        print("[ERROR] LLM_API_KEY is not set in .env file!")
        print("   Please set LLM_API_KEY in your .env file")
        return False
    
    # Test LLM client
    print("[*] Testing LLM API Connection...")
    print()
    
    llm_client = LLMClient()
    test_prompt = "Show active network connections"
    
    print(f"Test prompt: '{test_prompt}'")
    print("Calling LLM API...")
    print()
    
    try:
        result = llm_client.generate_command(test_prompt)
        
        if result['success']:
            print("[SUCCESS] API call successful!")
            print(f"Generated command: {result['command']}")
            return True
        else:
            print("[FAILED] API call failed!")
            print(f"Error: {result.get('error', 'Unknown error')}")
            print()
            print("Common Issues:")
            print("   1. Invalid API key - Check if your key is correct")
            print("   2. No API credits - Ensure you have credits/quota")
            print("   3. Wrong API endpoint - Verify LLM_API_BASE_URL")
            print("   4. Network issue - Check your internet connection")
            return False
            
    except Exception as e:
        print("[EXCEPTION] Error occurred!")
        print(f"Error: {str(e)}")
        print()
        print("This might be a network or configuration issue")
        return False

if __name__ == '__main__':
    success = test_llm_connection()
    print()
    print("=" * 60)
    sys.exit(0 if success else 1)

