import sqlite3
import os

DATABASE_PATH = 'proctoring.db'

def init_db():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Tests table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            duration_minutes INTEGER NOT NULL,
            questions TEXT NOT NULL,  -- JSON string
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Test sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_sessions (
            id TEXT PRIMARY KEY,  -- UUID
            test_id INTEGER NOT NULL,
            student_name TEXT NOT NULL,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP,
            status TEXT NOT NULL,  -- IN_PROGRESS, COMPLETED, TERMINATED
            score REAL,
            answers TEXT,  -- JSON string
            cheating_score REAL DEFAULT 0,
            FOREIGN KEY (test_id) REFERENCES tests (id)
        )
    ''')
    
    # Cheating logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cheating_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            violation_type TEXT NOT NULL,  -- FACE_DETECTION, PHONE_DETECTED, MULTIPLE_PERSONS, AUDIO_VIOLATION, TAB_SWITCH
            description TEXT NOT NULL,
            severity TEXT NOT NULL,  -- LOW, MEDIUM, HIGH
            timestamp TIMESTAMP NOT NULL,
            evidence_path TEXT,  -- Path to screenshot or audio file
            evidence_blob BLOB,  -- Optional binary evidence stored in DB
            metadata TEXT,  -- Additional JSON data
            FOREIGN KEY (session_id) REFERENCES test_sessions (id)
        )
    ''')
    
    # Insert sample test data if tables are empty
    cursor.execute('SELECT COUNT(*) FROM tests')
    if cursor.fetchone()[0] == 0:
        sample_questions = [
            {
                "type": "multiple_choice",
                "question": "What is the capital of France?",
                "options": ["London", "Berlin", "Paris", "Madrid"],
                "correct_answer": 2
            },
            {
                "type": "multiple_choice", 
                "question": "Which programming language is known for its use in web development?",
                "options": ["C++", "JavaScript", "Assembly", "COBOL"],
                "correct_answer": 1
            },
            {
                "type": "multiple_choice",
                "question": "What does HTML stand for?",
                "options": ["Hyper Text Markup Language", "High Tech Modern Language", "Home Tool Markup Language", "Hyperlink Text Management Language"],
                "correct_answer": 0
            },
            {
                "type": "multiple_choice",
                "question": "Which of these is a Python web framework?",
                "options": ["React", "Angular", "Django", "Vue.js"],
                "correct_answer": 2
            },
            {
                "type": "multiple_choice",
                "question": "What is the time complexity of binary search?",
                "options": ["O(n)", "O(log n)", "O(n²)", "O(1)"],
                "correct_answer": 1
            }
        ]
        
        cursor.execute('''
            INSERT INTO tests (title, description, duration_minutes, questions)
            VALUES (?, ?, ?, ?)
        ''', ('Sample Programming Test', 
              'A basic test covering programming concepts and web development',
              30, 
              str(sample_questions).replace("'", '"')))
    
    conn.commit()
    conn.close()

def get_db_connection():
    """Get database connection with row factory for easier access"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def calculate_cheating_score(session_id):
    """Calculate cheating probability score based on violations"""
    conn = get_db_connection()
    
    # Get all violations for the session
    violations = conn.execute('''
        SELECT violation_type, severity, COUNT(*) as count
        FROM cheating_logs 
        WHERE session_id = ?
        GROUP BY violation_type, severity
    ''', (session_id,)).fetchall()
    
    # Scoring weights
    severity_weights = {'LOW': 1, 'MEDIUM': 3, 'HIGH': 5}
    violation_weights = {
        'FACE_DETECTION': 2,
        'PHONE_DETECTED': 4,
        'MULTIPLE_PERSONS': 5,
        'AUDIO_VIOLATION': 3,
        'TAB_SWITCH': 2
    }
    
    total_score = 0
    for violation in violations:
        severity_multiplier = severity_weights.get(violation['severity'], 1)
        violation_multiplier = violation_weights.get(violation['violation_type'], 1)
        count = violation['count']
        
        total_score += severity_multiplier * violation_multiplier * count
    
    # Normalize to 0-100 scale (max theoretical score of 150)
    cheating_score = min(100, (total_score / 150) * 100)
    
    # Update session with cheating score
    conn.execute('''
        UPDATE test_sessions 
        SET cheating_score = ? 
        WHERE id = ?
    ''', (cheating_score, session_id))
    
    conn.commit()
    conn.close()
    
    return cheating_score