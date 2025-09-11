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
# In streamlit_app.py
print("--- Environment Check ---")
key_loaded = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
if key_loaded:
    print("✅ Service Key was found.")
else:
    print("❌ Service Key NOT found. The .env file was likely not loaded correctly.")
print("-----------------------")

def init_supabase():
    """Initialize Supabase client with credentials from environment variables"""
    url = os.getenv("SUPABASE_URL")
    # WARNING: Use the Service Role Key for this feature.
    # Keep this key secure and never expose it in client-side code.
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") 
    
    if not url or not key:
        st.error("Missing Supabase credentials. Please add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to your environment variables.")
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
    st.title("💻An2ot8")

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
                        st.success("Account created successfully!")
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
# Add these new functions anywhere before main_app()

def get_user_active_batch(user_id):
    """Fetches the active_batch_id from a user's metadata."""
    try:
        user_data = supabase.auth.admin.get_user_by_id(user_id).user
        return user_data.user_metadata.get('active_batch_id')
    except Exception as e:
        st.error(f"Error fetching user metadata: {e}")
        return None

def set_user_active_batch(user_id, batch_id):
    """Sets the active_batch_id in a user's metadata."""
    try:
        supabase.auth.admin.update_user_by_id(
            user_id,
            {'user_metadata': {'active_batch_id': batch_id}}
        )
    except Exception as e:
        st.error(f"Error setting active batch: {e}")
def update_section_progress(batch_id, user_id, new_index):
    """Updates the user's progress index for their assigned section."""
    try:
        supabase.table('section_assignments') \
                .update({'progress_index': new_index}) \
                .eq('batch_id', batch_id) \
                .eq('user_id', user_id) \
                .execute()
    except Exception as e:
        st.warning(f"Could not save progress: {e}")
def clear_user_active_batch(user_id):
    """Clears the active_batch_id from a user's metadata."""
    try:
        supabase.auth.admin.update_user_by_id(
            user_id,
            {'user_metadata': {'active_batch_id': None}}
        )
    except Exception as e:
        st.error(f"Error clearing active batch: {e}")

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
# The new function signature now includes batch_id
def save_annotation(comment_id, batch_id, user_email, label, categories, notes):
    """Save annotation to database, now including the batch_id."""
    try:
        annotation_data = {
            'comment_id': comment_id,
            'batch_id': batch_id, # Add batch_id to the data
            'user_id': user_email,
            'label': label,
            'categories': categories,
            'notes': notes
        }
        supabase.table('annotations').insert(annotation_data).execute()
        
        # We no longer update the comment's status, as it can be annotated in other batches.
        # supabase.table('comments').update({'status': 'annotated'}).eq('id', comment_id).execute()
        
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
    st.title("💻An2ot8")
    user = st.session_state.user
    st.write(f"Welcome, {user.email}!")
    
    with st.sidebar:
        # Sidebar logic...
        st.subheader("🎨 Theme")
        if st.button("🌙 Dark Mode" if not st.session_state.dark_mode else "☀️ Light Mode"):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()
        st.divider()
        st.subheader("👤 User Statistics")
        total_annotations, label_stats = get_user_stats(user.email)
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

    if not st.session_state.get('selected_batch'):
        active_batch_id = get_user_active_batch(user.id)
        if active_batch_id:
            response = supabase.table('batches').select('*').eq('id', active_batch_id).single().execute()
            st.session_state.selected_batch = response.data
            st.rerun()

    if not st.session_state.selected_batch:
        st.subheader("📁 Select a Batch")
        # Batch selection logic...
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
                    st.session_state.assigned_section_number = None
                    st.session_state.section_comments = []
                    st.session_state.current_comment_index = 0
                    st.rerun()
            st.divider()
    
    else:
        batch = st.session_state.selected_batch
        st.subheader(f"📁 {batch['name']}")
        
        if not st.session_state.section_comments:
            with st.spinner("Loading your section..."):
                # CHANGED: RPC now returns a list with a dictionary
                response = supabase.rpc('assign_section_to_user', {'p_batch_id': batch['id'], 'p_user_id': user.email}).execute()
                
                if response.data:
                    assignment = response.data[0]
                    section_number = assignment['assigned_section_number']
                    saved_progress = assignment['saved_progress_index']

                    if not get_user_active_batch(user.id):
                        set_user_active_batch(user.id, batch['id'])
                    
                    st.session_state.assigned_section_number = section_number
                    total_comments_in_batch = batch.get('comment_count', 0)
                    comments = get_comments_for_section(batch['id'], section_number, total_comments_in_batch)

                    if comments:
                        st.session_state.section_comments = comments
                        # CHANGED: Set the comment index from our saved progress
                        st.session_state.current_comment_index = saved_progress
                        st.rerun()
                    else:
                        st.success("🎉 Batch Complete! You can now select another batch.")
                        clear_user_active_batch(user.id)
                        st.session_state.selected_batch = None
                        st.rerun()
                else:
                    st.success("🎉 Batch Complete! You can now select another batch.")
                    clear_user_active_batch(user.id)
                    st.session_state.selected_batch = None
                    st.rerun()

        if st.session_state.section_comments:
            total_in_section = len(st.session_state.section_comments)
            
            if st.session_state.current_comment_index >= total_in_section:
                st.success(f"🎉 Section {st.session_state.assigned_section_number} complete!")
                st.balloons()
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Get Next Section", use_container_width=True):
                        st.session_state.assigned_section_number = None
                        st.session_state.section_comments = []
                        st.session_state.current_comment_index = 0
                        st.rerun()
                with col2:
                    if st.button("🔄 Change Batch", use_container_width=True):
                        clear_user_active_batch(user.id) # Also clear active batch here
                        st.session_state.selected_batch = None
                        st.session_state.assigned_section_number = None
                        st.session_state.section_comments = []
                        st.session_state.current_comment_index = 0
                        st.rerun()
                return

            st.info(f"Annotating Section {st.session_state.assigned_section_number} | Comment {st.session_state.current_comment_index + 1} of {total_in_section}")
            
            current_comment = st.session_state.section_comments[st.session_state.current_comment_index]
            
            st.text_area("Comment Text", value=current_comment['comment_text'], height=150, disabled=True)
            
            with st.form("annotation_form"):
                label = st.selectbox("Label *", options=['hate', 'non-hate'])
                categories = st.multiselect("Categories", options=['none','religion', 'race', 'caste', 'regionalism', 'language', 'body shaming', 'disability', 'age', 'gender', 'sexual', 'political', 'privacy', 'cyber bully'])
                notes = st.text_area("Notes (optional)")
                
                submit, skip = st.columns(2)
                with submit:
                    if st.form_submit_button("✅ Save Annotation", use_container_width=True, type="primary"):
                        if save_annotation(current_comment['id'], batch['id'], user.email, label, categories, notes):
                            st.success("Annotation saved!")
                            # CHANGED: Update progress in the database
                            new_index = st.session_state.current_comment_index + 1
                            update_section_progress(batch['id'], user.email, new_index)
                            st.session_state.current_comment_index = new_index
                            st.rerun()
                with skip:
                    if st.form_submit_button("⏭️ Skip For Now", use_container_width=True):
                        # CHANGED: Also update progress on skip
                        new_index = st.session_state.current_comment_index + 1
                        update_section_progress(batch['id'], user.email, new_index)
                        st.session_state.current_comment_index = new_index
                        st.rerun()
def main():
    """Main application entry point"""
    st.set_page_config(page_title="An2ot8", page_icon="💻", layout="wide")
    init_session_state()
    if not st.session_state.authenticated:
        authenticate_user()
    else:
        main_app()

if __name__ == "__main__":
    main()
