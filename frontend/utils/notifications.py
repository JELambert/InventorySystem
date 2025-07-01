"""
Toast Notification System for Streamlit Frontend.

Provides user-friendly notifications, progress indicators, and 
feedback mechanisms for improved user experience.
"""

import streamlit as st
import time
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from datetime import datetime, timedelta
import hashlib
import uuid


class NotificationType(Enum):
    """Notification types with associated styling and behavior."""
    SUCCESS = "success"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    LOADING = "loading"


class NotificationPriority(Enum):
    """Notification priority levels for display ordering."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


class Notification:
    """Individual notification container."""
    
    def __init__(
        self,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        duration: Optional[float] = None,
        action_label: Optional[str] = None,
        action_callback: Optional[Callable] = None,
        dismissible: bool = True,
        auto_dismiss: bool = True,
        context_data: Optional[Dict[str, Any]] = None
    ):
        self.id = str(uuid.uuid4())[:8]
        self.message = message
        self.type = notification_type
        self.priority = priority
        self.duration = duration or self._get_default_duration()
        self.action_label = action_label
        self.action_callback = action_callback
        self.dismissible = dismissible
        self.auto_dismiss = auto_dismiss
        self.context_data = context_data or {}
        self.created_at = datetime.now()
        self.dismissed = False
        self.shown = False
    
    def _get_default_duration(self) -> float:
        """Get default duration based on notification type."""
        durations = {
            NotificationType.SUCCESS: 3.0,
            NotificationType.INFO: 4.0,
            NotificationType.WARNING: 6.0,
            NotificationType.ERROR: 8.0,
            NotificationType.LOADING: 0  # No auto-dismiss for loading
        }
        return durations.get(self.type, 4.0)
    
    def is_expired(self) -> bool:
        """Check if notification has expired."""
        if not self.auto_dismiss or self.type == NotificationType.LOADING:
            return False
        
        elapsed = (datetime.now() - self.created_at).total_seconds()
        return elapsed > self.duration
    
    def dismiss(self):
        """Dismiss this notification."""
        self.dismissed = True


class NotificationManager:
    """Centralized notification management system."""
    
    def __init__(self):
        self.notifications_key = "_notifications"
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """Initialize session state for notifications."""
        if self.notifications_key not in st.session_state:
            st.session_state[self.notifications_key] = []
    
    def add_notification(
        self,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        duration: Optional[float] = None,
        action_label: Optional[str] = None,
        action_callback: Optional[Callable] = None,
        dismissible: bool = True,
        auto_dismiss: bool = True,
        context_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a notification to the queue.
        
        Returns:
            Notification ID for tracking
        """
        notification = Notification(
            message=message,
            notification_type=notification_type,
            priority=priority,
            duration=duration,
            action_label=action_label,
            action_callback=action_callback,
            dismissible=dismissible,
            auto_dismiss=auto_dismiss,
            context_data=context_data
        )
        
        notifications = st.session_state[self.notifications_key]
        notifications.append(notification)
        
        # Keep only recent notifications to prevent memory issues
        if len(notifications) > 50:
            st.session_state[self.notifications_key] = notifications[-50:]
        
        return notification.id
    
    def success(self, message: str, **kwargs) -> str:
        """Add success notification."""
        return self.add_notification(message, NotificationType.SUCCESS, **kwargs)
    
    def info(self, message: str, **kwargs) -> str:
        """Add info notification."""
        return self.add_notification(message, NotificationType.INFO, **kwargs)
    
    def warning(self, message: str, **kwargs) -> str:
        """Add warning notification."""
        return self.add_notification(message, NotificationType.WARNING, **kwargs)
    
    def error(self, message: str, **kwargs) -> str:
        """Add error notification."""
        return self.add_notification(message, NotificationType.ERROR, **kwargs)
    
    def loading(self, message: str, **kwargs) -> str:
        """Add loading notification."""
        kwargs['auto_dismiss'] = False
        return self.add_notification(message, NotificationType.LOADING, **kwargs)
    
    def dismiss_notification(self, notification_id: str):
        """Dismiss specific notification by ID."""
        notifications = st.session_state[self.notifications_key]
        for notification in notifications:
            if notification.id == notification_id:
                notification.dismiss()
                break
    
    def dismiss_all(self):
        """Dismiss all active notifications."""
        notifications = st.session_state[self.notifications_key]
        for notification in notifications:
            notification.dismiss()
    
    def get_active_notifications(self) -> List[Notification]:
        """Get all active (non-dismissed, non-expired) notifications."""
        notifications = st.session_state[self.notifications_key]
        active = []
        
        for notification in notifications:
            if not notification.dismissed and not notification.is_expired():
                active.append(notification)
        
        # Sort by priority (highest first) then by creation time
        active.sort(key=lambda n: (-n.priority.value, n.created_at))
        return active
    
    def render_notifications(self, container=None):
        """Render all active notifications."""
        if container is None:
            container = st.container()
        
        active_notifications = self.get_active_notifications()
        
        with container:
            for notification in active_notifications:
                self._render_notification(notification)
    
    def _render_notification(self, notification: Notification):
        """Render individual notification."""
        # Create notification container with custom styling
        notification_container = st.container()
        
        with notification_container:
            # Choose appropriate Streamlit method based on type
            if notification.type == NotificationType.SUCCESS:
                st.success(self._format_notification_message(notification))
            elif notification.type == NotificationType.INFO:
                st.info(self._format_notification_message(notification))
            elif notification.type == NotificationType.WARNING:
                st.warning(self._format_notification_message(notification))
            elif notification.type == NotificationType.ERROR:
                st.error(self._format_notification_message(notification))
            elif notification.type == NotificationType.LOADING:
                with st.spinner(notification.message):
                    time.sleep(0.1)  # Brief delay for spinner visibility
            
            # Add action buttons if present
            if notification.action_label and notification.action_callback:
                col1, col2 = st.columns([3, 1])
                with col2:
                    if st.button(notification.action_label, key=f"action_{notification.id}"):
                        try:
                            notification.action_callback()
                        except Exception as e:
                            st.error(f"Action failed: {e}")
            
            # Add dismiss button if dismissible
            if notification.dismissible:
                if st.button("✕", key=f"dismiss_{notification.id}", help="Dismiss notification"):
                    notification.dismiss()
                    st.rerun()
        
        notification.shown = True
    
    def _format_notification_message(self, notification: Notification) -> str:
        """Format notification message with appropriate icons and styling."""
        icons = {
            NotificationType.SUCCESS: "✅",
            NotificationType.INFO: "ℹ️",
            NotificationType.WARNING: "⚠️",
            NotificationType.ERROR: "❌",
            NotificationType.LOADING: "⏳"
        }
        
        icon = icons.get(notification.type, "")
        return f"{icon} {notification.message}"


class ProgressIndicator:
    """Enhanced progress indicator for long-running operations."""
    
    def __init__(self, title: str, total_steps: Optional[int] = None):
        self.title = title
        self.total_steps = total_steps
        self.current_step = 0
        self.start_time = datetime.now()
        self.step_times = []
        self.status_text = ""
        self.notification_manager = NotificationManager()
        self.loading_notification_id = None
        
        # Create UI elements
        self.title_container = st.empty()
        self.progress_bar = st.progress(0.0)
        self.status_container = st.empty()
        self.eta_container = st.empty()
        
        self._update_display()
    
    def update(self, step: Optional[int] = None, status: str = "", increment: bool = True):
        """Update progress indicator."""
        if step is not None:
            self.current_step = step
        elif increment:
            self.current_step += 1
        
        if status:
            self.status_text = status
        
        self.step_times.append(datetime.now())
        self._update_display()
    
    def _update_display(self):
        """Update the visual display of progress."""
        # Calculate progress percentage
        if self.total_steps:
            progress = min(self.current_step / self.total_steps, 1.0)
        else:
            progress = 0.0
        
        # Update title
        if self.total_steps:
            title_text = f"**{self.title}** - Step {self.current_step} of {self.total_steps}"
        else:
            title_text = f"**{self.title}** - Step {self.current_step}"
        
        self.title_container.markdown(title_text)
        
        # Update progress bar
        self.progress_bar.progress(progress)
        
        # Update status
        if self.status_text:
            self.status_container.text(self.status_text)
        
        # Calculate and show ETA
        if len(self.step_times) > 1 and self.total_steps:
            avg_step_time = self._calculate_average_step_time()
            remaining_steps = self.total_steps - self.current_step
            eta_seconds = avg_step_time * remaining_steps
            
            if eta_seconds > 0:
                eta_text = f"⏱️ Estimated time remaining: {self._format_duration(eta_seconds)}"
                self.eta_container.text(eta_text)
    
    def _calculate_average_step_time(self) -> float:
        """Calculate average time per step."""
        if len(self.step_times) < 2:
            return 0.0
        
        time_diffs = []
        for i in range(1, len(self.step_times)):
            diff = (self.step_times[i] - self.step_times[i-1]).total_seconds()
            time_diffs.append(diff)
        
        return sum(time_diffs) / len(time_diffs)
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds:.0f} seconds"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f} minutes"
        else:
            hours = seconds / 3600
            return f"{hours:.1f} hours"
    
    def complete(self, success_message: str = "Operation completed successfully"):
        """Mark progress as complete."""
        if self.total_steps:
            self.progress_bar.progress(1.0)
        
        total_time = (datetime.now() - self.start_time).total_seconds()
        completion_text = f"✅ {success_message} (Completed in {self._format_duration(total_time)})"
        
        self.status_container.success(completion_text)
        self.eta_container.empty()
        
        # Add success notification
        self.notification_manager.success(success_message)
    
    def error(self, error_message: str = "Operation failed"):
        """Mark progress as failed."""
        total_time = (datetime.now() - self.start_time).total_seconds()
        error_text = f"❌ {error_message} (Failed after {self._format_duration(total_time)})"
        
        self.status_container.error(error_text)
        self.eta_container.empty()
        
        # Add error notification
        self.notification_manager.error(error_message)
    
    def cleanup(self):
        """Clean up progress indicator UI elements."""
        self.title_container.empty()
        self.progress_bar.empty()
        self.status_container.empty()
        self.eta_container.empty()


class LoadingStates:
    """Manages loading states for various components."""
    
    def __init__(self):
        self.loading_states_key = "_loading_states"
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """Initialize session state for loading states."""
        if self.loading_states_key not in st.session_state:
            st.session_state[self.loading_states_key] = {}
    
    def set_loading(self, component_id: str, message: str = "Loading..."):
        """Set component loading state."""
        loading_states = st.session_state[self.loading_states_key]
        loading_states[component_id] = {
            'loading': True,
            'message': message,
            'start_time': datetime.now()
        }
    
    def clear_loading(self, component_id: str):
        """Clear component loading state."""
        loading_states = st.session_state[self.loading_states_key]
        if component_id in loading_states:
            del loading_states[component_id]
    
    def is_loading(self, component_id: str) -> bool:
        """Check if component is in loading state."""
        loading_states = st.session_state[self.loading_states_key]
        return loading_states.get(component_id, {}).get('loading', False)
    
    def get_loading_message(self, component_id: str) -> str:
        """Get loading message for component."""
        loading_states = st.session_state[self.loading_states_key]
        return loading_states.get(component_id, {}).get('message', 'Loading...')
    
    def render_loading_placeholder(self, component_id: str, height: int = 100):
        """Render loading placeholder for component."""
        if self.is_loading(component_id):
            message = self.get_loading_message(component_id)
            with st.container():
                st.markdown(
                    f"""
                    <div style="
                        height: {height}px; 
                        display: flex; 
                        align-items: center; 
                        justify-content: center;
                        background-color: #f0f2f6;
                        border-radius: 5px;
                        margin: 10px 0;
                    ">
                        <div style="text-align: center; color: #666;">
                            <div style="font-size: 24px; margin-bottom: 10px;">⏳</div>
                            <div>{message}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            return True
        return False


class SkeletonLoader:
    """Creates skeleton loading placeholders."""
    
    @staticmethod
    def render_skeleton_table(rows: int = 5, columns: int = 4):
        """Render skeleton placeholder for data table."""
        skeleton_html = """
        <div style="animation: pulse 2s infinite;">
        """
        
        # Header row
        skeleton_html += '<div style="display: flex; margin-bottom: 10px;">'
        for _ in range(columns):
            skeleton_html += '''
                <div style="
                    background-color: #e0e0e0; 
                    height: 20px; 
                    margin-right: 10px; 
                    flex: 1;
                    border-radius: 4px;
                "></div>
            '''
        skeleton_html += '</div>'
        
        # Data rows
        for _ in range(rows):
            skeleton_html += '<div style="display: flex; margin-bottom: 8px;">'
            for _ in range(columns):
                skeleton_html += '''
                    <div style="
                        background-color: #f5f5f5; 
                        height: 16px; 
                        margin-right: 10px; 
                        flex: 1;
                        border-radius: 4px;
                    "></div>
                '''
            skeleton_html += '</div>'
        
        skeleton_html += """
        </div>
        <style>
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        </style>
        """
        
        st.markdown(skeleton_html, unsafe_allow_html=True)
    
    @staticmethod
    def render_skeleton_cards(count: int = 3):
        """Render skeleton placeholder for card layouts."""
        cols = st.columns(count)
        
        for i, col in enumerate(cols):
            with col:
                st.markdown(
                    """
                    <div style="
                        background-color: #f5f5f5; 
                        height: 120px; 
                        border-radius: 8px;
                        animation: pulse 2s infinite;
                        margin-bottom: 10px;
                    "></div>
                    <style>
                    @keyframes pulse {
                        0% { opacity: 1; }
                        50% { opacity: 0.5; }
                        100% { opacity: 1; }
                    }
                    </style>
                    """,
                    unsafe_allow_html=True
                )


# Global notification manager instance
notification_manager = NotificationManager()


# Convenience functions for easy access
def show_success(message: str, **kwargs) -> str:
    """Show success notification."""
    return notification_manager.success(message, **kwargs)


def show_info(message: str, **kwargs) -> str:
    """Show info notification."""
    return notification_manager.info(message, **kwargs)


def show_warning(message: str, **kwargs) -> str:
    """Show warning notification."""
    return notification_manager.warning(message, **kwargs)


def show_error(message: str, **kwargs) -> str:
    """Show error notification."""
    return notification_manager.error(message, **kwargs)


def show_loading(message: str, **kwargs) -> str:
    """Show loading notification."""
    return notification_manager.loading(message, **kwargs)


def dismiss_notification(notification_id: str):
    """Dismiss specific notification."""
    notification_manager.dismiss_notification(notification_id)


def dismiss_all_notifications():
    """Dismiss all notifications."""
    notification_manager.dismiss_all()


def render_notifications(container=None):
    """Render all active notifications."""
    notification_manager.render_notifications(container)