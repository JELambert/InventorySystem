"""
Frontend Performance Optimization Utilities.

Provides session state optimization, lazy loading, and frontend caching
for improved user experience and reduced API calls.
"""

import streamlit as st
import time
import hashlib
import json
from typing import Any, Dict, List, Optional, Callable
from functools import wraps
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class SessionStateOptimizer:
    """Optimizes Streamlit session state usage."""
    
    @staticmethod
    def get_or_compute(key: str, compute_func: Callable, ttl_seconds: int = 300, *args, **kwargs) -> Any:
        """
        Get value from session state or compute and cache it.
        
        Args:
            key: Session state key
            compute_func: Function to compute value if not cached
            ttl_seconds: Time to live for cached value
            *args, **kwargs: Arguments for compute_func
            
        Returns:
            Cached or newly computed value
        """
        cache_key = f"{key}_cache"
        timestamp_key = f"{key}_timestamp"
        
        # Check if we have a cached value that's still valid
        if cache_key in st.session_state and timestamp_key in st.session_state:
            cached_time = st.session_state[timestamp_key]
            if datetime.now() - cached_time < timedelta(seconds=ttl_seconds):
                logger.debug(f"Cache hit for {key}")
                return st.session_state[cache_key]
        
        # Compute new value
        logger.debug(f"Computing new value for {key}")
        try:
            value = compute_func(*args, **kwargs)
            st.session_state[cache_key] = value
            st.session_state[timestamp_key] = datetime.now()
            return value
        except Exception as e:
            logger.error(f"Failed to compute value for {key}: {e}")
            # Return cached value if available, even if expired
            if cache_key in st.session_state:
                return st.session_state[cache_key]
            raise
    
    @staticmethod
    def invalidate_cache(pattern: str = None):
        """
        Invalidate cached values in session state.
        
        Args:
            pattern: Pattern to match keys (None to clear all cache)
        """
        keys_to_remove = []
        
        for key in st.session_state.keys():
            if key.endswith('_cache') or key.endswith('_timestamp'):
                if pattern is None or pattern in key:
                    keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del st.session_state[key]
        
        logger.info(f"Invalidated {len(keys_to_remove)} cache entries")
    
    @staticmethod
    def get_cache_stats() -> Dict[str, int]:
        """Get cache statistics from session state."""
        cache_keys = [k for k in st.session_state.keys() if k.endswith('_cache')]
        timestamp_keys = [k for k in st.session_state.keys() if k.endswith('_timestamp')]
        
        # Count active (non-expired) entries
        active_count = 0
        now = datetime.now()
        
        for cache_key in cache_keys:
            timestamp_key = cache_key.replace('_cache', '_timestamp')
            if timestamp_key in st.session_state:
                cached_time = st.session_state[timestamp_key]
                if now - cached_time < timedelta(seconds=300):  # Default TTL
                    active_count += 1
        
        return {
            "total_cache_entries": len(cache_keys),
            "active_entries": active_count,
            "expired_entries": len(cache_keys) - active_count,
            "timestamp_entries": len(timestamp_keys)
        }


class LazyLoader:
    """Implements lazy loading for heavy components."""
    
    @staticmethod
    def paginated_data(
        data: List[Any], 
        page_size: int = 50,
        page_key: str = "page"
    ) -> tuple[List[Any], Dict[str, Any]]:
        """
        Implement pagination for large datasets.
        
        Args:
            data: Full dataset
            page_size: Items per page
            page_key: Session state key for current page
            
        Returns:
            Tuple of (current_page_data, pagination_info)
        """
        if f"{page_key}_current" not in st.session_state:
            st.session_state[f"{page_key}_current"] = 1
        
        current_page = st.session_state[f"{page_key}_current"]
        total_items = len(data)
        total_pages = max(1, (total_items + page_size - 1) // page_size)
        
        # Ensure current page is valid
        if current_page > total_pages:
            current_page = total_pages
            st.session_state[f"{page_key}_current"] = current_page
        
        # Calculate slice
        start_idx = (current_page - 1) * page_size
        end_idx = min(start_idx + page_size, total_items)
        
        current_data = data[start_idx:end_idx]
        
        pagination_info = {
            "current_page": current_page,
            "total_pages": total_pages,
            "total_items": total_items,
            "page_size": page_size,
            "start_idx": start_idx + 1,
            "end_idx": end_idx,
            "has_previous": current_page > 1,
            "has_next": current_page < total_pages
        }
        
        return current_data, pagination_info
    
    @staticmethod
    def create_pagination_controls(pagination_info: Dict[str, Any], page_key: str = "page"):
        """Create pagination UI controls."""
        col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
        
        with col1:
            if st.button("⬅️ First", disabled=not pagination_info["has_previous"]):
                st.session_state[f"{page_key}_current"] = 1
                st.rerun()
        
        with col2:
            if st.button("◀️ Prev", disabled=not pagination_info["has_previous"]):
                st.session_state[f"{page_key}_current"] = max(1, pagination_info["current_page"] - 1)
                st.rerun()
        
        with col3:
            st.write(f"Page {pagination_info['current_page']} of {pagination_info['total_pages']} "
                    f"({pagination_info['start_idx']}-{pagination_info['end_idx']} of {pagination_info['total_items']} items)")
        
        with col4:
            if st.button("▶️ Next", disabled=not pagination_info["has_next"]):
                st.session_state[f"{page_key}_current"] = min(pagination_info["total_pages"], pagination_info["current_page"] + 1)
                st.rerun()
        
        with col5:
            if st.button("➡️ Last", disabled=not pagination_info["has_next"]):
                st.session_state[f"{page_key}_current"] = pagination_info["total_pages"]
                st.rerun()


class ProgressiveLoader:
    """Implements progressive data loading."""
    
    @staticmethod
    def load_with_progress(
        load_func: Callable,
        items: List[Any],
        batch_size: int = 10,
        progress_key: str = "progress"
    ) -> List[Any]:
        """
        Load items progressively with progress indicator.
        
        Args:
            load_func: Function to load each item
            items: List of items to load
            batch_size: Items to load per batch
            progress_key: Session state key for progress
            
        Returns:
            List of loaded items
        """
        if f"{progress_key}_loaded" not in st.session_state:
            st.session_state[f"{progress_key}_loaded"] = []
            st.session_state[f"{progress_key}_index"] = 0
        
        loaded_items = st.session_state[f"{progress_key}_loaded"]
        current_index = st.session_state[f"{progress_key}_index"]
        
        if current_index < len(items):
            # Show progress
            progress_bar = st.progress(current_index / len(items))
            status_text = st.empty()
            
            # Load next batch
            end_index = min(current_index + batch_size, len(items))
            batch_items = items[current_index:end_index]
            
            for i, item in enumerate(batch_items):
                status_text.text(f"Loading item {current_index + i + 1} of {len(items)}")
                try:
                    loaded_item = load_func(item)
                    loaded_items.append(loaded_item)
                except Exception as e:
                    logger.error(f"Failed to load item {item}: {e}")
                    loaded_items.append(None)
            
            # Update progress
            st.session_state[f"{progress_key}_index"] = end_index
            st.session_state[f"{progress_key}_loaded"] = loaded_items
            
            # Clean up UI elements
            progress_bar.empty()
            status_text.empty()
            
            # Trigger rerun if more items to load
            if end_index < len(items):
                time.sleep(0.1)  # Brief pause for better UX
                st.rerun()
        
        return loaded_items


def performance_monitor(func):
    """Decorator to monitor function performance."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Store performance metrics in session state
            if 'performance_metrics' not in st.session_state:
                st.session_state.performance_metrics = {}
            
            func_name = func.__name__
            if func_name not in st.session_state.performance_metrics:
                st.session_state.performance_metrics[func_name] = []
            
            st.session_state.performance_metrics[func_name].append({
                "execution_time": execution_time,
                "timestamp": datetime.now(),
                "success": True
            })
            
            # Keep only last 100 measurements
            if len(st.session_state.performance_metrics[func_name]) > 100:
                st.session_state.performance_metrics[func_name] = \
                    st.session_state.performance_metrics[func_name][-100:]
            
            logger.debug(f"{func_name} executed in {execution_time:.3f}s")
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Record failed execution
            if 'performance_metrics' not in st.session_state:
                st.session_state.performance_metrics = {}
            
            func_name = func.__name__
            if func_name not in st.session_state.performance_metrics:
                st.session_state.performance_metrics[func_name] = []
            
            st.session_state.performance_metrics[func_name].append({
                "execution_time": execution_time,
                "timestamp": datetime.now(),
                "success": False,
                "error": str(e)
            })
            
            logger.error(f"{func_name} failed after {execution_time:.3f}s: {e}")
            raise
    
    return wrapper


def get_performance_report() -> Dict[str, Any]:
    """Get performance report from session state metrics."""
    if 'performance_metrics' not in st.session_state:
        return {"message": "No performance data available"}
    
    metrics = st.session_state.performance_metrics
    report = {}
    
    for func_name, measurements in metrics.items():
        successful_measurements = [m for m in measurements if m["success"]]
        failed_measurements = [m for m in measurements if not m["success"]]
        
        if successful_measurements:
            execution_times = [m["execution_time"] for m in successful_measurements]
            report[func_name] = {
                "total_calls": len(measurements),
                "successful_calls": len(successful_measurements),
                "failed_calls": len(failed_measurements),
                "avg_execution_time": sum(execution_times) / len(execution_times),
                "min_execution_time": min(execution_times),
                "max_execution_time": max(execution_times),
                "success_rate": len(successful_measurements) / len(measurements) * 100
            }
        else:
            report[func_name] = {
                "total_calls": len(measurements),
                "successful_calls": 0,
                "failed_calls": len(failed_measurements),
                "success_rate": 0
            }
    
    return report


def optimize_session_state():
    """Clean up and optimize session state."""
    # Remove expired cache entries
    SessionStateOptimizer.invalidate_cache()
    
    # Limit performance metrics history
    if 'performance_metrics' in st.session_state:
        for func_name in list(st.session_state.performance_metrics.keys()):
            measurements = st.session_state.performance_metrics[func_name]
            if len(measurements) > 50:
                st.session_state.performance_metrics[func_name] = measurements[-50:]
    
    # Clean up old temporary data
    temp_keys = [k for k in st.session_state.keys() if k.startswith('temp_') or k.startswith('modal_')]
    for key in temp_keys:
        if key in st.session_state:
            del st.session_state[key]
    
    logger.info("Session state optimized")


def create_performance_dashboard():
    """Create a performance monitoring dashboard."""
    st.markdown("### 🚀 Performance Dashboard")
    
    # Session state stats
    cache_stats = SessionStateOptimizer.get_cache_stats()
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Cache Entries", cache_stats["total_cache_entries"])
    with col2:
        st.metric("Active Entries", cache_stats["active_entries"])
    with col3:
        st.metric("Expired Entries", cache_stats["expired_entries"])
    with col4:
        total_session_keys = len(st.session_state.keys())
        st.metric("Total Session Keys", total_session_keys)
    
    # Performance report
    if st.button("📊 Get Performance Report"):
        report = get_performance_report()
        if "message" not in report:
            st.markdown("**Function Performance:**")
            for func_name, stats in report.items():
                with st.expander(f"📈 {func_name}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Total Calls", stats["total_calls"])
                        st.metric("Success Rate", f"{stats['success_rate']:.1f}%")
                    with col2:
                        if stats["successful_calls"] > 0:
                            st.metric("Avg Time", f"{stats['avg_execution_time']:.3f}s")
                            st.metric("Max Time", f"{stats['max_execution_time']:.3f}s")
        else:
            st.info(report["message"])
    
    # Cache management
    if st.button("🗑️ Clear Cache"):
        SessionStateOptimizer.invalidate_cache()
        st.success("Cache cleared!")
        st.rerun()
    
    if st.button("🔧 Optimize Session State"):
        optimize_session_state()
        st.success("Session state optimized!")
        st.rerun()