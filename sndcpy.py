import subprocess
import socket
import time
import pyaudio

print("Installing sndcpy")
subprocess.run(["adb", "install", "-t", "-r", "-g", "sndcpy.apk"])

print("Granting permissions")
result = subprocess.run(["adb", "shell", "appops", "set", "com.rom1v.sndcpy", "PROJECT_MEDIA", "allow"])

print("Forwarding port")
subprocess.run(["adb", "forward", "tcp:28200", "localabstract:sndcpy"])

print("Starting sndcpy")
subprocess.run(["adb", "shell", "am", "start", "com.rom1v.sndcpy/.MainActivity"])

time.sleep(3)

print("Connecting to sndcpy")
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(3)
sock.connect(("127.0.0.1", 28200))
print("Connected to audio stream")


pa = pyaudio.PyAudio()

audio_stream = pa.open(
    format=pyaudio.paInt16,
    channels=2,
    rate=48000,
    output=True,
    frames_per_buffer=1024
)

while True:
    audio_data = sock.recv(4096)
    audio_stream.write(audio_data)