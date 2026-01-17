import 'dart:convert'; // Allows us to convert JSON strings to Objects and vice versa
import 'package:flutter/material.dart'; // The core Flutter UI framework
import 'package:http/http.dart' as http; // A package to make HTTP web requests

// The entry point of the application
void main() {
  runApp(const MyApp());
}

// The root widget of the application.
// StatelessWidget means this widget does not store any mutable state (variables that change).
class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Antigravity Connect',
      // Theme settings define the colors and fonts used throughout the app
      theme: ThemeData(
        // ColorScheme.fromSeed generates a full color palette from a single seed color
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true, // Enables the latest Material Design 3 guidelines
      ),
      home: const MyHomePage(title: 'Antigravity Connect'),
    );
  }
}

// A StatefulWidget IS capable of holding state. 
// This is needed because our list of messages (_messages) will change over time.
class MyHomePage extends StatefulWidget {
  const MyHomePage({super.key, required this.title});
  final String title;

  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

// The State class where the logic and mutable variables live
class _MyHomePageState extends State<MyHomePage> {
  // State variables
  bool _sending = false; // Is a message currently being sent? (Used to show spinner)
  List<NotificationItem> _messages = []; // Accessing our custom class to store messages
  bool _loading = true; // Are we currently fetching history?

  // initState is called exactly once when the widget is first created.
  // It's the perfect place to start loading initial data.
  @override
  void initState() {
    super.initState();
    _fetchMessages();
  }

  // Asynchronous function to fetch notification history from Ntfy.sh
  Future<void> _fetchMessages() async {
    setState(() {
      _loading = true; // Start loading spinner
    });

    try {
      // connecting to the Ntfy JSON stream API to get recent notifications
      // poll=1: Returns immediately after checking
      // since=12h: Returns notifications from the last 12 hours
      final response = await http.get(
        Uri.parse('https://ntfy.sh/antigrav_sam_notifications/json?poll=1&since=12h'),
      );

      if (response.statusCode == 200) {
        // The API returns multiple JSON objects, one per line.
        // We split the response body by newlines to get each message individually.
        final List<String> lines = response.body.split('\n');
        final List<NotificationItem> loaded = [];
        
        for (var line in lines) {
          if (line.trim().isEmpty) continue; // Skip empty lines
          try {
            // Parse the JSON string into a Map (key-value pairs)
            final data = jsonDecode(line);
            
            // We only care about 'message' events (ignoring keepalives, etc.)
            if (data['event'] == 'message') {
              loaded.add(NotificationItem(
                title: data['title'] ?? 'No Title', // Use 'No Title' if null
                message: data['message'] ?? '',
                // Convert unix timestamp (seconds) to DateTime object
                time: DateTime.fromMillisecondsSinceEpoch((data['time'] ?? 0) * 1000),
              ));
            }
          } catch (e) {
            // If a line is malformed, we just skip it
            print("Error parsing line: $e");
          }
        }
        
        // Update the state so the UI rebuilds with the new data
        setState(() {
          _messages = loaded.reversed.toList(); // Reverse so newest is at the top
        });
      }
    } catch (e) {
      print('Error fetching: $e');
    } finally {
      // This block runs whether try succeeded or failed
      setState(() {
        _loading = false; // Stop loading spinner
      });
    }
  }

  // Function to send a test notification from the phone BACK to the topic
  Future<void> _sendTestNotification() async {
    setState(() {
      _sending = true;
    });

    try {
      final response = await http.post(
        Uri.parse('https://ntfy.sh/antigrav_sam_notifications'),
        body: 'This is a test from your Mobile App!',
        headers: {
          'Title': 'Mobile Test',
          'Tags': 'mobile,testing', // Adds tags which might show as icons
        },
      );

      // Check if widget is still on screen before updating UI
      if (mounted) {
        if (response.statusCode == 200) {
          // Show a floating snackbar message at the bottom
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Test Notification Sent!')),
          );
          _fetchMessages(); // Refresh the list to show the new message
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Failed: ${response.statusCode}')),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _sending = false;
        });
      }
    }
  }

  // The build method attempts to draw the UI based on the current state.
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      // Top App Bar
      appBar: AppBar(
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        title: Text(widget.title),
        actions: [
          // Refresh button in the top right
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _fetchMessages,
          )
        ],
      ),
      // Main Body
      body: Column(
        children: [
          // Section 1: Header & Controls
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              children: [
                const Icon(Icons.mark_email_unread_outlined, size: 40, color: Colors.deepPurple),
                const SizedBox(height: 10),
                const Text(
                  'Connected to "antigrav_sam_notifications"',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 10),
                // Button to send test
                FilledButton.icon(
                  onPressed: _sending ? null : _sendTestNotification,
                  // Show spinner if sending, otherwise show icon
                  icon: _sending 
                      ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.send, size: 18),
                  label: const Text('Send Test'),
                ),
              ],
            ),
          ),
          const Divider(), // Visual separator line
          
          // Section 2: Notification List
          // Expanded ensures the list takes up all remaining vertical space
          Expanded(
            child: _loading 
              ? const Center(child: CircularProgressIndicator()) // internal loading spinner
              : _messages.isEmpty
                  ? const Center(child: Text("No recent notifications found."))
                  : ListView.builder(
                      itemCount: _messages.length,
                      itemBuilder: (context, index) {
                        final item = _messages[index];
                        // ListTile is a standard row widget for lists
                        return ListTile(
                          leading: const Icon(Icons.notifications),
                          title: Text(item.title, style: const TextStyle(fontWeight: FontWeight.bold)),
                          subtitle: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(item.message),
                              // Display time in a basic format
                              Text(
                                item.time.toString().substring(0, 16),
                                style: TextStyle(fontSize: 10, color: Colors.grey[600]),
                              ),
                            ],
                          ),
                        );
                      },
                    ),
          ),
        ],
      ),
    );
  }
}

// A simple data class to hold notification information
class NotificationItem {
  final String title;
  final String message;
  final DateTime time;

  NotificationItem({required this.title, required this.message, required this.time});
}
