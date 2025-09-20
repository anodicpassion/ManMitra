from flask import Flask, render_template, request, redirect, url_for
import os
import glob

app = Flask(__name__)

# Get all HTML files from the stitch_journaling_dashboard directory
def get_html_files():
    html_files = []
    dashboard_path = os.path.join(os.path.dirname(__file__), 'stitch_journaling_dashboard')
    
    # Find all code.html files recursively
    for root, dirs, files in os.walk(dashboard_path):
        for file in files:
            if file == 'code.html':
                # Get the relative path from dashboard directory
                rel_path = os.path.relpath(root, dashboard_path)
                # Create a route name from the directory name
                route_name = rel_path.replace('/', '_').replace(' ', '_').replace('(', '').replace(')', '').replace('&', 'and').replace('-', '_').lower()
                html_files.append({
                    'route_name': route_name,
                    'file_path': os.path.join(root, file),
                    'display_name': rel_path.replace('_', ' ').title()
                })
    
    return html_files

# Get all HTML files
html_files = get_html_files()

@app.route('/')
def index():
    """Home page with navigation to all screens"""
    return render_template('index.html', screens=html_files)

@app.route('/dashboard')
def dashboard():
    """Main journaling dashboard"""
    return render_template('stitch_journaling_dashboard/journaling_dashboard_4/code.html')

@app.route('/login')
def login():
    """Login/signup screen"""
    return render_template('stitch_journaling_dashboard/login/signup_screen_1/code.html')

@app.route('/ai-chat')
def ai_chat():
    """AI companion chat"""
    return render_template('stitch_journaling_dashboard/ai_companion_chat_screen_1/code.html')

@app.route('/peer-support')
def peer_support():
    """Peer support forum"""
    return render_template('stitch_journaling_dashboard/peer_support_forum_1/code.html')

@app.route('/settings')
def settings():
    """Settings page"""
    return render_template('stitch_journaling_dashboard/account_settings_screen_2/code.html')

# Dynamic routes for all other screens
for html_file in html_files:
    route_name = html_file['route_name']
    file_path = html_file['file_path']
    
    # Skip the ones we already defined above
    if route_name in ['journaling_dashboard_4', 'login_signup_screen_1', 'ai_companion_chat_screen_1', 'peer_support_forum_1', 'account_settings_screen_2']:
        continue
    
    # Create route function dynamically
    def make_route_handler(file_path):
        def route_handler():
            template_path = file_path.replace(os.path.join(os.path.dirname(__file__), 'stitch_journaling_dashboard') + '/', 'stitch_journaling_dashboard/')
            return render_template(template_path)
        return route_handler
    
    # Add the route
    app.add_url_rule(f'/{route_name}', route_name, make_route_handler(file_path))

# Navigation helper routes
@app.route('/navigate/<screen_name>')
def navigate(screen_name):
    """Navigate to any screen by name"""
    for html_file in html_files:
        if html_file['route_name'] == screen_name:
            return redirect(url_for(html_file['route_name']))
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5500)
