# Comment Annotation Tool

## Overview

This is a Streamlit-based comment annotation tool designed for collaborative text labeling tasks. The application enables multiple users to annotate comments for hate speech detection and categorization. It connects to Supabase for data storage and implements atomic claiming mechanisms to prevent conflicts when multiple annotators work simultaneously.

The tool focuses on hate speech annotation with binary classification (hate/non-hate/uncertain) and multi-category tagging (religion, race, caste, regionalism, language, other). It includes progress tracking, user management, and data export capabilities.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: Streamlit for rapid web application development
- **Session Management**: Streamlit's built-in session state for user authentication and UI state persistence
- **UI Components**: Form-based interfaces for annotation with progress tracking and sidebar statistics

### Backend Architecture
- **Database**: Supabase (PostgreSQL) for data persistence
- **Authentication**: Simple username-based authentication (extensible to Supabase Auth)
- **Data Access**: Direct Supabase client integration with Python SDK
- **Concurrency Control**: Atomic comment claiming with expiration timestamps to prevent conflicts

### Database Schema
- **Batches Table**: Organizes comments into manageable groups (~2500 comments each)
- **Comments Table**: Stores original text with status tracking and assignment mechanisms
- **Annotations Table**: Records user annotations with labels, categories, and notes
- **Status Management**: Comments progress from 'unassigned' → 'claimed' → 'annotated'

### Key Design Patterns
- **Atomic Operations**: Comment claiming uses database-level locking to ensure thread safety
- **Batch Processing**: Comments are pre-organized into batches for efficient workload distribution
- **Progress Tracking**: Real-time progress bars and statistics for user engagement
- **State Persistence**: Session state maintains user context across interactions

### Data Flow
1. User authenticates with username
2. Selects available batch from list
3. Claims next unassigned comment atomically
4. Annotates with labels, categories, and notes
5. Saves annotation and updates comment status
6. Progress updates automatically

## External Dependencies

### Primary Services
- **Supabase**: PostgreSQL database hosting with real-time capabilities
- **Streamlit**: Web application framework and hosting platform

### Python Libraries
- **supabase-py**: Official Supabase client for database operations
- **pandas**: Data manipulation for CSV export functionality
- **streamlit**: Core web framework

### Configuration Requirements
- **SUPABASE_URL**: Database connection endpoint
- **SUPABASE_ANON_KEY**: Public API key for database access

### Future Extensibility
- Designed to accommodate Supabase Auth for enhanced user management
- Schema supports additional annotation types and user roles
- Export functionality ready for various output formats