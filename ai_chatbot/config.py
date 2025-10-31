import os

# API Configuration
API_BASE_URL = os.getenv('API_BASE_URL', 'https://your-api-domain.com')

# Default settings
DEFAULT_TECHNICIAN_COUNT = int(os.getenv('DEFAULT_TECHNICIAN_COUNT', '5'))