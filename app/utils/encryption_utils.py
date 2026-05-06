"""
Encryption utilities for autopilot agents.
Provides encryption and decryption functionality compatible with the UI encryption scheme.

This module implements AES-256-GCM encryption with the same format used by the UI:
- IV (16 bytes) : Auth Tag (16 bytes) : Encrypted Data
- Uses "github-token" as AAD (Additional Authenticated Data)
- Compatible with TypeScript encryption/decryption in autopilot-ui
"""

import os
import binascii
from typing import Optional
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidTag

from .debug_utils import debug_print_sync as debug_print, error_print_sync as error_print


class EncryptionError(Exception):
    """Exception raised when encryption/decryption operations fail."""
    pass


class EncryptionUtils:
    """Encryption utilities for API key management."""
    
    def __init__(self, agent_name: str = "ENCRYPTION_UTILS"):
        """
        Initialize encryption utilities.
        
        Args:
            agent_name: Name of the agent for debugging purposes
        """
        self.agent_name = agent_name
        self.algorithm = "aes-256-gcm"
        self.aad = b"github-token"  # Additional Authenticated Data
        self._secret_key: Optional[bytes] = None
    
    def _get_secret_key(self) -> bytes:
        """
        Get the encryption secret key from environment variables.
        
        Returns:
            The encryption key as bytes
            
        Raises:
            EncryptionError: If the secret key is not available or invalid
        """
        if self._secret_key is not None:
            return self._secret_key
        
        secret_key_hex = os.environ.get("ENCRYPTION_SECRET_KEY")
        if not secret_key_hex:
            raise EncryptionError(
                "ENCRYPTION_SECRET_KEY environment variable is not set"
            )
        
        try:
            # Convert hex string to bytes
            self._secret_key = binascii.unhexlify(secret_key_hex)
            debug_print(
                f"DEBUG: Loaded encryption key (length: {len(self._secret_key)} bytes)", 
                agent_name=self.agent_name
            )
            
            # Validate key length for AES-256
            if len(self._secret_key) != 32:
                raise EncryptionError(
                    f"Invalid key length: {len(self._secret_key)} bytes. "
                    "AES-256 requires a 32-byte (256-bit) key."
                )
            
            return self._secret_key
            
        except (ValueError, binascii.Error) as e:
            raise EncryptionError(
                f"Invalid ENCRYPTION_SECRET_KEY format. Expected hex string: {e}"
            ) from e
    
    def encrypt_token(self, plaintext: str) -> str:
        """
        Encrypt a token using AES-256-GCM.
        
        This implementation exactly matches the UI's TypeScript encryption:
        - Uses 16-byte IV (same as crypto.randomBytes(16))
        - Sets AAD to "github-token"
        - Returns format: iv:auth_tag:encrypted_data
        
        Args:
            plaintext: The token to encrypt
            
        Returns:
            Encrypted token in format: iv:auth_tag:encrypted_data (all hex-encoded)
            
        Raises:
            EncryptionError: If encryption fails
        """
        try:
            key = self._get_secret_key()
            
            # Generate a random 16-byte IV to match UI (crypto.randomBytes(16))
            iv = os.urandom(16)
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(key), 
                modes.GCM(iv), 
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            
            # Set Additional Authenticated Data (AAD) - same as UI
            encryptor.authenticate_additional_data(self.aad)
            
            # Encrypt the plaintext
            ciphertext = encryptor.update(plaintext.encode('utf-8')) + encryptor.finalize()
            
            # Get the authentication tag
            auth_tag = encryptor.tag
            
            # Format: iv:auth_tag:encrypted_data (all hex-encoded) - same as UI
            encrypted_token = (
                iv.hex() + ":" + 
                auth_tag.hex() + ":" + 
                ciphertext.hex()
            )
            
            debug_print(
                f"DEBUG: Successfully encrypted token (length: {len(encrypted_token)} chars)", 
                agent_name=self.agent_name
            )
            
            return encrypted_token
            
        except Exception as e:
            debug_print(
                f"ERROR: Failed to encrypt token: {str(e)}", 
                agent_name=self.agent_name
            )
            raise EncryptionError(f"Encryption failed: {str(e)}") from e
    
    def decrypt_token(self, encrypted_data: str) -> str:
        """
        Decrypt a token using AES-256-GCM.
        
        This implementation exactly matches the UI's TypeScript decryption:
        - Expects 16-byte IV (same as Node.js crypto)
        - Uses AAD "github-token"
        - Parses format: iv:auth_tag:encrypted_data
        
        Args:
            encrypted_data: The encrypted token in format: iv:auth_tag:encrypted_data
            
        Returns:
            Decrypted plaintext token
            
        Raises:
            EncryptionError: If decryption fails or data is invalid
        """
        try:
            key = self._get_secret_key()
            
            # Split the encrypted data
            parts = encrypted_data.split(":")
            if len(parts) != 3:
                raise EncryptionError(
                    f"Invalid encrypted data format. Expected 3 parts, got {len(parts)}"
                )
            
            # Parse components
            iv_hex, auth_tag_hex, ciphertext_hex = parts
            
            try:
                iv = binascii.unhexlify(iv_hex)
                auth_tag = binascii.unhexlify(auth_tag_hex)
                ciphertext = binascii.unhexlify(ciphertext_hex)
            except binascii.Error as e:
                raise EncryptionError(f"Invalid hex encoding in encrypted data: {e}") from e
            
            # Validate IV length - UI uses 16-byte IV
            if len(iv) != 16:
                raise EncryptionError(f"Invalid IV length: {len(iv)} bytes, expected 16 (UI compatible)")
            
            # Validate auth tag length
            if len(auth_tag) != 16:
                raise EncryptionError(f"Invalid auth tag length: {len(auth_tag)} bytes, expected 16")
            
            debug_print(
                f"DEBUG: Parsed encrypted data - IV: {len(iv)} bytes, Tag: {len(auth_tag)} bytes, Ciphertext: {len(ciphertext)} bytes", 
                agent_name=self.agent_name
            )
            
            # Create cipher with 16-byte IV and auth tag - same as UI
            cipher = Cipher(
                algorithms.AES(key), 
                modes.GCM(iv, auth_tag), 
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            
            # Set Additional Authenticated Data (AAD) - must match what was used during encryption
            decryptor.authenticate_additional_data(self.aad)
            
            # Decrypt the ciphertext
            decrypted_bytes = decryptor.update(ciphertext) + decryptor.finalize()
            decrypted_token = decrypted_bytes.decode('utf-8')
            
            debug_print(
                f"DEBUG: Successfully decrypted token (length: {len(decrypted_token)} chars)", 
                agent_name=self.agent_name
            )
            
            return decrypted_token
            
        except InvalidTag:
            debug_print(
                "ERROR: Authentication tag verification failed - wrong key, corrupted data, or missing AAD", 
                agent_name=self.agent_name
            )
            raise EncryptionError("Authentication failed - encrypted data is invalid or corrupted")
        except UnicodeDecodeError as e:
            debug_print(
                f"ERROR: Failed to decode decrypted data as UTF-8: {e}", 
                agent_name=self.agent_name
            )
            raise EncryptionError("Decrypted data is not valid UTF-8 text") from e
        except Exception as e:
            debug_print(
                f"ERROR: Failed to decrypt token: {str(e)}", 
                agent_name=self.agent_name
            )
            raise EncryptionError(f"Decryption failed: {str(e)}") from e


def create_encryption_utils(agent_name: str) -> EncryptionUtils:
    """
    Create an encryption utilities instance for an agent.
    
    Args:
        agent_name: Name of the agent requesting encryption services
        
    Returns:
        EncryptionUtils instance
    """
    return EncryptionUtils(agent_name)


def encrypt_token(plaintext: str, agent_name: str = "ENCRYPTION_UTILS") -> str:
    """
    Encrypt a token using the default encryption settings.
    
    Args:
        plaintext: The token to encrypt
        agent_name: Name of the agent for debugging purposes
        
    Returns:
        Encrypted token string
        
    Raises:
        EncryptionError: If encryption fails
    """
    encryption_utils = create_encryption_utils(agent_name)
    return encryption_utils.encrypt_token(plaintext)


def decrypt_token(encrypted_data: str, agent_name: str = "ENCRYPTION_UTILS") -> str:
    """
    Decrypt a token using the default encryption settings.
    
    Args:
        encrypted_data: The encrypted token data
        agent_name: Name of the agent for debugging purposes
        
    Returns:
        Decrypted plaintext token
        
    Raises:
        EncryptionError: If decryption fails
    """
    encryption_utils = create_encryption_utils(agent_name)
    return encryption_utils.decrypt_token(encrypted_data)


def is_encryption_available(agent_name: str = "ENCRYPTION_UTILS") -> bool:
    """
    Check if encryption is available and properly configured.
    
    Args:
        agent_name: Name of the agent checking encryption availability
        
    Returns:
        True if encryption is available, False otherwise
    """
    try:
        encryption_utils = create_encryption_utils(agent_name)
        encryption_utils._get_secret_key()
        return True
    except Exception as e:
        debug_print(
            f"DEBUG: Encryption availability check failed: {e}", 
            agent_name=agent_name
        )
        return False
