"""
Photo capture component for AI-powered item analysis.

Provides camera input and file upload functionality for capturing item photos
that can be analyzed by AI to auto-generate item fields.
"""

import streamlit as st
import io
from PIL import Image
from typing import Optional, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


def validate_image(image_data: bytes, max_size_mb: int = 10) -> Tuple[bool, str]:
    """
    Validate uploaded image data.
    
    Args:
        image_data: Raw image bytes
        max_size_mb: Maximum allowed size in MB
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Check file size
        size_mb = len(image_data) / (1024 * 1024)
        if size_mb > max_size_mb:
            return False, f"Image size ({size_mb:.1f}MB) exceeds maximum allowed size ({max_size_mb}MB)"
        
        # Try to open with PIL to validate format
        image = Image.open(io.BytesIO(image_data))
        
        # Check image dimensions (reasonable limits)
        width, height = image.size
        if width < 100 or height < 100:
            return False, "Image is too small (minimum 100x100 pixels)"
        if width > 4000 or height > 4000:
            return False, "Image is too large (maximum 4000x4000 pixels)"
        
        # Check format
        if image.format not in ['JPEG', 'PNG', 'WEBP']:
            return False, f"Unsupported image format: {image.format}. Please use JPEG, PNG, or WEBP"
        
        return True, ""
        
    except Exception as e:
        return False, f"Invalid image file: {str(e)}"


def optimize_image_for_ai(image_data: bytes, target_size: int = 1024) -> bytes:
    """
    Optimize image for AI analysis by resizing and compressing.
    
    Args:
        image_data: Original image bytes
        target_size: Target max dimension in pixels
        
    Returns:
        Optimized image bytes
    """
    try:
        image = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if necessary (for JPEG compatibility)
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
        
        # Calculate new size maintaining aspect ratio
        width, height = image.size
        if max(width, height) > target_size:
            ratio = target_size / max(width, height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Save optimized image
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=85, optimize=True)
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"Error optimizing image: {e}")
        return image_data  # Return original if optimization fails


def show_photo_capture_interface(key_prefix: str = "photo") -> Optional[Dict[str, Any]]:
    """
    Show photo capture interface with camera input and file upload options.
    
    Args:
        key_prefix: Unique key prefix for widgets
        
    Returns:
        Dictionary with photo data if captured, None otherwise
    """
    
    st.markdown("### 📸 Capture Item Photo")
    st.markdown("Take a photo or upload an image for AI-powered item analysis")
    
    # Photo capture method selection
    capture_method = st.radio(
        "Choose capture method:",
        ["📱 Use Camera", "📁 Upload Photo"],
        key=f"{key_prefix}_capture_method",
        help="Choose how you want to provide the item photo"
    )
    
    photo_data = None
    
    if capture_method == "📱 Use Camera":
        # Camera input
        st.markdown("**📱 Camera Capture**")
        st.info("💡 **Photography Tips**: Ensure good lighting, center the item, include any visible labels or text")
        
        camera_photo = st.camera_input(
            "Take a photo of the item",
            key=f"{key_prefix}_camera",
            help="Position the item clearly in the frame and click to capture"
        )
        
        if camera_photo is not None:
            photo_data = {
                "source": "camera",
                "data": camera_photo.getvalue(),
                "name": f"camera_capture_{key_prefix}.jpg",
                "format": "JPEG"
            }
    
    else:
        # File upload
        st.markdown("**📁 File Upload**")
        st.info("💡 **Supported formats**: JPEG, PNG, WEBP | **Max size**: 10MB")
        
        uploaded_file = st.file_uploader(
            "Choose an image file",
            type=['jpg', 'jpeg', 'png', 'webp'],
            key=f"{key_prefix}_uploader",
            help="Select a clear photo of the item from your device"
        )
        
        if uploaded_file is not None:
            photo_data = {
                "source": "upload",
                "data": uploaded_file.getvalue(),
                "name": uploaded_file.name,
                "format": uploaded_file.type.split('/')[-1].upper()
            }
    
    # Process and display photo if captured
    if photo_data:
        return process_captured_photo(photo_data, key_prefix)
    
    return None


def process_captured_photo(photo_data: Dict[str, Any], key_prefix: str) -> Optional[Dict[str, Any]]:
    """
    Process captured photo with validation, preview, and optimization.
    
    Args:
        photo_data: Photo data dictionary
        key_prefix: Unique key prefix for widgets
        
    Returns:
        Processed photo data if valid, None otherwise
    """
    
    # Validate image
    is_valid, error_message = validate_image(photo_data["data"])
    
    if not is_valid:
        st.error(f"❌ **Image Error**: {error_message}")
        return None
    
    # Show image preview
    st.markdown("**📋 Photo Preview**")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Display image
        image = Image.open(io.BytesIO(photo_data["data"]))
        st.image(image, caption=f"Captured: {photo_data['name']}", use_column_width=True)
        
        # Image info
        width, height = image.size
        size_mb = len(photo_data["data"]) / (1024 * 1024)
        
        st.caption(f"📐 **Dimensions**: {width} × {height} pixels")
        st.caption(f"💾 **Size**: {size_mb:.1f} MB")
        st.caption(f"🖼️ **Format**: {photo_data['format']}")
    
    with col2:
        st.markdown("**🔧 Actions**")
        
        # Retake/reupload option
        if photo_data["source"] == "camera":
            if st.button("📷 Retake Photo", key=f"{key_prefix}_retake"):
                # Clear session state to allow retaking
                if f"{key_prefix}_camera" in st.session_state:
                    del st.session_state[f"{key_prefix}_camera"]
                st.rerun()
        else:
            if st.button("📁 Choose Different Photo", key=f"{key_prefix}_reupload"):
                # Clear session state to allow re-upload
                if f"{key_prefix}_uploader" in st.session_state:
                    del st.session_state[f"{key_prefix}_uploader"]
                st.rerun()
        
        # Image optimization option
        optimize_image = st.checkbox(
            "🚀 Optimize for AI",
            value=True,
            key=f"{key_prefix}_optimize",
            help="Resize and compress image for faster AI analysis"
        )
        
        # Context hints
        st.markdown("**💡 Context Hints** (Optional)")
        location_hint = st.text_input(
            "Location/Category",
            placeholder="e.g., Kitchen, Electronics",
            key=f"{key_prefix}_location_hint",
            help="Help AI understand context"
        )
        
        additional_context = st.text_area(
            "Additional Notes",
            placeholder="e.g., vintage, damaged, new in box",
            key=f"{key_prefix}_context",
            help="Any additional context for better analysis",
            height=80
        )
    
    # Prepare final photo data
    final_data = photo_data.copy()
    
    # Optimize if requested
    if optimize_image:
        with st.spinner("🔄 Optimizing image..."):
            try:
                optimized_data = optimize_image_for_ai(photo_data["data"])
                final_data["data"] = optimized_data
                final_data["optimized"] = True
                
                # Show optimization results
                original_size = len(photo_data["data"]) / (1024 * 1024)
                optimized_size = len(optimized_data) / (1024 * 1024)
                compression_ratio = (1 - optimized_size / original_size) * 100
                
                if compression_ratio > 5:  # Only show if significant compression
                    st.success(f"✅ Optimized: {original_size:.1f}MB → {optimized_size:.1f}MB ({compression_ratio:.0f}% reduction)")
                
            except Exception as e:
                st.warning(f"⚠️ Optimization failed: {str(e)}")
                final_data["optimized"] = False
    else:
        final_data["optimized"] = False
    
    # Add context hints
    final_data["context_hints"] = {
        "location": location_hint.strip() if location_hint else None,
        "additional_context": additional_context.strip() if additional_context else None
    }
    
    return final_data


def show_photo_analysis_progress():
    """Show progress indicator for photo analysis."""
    progress_container = st.container()
    
    with progress_container:
        st.markdown("### 🤖 AI Photo Analysis in Progress")
        
        # Progress steps
        steps = [
            "📤 Uploading image to AI service",
            "🔍 Analyzing image content", 
            "🏷️ Identifying brand and model",
            "💰 Estimating value and condition",
            "📝 Generating description",
            "✅ Finalizing results"
        ]
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Simulate progress steps
        for i, step in enumerate(steps):
            progress = (i + 1) / len(steps)
            progress_bar.progress(progress)
            status_text.text(step)
            
            # Small delay for visual effect
            import time
            time.sleep(0.5)
        
        progress_bar.progress(1.0)
        status_text.success("🎉 Analysis complete!")


def display_photo_analysis_results(analysis_results: Dict[str, Any], photo_data: Dict[str, Any]):
    """
    Display the results of photo analysis with confidence indicators.
    
    Args:
        analysis_results: AI analysis results
        photo_data: Original photo data
    """
    
    st.markdown("### 🎯 AI Photo Analysis Results")
    
    # Show photo alongside results
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("**📸 Analyzed Photo**")
        image = Image.open(io.BytesIO(photo_data["data"]))
        st.image(image, use_column_width=True)
        
        # Show analysis metadata
        metadata = analysis_results.get("metadata", {})
        if metadata:
            st.caption(f"🤖 Model: {metadata.get('model', 'Unknown')}")
            st.caption(f"⏱️ Analysis time: {metadata.get('generation_time', 0):.1f}s")
            st.caption(f"🔗 Confidence: {metadata.get('avg_confidence', 0) * 100:.0f}%")
    
    with col2:
        st.markdown("**🔍 Extracted Information**")
        
        # Display each field with confidence indicator
        confidence_scores = analysis_results.get("confidence_scores", {})
        
        fields_to_display = [
            ("refined_name", "Item Name", "📝"),
            ("brand", "Brand", "🏭"),
            ("model", "Model", "🔧"),
            ("item_type", "Type", "📦"),
            ("estimated_value", "Estimated Value", "💰"),
            ("description", "Description", "📋")
        ]
        
        for field_key, field_label, emoji in fields_to_display:
            value = analysis_results.get(field_key)
            confidence = confidence_scores.get(field_key, 0)
            
            if value:
                # Confidence color coding
                if confidence >= 0.8:
                    confidence_color = "🟢"
                elif confidence >= 0.6:
                    confidence_color = "🟡"
                else:
                    confidence_color = "🔴"
                
                # Format value based on field type
                if field_key == "estimated_value" and isinstance(value, (int, float)):
                    display_value = f"${value:.2f}"
                else:
                    display_value = str(value)
                
                st.markdown(f"{emoji} **{field_label}**: {display_value} {confidence_color} ({confidence:.0%})")
            else:
                st.markdown(f"{emoji} **{field_label}**: *Not detected*")
        
        # Show low confidence warning
        low_confidence_fields = [k for k, v in confidence_scores.items() if v < 0.6]
        if low_confidence_fields:
            st.warning(f"⚠️ Low confidence detected for: {', '.join(low_confidence_fields)}. Please review and edit as needed.")