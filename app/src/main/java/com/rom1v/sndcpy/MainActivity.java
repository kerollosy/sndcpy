package com.rom1v.sndcpy;

import android.provider.Settings;
import android.content.ComponentName;
import android.widget.Toast;
import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.media.projection.MediaProjectionManager;
import android.os.Bundle;
import android.util.Log;

public class MainActivity extends Activity {

    private static final String TAG = "SndcpyMainActivity";
    private static final int REQUEST_CODE_PERMISSION_AUDIO = 1;
    private static final int REQUEST_CODE_START_CAPTURE = 2;

    private boolean notificationAccessChecked = false;
    private boolean waitingForNotificationPermission = false;
    private boolean hasLeftActivity = false;

    private boolean hasNotificationAccess() {
        String enabled = Settings.Secure.getString(getContentResolver(), "enabled_notification_listeners");
        Log.d(TAG, "hasNotificationAccess() - enabled_notification_listeners: " + enabled);
        if (enabled == null) {
            Log.d(TAG, "hasNotificationAccess() - enabled is null, returning false");
            return false;
        }
        ComponentName cn = new ComponentName(this, MetaNotificationListener.class);
        String flat = cn.flattenToString();
        Log.d(TAG, "hasNotificationAccess() - looking for: " + flat);
        boolean hasAccess = enabled.contains(flat);
        Log.d(TAG, "hasNotificationAccess() - result: " + hasAccess);
        return hasAccess;
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        Log.d(TAG, "onCreate() called, savedInstanceState: " + (savedInstanceState != null ? "not null" : "null"));
        Log.d(TAG, "onCreate() - notificationAccessChecked: " + notificationAccessChecked);
        Log.d(TAG, "onCreate() - waitingForNotificationPermission: " + waitingForNotificationPermission);

        // 1. Check audio permission first
        boolean hasAudioPermission = checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED;
        Log.d(TAG, "onCreate() - hasAudioPermission: " + hasAudioPermission);

        if (!hasAudioPermission) {
            Log.d(TAG, "onCreate() - requesting audio permission");
            String[] permissions = {Manifest.permission.RECORD_AUDIO};
            requestPermissions(permissions, REQUEST_CODE_PERMISSION_AUDIO);
            return;
        }

        // Check if notification access is granted
        boolean hasNotifAccess = hasNotificationAccess();
        Log.d(TAG, "onCreate() - hasNotificationAccess: " + hasNotifAccess);

        if (!hasNotifAccess && !notificationAccessChecked) {
            Log.d(TAG, "onCreate() - requesting notification access");
            notificationAccessChecked = true;
            waitingForNotificationPermission = true;

            Intent intent = new Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS);
            startActivity(intent);
            return;
        }

        // Start the media projection capture intent
        Log.d(TAG, "onCreate() - calling startCaptureIntent()");
        startCaptureIntent();
    }

    @Override
    protected void onResume() {
        super.onResume();
        Log.d(TAG, "onResume() called, waitingForNotificationPermission: " + waitingForNotificationPermission + ", hasLeftActivity: " + hasLeftActivity);

        // Only check if we were waiting for permission AND the user has actually left the activity
        if (waitingForNotificationPermission && hasLeftActivity) {

            waitingForNotificationPermission = false;
            hasLeftActivity = false;

            if (!hasNotificationAccess()) {
                Log.d(TAG, "onResume() - notification access still not granted, continuing without it");
                Toast.makeText(this, "Notification access not granted. Metadata features will be unavailable.", Toast.LENGTH_SHORT).show();
                // Continue anyway
            } else {
                Log.d(TAG, "onResume() - notification access granted!");
            }

            Log.d(TAG, "onResume() - calling startCaptureIntent()");
            startCaptureIntent();
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        Log.d(TAG, "onPause() called");

        // Mark that user has left the activity
        if (waitingForNotificationPermission) {
            hasLeftActivity = true;
            Log.d(TAG, "onPause() - user has left activity, hasLeftActivity set to true");
        }
    }

    @Override
    public void onActivityResult(int requestCode, int resultCode, Intent data) {
        Log.d(TAG, "onActivityResult() - requestCode: " + requestCode + ", resultCode: " + resultCode + ", data: " + (data != null ? "not null" : "null"));

        if (requestCode == REQUEST_CODE_START_CAPTURE) {
            Log.d(TAG, "onActivityResult() - handling REQUEST_CODE_START_CAPTURE");
            if (resultCode == Activity.RESULT_OK) {
                Log.d(TAG, "onActivityResult() - RESULT_OK, starting RecordService");
                RecordService.start(this, data);
            } else {
                Log.d(TAG, "onActivityResult() - result was not OK, resultCode: " + resultCode);
            }
            Log.d(TAG, "onActivityResult() - calling finish()");
            finish();
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        Log.d(TAG, "onRequestPermissionsResult() - requestCode: " + requestCode);
        if (requestCode == REQUEST_CODE_PERMISSION_AUDIO) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                Log.d(TAG, "onRequestPermissionsResult() - audio permission granted");
                onCreate(null);
            } else {
                Log.d(TAG, "onRequestPermissionsResult() - audio permission denied");
                Toast.makeText(this, "Audio permission is required", Toast.LENGTH_LONG).show();
                finish();
            }
        }
    }

    private void startCaptureIntent() {
        Log.d(TAG, "startCaptureIntent() - creating media projection intent");
        MediaProjectionManager mediaProjectionManager = (MediaProjectionManager) getSystemService(MEDIA_PROJECTION_SERVICE);
        Intent intent = mediaProjectionManager.createScreenCaptureIntent();
        Log.d(TAG, "startCaptureIntent() - starting activity for result");
        startActivityForResult(intent, REQUEST_CODE_START_CAPTURE);
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        Log.d(TAG, "onDestroy() called");
    }
}