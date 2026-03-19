"""
Government-Grade Zoning Compliance Checker
Enterprise solution for government contractors and municipalities
Version: 2.0.0
Features: Authentication, Audit Logging, Database Integration, Security Compliance
"""

import os
import sys
import json
import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
from functools import wraps

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import jwt
from cryptography.fernet import Fernet

# Configure structured logging for government compliance
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s] - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'compliance_system.log')),
        logging.StreamHandler()
    ]
)

# Audit logger for government compliance tracking
audit_logger = logging.getLogger('audit')
audit_handler = logging.FileHandler(os.path.join(log_dir, 'audit.log'))
audit_handler.setFormatter(logging.Formatter(
    '%(asctime)s - AUDIT - User: %(user)s - Action: %(action)s - Details: %(message)s'
))
audit_logger.addHandler(audit_handler)

logger = logging.getLogger(__name__)

class UserRole(Enum):
    """User roles for government access control"""
    ADMIN = "admin"
    ANALYST = "analyst"
    REVIEWER = "reviewer"
    VIEWER = "viewer"

class AgencyType(Enum):
    """Government agency types"""
    FEDERAL = "federal"
    STATE = "state"
    COUNTY = "county"
    MUNICIPAL = "municipal"
    TRIBAL = "tribal"
    PRIVATE = "private"

class ComplianceStatus(Enum):
    """Compliance status enumeration"""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    REQUIRES_REVIEW = "requires_review"
    INSUFFICIENT_DATA = "insufficient_data"

# Government Security Constants
SESSION_TIMEOUT = 3600  # 1 hour
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 900  # 15 minutes

# In-memory user database (replace with real database in production)
class UserDatabase:
    """Government-grade user management system"""
    
    def __init__(self):
        self.users = {}
        self.login_attempts = {}
        self.session_tokens = {}
        self._create_default_users()
    
    def _create_default_users(self):
        """Create default government users for demonstration"""
        default_users = [
            {
                'username': 'admin',
                'password': generate_password_hash('AdminGov2024!'),
                'email': 'admin@gov-compliance.local',
                'role': UserRole.ADMIN,
                'agency': 'Municipal Planning Dept',
                'agency_type': AgencyType.MUNICIPAL,
                'full_name': 'System Administrator',
                'department': 'IT Security',
                'clearance_level': 'Top Secret',
                'created_at': datetime.now(),
                'last_login': None,
                'active': True,
                'mfa_enabled': True
            },
            {
                'username': 'analyst1',
                'password': generate_password_hash('AnalystGov2024!'),
                'email': 'analyst1@gov-compliance.local',
                'role': UserRole.ANALYST,
                'agency': 'County Zoning Board',
                'agency_type': AgencyType.COUNTY,
                'full_name': 'Sarah Johnson',
                'department': 'Zoning Analysis',
                'clearance_level': 'Confidential',
                'created_at': datetime.now(),
                'last_login': None,
                'active': True,
                'mfa_enabled': False
            },
            {
                'username': 'reviewer1',
                'password': generate_password_hash('ReviewGov2024!'),
                'email': 'reviewer1@gov-compliance.local',
                'role': UserRole.REVIEWER,
                'agency': 'State Planning Commission',
                'agency_type': AgencyType.STATE,
                'full_name': 'Michael Chen',
                'department': 'Compliance Review',
                'clearance_level': 'Secret',
                'created_at': datetime.now(),
                'last_login': None,
                'active': True,
                'mfa_enabled': True
            }
        ]
        
        for user in default_users:
            self.users[user['username']] = user
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user with government-grade security"""
        # Check for account lockout
        if self._is_account_locked(username):
            logger.warning(f"Login attempt for locked account: {username}")
            return None
        
        user = self.users.get(username)
        if not user or not user['active']:
            self._record_failed_attempt(username)
            return None
        
        if check_password_hash(user['password'], password):
            # Successful login
            self._clear_login_attempts(username)
            user['last_login'] = datetime.now()
            
            # Generate session token
            session_token = secrets.token_urlsafe(32)
            self.session_tokens[session_token] = {
                'username': username,
                'created_at': datetime.now(),
                'expires_at': datetime.now() + timedelta(seconds=SESSION_TIMEOUT)
            }
            
            # Log audit event
            audit_logger.info(f"User {username} authenticated successfully", 
                            extra={'user': username, 'action': 'LOGIN_SUCCESS'})
            
            return {'user': user, 'session_token': session_token}
        else:
            # Failed login
            self._record_failed_attempt(username)
            audit_logger.warning(f"Failed login attempt for user: {username}",
                               extra={'user': username, 'action': 'LOGIN_FAILURE'})
            return None
    
    def _is_account_locked(self, username: str) -> bool:
        """Check if account is locked due to failed attempts"""
        attempts = self.login_attempts.get(username, [])
        if len(attempts) >= MAX_LOGIN_ATTEMPTS:
            last_attempt = attempts[-1]
            if datetime.now() - last_attempt < timedelta(seconds=LOCKOUT_DURATION):
                return True
        return False
    
    def _record_failed_attempt(self, username: str):
        """Record failed login attempt"""
        if username not in self.login_attempts:
            self.login_attempts[username] = []
        self.login_attempts[username].append(datetime.now())
    
    def _clear_login_attempts(self, username: str):
        """Clear failed login attempts after successful login"""
        if username in self.login_attempts:
            del self.login_attempts[username]
    
    def validate_session(self, token: str) -> Optional[Dict]:
        """Validate session token"""
        session = self.session_tokens.get(token)
        if not session:
            return None
        
        if datetime.now() > session['expires_at']:
            del self.session_tokens[token]
            return None
        
        # Extend session
        session['expires_at'] = datetime.now() + timedelta(seconds=SESSION_TIMEOUT)
        return self.users.get(session['username'])
    
    def logout_user(self, token: str):
        """Logout user and invalidate session"""
        if token in self.session_tokens:
            username = self.session_tokens[token]['username']
            del self.session_tokens[token]
            audit_logger.info(f"User {username} logged out",
                            extra={'user': username, 'action': 'LOGOUT'})
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        return self.users.get(username)
    
    def get_all_users(self) -> List[Dict]:
        """Get all users (admin only)"""
        return list(self.users.values())
    
    def create_user(self, user_data: Dict) -> bool:
        """Create new user (admin only)"""
        if user_data['username'] in self.users:
            return False
        
        user_data['password'] = generate_password_hash(user_data['password'])
        user_data['created_at'] = datetime.now()
        user_data['last_login'] = None
        self.users[user_data['username']] = user_data
        
        audit_logger.info(f"New user created: {user_data['username']}",
                        extra={'user': user_data['username'], 'action': 'USER_CREATED'})
        return True
    
    def deactivate_user(self, username: str) -> bool:
        """Deactivate user account (admin only)"""
        if username in self.users:
            self.users[username]['active'] = False
            audit_logger.info(f"User deactivated: {username}",
                            extra={'user': username, 'action': 'USER_DEACTIVATED'})
            return True
        return False

# Audit Trail System
class AuditTrail:
    """Government compliance audit trail system"""
    
    def __init__(self):
        self.audit_logs = []
    
    def log_analysis(self, user: str, property_id: str, zone_type: str, compliance_score: float):
        """Log compliance analysis event"""
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'user': user,
            'action': 'COMPLIANCE_ANALYSIS',
            'property_id': property_id,
            'zone_type': zone_type,
            'compliance_score': compliance_score,
            'ip_address': request.remote_addr if request else 'unknown'
        }
        self.audit_logs.append(audit_entry)
        audit_logger.info(f"Analysis performed by {user} on {property_id}",
                        extra={'user': user, 'action': 'COMPLIANCE_ANALYSIS', 
                               'property_id': property_id, 'compliance_score': compliance_score})
    
    def log_data_access(self, user: str, data_type: str, record_id: str):
        """Log data access event"""
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'user': user,
            'action': 'DATA_ACCESS',
            'data_type': data_type,
            'record_id': record_id,
            'ip_address': request.remote_addr if request else 'unknown'
        }
        self.audit_logs.append(audit_entry)
    
    def log_export(self, user: str, export_type: str, record_count: int):
        """Log data export event"""
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'user': user,
            'action': 'DATA_EXPORT',
            'export_type': export_type,
            'record_count': record_count,
            'ip_address': request.remote_addr if request else 'unknown'
        }
        self.audit_logs.append(audit_entry)
        audit_logger.info(f"Data export by {user}: {record_count} records",
                        extra={'user': user, 'action': 'DATA_EXPORT', 'record_count': record_count})
    
    def get_audit_trail(self, user: str = None, start_date: datetime = None, end_date: datetime = None) -> List[Dict]:
        """Get filtered audit trail"""
        filtered_logs = self.audit_logs
        
        if user:
            filtered_logs = [log for log in filtered_logs if log['user'] == user]
        
        if start_date:
            filtered_logs = [log for log in filtered_logs 
                           if datetime.fromisoformat(log['timestamp']) >= start_date]
        
        if end_date:
            filtered_logs = [log for log in filtered_logs 
                           if datetime.fromisoformat(log['timestamp']) <= end_date]
        
        return filtered_logs

class ZoneType(Enum):
    """Standard zone types"""
    RESIDENTIAL_SINGLE = "R-1"
    RESIDENTIAL_MULTIPLE = "R-2"
    RESIDENTIAL_HIGH_DENSITY = "R-3"
    COMMERCIAL = "C-1"
    COMMERCIAL_GENERAL = "C-2"
    INDUSTRIAL_LIGHT = "I-1"
    INDUSTRIAL_HEAVY = "I-2"
    MIXED_USE = "MU"
    AGRICULTURAL = "A"

@dataclass
class GeographicCoordinate:
    """Geographic coordinate representation"""
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    altitude: Optional[float] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class PropertyBoundary:
    """Property boundary representation"""
    coordinates: List[Tuple[float, float]]
    area_sqft: float
    perimeter_ft: float
    centroid: GeographicCoordinate
    
    def to_dict(self) -> Dict:
        return {
            'coordinates': self.coordinates,
            'area_sqft': self.area_sqft,
            'perimeter_ft': self.perimeter_ft,
            'centroid': self.centroid.to_dict()
        }

@dataclass
class ZoningRegulation:
    """Zoning regulation representation"""
    zone_type: ZoneType
    max_building_height_ft: float
    max_lot_coverage_percent: float
    min_setback_front: float
    min_setback_rear: float
    min_setback_side: float
    max_far: float  # Floor Area Ratio
    min_parking_spaces: int
    allowed_uses: List[str]
    conditional_uses: List[str]
    prohibited_uses: List[str]
    
    def to_dict(self) -> Dict:
        result = asdict(self)
        result['zone_type'] = self.zone_type.value
        return result

@dataclass
class ComplianceCheck:
    """Individual compliance check result"""
    regulation: str
    status: ComplianceStatus
    actual_value: float
    required_value: float
    variance: float
    details: str
    
    def to_dict(self) -> Dict:
        result = asdict(self)
        result['status'] = self.status.value
        return result

@dataclass
class ComplianceReport:
    """Complete compliance analysis report"""
    property_id: str
    analysis_date: datetime
    coordinates: GeographicCoordinate
    boundary: Optional[PropertyBoundary]
    zone_type: ZoneType
    regulations: ZoningRegulation
    checks: List[ComplianceCheck]
    overall_status: ComplianceStatus
    compliance_score: float
    recommendations: List[str]
    analyst_notes: str
    
    def to_dict(self) -> Dict:
        result = asdict(self)
        result['analysis_date'] = self.analysis_date.isoformat()
        result['coordinates'] = self.coordinates.to_dict()
        if self.boundary:
            result['boundary'] = self.boundary.to_dict()
        result['zone_type'] = self.zone_type.value
        result['regulations'] = self.regulations.to_dict()
        result['checks'] = [check.to_dict() for check in self.checks]
        result['overall_status'] = self.overall_status.value
        return result

class ZoningDatabase:
    """Professional zoning regulations database"""
    
    def __init__(self):
        self.regulations = self._load_regulations()
    
    def _load_regulations(self) -> Dict[ZoneType, ZoningRegulation]:
        """Load comprehensive zoning regulations"""
        return {
            ZoneType.RESIDENTIAL_SINGLE: ZoningRegulation(
                zone_type=ZoneType.RESIDENTIAL_SINGLE,
                max_building_height_ft=35.0,
                max_lot_coverage_percent=40.0,
                min_setback_front=20.0,
                min_setback_rear=25.0,
                min_setback_side=10.0,
                max_far=0.4,
                min_parking_spaces=2,
                allowed_uses=["Single-family dwelling", "Home office", "Accessory structure"],
                conditional_uses=["Home-based business", "Day care"],
                prohibited_uses=["Commercial retail", "Industrial"]
            ),
            ZoneType.RESIDENTIAL_MULTIPLE: ZoningRegulation(
                zone_type=ZoneType.RESIDENTIAL_MULTIPLE,
                max_building_height_ft=45.0,
                max_lot_coverage_percent=50.0,
                min_setback_front=15.0,
                min_setback_rear=20.0,
                min_setback_side=10.0,
                max_far=0.6,
                min_parking_spaces=1.5,
                allowed_uses=["Duplex", "Triplex", "Fourplex"],
                conditional_uses=["Small retail", "Professional office"],
                prohibited_uses=["Industrial", "Large commercial"]
            ),
            ZoneType.COMMERCIAL: ZoningRegulation(
                zone_type=ZoneType.COMMERCIAL,
                max_building_height_ft=60.0,
                max_lot_coverage_percent=80.0,
                min_setback_front=10.0,
                min_setback_rear=15.0,
                min_setback_side=5.0,
                max_far=2.0,
                min_parking_spaces=4,
                allowed_uses=["Retail", "Office", "Restaurant"],
                conditional_uses=["Hotel", "Entertainment"],
                prohibited_uses=["Industrial manufacturing", "Residential"]
            ),
            ZoneType.INDUSTRIAL_LIGHT: ZoningRegulation(
                zone_type=ZoneType.INDUSTRIAL_LIGHT,
                max_building_height_ft=50.0,
                max_lot_coverage_percent=75.0,
                min_setback_front=25.0,
                min_setback_rear=25.0,
                min_setback_side=20.0,
                max_far=1.5,
                min_parking_spaces=5,
                allowed_uses=["Light manufacturing", "Warehouse", "Distribution"],
                conditional_uses=["Research facility", "Technical services"],
                prohibited_uses=["Heavy manufacturing", "Residential"]
            )
        }
    
    def get_regulation(self, zone_type: ZoneType) -> ZoningRegulation:
        """Get zoning regulation by zone type"""
        return self.regulations.get(zone_type, self.regulations[ZoneType.RESIDENTIAL_SINGLE])
    
    def get_zone_types(self) -> List[str]:
        """Get all available zone types"""
        return [zone.value for zone in ZoneType]

class GeocodingService:
    """Professional geocoding service"""
    
    def __init__(self):
        self.user_agent = "Zoning Compliance Checker 1.0 (Enterprise)"
        self.timeout = 10
    
    def geocode_address(self, address: str) -> Optional[GeographicCoordinate]:
        """Convert address to coordinates"""
        try:
            headers = {'User-Agent': self.user_agent}
            params = {
                'q': address,
                'limit': 1,
                'format': 'json'
            }
            
            response = requests.get(
                'https://nominatim.openstreetmap.org/search',
                params=params,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200 and response.json():
                data = response.json()[0]
                return GeographicCoordinate(
                    latitude=float(data['lat']),
                    longitude=float(data['lon']),
                    accuracy=float(data.get('importance', 0.5))
                )
            
        except Exception as e:
            logger.error(f"Geocoding failed for address '{address}': {e}")
        
        return None
    
    def reverse_geocode(self, lat: float, lon: float) -> Optional[str]:
        """Convert coordinates to address"""
        try:
            headers = {'User-Agent': self.user_agent}
            params = {
                'lat': lat,
                'lon': lon,
                'format': 'json'
            }
            
            response = requests.get(
                'https://nominatim.openstreetmap.org/reverse',
                params=params,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('display_name')
                
        except Exception as e:
            logger.error(f"Reverse geocoding failed for coordinates ({lat}, {lon}): {e}")
        
        return None

class ComplianceAnalyzer:
    """Professional compliance analysis engine"""
    
    def __init__(self, zoning_db: ZoningDatabase):
        self.zoning_db = zoning_db
    
    def analyze_compliance(
        self,
        coordinates: GeographicCoordinate,
        zone_type: ZoneType,
        property_data: Dict[str, Any]
    ) -> ComplianceReport:
        """Perform comprehensive compliance analysis"""
        
        regulations = self.zoning_db.get_regulation(zone_type)
        checks = []
        
        # Building height check
        if 'building_height_ft' in property_data:
            height_check = self._check_building_height(
                property_data['building_height_ft'],
                regulations
            )
            checks.append(height_check)
        
        # Lot coverage check
        if 'lot_coverage_percent' in property_data:
            coverage_check = self._check_lot_coverage(
                property_data['lot_coverage_percent'],
                regulations
            )
            checks.append(coverage_check)
        
        # Setback checks
        if 'setbacks' in property_data:
            setbacks = property_data['setbacks']
            setback_checks = self._check_setbacks(setbacks, regulations)
            checks.extend(setback_checks)
        
        # Floor Area Ratio check
        if 'far' in property_data:
            far_check = self._check_far(property_data['far'], regulations)
            checks.append(far_check)
        
        # Parking check
        if 'parking_spaces' in property_data:
            parking_check = self._check_parking(
                property_data['parking_spaces'],
                regulations
            )
            checks.append(parking_check)
        
        # Calculate overall status and score
        overall_status, compliance_score = self._calculate_overall_status(checks)
        recommendations = self._generate_recommendations(checks, regulations)
        
        return ComplianceReport(
            property_id=property_data.get('property_id', f'PROP-{datetime.now().strftime("%Y%m%d%H%M%S")}'),
            analysis_date=datetime.now(),
            coordinates=coordinates,
            boundary=property_data.get('boundary'),
            zone_type=zone_type,
            regulations=regulations,
            checks=checks,
            overall_status=overall_status,
            compliance_score=compliance_score,
            recommendations=recommendations,
            analyst_notes=property_data.get('analyst_notes', '')
        )
    
    def _check_building_height(self, height: float, regulations: ZoningRegulation) -> ComplianceCheck:
        """Check building height compliance"""
        variance = height - regulations.max_building_height_ft
        status = ComplianceStatus.COMPLIANT if variance <= 0 else ComplianceStatus.NON_COMPLIANT
        
        return ComplianceCheck(
            regulation="Building Height",
            status=status,
            actual_value=height,
            required_value=regulations.max_building_height_ft,
            variance=variance,
            details=f"Building height is {height}ft, maximum allowed is {regulations.max_building_height_ft}ft"
        )
    
    def _check_lot_coverage(self, coverage: float, regulations: ZoningRegulation) -> ComplianceCheck:
        """Check lot coverage compliance"""
        variance = coverage - regulations.max_lot_coverage_percent
        status = ComplianceStatus.COMPLIANT if variance <= 0 else ComplianceStatus.NON_COMPLIANT
        
        return ComplianceCheck(
            regulation="Lot Coverage",
            status=status,
            actual_value=coverage,
            required_value=regulations.max_lot_coverage_percent,
            variance=variance,
            details=f"Lot coverage is {coverage}%, maximum allowed is {regulations.max_lot_coverage_percent}%"
        )
    
    def _check_setbacks(self, setbacks: Dict, regulations: ZoningRegulation) -> List[ComplianceCheck]:
        """Check setback compliance"""
        checks = []
        
        setback_types = [
            ('front', regulations.min_setback_front),
            ('rear', regulations.min_setback_rear),
            ('side', regulations.min_setback_side)
        ]
        
        for setback_type, required in setback_types:
            if setback_type in setbacks:
                actual = setbacks[setback_type]
                variance = actual - required
                status = ComplianceStatus.COMPLIANT if variance >= 0 else ComplianceStatus.NON_COMPLIANT
                
                checks.append(ComplianceCheck(
                    regulation=f"{setback_type.capitalize()} Setback",
                    status=status,
                    actual_value=actual,
                    required_value=required,
                    variance=variance,
                    details=f"{setback_type.capitalize()} setback is {actual}ft, minimum required is {required}ft"
                ))
        
        return checks
    
    def _check_far(self, far: float, regulations: ZoningRegulation) -> ComplianceCheck:
        """Check Floor Area Ratio compliance"""
        variance = far - regulations.max_far
        status = ComplianceStatus.COMPLIANT if variance <= 0 else ComplianceStatus.NON_COMPLIANT
        
        return ComplianceCheck(
            regulation="Floor Area Ratio (FAR)",
            status=status,
            actual_value=far,
            required_value=regulations.max_far,
            variance=variance,
            details=f"FAR is {far}, maximum allowed is {regulations.max_far}"
        )
    
    def _check_parking(self, parking: int, regulations: ZoningRegulation) -> ComplianceCheck:
        """Check parking compliance"""
        variance = parking - regulations.min_parking_spaces
        status = ComplianceStatus.COMPLIANT if variance >= 0 else ComplianceStatus.NON_COMPLIANT
        
        return ComplianceCheck(
            regulation="Parking Spaces",
            status=status,
            actual_value=parking,
            required_value=regulations.min_parking_spaces,
            variance=variance,
            details=f"Parking spaces: {parking}, minimum required: {regulations.min_parking_spaces}"
        )
    
    def _calculate_overall_status(self, checks: List[ComplianceCheck]) -> Tuple[ComplianceStatus, float]:
        """Calculate overall compliance status and score"""
        if not checks:
            return ComplianceStatus.INSUFFICIENT_DATA, 0.0
        
        compliant_count = sum(1 for check in checks if check.status == ComplianceStatus.COMPLIANT)
        total_checks = len(checks)
        compliance_score = (compliant_count / total_checks) * 100
        
        if compliance_score >= 95:
            status = ComplianceStatus.COMPLIANT
        elif compliance_score >= 80:
            status = ComplianceStatus.REQUIRES_REVIEW
        else:
            status = ComplianceStatus.NON_COMPLIANT
        
        return status, compliance_score
    
    def _generate_recommendations(self, checks: List[ComplianceCheck], regulations: ZoningRegulation) -> List[str]:
        """Generate compliance recommendations"""
        recommendations = []
        
        for check in checks:
            if check.status == ComplianceStatus.NON_COMPLIANT:
                if "Height" in check.regulation:
                    recommendations.append(f"Reduce building height by {abs(check.variance):.1f}ft or apply for variance")
                elif "Coverage" in check.regulation:
                    recommendations.append(f"Reduce lot coverage by {abs(check.variance):.1f}% or consider site redesign")
                elif "Setback" in check.regulation:
                    recommendations.append(f"Increase {check.regulation.lower()} by {abs(check.variance):.1f}ft")
                elif "FAR" in check.regulation:
                    recommendations.append(f"Reduce building footprint to achieve FAR of {regulations.max_far}")
                elif "Parking" in check.regulation:
                    recommendations.append(f"Add {abs(check.variance):.0f} parking spaces")
        
        return recommendations

# Initialize government-grade Flask application
app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://*.gov", "https://*.mil", "http://localhost:*"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization", "X-API-Key"]
    }
})

# Initialize rate limiter for API protection
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Government security configuration
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', secrets.token_urlsafe(32)),
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Strict',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=1),
    JSON_SORT_KEYS=False,
    JSONIFY_PRETTYPRINT_REGULAR=True,
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max upload
    WTF_CSRF_ENABLED=True
)

# Initialize government services
user_db = UserDatabase()
audit_trail = AuditTrail()
zoning_db = ZoningDatabase()
geocoding_service = GeocodingService()
compliance_analyzer = ComplianceAnalyzer(zoning_db)

# Government-grade security decorators
def require_auth(f):
    """Decorator to require user authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        session_token = request.cookies.get('session_token')
        
        user = None
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            user = user_db.validate_session(token)
        elif session_token:
            user = user_db.validate_session(session_token)
        
        if not user:
            return jsonify({'error': 'Authentication required', 'code': 'AUTH_REQUIRED'}), 401
        
        # Check if user has required role
        request.current_user = user
        return f(*args, **kwargs)
    return decorated_function

def require_role(roles):
    """Decorator to require specific user role(s)"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(request, 'current_user'):
                return jsonify({'error': 'Authentication required'}), 401
            
            user_role = request.current_user.get('role')
            if isinstance(roles, list):
                if user_role not in roles:
                    return jsonify({'error': 'Insufficient permissions'}), 403
            else:
                if user_role != roles:
                    return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def audit_log(action):
    """Decorator to log actions for government compliance"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            result = f(*args, **kwargs)
            
            # Log the action
            user = getattr(request, 'current_user', None)
            username = user.get('username', 'anonymous') if user else 'anonymous'
            
            audit_logger.info(f"Action: {action}", 
                            extra={'user': username, 'action': action})
            
            return result
        return decorated_function
    return decorator

def require_api_key(f):
    """Enhanced decorator to require API key for enterprise/government access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        valid_key = os.environ.get('ENTERPRISE_API_KEY') or os.environ.get('GOVERNMENT_API_KEY')
        
        if valid_key and api_key != valid_key:
            audit_logger.warning(f"Invalid API key attempt from {request.remote_addr}",
                               extra={'user': 'api_client', 'action': 'INVALID_API_KEY'})
            return jsonify({'error': 'Invalid or missing API key', 'code': 'INVALID_API_KEY'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

def validate_json_request(f):
    """Enhanced decorator to validate JSON request with detailed error handling"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_json:
            return jsonify({
                'error': 'Content-Type must be application/json',
                'code': 'INVALID_CONTENT_TYPE'
            }), 400
        
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'error': 'Request body cannot be empty',
                    'code': 'EMPTY_REQUEST_BODY'
                }), 400
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"JSON validation error: {e}")
            return jsonify({
                'error': f'Invalid JSON: {str(e)}',
                'code': 'INVALID_JSON'
            }), 400
    return decorated_function

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
@app.route('/api/auth/login', methods=['POST'])
def login():
    """User authentication"""
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
        else:
            username = request.form.get('username')
            password = request.form.get('password')
        
        if not username or not password:
            if request.is_json:
                return jsonify({
                    'error': 'Username and password required',
                    'code': 'MISSING_CREDENTIALS'
                }), 400
            return render_template('login.html', error='Please enter both username and password')
        
        # Authenticate user
        auth_result = user_db.authenticate_user(username, password)
        
        if auth_result:
            user = auth_result['user']
            session_token = auth_result['session_token']
            
            # Set secure cookie for web sessions
            if not request.is_json:
                response = redirect(url_for('index'))
                response.set_cookie('session_token', session_token, 
                                  httponly=True, secure=False, samesite='Lax',
                                  max_age=SESSION_TIMEOUT)
                return response
            
            # Return JSON for API requests
            return jsonify({
                'success': True,
                'user': {
                    'username': user['username'],
                    'full_name': user['full_name'],
                    'role': user['role'].value,
                    'agency': user['agency']
                },
                'session_token': session_token
            }), 200
        else:
            if request.is_json:
                return jsonify({
                    'error': 'Invalid credentials or account locked',
                    'code': 'AUTH_FAILED'
                }), 401
            return render_template('login.html', error='Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout', methods=['POST', 'GET'])
def logout():
    """User logout"""
    session_token = request.cookies.get('session_token')
    
    if session_token:
        user_db.logout_user(session_token)
    
    response = redirect(url_for('index'))
    response.delete_cookie('session_token')
    return response

@app.route('/api/auth/profile', methods=['GET'])
@require_auth
def get_user_profile():
    """Get current user profile"""
    user = request.current_user
    return jsonify({
        'success': True,
        'user': {
            'username': user['username'],
            'full_name': user['full_name'],
            'email': user['email'],
            'role': user['role'].value,
            'agency': user['agency']
        }
    })

# Public API Routes (No Authentication Required)
@app.route('/api/zones')
def get_zones():
    """Get available zone types"""
    return jsonify({
        'success': True,
        'zones': zoning_db.get_zone_types(),
        'count': len(ZoneType)
    })

@app.route('/api/geocode', methods=['POST'])
@validate_json_request
def geocode_address():
    """Geocode address to coordinates"""
    try:
        data = request.get_json()
        address = data.get('address')
        
        if not address:
            return jsonify({'error': 'Address is required'}), 400
        
        coordinates = geocoding_service.geocode_address(address)
        
        if coordinates:
            return jsonify({
                'success': True,
                'coordinates': coordinates.to_dict(),
                'address': address
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Unable to geocode address'
            }), 404
    
    except Exception as e:
        logger.error(f"Geocoding error: {e}")
        return jsonify({'error': 'Geocoding service unavailable'}), 500

# Enhanced Compliance Analysis with Audit Logging
@app.route('/api/compliance/analyze', methods=['POST'])
@validate_json_request
@limiter.limit("30 per minute")
def analyze_compliance():
    """Perform compliance analysis with audit logging"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['zone_type', 'coordinates']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'error': f'{field} is required',
                    'code': 'MISSING_REQUIRED_FIELD'
                }), 400
        
        # Parse coordinates
        coords_data = data['coordinates']
        coordinates = GeographicCoordinate(
            latitude=coords_data['latitude'],
            longitude=coords_data['longitude']
        )
        
        # Parse zone type
        try:
            zone_type = ZoneType(data['zone_type'])
        except ValueError:
            return jsonify({
                'error': f"Invalid zone type: {data['zone_type']}",
                'code': 'INVALID_ZONE_TYPE'
            }), 400
        
        # Perform analysis
        report = compliance_analyzer.analyze_compliance(coordinates, zone_type, data)
        
        # Log analysis in audit trail (if user is logged in)
        if hasattr(request, 'current_user') and request.current_user:
            audit_trail.log_analysis(
                user=request.current_user['username'],
                property_id=report.property_id,
                zone_type=zone_type.value,
                compliance_score=report.compliance_score
            )
        
        return jsonify({
            'success': True,
            'report': report.to_dict()
        })
    
    except Exception as e:
        logger.error(f"Compliance analysis error: {e}")
        return jsonify({
            'error': 'Analysis service unavailable',
            'code': 'ANALYSIS_ERROR'
        }), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'services': {
            'geocoding': 'operational',
            'compliance_analysis': 'operational',
            'zoning_database': 'operational'
        }
    })

# Enterprise API endpoints
@app.route('/api/v1/compliance/batch', methods=['POST'])
@require_api_key
@validate_json_request
def batch_compliance_analysis():
    """Batch compliance analysis for enterprise clients"""
    try:
        data = request.get_json()
        properties = data.get('properties', [])
        
        if not properties:
            return jsonify({'error': 'No properties provided for batch analysis'}), 400
        
        results = []
        for prop in properties:
            try:
                coords_data = prop['coordinates']
                coordinates = GeographicCoordinate(
                    latitude=coords_data['latitude'],
                    longitude=coords_data['longitude']
                )
                
                zone_type = ZoneType(prop['zone_type'])
                report = compliance_analyzer.analyze_compliance(coordinates, zone_type, prop)
                results.append(report.to_dict())
                
            except Exception as e:
                logger.error(f"Batch analysis error for property: {e}")
                results.append({
                    'property_id': prop.get('property_id', 'unknown'),
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'results': results,
            'processed_count': len(results),
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Batch analysis error: {e}")
        return jsonify({'error': 'Batch analysis service unavailable'}), 500

@app.route('/api/v1/zones/<zone_type>')
@require_api_key
def get_zone_regulations(zone_type):
    """Get detailed regulations for specific zone type"""
    try:
        zone = ZoneType(zone_type)
        regulations = zoning_db.get_regulation(zone)
        
        return jsonify({
            'success': True,
            'regulations': regulations.to_dict(),
            'zone_type': zone_type
        })
    
    except ValueError:
        return jsonify({'error': f'Invalid zone type: {zone_type}'}), 404
    except Exception as e:
        logger.error(f"Zone regulations error: {e}")
        return jsonify({'error': 'Zone data unavailable'}), 500

# Web Interface Routes
@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')

@app.route('/analysis')
def analysis_page():
    """Compliance analysis interface"""
    return render_template('analysis.html')

@app.route('/about')
def about_page():
    """About page"""
    return render_template('about.html')

@app.route('/support')
def support_page():
    """Support page"""
    return render_template('support.html')

@app.route('/documentation')
def documentation_page():
    """Documentation page"""
    return render_template('documentation.html')

if __name__ == '__main__':
    logger.info("Starting Professional Zoning Compliance Checker")
    logger.info("Enterprise-grade solution for geospatial companies and government contractors")
    
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=os.environ.get('FLASK_ENV') == 'development'
    )
