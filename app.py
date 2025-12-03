from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_socketio import SocketIO, emit, join_room, leave_room
import sqlite3
import json
import os
import base64
from datetime import datetime
import uuid
from detection.proctoring_monitor import ProctoringMonitor
from models.database import init_db, get_db_connection

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Custom template filters
@app.template_filter('duration')
def duration_filter(start_time, end_time):
    """Calculate duration in minutes between two datetime strings"""
    if not start_time or not end_time:
        return "N/A"
    try:
        start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        duration_minutes = (end - start).total_seconds() / 60
        return f"{duration_minutes:.1f} min"
    except:
        return "N/A"

# Initialize database
init_db()

# Global monitoring instances
active_monitors = {}

@app.route('/')
def index():
    """Landing page with role selection"""
    return render_template('index.html')

@app.route('/admin')
def admin_dashboard():
    """Admin dashboard to view test results and cheating logs"""
    conn = get_db_connection()
    
    # Get all test sessions with cheating scores
    sessions = conn.execute('''
        SELECT s.*, COUNT(cl.id) as violation_count,
               AVG(CASE WHEN cl.severity = 'HIGH' THEN 3 
                       WHEN cl.severity = 'MEDIUM' THEN 2 
                       ELSE 1 END) as avg_severity
        FROM test_sessions s
        LEFT JOIN cheating_logs cl ON s.id = cl.session_id
        GROUP BY s.id
        ORDER BY s.start_time DESC
    ''').fetchall()
    
    conn.close()
    return render_template('admin_dashboard.html', sessions=sessions)

@app.route('/admin/session/<session_id>')
def view_session_details(session_id):
    """View detailed cheating logs for a specific session"""
    conn = get_db_connection()
    
    session = conn.execute('SELECT * FROM test_sessions WHERE id = ?', (session_id,)).fetchone()
    logs = conn.execute('''
        SELECT * FROM cheating_logs 
        WHERE session_id = ? 
        ORDER BY timestamp DESC
    ''', (session_id,)).fetchall()
    
    conn.close()
    return render_template('session_details.html', session=session, logs=logs)

@app.route('/admin/create_test')
def create_test():
    """Page to create a new test"""
    return render_template('create_test.html')

@app.route('/admin/save_test', methods=['POST'])
def save_test():
    """Save a new test to database"""
    test_data = request.json
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Insert test
    cursor.execute('''
        INSERT INTO tests (title, description, duration_minutes, questions)
        VALUES (?, ?, ?, ?)
    ''', (test_data['title'], test_data['description'], 
          test_data['duration'], json.dumps(test_data['questions'])))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/student')
def student_portal():
    """Student portal to select and start tests"""
    conn = get_db_connection()
    tests = conn.execute('SELECT * FROM tests ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('student_portal.html', tests=tests)

@app.route('/test/<test_id>')
def take_test(test_id):
    """Test taking interface with monitoring"""
    conn = get_db_connection()
    test = conn.execute('SELECT * FROM tests WHERE id = ?', (test_id,)).fetchone()
    
    if not test:
        return redirect(url_for('student_portal'))
    
    # Create test session
    session_id = str(uuid.uuid4())
    student_name = request.args.get('student_name', 'Anonymous')
    
    conn.execute('''
        INSERT INTO test_sessions (id, test_id, student_name, start_time, status)
        VALUES (?, ?, ?, ?, ?)
    ''', (session_id, test_id, student_name, datetime.now().isoformat(), 'IN_PROGRESS'))
    
    conn.commit()
    conn.close()
    
    # Parse questions
    questions = json.loads(test['questions'])
    
    return render_template('test_interface.html', 
                         test=test, 
                         questions=questions,
                         session_id=session_id)

@app.route('/api/submit_test', methods=['POST'])
def submit_test():
    """Submit test answers and calculate score"""
    data = request.json
    session_id = data['session_id']
    answers = data['answers']
    
    conn = get_db_connection()
    
    # Get test questions to calculate score
    test = conn.execute('''
        SELECT t.* FROM tests t
        JOIN test_sessions ts ON t.id = ts.test_id
        WHERE ts.id = ?
    ''', (session_id,)).fetchone()
    
    questions = json.loads(test['questions'])
    correct_answers = 0
    total_questions = len(questions)
    
    # Calculate score
    for i, question in enumerate(questions):
        if question['type'] == 'multiple_choice':
            if answers.get(str(i)) == question['correct_answer']:
                correct_answers += 1
    
    score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
    
    # Update session
    conn.execute('''
        UPDATE test_sessions 
        SET end_time = ?, status = ?, score = ?, answers = ?
        WHERE id = ?
    ''', (datetime.now().isoformat(), 'COMPLETED', score, json.dumps(answers), session_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'score': score})

@socketio.on('start_monitoring')
def handle_start_monitoring(data):
    """Start proctoring monitoring for a session"""
    session_id = data['session_id']
    room = f"session_{session_id}"
    join_room(room)
    
    # Initialize monitoring for this session
    if session_id not in active_monitors:
        active_monitors[session_id] = ProctoringMonitor(session_id)
    
    emit('monitoring_started', {'session_id': session_id})

@socketio.on('video_frame')
def handle_video_frame(data):
    """Process video frame for violations"""
    session_id = data['session_id']
    frame_data = data['frame']
    
    if session_id in active_monitors:
        monitor = active_monitors[session_id]
        violations = monitor.process_frame(frame_data)
        
        if violations:
            # Emit violations to admin
            emit('violation_detected', {
                'session_id': session_id,
                'violations': violations,
                'timestamp': datetime.now().isoformat()
            }, room=f"admin")

@socketio.on('audio_data')
def handle_audio_data(data):
    """Process audio data for violations"""
    session_id = data['session_id']
    audio_data = data['audio']
    
    if session_id in active_monitors:
        monitor = active_monitors[session_id]
        violations = monitor.process_audio(audio_data)
        
        if violations:
            emit('violation_detected', {
                'session_id': session_id,
                'violations': violations,
                'timestamp': datetime.now().isoformat()
            }, room=f"admin")

@socketio.on('tab_switch')
def handle_tab_switch(data):
    """Log tab switching violation"""
    session_id = data['session_id']
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO cheating_logs (session_id, violation_type, description, severity, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (session_id, 'TAB_SWITCH', 'Student switched browser tabs', 'MEDIUM', 
          datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    emit('violation_detected', {
        'session_id': session_id,
        'violations': [{'type': 'TAB_SWITCH', 'description': 'Tab switching detected'}],
        'timestamp': datetime.now().isoformat()
    }, room=f"admin")

@socketio.on('join_admin')
def handle_join_admin():
    """Join admin room for monitoring"""
    join_room('admin')

@socketio.on('stop_monitoring')
def handle_stop_monitoring(data):
    """Stop monitoring for a session"""
    session_id = data['session_id']
    
    if session_id in active_monitors:
        del active_monitors[session_id]
    
    leave_room(f"session_{session_id}")

if __name__ == '__main__':
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)