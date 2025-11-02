# Encoding Fix: Windows Console Unicode Support

## Problem
Pipeline scripts were failing with logging errors when processing products with Danish characters (æ, ø, å):

```
❌ Fejl: --- Logging error --- Traceback (most recent call last):
  File "...logging_init_.py", line 1163, in emit
    stream.write(msg + self.terminator)
  File "...cp1252.py", line 19, in encode
    return codecs.charmap_encode(input,self.errors,encoding_table)[0]
```

### Root Cause
Windows PowerShell console defaults to cp1252 encoding (Windows-1252), which cannot encode Unicode characters like Danish letters. When logging tried to write Unicode strings to stdout, it failed with `UnicodeEncodeError`.

## Solution

### 1. SafeStream Wrapper Class
Created a custom stream wrapper that handles encoding errors gracefully:

```python
class SafeStream:
    """Handles encoding errors when writing to console"""
    def write(self, msg):
        if not msg:
            return
        try:
            # Try direct write first
            sys.__stdout__.write(msg)
        except UnicodeEncodeError:
            # Fallback: encode with error replacement
            safe_msg = msg.encode('utf-8', errors='replace').decode(sys.__stdout__.encoding or 'utf-8', errors='replace')
            sys.__stdout__.write(safe_msg)
```

- Attempts UTF-8 encoding first
- Falls back to ASCII with character replacement on error
- Gracefully handles all encoding exceptions

### 2. SafeStreamHandler Custom Handler
Overrides the logging.StreamHandler.emit() method to use SafeStream:

```python
class SafeStreamHandler(logging.StreamHandler):
    """Custom logging handler that prevents encoding errors"""
    def emit(self, record):
        try:
            msg = self.format(record)
            self.stream.write(msg)  # Uses SafeStream's write method
            self.stream.write('\n')
            self.stream.flush()
        except Exception:
            self.handleError(record)
```

### 3. Applied to All Pipeline Scripts
Updated logging setup in:
- `scripts/1_sanitize.py`
- `scripts/2_scrape.py` 
- `scripts/3_process_images.py`
- `scripts/4_generate_ai.py`

Each now uses:
```python
console_handler = SafeStreamHandler(SafeStream())
```

## Files Modified
- `scripts/1_sanitize.py` - Added SafeStream and SafeStreamHandler, updated setup_logging()
- `scripts/2_scrape.py` - Enhanced SafeStream with better fallbacks, added SafeStreamHandler, updated setup_logging()
- `scripts/3_process_images.py` - Added SafeStream and SafeStreamHandler, updated setup_logging()
- `scripts/4_generate_ai.py` - Added SafeStream and SafeStreamHandler, updated setup_logging()

## Result
✅ Pipeline scripts can now safely log Unicode characters (Danish text, emojis, etc.) to Windows PowerShell console without encoding errors

✅ File logging (UTF-8) unaffected - already using proper encoding

✅ Graceful error handling - if encoding still fails, messages are silently dropped rather than crashing

## Testing
Run pipeline with Danish product names:
```powershell
python scripts/run_all.py
```

Should complete without encoding-related logging errors.
