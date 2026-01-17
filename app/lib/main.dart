import 'dart:async'; // Required for Timer
import 'dart:convert'; // Allows us to convert JSON strings to Objects and vice versa
import 'package:flutter/material.dart'; // The core Flutter UI framework
import 'package:http/http.dart' as http; // A package to make HTTP web requests

// The entry point of the application
void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Antigravity Connect',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true,
      ),
      home: const MyHomePage(title: 'Antigravity Connect'),
    );
  }
}

class MyHomePage extends StatefulWidget {
  const MyHomePage({super.key, required this.title});
  final String title;

  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  // State variables
  bool _sending = false;
  List<NotificationItem> _messages = [];
  bool _loading = true;
  
  // Polling variables
  Timer? _timer;
  int? _selectedInterval = 60; // Default to 60 seconds. null means "Manual"

  // Options for the dropdown
  final Map<int?, String> _intervalOptions = {
    null: 'Manual (Push Only)',
    10: 'Every 10 sec (High Battery)',
    30: 'Every 30 sec',
    60: 'Every 1 min (Recommended)',
    300: 'Every 5 min',
  };

  @override
  void initState() {
    super.initState();
    _fetchMessages();
    _startPolling();
  }

  @override
  void dispose() {
    _timer?.cancel(); // Always clean up timers!
    super.dispose();
  }

  void _startPolling() {
    _timer?.cancel(); // Cancel any existing timer
    
    if (_selectedInterval != null) {
      _timer = Timer.periodic(Duration(seconds: _selectedInterval!), (timer) {
        // We do a "silent" fetch - don't show loading spinner for background polls
        _fetchMessages(silent: true);
      });
    }
  }

  void _onIntervalChanged(int? newValue) {
    setState(() {
      _selectedInterval = newValue;
    });
    _startPolling();
    
    // Feedback to user
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(newValue == null 
          ? "Polling stopped. Tap refresh to update." 
          : "Polling enabled: ${_intervalOptions[newValue]}"),
        duration: const Duration(seconds: 2),
      ),
    );
  }

  // Fetch messages. 'silent' determines if we show the loading spinner.
  Future<void> _fetchMessages({bool silent = false}) async {
    if (!silent) {
      setState(() {
        _loading = true;
      });
    }

    try {
      final response = await http.get(
        Uri.parse('https://ntfy.sh/antigrav_sam_notifications/json?poll=1&since=12h'),
      );

      if (response.statusCode == 200) {
        final List<String> lines = response.body.split('\n');
        final List<NotificationItem> loaded = [];
        
        for (var line in lines) {
          if (line.trim().isEmpty) continue;
          try {
            final data = jsonDecode(line);
            if (data['event'] == 'message') {
              loaded.add(NotificationItem(
                title: data['title'] ?? 'No Title',
                message: data['message'] ?? '',
                time: DateTime.fromMillisecondsSinceEpoch((data['time'] ?? 0) * 1000),
              ));
            }
          } catch (e) {
            print("Error parsing line: $e");
          }
        }
        
        // Only update state if data changed to avoid unnecessary rebuilds (simple check)
        if (mounted) {
            setState(() {
            _messages = loaded.reversed.toList();
            });
        }
      }
    } catch (e) {
      print('Error fetching: $e');
    } finally {
      if (mounted && !silent) {
        setState(() {
          _loading = false;
        });
      }
    }
  }

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
          'Tags': 'mobile,testing',
        },
      );

      if (mounted) {
        if (response.statusCode == 200) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Test Notification Sent!')),
          );
          _fetchMessages();
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        title: Text(widget.title),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh Now',
            onPressed: () => _fetchMessages(silent: false),
          )
        ],
      ),
      body: Column(
        children: [
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
                
                // --- New Polling Controls ---
                const SizedBox(height: 16),
                Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                    decoration: BoxDecoration(
                        color: Colors.deepPurple.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(8),
                    ),
                    child: DropdownButtonHideUnderline(
                        child: DropdownButton<int?>(
                            value: _selectedInterval,
                            isDense: true,
                            hint: const Text("Select Update Speed"),
                            icon: const Icon(Icons.timer_outlined, color: Colors.deepPurple),
                            style: const TextStyle(color: Colors.deepPurple, fontWeight: FontWeight.bold),
                            onChanged: _onIntervalChanged,
                            items: _intervalOptions.entries.map((entry) {
                                return DropdownMenuItem<int?>(
                                    value: entry.key,
                                    child: Text(entry.value),
                                );
                            }).toList(),
                        ),
                    ),
                ),
                // ----------------------------
                
                const SizedBox(height: 16),
                FilledButton.icon(
                  onPressed: _sending ? null : _sendTestNotification,
                  icon: _sending 
                      ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.send, size: 18),
                  label: const Text('Send Test'),
                ),
              ],
            ),
          ),
          const Divider(),
          Expanded(
            child: _loading 
              ? const Center(child: CircularProgressIndicator())
              : _messages.isEmpty
                  ? const Center(child: Text("No recent notifications found."))
                  : ListView.builder(
                      itemCount: _messages.length,
                      itemBuilder: (context, index) {
                        return NotificationTile(item: _messages[index]);
                      },
                    ),
          ),
        ],
      ),
    );
  }
}

class NotificationTile extends StatefulWidget {
  final NotificationItem item;
  const NotificationTile({super.key, required this.item});

  @override
  State<NotificationTile> createState() => _NotificationTileState();
}

class _NotificationTileState extends State<NotificationTile> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      // Use InkWell for the ripple effect on tap
      child: InkWell(
        onTap: () {
          setState(() {
            _expanded = !_expanded;
          });
        },
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(12.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header Row: Icon + Title + Time
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.notifications, color: Colors.deepPurple),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          widget.item.title,
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                        ),
                        Text(
                          widget.item.time.toString().substring(0, 16),
                          style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                        ),
                      ],
                    ),
                  ),
                  Icon(
                    _expanded ? Icons.expand_less : Icons.expand_more,
                    color: Colors.grey,
                  ),
                ],
              ),
              const SizedBox(height: 8),
              // Body Text
              // If collapsed, we chop the string to ~100 chars or use maxLines
              // User asked for "max character limit", but maxLines is safer for layout.
              // We'll interpret it as a short preview.
              Text(
                widget.item.message,
                style: const TextStyle(fontSize: 14),
                maxLines: _expanded ? null : 2, // 2 lines collapsed, unlimited extended
                overflow: _expanded ? TextOverflow.visible : TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class NotificationItem {
  final String title;
  final String message;
  final DateTime time;

  NotificationItem({required this.title, required this.message, required this.time});
}
