import os
import sys
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.downloader import YouTubeDownloader

def test_downloads():
    print("--- Starting Download Verification ---")
    
    # Use a very short video for testing
    TEST_URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw" # "Me at the zoo" (first video, short)
    DOWNLOAD_DIR = os.path.join(os.getcwd(), "test_downloads")
    
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
        
    print(f"Download directory: {DOWNLOAD_DIR}")
    
    downloader = YouTubeDownloader()
    
    # Callbacks
    def on_progress(percent, text):
        print(f"  [Progress] {text}")
        
    def on_complete(info):
        print(f"  [Complete] Downloaded: {info['title']} ({info['format']})")
        
    def on_error(err):
        print(f"  [Error] {err}")

    downloader.callback_progress = on_progress
    downloader.callback_complete = on_complete
    downloader.callback_error = on_error

    # Test Cases
    formats = ["mp4", "mp3", "original"]
    
    for fmt in formats:
        print(f"\nTesting format: {fmt}...")
        try:
            # We need to wait because the downloader is threaded
            downloader.download(TEST_URL, DOWNLOAD_DIR, fmt)
            
            # Wait loop
            timeout = 60 # seconds
            start_time = time.time()
            while downloader.downloading:
                time.sleep(1)
                if time.time() - start_time > timeout:
                    print(f"  [Timeout] Download took too long")
                    break
            
            # Verify file existence (rough check since filename varies)
            print(f"  Verify: checking files in {DOWNLOAD_DIR}...")
            files = os.listdir(DOWNLOAD_DIR)
            print(f"  Files found: {files}")
            
        except Exception as e:
            print(f"  [Exception] {e}")

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    test_downloads()
