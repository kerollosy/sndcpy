package com.rom1v.sndcpy;

import java.io.IOException;
import android.util.Log;

public class MetadataWriter {
    private static volatile java.io.OutputStream out = null;
    private static final Object LOCK = new Object();

    static void setOutput(java.io.OutputStream o) {
        synchronized (LOCK) {
            out = o;
        }
    }

    static void clearOutput() {
        synchronized (LOCK) {
            out = null;
        }
    }

    static void send(String jsonLine) {
        synchronized (LOCK) {
            if (out == null) {
                Log.w("sndcpy-meta", "MetadataWriter.send() called but out == null");
                return;
            }
            try {
                byte[] b = (jsonLine + "\n").getBytes(java.nio.charset.StandardCharsets.UTF_8);
                out.write(b);
                out.flush();
                Log.d("sndcpy-meta", "Wrote to metadata socket: " + jsonLine);
            } catch (IOException e) {
                Log.e("sndcpy-meta", "Failed to write metadata", e);
                try { out.close(); } catch (IOException ignored) {}
                out = null;
            }
        }
    }

}