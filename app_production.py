"""
Production Flask Web Application - Integrated Capitalization Checker
Ready for public deployment with security features
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from integrated_capitalizer import IntegratedCapitalizer
import os
import time
import logging
from logging.handlers import RotatingFileHandler
from functools import wraps

app = Flask(__name__)

# Production config
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-this-in-production-please')
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1MB max request size

# Enable CORS for API routes
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Setup logging
if not app.debug:
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Capitalization Checker startup')

# Global checker instance
checker = None

# Simple rate limiting (in-memory)
request_counts = {}
RATE_LIMIT = 100  # requests per minute per IP

def rate_limit(f):
    """Rate limiting decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ip = request.remote_addr
        current_time = time.time()
        
        if ip not in request_counts:
            request_counts[ip] = []
        
        # Remove requests older than 1 minute
        request_counts[ip] = [t for t in request_counts[ip] if current_time - t < 60]
        
        if len(request_counts[ip]) >= RATE_LIMIT:
            app.logger.warning(f'Rate limit exceeded for IP: {ip}')
            return jsonify({'error': 'Rate limit exceeded. Please try again in a minute.'}), 429
        
        request_counts[ip].append(current_time)
        return f(*args, **kwargs)
    
    return decorated_function

def get_checker():
    """Lazy initialization of checker"""
    global checker
    if checker is None:
        db_path = os.environ.get('DATABASE_PATH', 
                                 os.path.join(os.path.dirname(__file__), 'geonames.db'))
        
        if not os.path.exists(db_path):
            app.logger.error(f'Database not found at {db_path}')
            raise FileNotFoundError(f'Database not found. Please run geonames_downloader.py first.')
        
        checker = IntegratedCapitalizer(db_path)
        app.logger.info('Capitalization checker initialized successfully')
    
    return checker

@app.route('/')
def index():
    """Render main page"""
    return render_template('index.html')

@app.route('/api/check', methods=['POST'])
@rate_limit
def check_text():
    """API endpoint to check text capitalization"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        if len(text) > 10000:
            return jsonify({'error': 'Text too long. Maximum 10,000 characters.'}), 400
        
        checker = get_checker()
        result = checker.analyze_text(text)
        
        app.logger.info(f'Check completed: {result["total_corrections"]} corrections')
        return jsonify(result)
        
    except FileNotFoundError as e:
        app.logger.error(f'Database error: {str(e)}')
        return jsonify({'error': 'Database not available'}), 503
    except Exception as e:
        app.logger.error(f'Error in check_text: {str(e)}')
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/check-word', methods=['POST'])
@rate_limit
def check_word():
    """API endpoint to check a single word"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        word = data.get('word', '').strip()
        context = data.get('context', '').strip()
        
        if not word:
            return jsonify({'error': 'No word provided'}), 400
        
        if len(word) > 100:
            return jsonify({'error': 'Word too long'}), 400
        
        checker = get_checker()
        needs_correction, correct_form, reason = checker.check_word(word, context)
        
        return jsonify({
            'word': word,
            'needs_correction': needs_correction,
            'correct_form': correct_form,
            'reason': reason
        })
        
    except FileNotFoundError as e:
        app.logger.error(f'Database error: {str(e)}')
        return jsonify({'error': 'Database not available'}), 503
    except Exception as e:
        app.logger.error(f'Error in check_word: {str(e)}')
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get database statistics"""
    try:
        checker = get_checker()
        
        # Get count of geographic names
        cursor = checker.geo_checker.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM geonames")
        geo_count = cursor.fetchone()[0]
        
        # Get count by feature class
        cursor.execute("""
            SELECT feature_class, COUNT(*) 
            FROM geonames 
            GROUP BY feature_class
        """)
        feature_counts = dict(cursor.fetchall())
        
        return jsonify({
            'total_geographic_names': geo_count,
            'feature_counts': feature_counts,
            'rule_categories': len(checker.rules)
        })
        
    except FileNotFoundError as e:
        app.logger.error(f'Database error: {str(e)}')
        return jsonify({'error': 'Database not available'}), 503
    except Exception as e:
        app.logger.error(f'Error in get_stats: {str(e)}')
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/health')
def health():
    """Health check endpoint for monitoring"""
    try:
        checker = get_checker()
        # Quick database test
        result = checker.geo_checker.lookup_name('Paris')
        
        if result:
            return jsonify({
                'status': 'healthy',
                'database': 'connected',
                'entries': 'accessible'
            }), 200
        else:
            return jsonify({
                'status': 'degraded',
                'database': 'connected',
                'entries': 'empty'
            }), 200
            
    except FileNotFoundError:
        return jsonify({
            'status': 'unhealthy',
            'database': 'not_found'
        }), 503
    except Exception as e:
        app.logger.error(f'Health check failed: {str(e)}')
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    app.logger.error(f'Internal error: {str(error)}')
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(413)
def request_too_large(error):
    """Handle request too large errors"""
    return jsonify({'error': 'Request too large. Maximum 1MB.'}), 413

# For development
if __name__ == '__main__':
    # Check if database exists
    if not os.path.exists('geonames.db'):
        print("ERROR: geonames.db not found!")
        print("Please run 'python geonames_downloader.py' first to create the database.")
        exit(1)
    
    print("\n" + "=" * 60)
    print("Integrated Capitalization Checker - DEVELOPMENT MODE")
    print("=" * 60)
    print("\nStarting server...")
    print("Open http://localhost:5000 in your browser")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)

# For production (gunicorn)
else:
    # Production initialization
    if not os.path.exists('logs'):
        os.mkdir('logs')
