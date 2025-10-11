import subprocess
import socket
import time
import pyaudio
import os
import sys

def main():
    apk_path = "sndcpy.apk"
    port = 28200
    device = None
    
    if len(sys.argv) > 1:
        apk_path = sys.argv[1]
    
    if len(sys.argv) > 2:
        device = sys.argv[2]
    
    adb_cmd = ["adb"]
    if device:
        adb_cmd.extend(["-s", device])
    
    if not os.path.exists(apk_path):
        print(f"Error: APK not found at {apk_path}")
        sys.exit(1)
    
    print(f"Installing {apk_path}")
    subprocess.run(["adb", "install", "-t", "-r", "-g", apk_path])
    
    print("Granting permissions")
    subprocess.run(["adb", "shell", "appops", "set", "com.rom1v.sndcpy", "PROJECT_MEDIA", "allow"])
    
    print(f"Forwarding port {port}")
    subprocess.run(["adb", "forward", f"tcp:{port}", "localabstract:sndcpy"])
    
    print("Starting sndcpy")
    subprocess.run(["adb", "shell", "am", "start", "com.rom1v.sndcpy/.MainActivity"])
    
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