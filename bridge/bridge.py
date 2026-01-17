import subprocess  # Used to run shell commands (like dbus-monitor) from Python
import requests    # Used to send HTTP requests to the Ntfy.sh server
import json        # (Optional) Used for JSON handling if we needed complex parsing
import sys         # Used for system-specific parameters and functions

# ==========================================
# Configuration Section
# ==========================================
# NTFY_TOPIC: This is the unique channel name on ntfy.sh.
# Anyone subscribed to this topic will receive these notifications.
# You can change 'antigrav_sam_notifications' to any random string to make it private.
NTFY_TOPIC = "antigrav_sam_notifications"

# NTFY_URL: The full URL where we send the POST requests.
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"

# Global variable to track the last sent message for deduplication
last_sent_notification = ""

def filter_notification(app_name, summary, body):
    """
    Decides whether a notification should be forwarded to the phone.
    
    Args:
        app_name (str): The name of the application sending the notification (e.g., 'Slack', 'notify-send').
        summary (str): The title of the notification.
        body (str): The main content/message of the notification.
        
    Returns:
        bool: True if we should forward it, False if we should ignore it.
    """
    # Safety Check: Ignore our own test notifications to prevent infinite loops.
    # If we sent a notification saying "Sent to Phone", and then caught that notification
    # and sent it again, we'd create a spam loop.
    if app_name == "notify-send" and "bridge_test" in summary:
        return True
    
    # Example of filtering: Uncomment the lines below to ignore Spotify song changes
    # if app_name == "Spotify":
    #     return False
    
    # By default, we return True to forward everything to the mobile device.
    return True

def send_to_ntfy(title, message, priority="default"):
    """
    Sends the actual HTTP POST request to Ntfy.sh.
    
    Args:
        title (str): Notification title.
        message (str): Notification body text.
        priority (str): Priority level (default, high, low). Affects how the phone alerts.
    """
    try:
        # Headers define metadata for Ntfy
        headers = {
            "Title": title,
            "Priority": priority,
            "Tags": "computer"  # Adds a little computer icon to the notification
        }
        
        # We encode the message to 'utf-8' to handle emojis and special characters correctly.
        response = requests.post(
            NTFY_URL,
            data=message.encode('utf-8'),
            headers=headers,
            timeout=5  # Timeout after 5 seconds if server doesn't respond
        )
        
        # Check if the request was successful (HTTP Status Code 200 means OK)
        if response.status_code == 200:
            print(f"[Sent] {title}: {message}")
        else:
            print(f"[Failed] Status: {response.status_code} - {response.text}")
            
    except Exception as e:
        # Catch network errors (like no internet connection) so the script doesn't crash
        print(f"[Error] sending to ntfy: {e}")

def run_monitor_subprocess():
    """
    Main loop: Monitors the Linux Notification Bus (DBus) using 'dbus-monitor'.
    
    Why 'dbus-monitor'? 
    Linux uses a system called DBus for applications to talk to each other.
    Notifications are sent over the 'org.freedesktop.Notifications' interface.
    We run the command-line tool `dbus-monitor` and read its output line-by-line.
    """
    
    # The command we want to run. 
    # interface='org.freedesktop.Notifications' filters for just notifications.
    cmd = ["dbus-monitor", "interface='org.freedesktop.Notifications'"]
    
    # subprocess.Popen starts the command in the background.
    # stdout=subprocess.PIPE allows us to read the output of the command.
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,  # Treat output as text, not raw bytes
        bufsize=1   # Line buffered
    )

    current_notification = {}
    capturing = False # A flag to know if we are currently reading a notification block

    print("Bridge (Subprocess Mode) Started. Press Ctrl+C to stop.")
    
    global last_sent_notification

    try:
        # Infinite loop to keep reading lines forever
        while True:
            line = process.stdout.readline()
            if not line:
                break # Stop if the command exits
            
            line = line.strip() # Remove leading/trailing whitespace
            
            # dbus-monitor output starts a new notification with "member=Notify"
            if "member=Notify" in line:
                capturing = True
                current_notification = {"args": []} # Reset list to hold new args
                continue

            # If we are inside a notification block, we parse the arguments
            if capturing:
                # We are looking for lines that look like: string "Title" or uint32 0
                if line.startswith("string") or line.startswith("uint32") or line.startswith("int32"):
                    if line.startswith("string"):
                        # Extract the text between the first and last quote
                        # Example: string "Hello World" -> Hello World
                        content = line[line.find('"')+1 : line.rfind('"')]
                        current_notification["args"].append(content)
                    elif line.startswith("uint32"):
                         # Example: uint32 100 -> 100
                         current_notification["args"].append(line.split()[-1])
                    
                    # The DBus Notify specification has a standard order of arguments:
                    # Arg 0: App Name (string)
                    # Arg 1: Replaces ID (uint32)
                    # Arg 2: App Icon (string)
                    # Arg 3: Summary/Title (string)
                    # Arg 4: Body/Message (string)
                    # ... and more
                    
                    args = current_notification["args"]
                    
                    # Once we have at least 5 arguments, we have enough info to send
                    if len(args) >= 5:
                        app_name = args[0]
                        summary = args[3]
                        body = args[4]
                        
                        # Deduplication Logic
                        current_signature = f"{app_name}:{summary}:{body}"
                        print(f"[Debug] New: '{current_signature}' vs Last: '{last_sent_notification}'")
                        
                        if current_signature != last_sent_notification:
                             # Apply our filter logic
                            if filter_notification(app_name, summary, body):
                                send_to_ntfy(summary, body)
                                last_sent_notification = current_signature
                        else:
                             print("[Skipped] Duplicate (Subprocess)")
                        
                        # Stop capturing this notification and wait for the next one
                        capturing = False 
                        current_notification = {}

    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        print("\nStopping bridge.")
        process.terminate()

if __name__ == "__main__":
    run_monitor_subprocess()
