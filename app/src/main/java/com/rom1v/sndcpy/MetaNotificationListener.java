package com.rom1v.sndcpy;

import android.content.ComponentName;
import android.content.Context;
import android.media.MediaMetadata;
import android.media.session.MediaController;
import android.media.session.MediaSessionManager;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;
import android.util.Log;
import android.view.KeyEvent;

import org.json.JSONObject;

import java.util.List;

public class MetaNotificationListener extends NotificationListenerService {

    private static MediaController activeController = null;

    @Override
    public void onListenerConnected() {
        super.onListenerConnected();
        Log.d("sndcpy-meta", "Notification listener connected");
        updatePlayingSongInfo(this);
    }

    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        if (sbn == null || sbn.getNotification() == null) return;

        // Only react to media-style notifications
        if (sbn.getNotification().extras.containsKey("android.mediaSession")) {
            updatePlayingSongInfo(this);
        }
    }

    private void updatePlayingSongInfo(Context context) {
        try {
            MediaSessionManager msm =
                    (MediaSessionManager) context.getSystemService(Context.MEDIA_SESSION_SERVICE);
            List<MediaController> controllers =
                    msm.getActiveSessions(new ComponentName(context, MetaNotificationListener.class));

            if (controllers == null || controllers.isEmpty()) {
                Log.d("sndcpy-meta", "No active media sessions");
                activeController = null;
                return;
            }

            // Find the first active playback controller
            MediaController controller = null;
            for (MediaController c : controllers) {
                if (c.getPlaybackState() != null &&
                        c.getPlaybackState().getState() ==
                                android.media.session.PlaybackState.STATE_PLAYING) {
                    controller = c;
                    break;
                }
            }
            if (controller == null) {
                controller = controllers.get(0); // fallback
            }

            activeController = controller; // Store for playback control

            MediaMetadata metadata = controller.getMetadata();
            if (metadata == null) {
                Log.d("sndcpy-meta", "No metadata found");
                return;
            }

            String title = metadata.getString(MediaMetadata.METADATA_KEY_TITLE);
            String artist = metadata.getString(MediaMetadata.METADATA_KEY_ARTIST);
            String album = metadata.getString(MediaMetadata.METADATA_KEY_ALBUM);

            JSONObject json = new JSONObject();
            json.put("package", controller.getPackageName());
            json.put("title", title != null ? title : "");
            json.put("artist", artist != null ? artist : "");
            json.put("album", album != null ? album : "");

            MetadataWriter.send(json.toString());
            Log.d("sndcpy-meta", "Sent metadata: " + json);

        } catch (SecurityException e) {
            Log.e("sndcpy-meta", "Missing notification access permission", e);
        } catch (Exception e) {
            Log.e("sndcpy-meta", "updatePlayingSongInfo failed", e);
        }
    }

    // Playback control methods
    public static void sendPlayPause() {
        if (activeController == null) {
            Log.w("sndcpy-meta", "No active controller for play/pause");
            return;
        }
        try {
            if (activeController.getPlaybackState() != null &&
                activeController.getPlaybackState().getState() == android.media.session.PlaybackState.STATE_PLAYING) {
                activeController.getTransportControls().pause();
                Log.d("sndcpy-meta", "Sent PAUSE");
            } else {
                activeController.getTransportControls().play();
                Log.d("sndcpy-meta", "Sent PLAY");
            }
        } catch (Exception e) {
            Log.e("sndcpy-meta", "Failed to play/pause", e);
        }
    }

    public static void sendNext() {
        if (activeController == null) {
            Log.w("sndcpy-meta", "No active controller for next");
            return;
        }
        try {
            activeController.getTransportControls().skipToNext();
            Log.d("sndcpy-meta", "Sent NEXT");
        } catch (Exception e) {
            Log.e("sndcpy-meta", "Failed to skip next", e);
        }
    }

    public static void sendPrevious() {
        if (activeController == null) {
            Log.w("sndcpy-meta", "No active controller for previous");
            return;
        }
        try {
            activeController.getTransportControls().skipToPrevious();
            Log.d("sndcpy-meta", "Sent PREVIOUS");
        } catch (Exception e) {
            Log.e("sndcpy-meta", "Failed to skip previous", e);
        }
    }

    public static void sendStop() {
        if (activeController == null) {
            Log.w("sndcpy-meta", "No active controller for stop");
            return;
        }
        try {
            activeController.getTransportControls().stop();
            Log.d("sndcpy-meta", "Sent STOP");
        } catch (Exception e) {
            Log.e("sndcpy-meta", "Failed to stop", e);
        }
    }
}