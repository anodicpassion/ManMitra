# ManMitra - Mental Wellness Journaling Dashboard

A Flask web application that connects all the HTML screens from the stitch_journaling_dashboard folder with simple navigation routes.

## Features

- **Simple Navigation**: All HTML screens are accessible through Flask routes
- **Main Screens**: Dashboard, AI Chat, Peer Support, Login, Settings
- **Complete Screen Library**: Access to all 50+ screens in the dashboard
- **Responsive Design**: Mobile-friendly interface with Tailwind CSS

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

1. Start the Flask development server:
```bash
python app.py
```

2. Open your browser and navigate to:
```
http://localhost:5000
```

## Available Routes

### Main Navigation
- `/` - Home page with navigation to all screens
- `/dashboard` - Main journaling dashboard
- `/ai-chat` - AI companion chat interface
- `/peer-support` - Peer support forum
- `/login` - Login/signup screen
- `/settings` - Account settings

### All Other Screens
All other screens are automatically available at `/{screen_name}` where screen_name is derived from the folder name.

Examples:
- `/about_us_screen_1`
- `/achievements_and_badges_screen_1`
- `/crisis_support_screen_2`
- `/mood_analytics_screen_1`

## Project Structure

```
ManMitra/
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── templates/                      # HTML templates
│   ├── index.html                 # Navigation home page
│   └── stitch_journaling_dashboard/ # All screen HTML files
└── README.md                      # This file
```

## Navigation

The application includes bottom navigation bars in most screens that allow easy movement between:
- AI Chat
- Journal Dashboard
- Peer Support
- Settings

## Development

The Flask app automatically discovers all HTML files in the `stitch_journaling_dashboard` directory and creates routes for them. To add new screens, simply add HTML files to the appropriate folder structure.

## Notes

- This is a simple navigation demo without backend functionality
- No authentication or data persistence is implemented
- All screens are accessible for demonstration purposes