import dbus
import dbus.lowlevel
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib
import requests

# Constants for message filter return values
HANDLER_RESULT_NOT_YET_HANDLED = True
HANDLER_RESULT_HANDLED = False

# ==========================================
# Configuration Section
# ==========================================
# NTFY_TOPIC: This is the unique channel name on ntfy.sh.
# Anyone subscribed to this topic will receive these notifications.
# You can change 'antigrav_sam_notifications' to any random string to make it private.
NTFY_TOPIC = "antigrav_sam_notifications"

# NTFY_URL: The full URL where we send the POST requests.
# LOCALHOST MODE: We now point to our local server!
NTFY_URL = f"http://127.0.0.1:8080/{NTFY_TOPIC}"

# Global var for deduplication
last_sent_notification = ""

def send_to_ntfy(title, message, priority="default"):
    """Sends notification to Ntfy.sh (Local) using Curl to avoid python request issues"""
    try:
        print(f"[Debug] Sending to Ntfy: {title}")
        
        # We use curl because it respects the IP address reliably
        import subprocess
        
        # Build command
        # curl -H "Title: ..." -H "Priority: ..." -d "message" http://127.0.0.1:8080/topic
        cmd = [
            "curl",
            "-s", # Silent
            "-o", "/dev/null", # Discard output
            "-w", "%{http_code}", # Write status code
            "-H", f"Title: {title}",
            "-H", f"Priority: {priority}",
            # "-H", "Tags: computer",
            "-d", message,
            f"http://127.0.0.1:8080/{NTFY_TOPIC}"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        status_code = result.stdout.strip()
        
        if status_code == "200":
            print(f"[Sent] {title}")
        else:
            print(f"[Failed] Status: {status_code} (Curl)")
            
    except Exception as e:
        print(f"[Error] sending to ntfy: {e}")

def message_filter(connection, message):
    try:
        """
        Callback for EVERY message seen on the bus.
        """
        if message.get_member() != "Notify":
            return HANDLER_RESULT_NOT_YET_HANDLED

        args = message.get_args_list()
        
        if len(args) < 5:
            return HANDLER_RESULT_NOT_YET_HANDLED

        app_name = str(args[0])
        summary = str(args[3])
        body = str(args[4])
        
        # Antigravity specific debug
        if "Antigravity" in app_name:
            print(f"[DEBUG DUMP] Antigravity Raw Args: {args}")

        # Requested Debug: Print all args
        print(f"\n--- Notification Args Dump ---")
        for i, arg in enumerate(args):
            print(f"Arg [{i}]: {arg}")
        print("------------------------------\n")

        global last_sent_notification
        current_signature = f"{app_name}:{summary}:{body}"
        
        if current_signature == last_sent_notification:
            print("[Skipped] Duplicate")
            return HANDLER_RESULT_HANDLED

        print(f"[Received] App: {app_name} | Title: {summary}")
        
        # Filter Logic
        if app_name == "notify-send" and "bridge_test" in summary:
            pass # Allow test
        
        # Use App Name as the Title (e.g. "Antigravity")
        # instead of the summary (e.g. "Review requested")
        clean_title = app_name

        send_to_ntfy(clean_title, body)
        last_sent_notification = current_signature
        
        return HANDLER_RESULT_HANDLED
    except Exception as e:
        print(f"[CRITICAL ERROR] In message_filter: {e}")
        return HANDLER_RESULT_NOT_YET_HANDLED

def main():
    print("Starting Antigravity Bridge (Monitor Mode)...")
    print(f"Target: {NTFY_URL}")

    # 1. Init Main Loop
    DBusGMainLoop(set_as_default=True)
    
    # 2. Connect to Session Bus
    bus = dbus.SessionBus()
    
    # 3. Add Message Filter
    bus.add_message_filter(message_filter)
    
    # 4. Become a Monitor
    try:
        dbus_obj = bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
        monitor_iface = dbus.Interface(dbus_obj, 'org.freedesktop.DBus.Monitoring')
        
        match_rule = "type='method_call',interface='org.freedesktop.Notifications',member='Notify',eavesdrop='true'"
        monitor_iface.BecomeMonitor([match_rule], dbus.UInt32(0))
        
        print("native monitor enabled.")
    except Exception as e:
        print(f"Failed to become monitor: {e}")
        bus.add_match_string("type='method_call',interface='org.freedesktop.Notifications',member='Notify',eavesdrop='true'")

    # Start reply listener AFTER dbus init
    # Start the reply listener in a background thread
    listener_thread = threading.Thread(target=poll_replies, daemon=True)
    listener_thread.start()

    # 5. Run Loop
    loop = GLib.MainLoop()
    try:
        print("Listening for notifications... (Ctrl+C to stop)")
        loop.run()
    except KeyboardInterrupt:
        print("\nStopping bridge.")
    except Exception as e:
        print(f"\n[CRITICAL MAIN LOOP ERROR]: {e}")

# ==========================================
# Bidirectional Listener (Replies)
# ==========================================
import threading
import json
import time

def handle_reply(data):
    """
    Handles a reply received from the phone.
    Now uses the native 'antigravity chat' CLI command.
    """
    try:
        title = data.get('title', 'Reply')
        message = data.get('message', '')
        
        # Log to console
        print(f"\n[Incoming Reply] {title}: {message}")
        
        # Write to file (backup)
        log_path = "incoming_replies.log"
        with open(log_path, "a") as f:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")
            
        print(f"Reply saved to {log_path}")
        
        # ==========================================
        # Antigravity CLI Auto-Reply
        # ==========================================
        import subprocess
        
        print(f"[Auto-Reply] Sending via CLI: {message[:50]}...")
        
        # Use antigravity chat command
        # Syntax: antigravity chat "message"
        result = subprocess.run(
            ["antigravity", "chat", message],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            print(f"[Auto-Reply] ✅ Sent successfully via CLI.")
        else:
            print(f"[Auto-Reply] ❌ CLI Error: {result.stderr}")
            # Fallback: Show desktop notification
            subprocess.run(["notify-send", "Reply Error", f"Failed to send: {result.stderr}"])
        
    except Exception as e:
        print(f"[Error] Handling reply: {e}")

def poll_replies():
    """
    Background thread that listens to the Ntfy stream for updates.
    Uses STREAMING mode to receive realtime messages.
    """
    print("Starting Reply Listener (Background)...")
    
    # Streaming URL - use 'since=10s' for recent messages only (avoids replay)
    # We also track processed message IDs to prevent duplicates
    url = f"http://127.0.0.1:8080/{NTFY_TOPIC}/json?since=10s"
    processed_ids = set()  # Track which message IDs we've already handled
    
    while True:
        try:
            print("[Reply Listener] Connecting to stream...")
            with requests.get(url, stream=True, timeout=None) as r:
                r.raise_for_status()
                print("[Reply Listener] Connected! Waiting for replies...")
                for line in r.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            event = data.get('event')
                            msg_id = data.get('id')
                            
                            # Skip already processed messages
                            if msg_id in processed_ids:
                                continue
                            
                            if event == 'message':
                                # Check tags to see if it's a reply
                                tags = data.get('tags', [])
                                title = data.get('title', '')
                                
                                if 'reply' in tags or title == 'Reply from Mobile':
                                    handle_reply(data)
                                    if msg_id:
                                        processed_ids.add(msg_id)
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            print(f"[Listener Error] Connection lost: {e}. Retrying in 5s...")
            time.sleep(5)

# Update main to start the thread
def main():
    print("Starting Antigravity Bridge (Monitor Mode)...")
    print(f"Target: {NTFY_URL}")
    
    # Start the reply listener in a background thread
    listener_thread = threading.Thread(target=poll_replies, daemon=True)
    listener_thread.start()

    # 1. Init Main Loop
    DBusGMainLoop(set_as_default=True)
    
    # 2. Connect to Session Bus
    bus = dbus.SessionBus()
    
    # 3. Add Message Filter (This handles the incoming messages)
    bus.add_message_filter(message_filter)
    
    # 4. Become a Monitor
    try:
        dbus_obj = bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
        monitor_iface = dbus.Interface(dbus_obj, 'org.freedesktop.DBus.Monitoring')
        
        # Match rule: Method calls to Notify
        match_rule = "type='method_call',interface='org.freedesktop.Notifications',member='Notify',eavesdrop='true'"
        monitor_iface.BecomeMonitor([match_rule], dbus.UInt32(0))
        
        print("native monitor enabled.")
    except Exception as e:
        print(f"Failed to become monitor: {e}")
        print("Fallback: Using simple match rules (might not capture everything)")
        bus.add_match_string("type='method_call',interface='org.freedesktop.Notifications',member='Notify',eavesdrop='true'")

    # 5. Run Loop
    loop = GLib.MainLoop()
    try:
        print("Listening for notifications... (Ctrl+C to stop)")
        loop.run()
    except KeyboardInterrupt:
        print("\nStopping bridge.")

if __name__ == "__main__":
    main()
