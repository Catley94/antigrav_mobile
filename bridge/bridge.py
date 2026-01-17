import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib
import requests

# ==========================================
# Configuration Section
# ==========================================
NTFY_TOPIC = "antigrav_sam_notifications"
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"

# Global var for deduplication
last_sent_notification = ""

def send_to_ntfy(title, message, priority="default"):
    """Sends notification to Ntfy.sh"""
    try:
        headers = {
            "Title": title,
            "Priority": priority,
            "Tags": "computer"
        }
        
        print(f"[Debug] Sending to Ntfy: {title}")
        
        response = requests.post(
            NTFY_URL,
            data=message.encode('utf-8'),
            headers=headers,
            timeout=5
        )
        if response.status_code == 200:
            print(f"[Sent] {title}")
        else:
            print(f"[Failed] Status: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[Error] sending to ntfy: {e}")

def message_filter(connection, message):
    """
    Callback for EVERY message seen on the bus.
    We filter for 'Notify' method calls locally just to be safe/organized,
    though BecomeMonitor should only send us what we asked for.
    """
    if message.get_member() != "Notify":
        return dbus.HANDLER_RESULT_NOT_YET_HANDLED

    args = message.get_args_list()
    # Notify signature: (susssasa{sv}i)
    # 0: app_name (string)
    # 1: replaces_id (uint32)
    # 2: app_icon (string)
    # 3: summary (string) - Title
    # 4: body (string) - Message
    
    if len(args) < 5:
        return dbus.HANDLER_RESULT_NOT_YET_HANDLED

    app_name = str(args[0])
    summary = str(args[3])
    body = str(args[4])
    
    # Antigravity specific debug
    if "Antigravity" in app_name:
        print(f"[DEBUG DUMP] Antigravity Raw Args: {args}")

    global last_sent_notification
    current_signature = f"{app_name}:{summary}:{body}"
    
    if current_signature == last_sent_notification:
        print("[Skipped] Duplicate")
        return dbus.HANDLER_RESULT_HANDLED

    print(f"[Received] App: {app_name} | Title: {summary}")
    
    # Filter Logic
    if app_name == "notify-send" and "bridge_test" in summary:
        pass # Allow test
    
    send_to_ntfy(summary, body)
    last_sent_notification = current_signature
    
    return dbus.HANDLER_RESULT_HANDLED

def main():
    print("Starting Antigravity Bridge (Monitor Mode)...")
    print(f"Target: {NTFY_URL}")

    # 1. Init Main Loop
    DBusGMainLoop(set_as_default=True)
    
    # 2. Connect to Session Bus
    bus = dbus.SessionBus()
    
    # 3. Add Message Filter (This handles the incoming messages)
    bus.add_message_filter(message_filter)
    
    # 4. Become a Monitor
    # We call the BecomeMonitor method on the DBus driver.
    # This matches behavior of 'dbus-monitor' CLI.
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
