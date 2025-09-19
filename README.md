An2ot8 - A Collaborative Annotation Tool
An2ot8 is a web-based data annotation tool built with Streamlit and powered by a Supabase backend. It provides a collaborative environment for users to label text data efficiently by organizing comments into batches and assigning sections to individual annotators.
 Features
User Authentication: Secure sign-up and sign-in functionality using Supabase Auth.
Batch Processing: Organize large datasets into manageable "batches" for annotation.
Section-Based Annotation: Batches are automatically divided into smaller sections. Each user is assigned a unique section to work on, preventing duplicate work and enabling parallel annotation.
Progress Tracking:
Real-time progress bars show the completion status of each batch.
The application saves your progress within a section, so you can pick up where you left off.
Intuitive Annotation Interface:
Clean UI for viewing comments.
Select a primary label (e.g., "hate," "non-hate").
Assign multiple categories (e.g., "race," "gender," "political").
Add optional notes for complex cases.
Skip comments to revisit later.
User Dashboard:
View personal annotation statistics, including total annotations and label distribution.
Toggle between dark and light themes for user comfort.
Data Export: Download your annotations as a CSV file at any time.
Tech Stack
Frontend: Streamlit
Backend & Database: Supabase
Data Manipulation: Pandas
Getting Started
Follow these instructions to set up and run the project locally.
Prerequisites
Python 3.8+
A Supabase account and project.
1. Clone the Repository
git clone https://your-repository-url/an2ot8.git
cd an2ot8


2. Install Dependencies
It's recommended to use a virtual environment.
# Create and activate a virtual environment (optional)
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

# Install required packages
pip install streamlit pandas supabase python-dotenv


3. Set up Supabase
Create Tables: In your Supabase project's SQL Editor, set up the following tables:
batches: To store batch information (id, name, description, comment_count).
comments: To store the comments to be annotated (id, comment_text, original_index).
annotations: To store the results (id, comment_id, batch_id, user_id, label, categories, notes).
comment_batches: A linking table to associate comments with batches (batch_id, comment_id).
section_assignments: To track which user is assigned to which section of a batch (batch_id, user_id, assigned_section_number, progress_index).
Create RPC Functions: In the SQL Editor, create the necessary PostgreSQL functions for handling server-side logic. The application uses assign_section_to_user and count_annotated_in_batch. You will need to implement the SQL logic for these based on your table schemas.
4. Environment Variables
Create a .env file in the root directory of the project and add your Supabase credentials.
# .env
SUPABASE_URL="YOUR_SUPABASE_URL"
SUPABASE_SERVICE_ROLE_KEY="YOUR_SUPABASE_SERVICE_ROLE_KEY"


Important: The SUPABASE_SERVICE_ROLE_KEY provides admin-level access to your Supabase project. Keep it secure and never expose it on the client-side.
5. Run the Application
Once the setup is complete, you can run the Streamlit app with the following command:
streamlit run streamlit_app.py


Open your web browser and navigate to the local URL provided (usually http://localhost:8501).
How to Use
Sign Up / Sign In: Create an account or log in with your credentials.
Select a Batch: From the main screen, choose an available batch to start annotating. The progress for each batch is displayed.
Start Annotating: The app will automatically assign you a section of comments.
Read the comment displayed.
Select a label and any relevant categories.
Add notes if necessary.
Click "Save Annotation" to submit or "Skip For Now" to move to the next comment.
Continue or Change:
If you complete a section, you can request the next one.
If you leave and come back, the app will remember your active batch and your progress.
You can switch to a different batch from the main annotation screen.
Monitor & Download: Use the sidebar to track your stats or download your annotation data.
This README provides a template for understanding and setting up the An2ot8 application. You may need to adjust the Supabase schema and RPC functions based on the specific SQL implementation.
