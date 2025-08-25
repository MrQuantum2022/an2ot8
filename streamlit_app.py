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
    # NEW: State for section-based annotation
    if 'assigned_section_number' not in st.session_state:
        st.session_state.assigned_section_number = None
    if 'section_comments' not in st.session_state:
        st.session_state.section_comments = []
    if 'current_comment_index' not in st.session_state:
        st.session_state.current_comment_index = 0
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = True

def authenticate_user():
    """Supabase authentication"""
    st.title("🏷️ Comment Annotation Tool")
    
    try:
        user = supabase.auth.get_user()
        if user and user.user:
            st.session_state.user = user.user
            st.session_state.authenticated = True
            st.rerun()
    except:
        pass
    
    tab1, tab2 = st.tabs(["Sign In", "Sign Up"])
    
    with tab1:
        with st.form("signin_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            signin_btn = st.form_submit_button("Sign In")
            
            if signin_btn:
                try:
                    response = supabase.auth.sign_in_with_password({"email": email, "password": password})
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
                    response = supabase.auth.sign_up({"email": signup_email, "password": signup_password})
                    if response.user:
                        st.success("Account created successfully! Please check your email to verify your account.")
                except Exception as e:
                    st.error(f"Sign up failed: {str(e)}")

def get_available_batches():
    """Fetch available batches from Supabase"""
    try:
        # Now fetching comment_count directly from the table
        response = supabase.table('batches').select('id, name, description, comment_count').execute()
        return response.data
    except Exception as e:
        st.error(f"Error fetching batches: {str(e)}")
        return []

def get_batch_progress(batch_id, total_count):
    """Get annotated comments count for a batch using a dedicated RPC."""
    try:
        # The total count is passed in from the 'batches' table.
        # Call the RPC to get the annotated count.
        response = supabase.rpc('count_annotated_in_batch', {
            'p_batch_id': batch_id
        }).execute()
        
        annotated_count = response.data
        return total_count, annotated_count
    except Exception as e:
        # The original error object might be complex, so we convert it to a string.
        st.error(f"Error getting batch progress: {str(e)}")
        return total_count, 0

def get_user_stats(user_email):
    """Get user annotation statistics"""
    try:
        response = supabase.table('annotations').select('*').eq('user_id', user_email).execute()
        total_annotations = len(response.data)
        labels = {annotation.get('label', 'unknown'): 0 for annotation in response.data}
        for annotation in response.data:
            labels[annotation.get('label', 'unknown')] += 1
        return total_annotations, labels
    except Exception as e:
        st.error(f"Error getting user stats: {str(e)}")
        return 0, {}

# NEW: Function to get or assign a section
def get_or_assign_user_section(batch_id, user_email):
    """Call the RPC to get an already assigned section or assign a new one."""
    try:
        response = supabase.rpc('assign_section_to_user', {
            'p_batch_id': batch_id,
            'p_user_id': user_email
        }).execute()
        if response.data:
            return response.data
        return None
    except Exception as e:
        st.error(f"Error assigning section: {e}")
        return None

# NEW: Function to fetch comments for an assigned section
def get_comments_for_section(batch_id, section_number, total_batch_size):
    """Fetch the comments for a given section number with dynamic section size."""
    try:
        # Calculate the dynamic section size. Using integer division.
        if total_batch_size < 10:
            section_size = total_batch_size
        else:
            section_size = total_batch_size // 10

        # The rest of the logic uses the new dynamic section_size
        start_index = (section_number - 1) * section_size
        end_index = start_index + section_size - 1
        
        response = supabase.table('comment_batches') \
                           .select('comments(*)') \
                           .eq('batch_id', batch_id) \
                           .order('original_index', foreign_table='comments', desc=False) \
                           .range(start_index, end_index) \
                           .execute()
        
        if response.data:
            return [item['comments'] for item in response.data if item.get('comments')]
        return []
    except Exception as e:
        st.error(f"Error fetching comments for section: {e}")
        return []

def save_annotation(comment_id, user_email, label, categories, notes):
    """Save annotation to database"""
    try:
        annotation_data = {'comment_id': comment_id, 'user_id': user_email, 'label': label, 'categories': categories, 'notes': notes}
        supabase.table('annotations').insert(annotation_data).execute()
        supabase.table('comments').update({'status': 'annotated'}).eq('id', comment_id).execute()
        return True
    except Exception as e:
        st.error(f"Error saving annotation: {str(e)}")
        return False

# This function might need updates depending on how you handle downloads now
def download_annotations():
    """Generate CSV download for all annotations"""
    # This might need to be adjusted to join through the new tables if batch_name is required.
    try:
        response = supabase.table('annotations').select('''
            *, comments (comment_text, original_index)
        ''').execute()
        
        if not response.data:
            st.warning("No annotations found to download.")
            return None
            
        csv_data = [{'annotation_id': ann['id'], 'comment_id': ann['comment_id'], 'user_id': ann['user_id'],
                     'label': ann['label'], 'categories': ', '.join(ann.get('categories', [])), 'notes': ann.get('notes', ''),
                     'created_at': ann['created_at'], 'comment_text': ann.get('comments', {}).get('comment_text', '')}
                    for ann in response.data]
        return pd.DataFrame(csv_data)
    except Exception as e:
        st.error(f"Error generating CSV: {str(e)}")
        return None

def apply_theme():
    # Theme application logic remains the same
    pass

def main_app():
    """Main application interface"""
    apply_theme()
    st.title("🏷️ Comment Annotation Tool")
    user_email = st.session_state.user.email
    st.write(f"Welcome, {user_email}!")
    
    with st.sidebar:
        # Sidebar logic remains the same
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
        if st.button("📥 Download All Annotations"):
            df = download_annotations()
            if df is not None:
                csv = df.to_csv(index=False)
                st.download_button("Download CSV", csv, f"annotations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", "text/csv")
        st.divider()
        if st.button("🚪 Logout"):
            try:
                supabase.auth.sign_out()
            except:
                pass
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    # Main content area - REWRITTEN LOGIC
    if not st.session_state.selected_batch:
        st.subheader("📁 Select a Batch")
        batches = get_available_batches()
        if not batches:
            st.warning("No batches available.")
            return
            
        for batch in batches:
            total_count = batch.get('comment_count', 0)
            _, annotated_count = get_batch_progress(batch['id'], total_count)
            progress = annotated_count / total_count if total_count > 0 else 0
            
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.write(f"**{batch['name']}**")
                st.write(batch.get('description', ''))
            with col2:
                st.progress(progress)
                st.write(f"{annotated_count}/{total_count} annotated")
            with col3:
                if st.button("Select", key=f"select_{batch['id']}"):
                    st.session_state.selected_batch = batch
                    # When a batch is selected, we reset section state and rerun to trigger assignment
                    st.session_state.assigned_section_number = None
                    st.session_state.section_comments = []
                    st.session_state.current_comment_index = 0
                    st.rerun()
            st.divider()
    
    else:
        # Annotation interface for a selected batch
        batch = st.session_state.selected_batch
        st.subheader(f"📁 {batch['name']}")
        
        # Assign section and fetch comments if not already done
        if not st.session_state.section_comments:
            with st.spinner("Assigning you a new section..."):
                section_number = get_or_assign_user_section(batch['id'], user_email)
                if section_number is not None:
                    st.session_state.assigned_section_number = section_number
                    
                    # --- CHANGED LINES START ---
                    # We now pass the total count from the batch object to the function.
                    total_comments_in_batch = batch.get('comment_count', 0)
                    comments = get_comments_for_section(batch['id'], section_number, total_comments_in_batch)
                    # --- CHANGED LINES END ---

                    if comments:
                        st.session_state.section_comments = comments
                        st.session_state.current_comment_index = 0
                        st.rerun()
                    else:
                        st.success("🎉 No more comments available in this batch!")
                        return
                else:
                    st.error("Could not assign a section. There may be no comments left.")
                    return

        # Display annotation UI if we have comments for the section
        if st.session_state.section_comments:
            total_in_section = len(st.session_state.section_comments)
            
            # Check if section is completed
            if st.session_state.current_comment_index >= total_in_section:
                st.success(f"🎉 Section {st.session_state.assigned_section_number} complete!")
                st.balloons()
                if st.button("Get Next Section"):
                    st.session_state.assigned_section_number = None
                    st.session_state.section_comments = []
                    st.session_state.current_comment_index = 0
                    st.rerun()
                if st.button("🔄 Change Batch"):
                    st.session_state.selected_batch = None
                    st.session_state.assigned_section_number = None
                    st.session_state.section_comments = []
                    st.session_state.current_comment_index = 0
                    st.rerun()
                return

            # Display progress within the current section
            st.info(f"Annotating Section {st.session_state.assigned_section_number} | Comment {st.session_state.current_comment_index + 1} of {total_in_section}")
            
            current_comment = st.session_state.section_comments[st.session_state.current_comment_index]
            
            st.text_area("Comment Text", value=current_comment['comment_text'], height=150, disabled=True)
            
            with st.form("annotation_form"):
                label = st.selectbox("Label *", options=['hate', 'non-hate'])
                categories = st.multiselect("Categories", options=['religion', 'race', 'caste', 'regionalism', 'language', 'body shaming', 'disability', 'age', 'gender', 'sexual', 'political', 'none', 'other'])
                notes = st.text_area("Notes (optional)")
                
                submit, skip = st.columns(2)
                with submit:
                    if st.form_submit_button("✅ Save Annotation", use_container_width=True, type="primary"):
                        if save_annotation(current_comment['id'], user_email, label, categories, notes):
                            st.success("Annotation saved!")
                            st.session_state.current_comment_index += 1
                            st.rerun()
                with skip:
                    if st.form_submit_button("⏭️ Skip For Now", use_container_width=True):
                        st.session_state.current_comment_index += 1
                        st.rerun()
def main():
    """Main application entry point"""
    st.set_page_config(page_title="Comment Annotation Tool", page_icon="🏷️", layout="wide")
    init_session_state()
    if not st.session_state.authenticated:
        authenticate_user()
    else:
        main_app()

if __name__ == "__main__":
    main()