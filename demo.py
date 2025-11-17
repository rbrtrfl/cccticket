#!/usr/bin/env python3
"""
Demo script that runs both the test server and ticket checker.
This is for demonstration purposes only.
"""
import subprocess
import time
import sys
from pathlib import Path

def main():
    print("=" * 70)
    print("CCC Ticket Checker Demo - Multi-Threaded Cookie Collection")
    print("=" * 70)
    print("\nThis demo will:")
    print("1. Start a test web server (shop closed for 10 seconds)")
    print("2. Start the multi-threaded ticket checker (3 threads)")
    print("3. Collect cookies from 3 parallel threads")
    print("4. Save all collected cookies to cookies_all.txt\n")
    
    input("Press Enter to start the demo...")
    
    # Start the test server
    print("\n🚀 Starting test server...")
    server_process = subprocess.Popen(
        [sys.executable, "test_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Give the server time to start
    time.sleep(2)
    
    print("✓ Test server running on http://127.0.0.1:5000/")
    print("\n🔍 Starting multi-threaded ticket checker...\n")
    print("-" * 70)
    
    # Run the ticket checker
    try:
        checker_process = subprocess.Popen(
            [sys.executable, "ticket_checker.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Stream output from the checker
        for line in checker_process.stdout:
            print(line, end='')
            
        checker_process.wait()
        
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
    finally:
        print("\n" + "-" * 70)
        print("🛑 Stopping test server...")
        server_process.terminate()
        server_process.wait()
        print("✓ Demo complete!")
        
        # Check output files
        print("\n📊 Results:")
        print("-" * 70)
        
        all_cookies_file = Path("cookies_all.txt")
        if all_cookies_file.exists():
            print(f"\n📄 All cookies saved to: {all_cookies_file}")
            print("\nCookie contents:")
            print(all_cookies_file.read_text())
            print("💡 Test each cookie manually in your browser to find the best queue position")
        else:
            print("\n❌ No cookies file found - check if collection succeeded")

if __name__ == "__main__":
    main()
