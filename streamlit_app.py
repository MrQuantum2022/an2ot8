import streamlit as st
import pandas as pd
from supabase import create_client, Client
import os
from datetime import datetime
import json
from dotenv import load_dotenv  

# Load environment variables from .env file
load_dotenv()

# Initialize Supabase client
@st.cache_resource
def init_supabase():
    """Initialize Supabase client with credentials from environment variables"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    
    if not url or not key:
        st.error("Missing Supabase credentials. Please add SUPABASE_URL and SUPABASE_ANON_KEY to your environment variables.")
        st.stop()
    
    return create_client(url, key)

supabase: Client = init_supabase()

# Initialize session state
def init_session_state():
    """Initialize all session state variables"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'selected_batch' not in st.session_state:
        st.session_state.selected_batch = None
    if 'current_comment' not in st.session_state:
        st.session_state.current_comment = None
    if 'annotation_saved' not in st.session_state:
        st.session_state.annotation_saved = False
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = True

def authenticate_user():
    """Supabase authentication"""
    st.title("🏷️ Comment Annotation Tool")
    
    # Check if user is already logged in
    try:
        user = supabase.auth.get_user()
        if user and user.user:
            st.session_state.user = user.user
            st.session_state.authenticated = True
            st.rerun()
    except:
        pass
    
    # Show login/signup options
    tab1, tab2 = st.tabs(["Sign In", "Sign Up"])
    
    with tab1:
        with st.form("signin_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            signin_btn = st.form_submit_button("Sign In")
            
            if signin_btn:
                try:
                    response = supabase.auth.sign_in_with_password({
                        "email": email,
                        "password": password
                    })
                    if response.user:
                        st.session_state.user = response.user
                        st.session_state.authenticated = True
                        st.success("Successfully signed in!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Sign in failed: {str(e)}")
    
    with tab2:
        with st.form("signup_form"):
            signup_email = st.text_input("Email", key="signup_email")
            signup_password = st.text_input("Password", type="password", key="signup_password")
            signup_btn = st.form_submit_button("Sign Up")
            
            if signup_btn:
                try:
                    response = supabase.auth.sign_up({
                        "email": signup_email,
                        "password": signup_password
                    })
                    if response.user:
                        st.success("Account created successfully! Please check your email to verify your account.")
                except Exception as e:
                    st.error(f"Sign up failed: {str(e)}")

def get_available_batches():
    """Fetch available batches from Supabase"""
    try:
        response = supabase.table('batches').select('*').execute()
        return response.data
    except Exception as e:
        st.error(f"Error fetching batches: {str(e)}")
        return []

def get_batch_progress(batch_id):
    """Get progress statistics for a batch"""
    try:
        # Get total comments in batch
        total_response = supabase.table('comments').select('id').eq('batch_id', batch_id).execute()
        total_count = len(total_response.data)
        
        # Get annotated comments count
        annotated_response = supabase.table('comments').select('id').eq('batch_id', batch_id).eq('status', 'annotated').execute()
        annotated_count = len(annotated_response.data)
        
        return total_count, annotated_count
    except Exception as e:
        st.error(f"Error getting batch progress: {str(e)}")
        return 0, 0

def get_user_stats(user_email):
    """Get user annotation statistics"""
    try:
        response = supabase.table('annotations').select('*').eq('user_id', user_email).execute()
        total_annotations = len(response.data)
        
        # Count by label
        labels = {}
        for annotation in response.data:
            label = annotation.get('label', 'unknown')
            labels[label] = labels.get(label, 0) + 1
            
        return total_annotations, labels
    except Exception as e:
        st.error(f"Error getting user stats: {str(e)}")
        return 0, {}

def claim_next_comment(batch_id, user_email):
    """Claim the next available comment in a batch using RPC"""
    try:
        response = supabase.rpc('claim_next_comment_in_batch', {
            'p_user_id': user_email,
            'p_batch_id': batch_id
        }).execute()
        
        if response.data and len(response.data) > 0:
            # RPC returns a list, get the first item
            comment_data = response.data[0]
            # Convert to dictionary format expected by the app
            return {
                'id': comment_data.get('comment_id'),
                'comment_text': comment_data.get('comment_text'),
                'original_index': comment_data.get('original_index'),
                'batch_id': comment_data.get('batch_id'),
                'status': comment_data.get('status'),
                'assigned_to': comment_data.get('assigned_to'),
                'claimed_at': comment_data.get('claimed_at'),
                'lock_expires_at': comment_data.get('lock_expires_at'),
                'created_at': comment_data.get('created_at')
            }
        else:
            return None
    except Exception as e:
        st.error(f"Error claiming comment: {str(e)}")
        return None

def save_annotation(comment_id, user_email, label, categories, notes):
    """Save annotation to database"""
    try:
        # Save annotation
        annotation_data = {
            'comment_id': comment_id,
            'user_id': user_email,
            'label': label,
            'categories': categories,
            'notes': notes
        }
        
        supabase.table('annotations').insert(annotation_data).execute()
        
        # Update comment status
        supabase.table('comments').update({'status': 'annotated'}).eq('id', comment_id).execute()
        
        return True
    except Exception as e:
        st.error(f"Error saving annotation: {str(e)}")
        return False

def download_annotations():
    """Generate CSV download for all annotations"""
    try:
        # Fetch all annotations with related comment data
        response = supabase.table('annotations').select('''
            *,
            comments (
                comment_text,
                original_index,
                batches (
                    name
                )
            )
        ''').execute()
        
        if not response.data:
            st.warning("No annotations found to download.")
            return None
            
        # Process data for CSV
        csv_data = []
        for annotation in response.data:
            comment_data = annotation.get('comments', {})
            batch_data = comment_data.get('batches', {}) if comment_data else {}
            
            csv_row = {
                'annotation_id': annotation['id'],
                'comment_id': annotation['comment_id'],
                'user_id': annotation['user_id'],
                'label': annotation['label'],
                'categories': ', '.join(annotation.get('categories', [])),
                'notes': annotation.get('notes', ''),
                'created_at': annotation['created_at'],
                'comment_text': comment_data.get('comment_text', ''),
                'original_index': comment_data.get('original_index', ''),
                'batch_name': batch_data.get('name', '')
            }
            csv_data.append(csv_row)
            
        df = pd.DataFrame(csv_data)
        return df
        
    except Exception as e:
        st.error(f"Error generating CSV: {str(e)}")
        return None

def apply_theme():
    """Apply theme based on user preference"""
    if st.session_state.dark_mode:
        st.markdown("""
        <style>
        .stApp {
            background-color: #0e1117;
            color: #fafafa;
        }
        .stSidebar {
            background-color: #262730;
        }
        .stSelectbox > div > div {
            background-color: #262730;
            color: #fafafa;
        }
        .stTextArea textarea {
            background-color: #262730;
            color: #fafafa;
        }
        .stTextInput input {
            background-color: #262730;
            color: #fafafa;
        }
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
        .stApp {
            background-color: #ffffff;
            color: #262730;
        }
        .stSidebar {
            background-color: #f0f2f6;
        }
        </style>
        """, unsafe_allow_html=True)

def main_app():
    """Main application interface"""
    apply_theme()
    st.title("🏷️ Comment Annotation Tool")
    user_email = st.session_state.user.email if st.session_state.user else "Unknown"
    st.write(f"Welcome, {user_email}!")
    
    # Sidebar with user stats and controls
    with st.sidebar:
        # Theme toggle
        st.subheader("🎨 Theme")
        if st.button("🌙 Dark Mode" if not st.session_state.dark_mode else "☀️ Light Mode"):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()
        
        st.divider()
        
        st.subheader("👤 User Statistics")
        total_annotations, label_stats = get_user_stats(user_email)
        
        st.metric("Total Annotations", total_annotations)
        
        if label_stats:
            st.write("**Labels Distribution:**")
            for label, count in label_stats.items():
                st.write(f"- {label}: {count}")
        
        st.divider()
        
        # Download CSV button
        if st.button("📥 Download All Annotations"):
            df = download_annotations()
            if df is not None:
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"annotations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        st.divider()
        
        if st.button("🚪 Logout"):
            try:
                supabase.auth.sign_out()
            except:
                pass
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    # Main content area
    if not st.session_state.selected_batch:
        # Batch selection
        st.subheader("📁 Select a Batch")
        
        batches = get_available_batches()
        
        if not batches:
            st.warning("No batches available.")
            return
            
        # Display batches with progress
        for batch in batches:
            with st.container():
                col1, col2, col3 = st.columns([3, 2, 1])
                
                with col1:
                    st.write(f"**{batch['name']}**")
                    if batch.get('description'):
                        st.write(batch['description'])
                
                with col2:
                    total_count, annotated_count = get_batch_progress(batch['id'])
                    progress = annotated_count / total_count if total_count > 0 else 0
                    st.progress(progress)
                    st.write(f"{annotated_count}/{total_count} annotated")
                
                with col3:
                    if st.button(f"Select", key=f"select_{batch['id']}"):
                        st.session_state.selected_batch = batch
                        st.session_state.annotation_saved = True  # Trigger comment claim
                        st.rerun()
                
                st.divider()
    
    else:
        # Show selected batch and annotation interface
        batch = st.session_state.selected_batch
        
        # Batch header with progress
        st.subheader(f"📁 {batch['name']}")
        total_count, annotated_count = get_batch_progress(batch['id'])
        progress = annotated_count / total_count if total_count > 0 else 0
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.progress(progress)
            st.write(f"Progress: {annotated_count}/{total_count} comments annotated ({progress:.1%})")
        with col2:
            if st.button("🔄 Change Batch"):
                st.session_state.selected_batch = None
                st.session_state.current_comment = None
                st.rerun()
        
        # Claim next comment if needed
        if st.session_state.annotation_saved or not st.session_state.current_comment:
            with st.spinner("Claiming next comment..."):
                user_email = st.session_state.user.email if st.session_state.user else "unknown"
                comment = claim_next_comment(batch['id'], user_email)
                
                if comment:
                    st.session_state.current_comment = comment
                    st.session_state.annotation_saved = False
                else:
                    st.success("🎉 All comments in this batch have been annotated!")
                    st.balloons()
                    return
        
        # Display current comment and annotation form
        if st.session_state.current_comment:
            comment = st.session_state.current_comment
            
            st.divider()
            st.subheader("📝 Annotate Comment")
            
            # Display comment
            st.text_area(
                "Comment Text",
                value=comment['comment_text'],
                height=150,
                disabled=True,
                key="comment_display"
            )
            
            # Annotation form
            with st.form("annotation_form"):
                # Label selection
                label = st.selectbox(
                    "Label *",
                    options=['hate', 'non-hate'],
                    key="label_select"
                )
                
                # Categories multi-select
                categories = st.multiselect(
                    "Categories",
                    options=['religion', 'race', 'caste', 'regionalism', 'language', 'body shaming', 'disability', 'age', 'gender', 'sexual', 'political', 'none', 'other'],
                    key="categories_select"
                )
                
                # Notes
                notes = st.text_area(
                    "Notes (optional)",
                    key="notes_input"
                )
                
                # Submit buttons
                col1, col2 = st.columns(2)
                with col1:
                    submit = st.form_submit_button("✅ Save Annotation", type="primary")
                with col2:
                    skip = st.form_submit_button("⏭️ Skip Comment")
                
                if submit:
                    user_email = st.session_state.user.email if st.session_state.user else "unknown"
                    if save_annotation(comment['id'], user_email, label, categories, notes):
                        st.success("Annotation saved successfully!")
                        st.session_state.annotation_saved = True
                        st.rerun()
                
                if skip:
                    # Release the comment claim by updating status back to unassigned
                    try:
                        supabase.table('comments').update({
                            'status': 'unassigned',
                            'assigned_to': None,
                            'claimed_at': None,
                            'lock_expires_at': None
                        }).eq('id', comment['id']).execute()
                        
                        st.session_state.annotation_saved = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error skipping comment: {str(e)}")

def main():
    """Main application entry point"""
    st.set_page_config(
        page_title="Comment Annotation Tool",
        page_icon="🏷️",
        layout="wide"
    )
    
    init_session_state()
    
    if not st.session_state.authenticated:
        authenticate_user()
    else:
        main_app()

if __name__ == "__main__":
    main()
