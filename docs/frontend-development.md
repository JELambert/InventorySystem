# Frontend Development Guide - Home Inventory System

**Last Updated**: 2025-01-26  
**Version**: 1.0  
**Related**: [Main Runbook](../RUNBOOK.md) | [Testing Runbook](./testing-runbook.md)

This guide provides comprehensive procedures for frontend development, maintenance, and troubleshooting in the Home Inventory System.

---

## 🖥️ Frontend Architecture

### Technology Stack

**Core Framework:**
- **Streamlit 1.28.0+** - Main web application framework
- **Python 3.12+** - Programming language
- **Requests 2.31.0+** - HTTP client for API communication

**Data and Visualization:**
- **Pandas 2.0.0+** - Data manipulation and display
- **Plotly 5.17.0+** - Interactive charts and visualizations
- **Pydantic 2.4.0+** - Data validation (matching backend)

**Development Tools:**
- **Git** - Version control
- **VS Code** - Recommended IDE with Streamlit extensions

### Application Structure

```
frontend/
├── app.py                      # Main application entry point
├── requirements.txt            # Python dependencies
├── .streamlit/
│   └── config.toml            # Streamlit configuration
├── pages/                     # Multi-page application
│   ├── 01_📊_Dashboard.py     # System overview and statistics
│   ├── 02_📍_Locations.py     # Location browser and search
│   └── 03_⚙️_Manage.py        # Location CRUD operations
├── utils/                     # Utility modules
│   ├── __init__.py
│   ├── api_client.py          # Backend API communication
│   ├── config.py              # Configuration management
│   └── helpers.py             # UI helpers and utilities
├── components/                # Reusable UI components (future)
└── scripts/                   # Development and verification scripts
    └── verify_frontend_phase2.py
```

---

## 🛠️ Development Workflow

### Setting Up Development Environment

#### Prerequisites
```bash
# Ensure Python 3.12+ is installed
python --version

# Ensure backend is available (for API integration)
curl -I http://127.0.0.1:8000/health
```

#### Environment Setup
```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Verify installation
python scripts/verify_frontend_phase2.py
```

#### Development Server
```bash
# Start development server
streamlit run app.py

# With custom configuration
streamlit run app.py --server.port 8501 --server.address 0.0.0.0

# With debug logging
streamlit run app.py --logger.level=debug
```

### Code Organization Patterns

#### Page Structure Pattern
```python
"""
Standard page structure for Streamlit pages.
"""

import streamlit as st
import logging
from utils.api_client import APIClient
from utils.helpers import show_error, show_success

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Page Name - Home Inventory System",
    page_icon="📊",
    layout="wide"
)

def load_data():
    """Load data for the page."""
    # Data loading logic
    pass

def main():
    """Main page function."""
    st.title("📊 Page Title")
    st.markdown("Page description")
    
    # Page content
    
if __name__ == "__main__":
    main()
```

#### API Client Usage Pattern
```python
from utils.api_client import APIClient, APIError
from utils.helpers import handle_api_error

# Initialize API client
api_client = st.session_state.get('api_client', APIClient())

try:
    # Make API call
    result = api_client.get_locations()
    # Process result
    
except APIError as e:
    handle_api_error(e, "load locations")
except Exception as e:
    st.error(f"Unexpected error: {e}")
```

#### Session State Management
```python
from utils.helpers import SessionManager

# Get or set session state values
current_page = SessionManager.get('current_page', 0)
SessionManager.set('selected_location', location_data)

# Clear session state
SessionManager.clear('temp_data')

# Check existence
if SessionManager.has('user_preferences'):
    # Handle existing data
    pass
```

---

## 🎨 UI/UX Development Guidelines

### Streamlit Component Usage

#### Data Display Components
```python
# Interactive data table
st.data_editor(
    dataframe,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Name": st.column_config.TextColumn("Location Name"),
        "Type": st.column_config.SelectboxColumn("Type", options=types)
    }
)

# Metrics display
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Locations", total_count, delta=change)
```

#### Form Components
```python
# Form with validation
with st.form("location_form"):
    name = st.text_input("Name", max_chars=255)
    location_type = st.selectbox("Type", options)
    
    submitted = st.form_submit_button("Submit")
    if submitted:
        # Validation and processing
        if not name:
            st.error("Name is required")
        else:
            # Process form
            pass
```

#### Visualization Components
```python
import plotly.express as px
import plotly.graph_objects as go

# Pie chart
fig = go.Figure(data=[go.Pie(
    labels=labels,
    values=values,
    hole=0.4
)])
st.plotly_chart(fig, use_container_width=True)

# Bar chart
fig = px.bar(data, x="category", y="count")
st.plotly_chart(fig)
```

### Layout Patterns

#### Multi-Column Layouts
```python
# Three-column layout
col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    # Left sidebar content
    pass

with col2:
    # Main content area
    pass

with col3:
    # Right sidebar content
    pass
```

#### Expandable Sections
```python
# Expandable content
with st.expander("Advanced Options"):
    # Optional content
    advanced_setting = st.checkbox("Enable advanced mode")
```

#### Tabbed Interface
```python
# Tab layout
tab1, tab2, tab3 = st.tabs(["Overview", "Details", "Settings"])

with tab1:
    # Overview content
    pass

with tab2:
    # Details content
    pass
```

### Error Handling and User Feedback

#### Error Display Patterns
```python
from utils.helpers import show_error, show_success, show_warning

# Success feedback
show_success("Location created successfully!")

# Error feedback
show_error("Failed to connect to API", details=str(exception))

# Warning feedback
show_warning("This action cannot be undone")

# Info feedback
st.info("ℹ️ Tip: Use the search box to filter locations")
```

#### Loading States
```python
# Loading spinner
with st.spinner("Loading data..."):
    data = load_data()

# Progress bar
progress_bar = st.progress(0)
for i in range(100):
    # Update progress
    progress_bar.progress(i + 1)
```

---

## 🔌 API Integration Patterns

### API Client Configuration

#### Configuration Management
```python
# utils/config.py
class AppConfig:
    API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))
    API_RETRY_COUNT = int(os.getenv("API_RETRY_COUNT", "3"))
    
    @classmethod
    def get_api_url(cls, endpoint: str) -> str:
        return f"{cls.API_BASE_URL}/api/v1/{endpoint}"
```

#### Error Handling
```python
# Custom exception handling
class APIError(Exception):
    def __init__(self, message, status_code=None, response_data=None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}

# Usage in API client
try:
    response = self.session.get(url, timeout=self.timeout)
    if not response.ok:
        raise APIError(
            message=response.json().get('detail', 'API Error'),
            status_code=response.status_code
        )
except requests.exceptions.ConnectionError:
    raise APIError("Cannot connect to API server")
```

### Data Flow Patterns

#### Page Data Loading
```python
@st.cache_data(ttl=60)  # Cache for 60 seconds
def load_locations(search_term="", location_type=None):
    """Load locations with caching."""
    api_client = APIClient()
    return api_client.get_locations(
        search=search_term,
        type=location_type
    )

# Usage in page
def main():
    search = st.text_input("Search")
    locations = load_locations(search_term=search)
    display_locations(locations)
```

#### Form Submission
```python
def submit_location_form(form_data):
    """Submit location form with error handling."""
    api_client = st.session_state.api_client
    
    try:
        result = api_client.create_location(form_data)
        show_success(f"Created location: {result['name']}")
        st.rerun()  # Refresh page data
        
    except APIError as e:
        if e.status_code == 400:
            show_error("Invalid data", e.message)
        elif e.status_code == 409:
            show_error("Location already exists")
        else:
            show_error("Failed to create location", e.message)
```

---

## 🧪 Testing and Quality Assurance

### Manual Testing Procedures

#### Page Testing Checklist
- [ ] Page loads without errors
- [ ] All UI components render correctly
- [ ] Forms validate input properly
- [ ] API calls work and display data
- [ ] Error states display helpful messages
- [ ] Navigation works between pages
- [ ] Responsive design on different screen sizes

#### API Integration Testing
```python
# Test API connectivity
def test_api_connectivity():
    client = APIClient()
    assert client.health_check(), "API health check failed"
    
    # Test each endpoint
    locations = client.get_locations()
    assert isinstance(locations, list), "Locations should be a list"
```

#### Browser Testing
- **Chrome**: Primary testing browser
- **Firefox**: Secondary browser testing
- **Safari**: macOS compatibility
- **Mobile**: Responsive design verification

### Verification Scripts

#### Frontend Verification
```bash
# Run comprehensive verification
python scripts/verify_frontend_phase2.py

# Expected output: 6/6 tests passing
```

#### Performance Testing
```bash
# Test with large datasets
python -c "
from utils.api_client import APIClient
import time

client = APIClient()
start_time = time.time()
locations = client.get_locations(limit=1000)
end_time = time.time()

print(f'Loaded {len(locations)} locations in {end_time - start_time:.2f}s')
"
```

---

## 🚀 Deployment and Production

### Production Configuration

#### Environment Variables
```bash
# Production API URL
export API_BASE_URL=https://api.yourdomain.com

# Performance settings
export API_TIMEOUT=10
export API_RETRY_COUNT=2

# Security settings
export DEBUG=false
export SHOW_API_ERRORS=false
```

#### Streamlit Configuration
```toml
# .streamlit/config.toml for production
[global]
developmentMode = false

[server]
port = 8501
address = "0.0.0.0"
enableStaticServing = true
enableCORS = false

[browser]
gatherUsageStats = false
showErrorDetails = false

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
```

### Docker Deployment

#### Dockerfile
```dockerfile
FROM python:3.12-slim

WORKDIR /app/frontend

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0"]
```

#### Docker Compose Integration
```yaml
services:
  frontend:
    build: ./frontend
    ports:
      - "8501:8501"
    environment:
      - API_BASE_URL=http://backend:8000
    depends_on:
      - backend
```

---

## 🔧 Troubleshooting Guide

### Common Issues and Solutions

#### Page Loading Issues
```bash
# Clear Streamlit cache
streamlit cache clear

# Check for syntax errors
python scripts/verify_frontend_phase2.py

# Restart with debug logging
streamlit run app.py --logger.level=debug
```

#### API Connection Problems
```bash
# Test API connectivity
curl -I http://127.0.0.1:8000/health

# Check API client configuration
python -c "from utils.config import AppConfig; print(AppConfig.API_BASE_URL)"

# Test from frontend environment
cd frontend
python -c "
from utils.api_client import APIClient
client = APIClient()
print('Connected:', client.health_check())
"
```

#### Performance Issues
```bash
# Enable performance monitoring
export STREAMLIT_PROFILING=true
streamlit run app.py

# Check memory usage
python -c "
import psutil
process = psutil.Process()
print(f'Memory: {process.memory_info().rss / 1024 / 1024:.1f} MB')
"
```

### Debugging Techniques

#### Streamlit Debug Mode
```python
# Add debug information to pages
if st.checkbox("🐛 Debug Mode"):
    st.write("Session State:", st.session_state)
    st.write("Config:", AppConfig.__dict__)
```

#### API Request Logging
```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("api_client")

# Log API requests
logger.debug(f"Making request to {url}")
logger.debug(f"Response: {response.status_code}")
```

---

## 📚 References and Resources

### Documentation Links
- **Streamlit Documentation**: https://docs.streamlit.io/
- **Plotly Documentation**: https://plotly.com/python/
- **Pandas Documentation**: https://pandas.pydata.org/docs/
- **Requests Documentation**: https://requests.readthedocs.io/

### Project-Specific Resources
- **[Main Runbook](../RUNBOOK.md)** - Complete operational guide
- **[Testing Runbook](./testing-runbook.md)** - Testing procedures
- **[API Documentation](http://localhost:8000/docs)** - Backend API reference

### Development Tools
- **VS Code Extensions**:
  - Python
  - Streamlit (community extension)
  - GitLens
  - Python Docstring Generator

### Best Practices Resources
- **Streamlit Best Practices**: https://docs.streamlit.io/knowledge-base
- **Python Code Style**: https://pep8.org/
- **API Design**: https://restfulapi.net/

---

**Last Updated**: 2025-01-26  
**Next Review**: When Phase 3 features are implemented  
**Maintainer**: Frontend development team