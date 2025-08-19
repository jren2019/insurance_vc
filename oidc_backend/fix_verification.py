#!/usr/bin/env python3
"""
Script to fix the CBOR verification issue in app_with_db.py
"""
import re

def fix_verification_code():
    """Fix the CBOR handling issue in the verification function"""
    
    # Read the current file
    with open('app_with_db.py', 'r') as f:
        content = f.read()
    
    # Find the problematic namespaces section
    pattern = r'("namespaces":\s*\{[^}]*\})'
    
    # Replace with a safer version
    replacement = '''"namespaces": {
                        str(ns): [
                            str(cbor2.loads(_as_bytes(b)).get("elementIdentifier", "")) 
                            for b in items 
                            if isinstance(b, (bytes, bytearray)) or (hasattr(b, "value") and isinstance(b.value, (bytes, bytearray)))
                        ]
                        for ns, items in ns_map.items()
                    }'''
    
    # Apply the fix
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # Write the fixed content back
    with open('app_with_db.py', 'w') as f:
        f.write(new_content)
    
    print("✅ Fixed CBOR verification issue in app_with_db.py")

if __name__ == "__main__":
    fix_verification_code()
