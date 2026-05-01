"""Firebase Realtime Database integratsiyasi"""
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
import os

class FirebaseDB:
    def __init__(self):
        self.app = None
        self.db = None
        self.is_initialized = False
    
    def initialize(self, database_url, credential_path=None):
        """Firebase ni ishga tushirish"""
        try:
            if not self.is_initialized:
                if credential_path and os.path.exists(credential_path):
                    cred = credentials.Certificate(credential_path)
                    self.app = firebase_admin.initialize_app(cred, {
                        'databaseURL': database_url
                    })
                else:
                    # Anonymous auth (faqat o'qish uchun ruxsat bo'lsa)
                    self.app = firebase_admin.initialize_app(None, {
                        'databaseURL': database_url
                    })
                
                self.db = db.reference('/')
                self.is_initialized = True
                print("[OK] Firebase muvaffaqiyatli ulandi!")
                return True
        except Exception as e:
            print(f"[XATO] Firebase ulanish xatosi: {e}")
            return False
    
    # =========== USERS ===========
    def save_user(self, telegram_id, name, phone=None, user_type=None):
        """Foydalanuvchini saqlash"""
        if not self.is_initialized:
            return False
        
        user_data = {
            'telegram_id': telegram_id,
            'name': name,
            'phone': phone,
            'user_type': user_type,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        self.db.child('users').child(str(telegram_id)).set(user_data)
        return True
    
    def get_user(self, telegram_id):
        """Foydalanuvchi ma'lumotlarini olish"""
        if not self.is_initialized:
            return None
        return self.db.child('users').child(str(telegram_id)).get()
    
    def get_all_users(self):
        """Barcha foydalanuvchilarni olish"""
        if not self.is_initialized:
            return []
        users = self.db.child('users').get()
        return list(users.values()) if users else []
    
    # =========== ORDERS ===========
    def create_order(self, order_id, user_id, order_type, destination, passenger_count=1):
        """Yangi buyurtma yaratish"""
        if not self.is_initialized:
            return False
        
        order_data = {
            'id': order_id,
            'user_id': user_id,
            'order_type': order_type,
            'destination': destination,
            'passenger_count': passenger_count,
            'driver_id': None,
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        self.db.child('orders').child(str(order_id)).set(order_data)
        return True
    
    def assign_order(self, order_id, driver_id):
        """Buyurtmani haydovchiga biriktirish"""
        if not self.is_initialized:
            return False
        
        self.db.child('orders').child(str(order_id)).update({
            'driver_id': driver_id,
            'status': 'assigned',
            'updated_at': datetime.now().isoformat()
        })
        return True
    
    def complete_order(self, order_id):
        """Buyurtmani tugatish"""
        if not self.is_initialized:
            return False
        
        self.db.child('orders').child(str(order_id)).update({
            'status': 'completed',
            'completed_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        })
        return True
    
    def get_order(self, order_id):
        """Buyurtma ma'lumotlarini olish"""
        if not self.is_initialized:
            return None
        return self.db.child('orders').child(str(order_id)).get()
    
    def get_pending_orders(self):
        """Kutilayotgan buyurtmalarni olish"""
        if not self.is_initialized:
            return []
        
        orders = self.db.child('orders').get()
        if not orders:
            return []
        return [o for o in orders.values() if o.get('status') == 'pending']
    
    def get_driver_orders(self, driver_id):
        """Haydovchining buyurtmalarini olish"""
        if not self.is_initialized:
            return []
        
        orders = self.db.child('orders').get()
        if not orders:
            return []
        return [o for o in orders.values() if o.get('driver_id') == driver_id]
    
    # =========== DRIVERS ===========
    def save_driver(self, telegram_id, name, phone, status='active'):
        """Haydovchini saqlash"""
        if not self.is_initialized:
            return False
        
        driver_data = {
            'telegram_id': telegram_id,
            'name': name,
            'phone': phone,
            'status': status,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        self.db.child('drivers').child(str(telegram_id)).set(driver_data)
        return True
    
    def get_driver(self, telegram_id):
        """Haydovchi ma'lumotlarini olish"""
        if not self.is_initialized:
            return None
        return self.db.child('drivers').child(str(telegram_id)).get()
    
    def update_driver_status(self, telegram_id, status):
        """Haydovchi statusini yangilash"""
        if not self.is_initialized:
            return False
        
        self.db.child('drivers').child(str(telegram_id)).update({
            'status': status,
            'updated_at': datetime.now().isoformat()
        })
        return True
    
    def get_active_drivers(self):
        """Faol haydovchilar ro'yxatini olish"""
        if not self.is_initialized:
            return []
        
        drivers = self.db.child('drivers').get()
        if not drivers:
            return []
        return [d for d in drivers.values() if d.get('status') == 'active']
    
    # =========== DRIVER APPLICATIONS ===========
    def save_application(self, app_id, telegram_id, name, phone, status='pending'):
        """Haydovchi arizasini saqlash"""
        if not self.is_initialized:
            return False
        
        self.db.child('applications').child(str(app_id)).set({
            'id': app_id,
            'telegram_id': telegram_id,
            'name': name,
            'phone': phone,
            'status': status,
            'created_at': datetime.now().isoformat()
        })
        return True
    
    def update_application_status(self, app_id, status):
        """Ariza statusini yangilash"""
        if not self.is_initialized:
            return False
        
        self.db.child('applications').child(str(app_id)).update({
            'status': status,
            'updated_at': datetime.now().isoformat()
        })
        return True
    
    def get_pending_applications(self):
        """Kutilayotgan arizalarni olish"""
        if not self.is_initialized:
            return []
        
        apps = self.db.child('applications').get()
        if not apps:
            return []
        return [a for a in apps.values() if a.get('status') == 'pending']
    
    # =========== STATISTICS ===========
    def get_statistics(self):
        """Bot statistikasini olish"""
        if not self.is_initialized:
            return {}
        
        users = self.db.child('users').get() or {}
        orders = self.db.child('orders').get() or {}
        drivers = self.db.child('drivers').get() or {}
        
        total_orders = len(orders)
        completed = sum(1 for o in orders.values() if o.get('status') == 'completed')
        pending = sum(1 for o in orders.values() if o.get('status') == 'pending')
        
        return {
            'total_users': len(users),
            'total_drivers': len(drivers),
            'total_orders': total_orders,
            'completed_orders': completed,
            'pending_orders': pending,
            'active_drivers': sum(1 for d in drivers.values() if d.get('status') == 'active')
        }

# Global instance
firebase_db = FirebaseDB()
