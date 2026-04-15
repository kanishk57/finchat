"""
Vector Store Reference Module
Holds a global reference to the vector store for use across modules
"""

# Global vector store reference
vector_store = None

def set_vector_store(store):
    """Set the vector store reference"""
    global vector_store
    vector_store = store

def get_vector_store():
    """Get the vector store reference"""
    return vector_store