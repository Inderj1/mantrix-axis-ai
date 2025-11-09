#!/usr/bin/env python3
"""Test script to verify Anthropic Claude and OpenAI API keys"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

print("=" * 80)
print("API KEY VERIFICATION TEST")
print("=" * 80)

# Test 1: Anthropic Claude API
print("\n[1/2] Testing Anthropic Claude API...")
print(f"API Key: {ANTHROPIC_API_KEY[:20]}..." if ANTHROPIC_API_KEY else "API Key: NOT FOUND")

if ANTHROPIC_API_KEY:
    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=ANTHROPIC_API_KEY)

        # Test with Claude 3 Opus (most stable/available model)
        print("Testing model: claude-3-opus-20240229")
        response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=50,
            messages=[{"role": "user", "content": "Say 'API test successful' if you can read this."}]
        )
        print(f"✅ SUCCESS: {response.content[0].text}")

        # Test Claude 3.5 Sonnet v2 (October 2024)
        print("\nTesting model: claude-3-5-sonnet-20241022")
        try:
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=50,
                messages=[{"role": "user", "content": "Say 'Sonnet works' if you can read this."}]
            )
            print(f"✅ SUCCESS: {response.content[0].text}")
        except Exception as e:
            print(f"❌ Model not available: {e}")

        # Test Claude 3.5 Sonnet v1 (June 2024)
        print("\nTesting model: claude-3-5-sonnet-20240620")
        try:
            response = client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=50,
                messages=[{"role": "user", "content": "Say 'Sonnet v1 works' if you can read this."}]
            )
            print(f"✅ SUCCESS: {response.content[0].text}")
        except Exception as e:
            print(f"❌ Model not available: {e}")

    except Exception as e:
        print(f"❌ ERROR: {e}")
        print(f"\nError type: {type(e).__name__}")
else:
    print("❌ ANTHROPIC_API_KEY not found in environment")

# Test 2: OpenAI API
print("\n" + "=" * 80)
print("[2/2] Testing OpenAI API...")
print(f"API Key: {OPENAI_API_KEY[:20]}..." if OPENAI_API_KEY else "API Key: NOT FOUND")

if OPENAI_API_KEY:
    try:
        from openai import OpenAI

        client = OpenAI(api_key=OPENAI_API_KEY)

        # Test with GPT-4
        print("Testing model: gpt-4")
        response = client.chat.completions.create(
            model="gpt-4",
            max_tokens=50,
            messages=[{"role": "user", "content": "Say 'OpenAI API test successful' if you can read this."}]
        )
        print(f"✅ SUCCESS: {response.choices[0].message.content}")

        # Test with GPT-4o
        print("\nTesting model: gpt-4o")
        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=50,
            messages=[{"role": "user", "content": "Say 'GPT-4o works' if you can read this."}]
        )
        print(f"✅ SUCCESS: {response.choices[0].message.content}")

    except Exception as e:
        print(f"❌ ERROR: {e}")
        print(f"\nError type: {type(e).__name__}")
else:
    print("❌ OPENAI_API_KEY not found in environment")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
