# Working Cache - Implementation Plans

## Feature Implementation: Image Support Integration

### Overview
Extended the Telegram bot to support image inputs alongside text messages, enabling users to send images for OpenAI Assistant analysis using the proper Assistants API format.

### Implementation Status
- ✅ **Phase 1 Completed**: Telegram Image Handling
- ✅ **Phase 2 Completed**: OpenAI Integration (FIXED)
- ✅ **Phase 3 Completed**: Context Management & File Cleanup (NEW)
- ⏳ **Phase 4 Pending**: System Optimization

## Recent Issue Resolution: Context Conflicts with Sequential Images

### Problem Identified (June 28, 2025)
After implementing basic image support, users reported errors when sending multiple images in sequence:
```
Error while downloading https://prodfsuploads09.blob.core.windows.net/files/file-T1gRdbJ5CVwjbrAosUjNWT...
Assistant run failed: LastError(code='invalid_image_url', message='Error while downloading...')
```

### Root Cause Analysis
- **Thread Persistence**: Each user maintains one persistent OpenAI thread for conversation continuity
- **File Reference Storage**: Thread messages contain `file_id` references to uploaded images
- **Immediate File Cleanup**: Files were deleted immediately after processing to save storage quota
- **Context Loading Issue**: When processing subsequent images, OpenAI Assistant attempts to load the entire thread context, including references to already-deleted files

### Solution Implemented: User-Controlled File Management

**Complete redesign of file lifecycle management:**

1. **File Tracking System**: Added Redis-based tracking of user files with `user_files:{user_id}` keys
2. **Deferred Cleanup**: Removed immediate file deletion after image processing
3. **Reset Command Integration**: Enhanced `/reset` command to delete all user files from OpenAI storage
4. **User Control**: Users can explicitly clear their context and files when needed

### Technical Implementation (June 28, 2025)

#### Enhanced session_manager.py:
```python
# New file tracking functions
def add_user_file(user_id: int, file_id: str)
def get_user_files(user_id: int) -> list[str]
def clear_user_files(user_id: int)

# Async reset with file cleanup
async def reset_thread(user_id: int):
    await delete_user_files_from_openai(user_id)  # Delete from OpenAI
    r.delete(_key(user_id))  # Clear thread_id
```

#### Modified openai_handler.py:
```python
# File tracking integration
add_user_file(user_id, uploaded_file.id)

# Removed immediate cleanup
# await client.files.delete(uploaded_file.id)  # No longer done
logger.debug(f"File {uploaded_file.id} stored for user {user_id}, will be cleaned on /reset")
```

#### Updated main.py:
```python
# Enhanced reset command
await reset_thread(user_id)  # Now async
await update.message.reply_text("🔄 История и файлы сброшены. Новая беседа начата!")
```

### Architecture Benefits

1. **Context Integrity**: No more broken file references in conversation threads
2. **User Control**: Explicit file management through familiar `/reset` command
3. **Storage Efficiency**: Files accumulate but are cleaned when users choose to reset
4. **Error Prevention**: Eliminates sequential image processing errors
5. **Backward Compatibility**: Existing text conversations remain unaffected

### Quality Assurance Results

- **Sequential Images**: ✅ Multiple images in same conversation work perfectly
- **Context Preservation**: ✅ Image context maintained throughout conversation
- **File Cleanup**: ✅ All user files properly deleted on `/reset`
- **Storage Management**: ✅ No storage quota issues with controlled cleanup
- **User Experience**: ✅ Clear feedback on reset operation

## Feature Implementation: Image Support Integration

### Implementation Status
- ✅ **Phase 1 Completed**: Telegram Image Handling
- ✅ **Phase 2 Completed**: OpenAI Integration (FIXED)
- ✅ **Phase 3 Completed**: User Experience Enhancements & Context Management
- ⏳ **Phase 4 Pending**: System Optimization

### Phase 3: User Experience Enhancements ✅ COMPLETED (June 28, 2025)

#### What Was Delivered:
- ✅ Support for image-only messages (no accompanying text required)
- ✅ Support for text + image combinations
- ✅ Maintained conversation context with image messages (FIXED context conflicts)
- ✅ Enhanced user feedback: "🔄 История и файлы сброшены. Новая беседа начата!"
- ✅ File management through `/reset` command integration
- ✅ Context integrity preserved across multiple sequential images

#### Context Management Solution:
- **Problem**: OpenAI thread context included references to deleted files
- **Solution**: User-controlled file cleanup via `/reset` command
- **Benefit**: Users can manage their storage and context explicitly

### Phase 4: System Optimization (Pending)
- Implement file size limits and user quotas
- Add image-specific analytics tracking
- Update token usage calculations for vision requests
- Add comprehensive logging for image processing pipeline
- Performance optimization for concurrent image processing
- Optional: Automated cleanup policies (e.g., delete files older than 30 days)

### Files Modified (June 28, 2025)

**Phase 3 Implementation:**
- `session_manager.py`: Added file tracking system with Redis storage
- `openai_handler.py`: Integrated file tracking, removed immediate cleanup
- `main.py`: Enhanced `/reset` command with async file deletion

**Dependencies:**
- No new dependencies required
- Enhanced Redis schema: `user_files:{user_id}` sets for file tracking

### Key Features Delivered

1. **Context Integrity**: Solved sequential image processing errors
2. **User-Controlled Cleanup**: `/reset` command manages both context and files
3. **Storage Optimization**: Files accumulate but are cleaned on user demand
4. **Error Prevention**: No more broken file references in conversations
5. **Enhanced UX**: Clear feedback on reset operations
6. **Backward Compatibility**: All existing functionality preserved

### Technical Considerations

- **Redis Schema**: New `user_files:{user_id}` sets track file ownership
- **OpenAI Storage**: Files persist until user initiates cleanup
- **Error Recovery**: Graceful handling of already-deleted files during cleanup
- **Performance**: Async file deletion prevents blocking operations
- **Logging**: Comprehensive tracking of file lifecycle events

### User Workflow

1. **Image Upload**: File uploaded to OpenAI, `file_id` tracked in Redis
2. **Image Processing**: File remains available for context continuity
3. **Sequential Images**: All work perfectly within same conversation
4. **Reset Command**: User can clear context and all files with `/reset`
5. **Fresh Start**: New conversation begins with clean context

---

*This document tracks implementation progress and technical decisions for ongoing development.*
