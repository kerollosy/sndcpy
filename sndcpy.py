import subprocess
import socket
import time
import pyaudio
import os
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="Stream audio from Android device")
    parser.add_argument("apk_path", nargs="?", default="sndcpy.apk", help="Path to sndcpy APK file")
    parser.add_argument("device", nargs="?", help="Specific device serial number (if multiple devices connected)")
    parser.add_argument("-p", "--port", type=int, default=28200, help="Local port for forwarding")
    
    args = parser.parse_args()
    
    apk_path = args.apk_path
    port = args.port
    device = args.device
    
    adb_cmd = ["adb"]
    if device:
        adb_cmd.extend(["-s", device])
        print(f"Using device: {device}")
    
    if not os.path.exists(apk_path):
        print(f"Error: APK not found at {apk_path}")
        sys.exit(1)
    
    print(f"Installing {apk_path}")
    subprocess.run(adb_cmd + ["install", "-t", "-r", "-g", apk_path])
    
    print("Granting permissions")
    subprocess.run(adb_cmd + ["shell", "appops", "set", "com.rom1v.sndcpy", "PROJECT_MEDIA", "allow"])
    
    print(f"Forwarding port {port}")
    subprocess.run(adb_cmd + ["forward", f"tcp:{port}", "localabstract:sndcpy"])
    
    print("Starting sndcpy")
    subprocess.run(adb_cmd + ["shell", "am", "start", "com.rom1v.sndcpy/.MainActivity"])
    
    time.sleep(3)
    
    print("Connecting to sndcpy")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(("127.0.0.1", port))
        print("Connected to audio stream")
    except socket.error as e:
        print(f"Connection failed: {e}")
        sys.exit(1)
    
    pa = pyaudio.PyAudio()
    audio_stream = pa.open(
        format=pyaudio.paInt16,
        channels=2,
        rate=48000,
        output=True,
        frames_per_buffer=1024
    )
    
    print("Streaming audio...")
    try:
        while True:
            audio_data = sock.recv(4096)
            if not audio_data:
                print("Connection closed by device")
                break
            audio_stream.write(audio_data)
    except socket.error as e:
        print(f"Socket error: {e}")
    finally:
        # Basic cleanup
        if audio_stream:
            audio_stream.close()
        if pa:
            pa.terminate()
        if sock:
            sock.close()

if __name__ == "__main__":
    main()