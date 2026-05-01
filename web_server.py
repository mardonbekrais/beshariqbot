"""Web server for health checks and keeping bot alive"""
from flask import Flask, jsonify
import threading
import subprocess
import signal
import sys
import os

app = Flask(__name__)

# Global variable to track bot process
bot_process = None

@app.route('/')
def home():
    """Asosiy sahifa - UptimeRobot uchun"""
    return jsonify({
        'status': 'ok',
        'service': 'TaxiBot',
        'message': 'Bot is running',
        'version': '1.0.0'
    }), 200

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'TaxiBot',
        'bot_status': 'running' if bot_process and bot_process.poll() is None else 'stopped',
        'firebase_connected': True
    }), 200

@app.route('/health', methods=['HEAD'])
def health_head():
    """HEAD request for health check"""
    return '', 200

@app.route('/', methods=['HEAD'])
def home_head():
    """HEAD request for home page"""
    return '', 200

def start_bot():
    """Telegram botni background da ishga tushirish"""
    global bot_process
    try:
        # Botni alohida process da ishga tushurish
        bot_process = subprocess.Popen([
            sys.executable, 'app.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print("[OK] Telegram bot background da ishga tushirildi")
        return bot_process
    except Exception as e:
        print(f"[XATO] Botni ishga tushurish xatosi: {e}")
        return None

def signal_handler(signum, frame):
    """Signal handler for graceful shutdown"""
    global bot_process
    print("\n[STOP] Server to'xtatilmoqda...")
    
    if bot_process:
        bot_process.terminate()
        bot_process.wait()
        print("[OK] Bot to'xtatildi")
    
    sys.exit(0)

if __name__ == '__main__':
    # Signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Botni ishga tushurish
    start_bot()
    
    # Web serverni ishga tushurish
    port = int(os.environ.get('PORT', 5000))
    print(f"[WEB] Web server {port} portda ishga tushirildi...")
    
    app.run(host='0.0.0.0', port=port, debug=False)
