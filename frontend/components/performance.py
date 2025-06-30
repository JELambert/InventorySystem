"""
Performance optimization components for the Home Inventory System.

This module provides caching, lazy loading, and performance monitoring
features for the Streamlit frontend.
"""

import streamlit as st
import time
import psutil
import logging
from typing import Any, Callable, Dict, Optional, List
from functools import wraps
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Monitor and track application performance metrics."""
    
    def __init__(self):
        self.metrics = {}
        self.start_time = time.time()
    
    def start_timer(self, operation: str) -> str:
        """Start timing an operation."""
        timer_id = f"{operation}_{int(time.time() * 1000)}"
        self.metrics[timer_id] = {
            'operation': operation,
            'start_time': time.time(),
            'end_time': None,
            'duration': None
        }
        return timer_id
    
    def end_timer(self, timer_id: str) -> Optional[float]:
        """End timing an operation and return duration."""
        if timer_id in self.metrics:
            end_time = time.time()
            duration = end_time - self.metrics[timer_id]['start_time']
            
            self.metrics[timer_id].update({
                'end_time': end_time,
                'duration': duration
            })
            
            return duration
        return None
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system performance metrics."""
        try:
            process = psutil.Process()
            
            return {
                'memory_usage_mb': process.memory_info().rss / 1024 / 1024,
                'memory_percent': process.memory_percent(),
                'cpu_percent': process.cpu_percent(),
                'uptime_seconds': time.time() - self.start_time,
                'thread_count': process.num_threads(),
                'open_files': len(process.open_files()) if hasattr(process, 'open_files') else 0
            }
        except Exception as e:
            logger.warning(f"Failed to get system metrics: {e}")
            return {}
    
    def get_operation_stats(self) -> Dict[str, Any]:
        """Get statistics for timed operations."""
        operations = {}
        
        for metric in self.metrics.values():
            if metric['duration'] is not None:
                op_name = metric['operation']
                
                if op_name not in operations:
                    operations[op_name] = {
                        'count': 0,
                        'total_duration': 0,
                        'avg_duration': 0,
                        'min_duration': float('inf'),
                        'max_duration': 0
                    }
                
                stats = operations[op_name]
                duration = metric['duration']
                
                stats['count'] += 1
                stats['total_duration'] += duration
                stats['avg_duration'] = stats['total_duration'] / stats['count']
                stats['min_duration'] = min(stats['min_duration'], duration)
                stats['max_duration'] = max(stats['max_duration'], duration)
        
        return operations

# Global performance monitor instance
perf_monitor = PerformanceMonitor()

def timed_operation(operation_name: str):
    """Decorator to time function execution."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            timer_id = perf_monitor.start_timer(operation_name)
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = perf_monitor.end_timer(timer_id)
                if duration and duration > 1.0:  # Log slow operations
                    logger.info(f"Slow operation '{operation_name}': {duration:.2f}s")
        return wrapper
    return decorator

@st.cache_data(ttl=300)  # Cache for 5 minutes
def cached_api_call(endpoint: str, **params) -> Any:
    """Cached API call wrapper."""
    from utils.api_client import APIClient
    
    client = APIClient()
    
    # Map endpoint to client method
    method_map = {
        'get_locations': client.get_locations,
        'get_location_stats': client.get_location_stats,
        'search_locations': client.search_locations
    }
    
    if endpoint in method_map:
        return method_map[endpoint](**params)
    else:
        raise ValueError(f"Unknown endpoint: {endpoint}")

def lazy_load_data(
    load_function: Callable,
    key: str,
    expiry_minutes: int = 5,
    show_loading: bool = True
) -> Any:
    """Lazy load data with session state caching."""
    cache_key = f"lazy_cache_{key}"
    expiry_key = f"lazy_expiry_{key}"
    
    # Check if data exists and is still valid
    if cache_key in st.session_state and expiry_key in st.session_state:
        if datetime.now() < st.session_state[expiry_key]:
            return st.session_state[cache_key]
    
    # Load fresh data
    if show_loading:
        with st.spinner(f"Loading {key}..."):
            data = load_function()
    else:
        data = load_function()
    
    # Cache the data
    st.session_state[cache_key] = data
    st.session_state[expiry_key] = datetime.now() + timedelta(minutes=expiry_minutes)
    
    return data

def paginated_display(
    items: List[Any],
    items_per_page: int = 20,
    display_function: Optional[Callable] = None,
    key_prefix: str = "paginated"
) -> None:
    """Display items with pagination to improve performance."""
    if not items:
        st.info("No items to display")
        return
    
    total_pages = max(1, (len(items) + items_per_page - 1) // items_per_page)
    
    # Page selection
    page_key = f"{key_prefix}_page"
    if page_key not in st.session_state:
        st.session_state[page_key] = 0
    
    current_page = st.session_state[page_key]
    
    # Calculate slice indices
    start_idx = current_page * items_per_page
    end_idx = min(start_idx + items_per_page, len(items))
    page_items = items[start_idx:end_idx]
    
    # Display items
    if display_function:
        for item in page_items:
            display_function(item)
    else:
        # Default display
        for i, item in enumerate(page_items, start_idx + 1):
            st.write(f"{i}. {item}")
    
    # Pagination controls
    if total_pages > 1:
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if st.button("⬅️ Previous", key=f"{key_prefix}_prev", disabled=current_page == 0):
                st.session_state[page_key] = max(0, current_page - 1)
                st.rerun()
        
        with col2:
            st.write(f"Page {current_page + 1} of {total_pages}")
        
        with col3:
            if st.button("Next ➡️", key=f"{key_prefix}_next", disabled=current_page >= total_pages - 1):
                st.session_state[page_key] = min(total_pages - 1, current_page + 1)
                st.rerun()

def optimize_dataframe_display(df, max_rows: int = 1000):
    """Optimize DataFrame display for large datasets."""
    if len(df) > max_rows:
        st.warning(f"Dataset has {len(df)} rows. Showing first {max_rows} for performance.")
        return df.head(max_rows)
    return df

def show_performance_metrics():
    """Display current performance metrics."""
    with st.expander("📊 Performance Metrics"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**System Metrics:**")
            system_metrics = perf_monitor.get_system_metrics()
            
            if system_metrics:
                st.metric("Memory Usage", f"{system_metrics.get('memory_usage_mb', 0):.1f} MB")
                st.metric("CPU Usage", f"{system_metrics.get('cpu_percent', 0):.1f}%")
                st.metric("Uptime", f"{system_metrics.get('uptime_seconds', 0):.0f}s")
        
        with col2:
            st.markdown("**Operation Statistics:**")
            op_stats = perf_monitor.get_operation_stats()
            
            if op_stats:
                for op_name, stats in op_stats.items():
                    st.write(f"**{op_name}:**")
                    st.write(f"- Count: {stats['count']}")
                    st.write(f"- Avg Duration: {stats['avg_duration']:.3f}s")
                    st.write(f"- Max Duration: {stats['max_duration']:.3f}s")
            else:
                st.info("No operation statistics available")

class VirtualizedList:
    """Virtual scrolling for large lists to improve performance."""
    
    def __init__(self, items: List[Any], item_height: int = 50):
        self.items = items
        self.item_height = item_height
        self.container_height = 400  # Default container height
    
    def display(self, render_item: Callable, key: str = "vlist"):
        """Display virtualized list."""
        if not self.items:
            st.info("No items to display")
            return
        
        # Calculate visible range
        items_visible = self.container_height // self.item_height
        total_items = len(self.items)
        
        # Scroll position
        scroll_key = f"{key}_scroll"
        if scroll_key not in st.session_state:
            st.session_state[scroll_key] = 0
        
        scroll_pos = st.session_state[scroll_key]
        
        # Calculate start and end indices
        start_idx = max(0, scroll_pos)
        end_idx = min(total_items, start_idx + items_visible)
        
        # Display scroll controls
        col1, col2, col3 = st.columns([1, 3, 1])
        
        with col1:
            if st.button("⬆️ Up", key=f"{key}_up", disabled=start_idx == 0):
                st.session_state[scroll_key] = max(0, scroll_pos - items_visible)
                st.rerun()
        
        with col2:
            # Slider for position
            if total_items > items_visible:
                max_scroll = total_items - items_visible
                new_pos = st.slider(
                    "Position",
                    0, max_scroll,
                    scroll_pos,
                    key=f"{key}_slider"
                )
                if new_pos != scroll_pos:
                    st.session_state[scroll_key] = new_pos
                    st.rerun()
        
        with col3:
            if st.button("⬇️ Down", key=f"{key}_down", disabled=end_idx >= total_items):
                st.session_state[scroll_key] = min(total_items - items_visible, scroll_pos + items_visible)
                st.rerun()
        
        # Display visible items
        st.markdown(f"Showing items {start_idx + 1}-{end_idx} of {total_items}")
        
        for i in range(start_idx, end_idx):
            render_item(self.items[i], i)

def enable_performance_monitoring():
    """Enable performance monitoring features."""
    if st.checkbox("🔧 Show Performance Info", help="Display performance metrics"):
        show_performance_metrics()

def clear_all_caches():
    """Clear all Streamlit caches."""
    try:
        st.cache_data.clear()
        
        # Clear session state caches
        keys_to_remove = [key for key in st.session_state.keys() if key.startswith('lazy_cache_')]
        for key in keys_to_remove:
            del st.session_state[key]
        
        st.success("All caches cleared successfully!")
        st.rerun()
        
    except Exception as e:
        st.error(f"Failed to clear caches: {e}")

def show_cache_management():
    """Display cache management interface."""
    with st.expander("🗄️ Cache Management"):
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🗑️ Clear All Caches", type="secondary"):
                clear_all_caches()
        
        with col2:
            # Show cache info
            cache_keys = [key for key in st.session_state.keys() if key.startswith('lazy_cache_')]
            st.write(f"Cached items: {len(cache_keys)}")