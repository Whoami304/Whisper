from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
# from protection import PasswordProtection
from Crypto.Random import get_random_bytes  

import hashlib # Add this import
 

class AESCipher: # Removed (PasswordProtection) inheritance for simplicity in this fix
    def __init__(self):
        self.key = None
        # self.iv will be set during encryption with a random value
        self.iv = None 

    def _derive_key(self, password: str): # Renamed function
        """Derive a 32-byte hash from the password for AES-256 key."""
        password_bytes = password.encode('utf-8')
        self.key = hashlib.sha256(password_bytes).digest() # Use full 32 bytes for key

    def encrypt(self, plaintext: str) -> bytes:
        """Encrypt with proper error handling and random IV"""
        if not isinstance(plaintext, str):
            raise ValueError("Plaintext must be a string")
        
        if self.key is None:
            raise ValueError("Key not set - call _derive_key first") # Updated message
        
        self.iv = get_random_bytes(16) # Generate random IV for each encryption
        try:
            plaintext_bytes = plaintext.encode('utf-8')
            cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
            padded = pad(plaintext_bytes, AES.block_size)
            ciphertext = cipher.encrypt(padded)
            return self.iv + ciphertext  # Prepend IV for storage
        except Exception as e:
            raise ValueError(f"Encryption failed: {str(e)}")

    def decrypt(self, ciphertext: bytes) -> str:
        """Decrypt with proper error handling"""
        if not isinstance(ciphertext, bytes):
            raise ValueError("Ciphertext must be bytes")
        
        if self.key is None:
            raise ValueError("Key not set - call _derive_key first") # Updated message
        
        if len(ciphertext) < 16:
            raise ValueError("Invalid ciphertext - too short (missing IV or encrypted data).") # More descriptive error
        
        try:
            # Extract IV from first 16 bytes
            iv = ciphertext[:16]
            actual_ciphertext = ciphertext[16:]
            
            cipher = AES.new(self.key, AES.MODE_CBC, iv)
            decrypted = cipher.decrypt(actual_ciphertext)
            unpadded = unpad(decrypted, AES.block_size)
            
            # --- MODIFICATION STARTS HERE ---
            # Check if unpadded is bytes. If so, decode it. Otherwise, return it directly.
            if isinstance(unpadded, bytes):
                return unpadded.decode('utf-8')
            else:
                return unpadded
            # --- MODIFICATION ENDS HERE ---
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")